<template>
  <Transition name="action-overlay">
    <div v-if="isVisible" class="night-action-overlay" :class="actionClass">
      <!-- 背景粒子效果 -->
      <div class="particles">
        <div v-for="i in 20" :key="i" class="particle" :style="getParticleStyle(i)"></div>
      </div>

      <!-- 夜晚进度指示器 -->
      <div class="night-progress">
        <div class="progress-step" :class="{ active: currentAction === 'wolf', done: nightProgress > 1 }">
          <span class="step-icon">🐺</span>
          <span class="step-label">狼人</span>
        </div>
        <div class="progress-line" :class="{ done: nightProgress > 1 }"></div>
        <div class="progress-step" :class="{ active: currentAction === 'seer', done: nightProgress > 2 }">
          <span class="step-icon">🔮</span>
          <span class="step-label">预言家</span>
        </div>
        <div class="progress-line" :class="{ done: nightProgress > 2 }"></div>
        <div class="progress-step" :class="{ active: currentAction === 'witch', done: nightProgress > 3 }">
          <span class="step-icon">🧪</span>
          <span class="step-label">女巫</span>
        </div>
        <div class="progress-line" :class="{ done: nightProgress > 3 }"></div>
        <div class="progress-step" :class="{ active: currentAction === 'guard', done: nightProgress > 4 }">
          <span class="step-icon">🛡️</span>
          <span class="step-label">守卫</span>
        </div>
      </div>

      <!-- 主要动画内容 -->
      <div class="action-content">
        <!-- 狼人动画 -->
        <div v-if="currentAction === 'wolf'" class="wolf-action">
          <div class="wolf-eyes">
            <div class="eye left"></div>
            <div class="eye right"></div>
          </div>
          <div class="wolf-claws">
            <svg class="claw" viewBox="0 0 100 100">
              <path d="M20,80 Q30,20 50,10 Q70,20 80,80" fill="none" stroke="currentColor" stroke-width="4"/>
              <path d="M30,70 Q40,30 50,20" fill="none" stroke="currentColor" stroke-width="3"/>
              <path d="M50,70 Q50,35 50,25" fill="none" stroke="currentColor" stroke-width="3"/>
              <path d="M70,70 Q60,30 50,20" fill="none" stroke="currentColor" stroke-width="3"/>
            </svg>
          </div>
          <div class="action-text">🐺 狼人正在行动...</div>
        </div>

        <!-- 女巫动画 -->
        <div v-if="currentAction === 'witch'" class="witch-action">
          <div class="cauldron">
            <div class="pot"></div>
            <div class="bubbles">
              <div v-for="i in 8" :key="i" class="bubble" :style="getBubbleStyle(i)"></div>
            </div>
            <div class="steam">
              <div v-for="i in 5" :key="i" class="steam-particle" :style="getSteamStyle(i)"></div>
            </div>
          </div>
          <div class="potions">
            <div class="potion save">
              <div class="liquid"></div>
              <span>💚</span>
            </div>
            <div class="potion poison">
              <div class="liquid"></div>
              <span>💀</span>
            </div>
          </div>
          <div class="action-text">🧪 女巫正在调配药水...</div>
        </div>

        <!-- 守卫动画 -->
        <div v-if="currentAction === 'guard'" class="guard-action">
          <div class="shield-container">
            <svg class="shield" viewBox="0 0 100 120">
              <defs>
                <linearGradient id="shieldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" style="stop-color:#ffd700"/>
                  <stop offset="50%" style="stop-color:#daa520"/>
                  <stop offset="100%" style="stop-color:#b8860b"/>
                </linearGradient>
              </defs>
              <path 
                d="M50,5 L95,25 L90,75 Q70,105 50,115 Q30,105 10,75 L5,25 Z" 
                fill="url(#shieldGrad)"
                stroke="#8b7500"
                stroke-width="3"
              />
              <path 
                d="M50,20 L80,35 L77,70 Q65,90 50,97 Q35,90 23,70 L20,35 Z" 
                fill="none"
                stroke="rgba(255,255,255,0.5)"
                stroke-width="2"
              />
              <text x="50" y="65" text-anchor="middle" fill="#5a4500" font-size="28">🛡️</text>
            </svg>
            <div class="shield-glow"></div>
          </div>
          <div class="protection-rings">
            <div v-for="i in 3" :key="i" class="ring" :style="getRingStyle(i)"></div>
          </div>
          <div class="action-text">🛡️ 守卫正在守护...</div>
        </div>

        <!-- 预言家动画 -->
        <div v-if="currentAction === 'seer'" class="seer-action">
          <div class="crystal-ball">
            <div class="ball">
              <div class="inner-glow"></div>
              <div class="visions">
                <span class="vision good">👼</span>
                <span class="vision evil">😈</span>
              </div>
            </div>
            <div class="ball-stand"></div>
          </div>
          <div class="magic-stars">
            <div v-for="i in 12" :key="i" class="star" :style="getStarStyle(i)">✨</div>
          </div>
          <div class="action-text">🔮 预言家正在查验...</div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed, watch, ref } from 'vue'
import { useGameStore } from '../../stores/gameStore'

const gameStore = useGameStore()
const isVisible = ref(false)
const currentAction = ref<'wolf' | 'witch' | 'guard' | 'seer' | null>(null)

// 根据阶段判断当前动画
const phaseToAction = computed(() => {
  const phase = gameStore.currentPhase
  if (phase === 'NIGHT_WOLF_DISCUSS' || phase === 'NIGHT_WOLF_VOTE') return 'wolf'
  if (phase === 'NIGHT_WITCH') return 'witch'
  if (phase === 'NIGHT_GUARD') return 'guard'
  if (phase === 'NIGHT_SEER') return 'seer'
  return null
})

// 夜晚进度（用于显示进度条）
const nightProgress = computed(() => {
  const phase = gameStore.currentPhase
  if (phase === 'NIGHT_WOLF_DISCUSS' || phase === 'NIGHT_WOLF_VOTE') return 1
  if (phase === 'NIGHT_SEER') return 2
  if (phase === 'NIGHT_WITCH') return 3
  if (phase === 'NIGHT_GUARD') return 4
  if (phase === 'NIGHT_RESOLVE') return 5
  return 0
})

// 当前角色
const myRole = computed(() => gameStore.myPlayer?.role)

// 判断是否应该显示动画（当其他角色行动时，非该角色玩家会看到动画）
watch(
  () => gameStore.currentPhase,
  () => {
    const action = phaseToAction.value
    if (!action) {
      isVisible.value = false
      return
    }

    // 判断是否是该角色的玩家
    const roleMapping: Record<string, string[]> = {
      'wolf': ['wolf', 'wolf_king'],
      'witch': ['witch'],
      'guard': ['guard'],
      'seer': ['seer']
    }

    const isMyAction = roleMapping[action]?.includes(myRole.value || '')
    
    // 如果不是当前玩家的行动阶段，显示动画
    if (!isMyAction) {
      currentAction.value = action
      isVisible.value = true
    } else {
      isVisible.value = false
    }
  },
  { immediate: true }
)

const actionClass = computed(() => {
  return currentAction.value ? `action-${currentAction.value}` : ''
})

// 粒子样式生成
function getParticleStyle(_index: number) {
  const size = Math.random() * 6 + 2
  return {
    '--size': `${size}px`,
    '--delay': `${Math.random() * 3}s`,
    '--duration': `${Math.random() * 3 + 2}s`,
    '--x-start': `${Math.random() * 100}%`,
    '--x-end': `${Math.random() * 100}%`,
    '--y-start': `${Math.random() * 100}%`
  }
}

// 气泡样式
function getBubbleStyle(index: number) {
  return {
    '--delay': `${index * 0.3}s`,
    '--x': `${20 + Math.random() * 60}%`,
    '--size': `${8 + Math.random() * 12}px`
  }
}

// 蒸汽样式
function getSteamStyle(index: number) {
  return {
    '--delay': `${index * 0.5}s`,
    '--x': `${30 + index * 10}%`
  }
}

// 守卫光环样式
function getRingStyle(index: number) {
  return {
    '--delay': `${index * 0.3}s`,
    '--size': `${80 + index * 40}px`
  }
}

// 星星样式
function getStarStyle(index: number) {
  const angle = (index / 12) * Math.PI * 2
  const radius = 60 + Math.random() * 30
  return {
    '--delay': `${index * 0.1}s`,
    '--x': `${50 + Math.cos(angle) * radius}%`,
    '--y': `${50 + Math.sin(angle) * radius}%`
  }
}
</script>

<style scoped>
.night-action-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 100;
  pointer-events: none;
  background: radial-gradient(circle at center, transparent 0%, rgba(0, 0, 0, 0.7) 100%);
}

/* 夜晚进度指示器 */
.night-progress {
  position: absolute;
  top: 100px;
  display: flex;
  align-items: center;
  gap: 0;
  padding: 16px 32px;
  background: linear-gradient(135deg, rgba(20, 10, 40, 0.9) 0%, rgba(40, 20, 60, 0.9) 100%);
  border-radius: 60px;
  backdrop-filter: blur(15px);
  border: 1px solid rgba(138, 92, 246, 0.3);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.5),
    0 0 60px rgba(138, 92, 246, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.progress-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  opacity: 0.35;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  padding: 0 4px;
}

.progress-step.active {
  opacity: 1;
  transform: scale(1.15);
}

.progress-step.active .step-icon {
  animation: iconPulse 1.5s ease-in-out infinite;
  filter: drop-shadow(0 0 8px currentColor);
}

.progress-step.done {
  opacity: 0.6;
}

.progress-step.done .step-icon {
  filter: grayscale(0.3);
}

.progress-step .step-icon {
  font-size: 1.8rem;
  transition: all 0.3s ease;
}

.progress-step .step-label {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.6);
  white-space: nowrap;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.progress-step.active .step-label {
  color: #fbbf24;
  font-weight: 700;
  text-shadow: 0 0 10px rgba(251, 191, 36, 0.5);
}

.progress-step.done .step-label {
  color: rgba(74, 222, 128, 0.8);
}

.progress-line {
  width: 40px;
  height: 3px;
  background: rgba(255, 255, 255, 0.15);
  margin: 0 6px;
  margin-bottom: 24px;
  border-radius: 2px;
  transition: all 0.4s ease;
  position: relative;
  overflow: hidden;
}

.progress-line::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  width: 0;
  background: linear-gradient(90deg, #fbbf24, #4ade80);
  border-radius: 2px;
  transition: width 0.5s ease;
}

.progress-line.done {
  background: rgba(74, 222, 128, 0.3);
}

.progress-line.done::after {
  width: 100%;
}

@keyframes iconPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

/* 过渡动画 */
.action-overlay-enter-active,
.action-overlay-leave-active {
  transition: all 0.5s ease;
}

.action-overlay-enter-from,
.action-overlay-leave-to {
  opacity: 0;
}

/* 粒子背景 */
.particles {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.particle {
  position: absolute;
  width: var(--size);
  height: var(--size);
  border-radius: 50%;
  left: var(--x-start);
  top: var(--y-start);
  animation: float var(--duration) var(--delay) infinite ease-in-out;
}

.action-wolf .particle {
  background: rgba(220, 38, 38, 0.6);
  box-shadow: 0 0 10px rgba(220, 38, 38, 0.8);
}

.action-witch .particle {
  background: rgba(168, 85, 247, 0.6);
  box-shadow: 0 0 10px rgba(168, 85, 247, 0.8);
}

.action-guard .particle {
  background: rgba(234, 179, 8, 0.6);
  box-shadow: 0 0 10px rgba(234, 179, 8, 0.8);
}

.action-seer .particle {
  background: rgba(59, 130, 246, 0.6);
  box-shadow: 0 0 10px rgba(59, 130, 246, 0.8);
}

@keyframes float {
  0%, 100% {
    transform: translate(0, 0) scale(1);
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  90% {
    opacity: 1;
  }
  100% {
    transform: translate(calc(var(--x-end) - var(--x-start)), -100vh) scale(0.5);
    opacity: 0;
  }
}

/* 动画内容容器 */
.action-content {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.action-text {
  margin-top: 30px;
  font-size: 1.5rem;
  font-weight: bold;
  letter-spacing: 2px;
  animation: pulse-text 2s infinite;
}

.action-wolf .action-text { color: #ef4444; text-shadow: 0 0 20px rgba(239, 68, 68, 0.8); }
.action-witch .action-text { color: #a855f7; text-shadow: 0 0 20px rgba(168, 85, 247, 0.8); }
.action-guard .action-text { color: #eab308; text-shadow: 0 0 20px rgba(234, 179, 8, 0.8); }
.action-seer .action-text { color: #3b82f6; text-shadow: 0 0 20px rgba(59, 130, 246, 0.8); }

@keyframes pulse-text {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.02); }
}

/* ==================== 狼人动画 ==================== */
.wolf-action {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.wolf-eyes {
  display: flex;
  gap: 40px;
  margin-bottom: 20px;
}

.wolf-eyes .eye {
  width: 30px;
  height: 15px;
  background: #ef4444;
  border-radius: 50% 50% 50% 50% / 100% 100% 0% 0%;
  box-shadow: 0 0 30px rgba(239, 68, 68, 0.8), inset 0 0 10px rgba(255, 255, 255, 0.3);
  animation: wolf-blink 4s infinite;
}

.wolf-eyes .eye::after {
  content: '';
  position: absolute;
  width: 8px;
  height: 8px;
  background: #000;
  border-radius: 50%;
  top: 3px;
  left: 50%;
  transform: translateX(-50%);
  animation: eye-move 3s infinite;
}

@keyframes wolf-blink {
  0%, 45%, 55%, 100% { transform: scaleY(1); }
  50% { transform: scaleY(0.1); }
}

@keyframes eye-move {
  0%, 100% { transform: translateX(-50%); }
  25% { transform: translateX(-70%); }
  75% { transform: translateX(-30%); }
}

.wolf-claws {
  display: flex;
  gap: 20px;
}

.wolf-claws .claw {
  width: 100px;
  height: 100px;
  color: #ef4444;
  filter: drop-shadow(0 0 10px rgba(239, 68, 68, 0.8));
  animation: claw-slash 1.5s infinite;
}

.wolf-claws .claw:nth-child(1) { animation-delay: 0s; }
.wolf-claws .claw:nth-child(2) { animation-delay: 0.3s; transform: scaleX(-1); }

@keyframes claw-slash {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  25% { transform: translateY(-20px) rotate(-10deg); }
  50% { transform: translateY(10px) rotate(5deg); }
}

/* ==================== 女巫动画 ==================== */
.witch-action {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.cauldron {
  position: relative;
  width: 150px;
  height: 120px;
}

.cauldron .pot {
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 120px;
  height: 80px;
  background: linear-gradient(to bottom, #374151 0%, #1f2937 100%);
  border-radius: 0 0 60px 60px;
  box-shadow: inset 0 -20px 30px rgba(168, 85, 247, 0.5);
}

.cauldron .pot::before {
  content: '';
  position: absolute;
  top: -10px;
  left: -10px;
  right: -10px;
  height: 20px;
  background: #4b5563;
  border-radius: 10px;
}

.bubbles {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  width: 80px;
  height: 40px;
}

.bubble {
  position: absolute;
  bottom: 0;
  left: var(--x);
  width: var(--size);
  height: var(--size);
  background: rgba(168, 85, 247, 0.6);
  border-radius: 50%;
  animation: bubble-rise 2s var(--delay) infinite;
}

@keyframes bubble-rise {
  0% { transform: translateY(0) scale(1); opacity: 0.8; }
  100% { transform: translateY(-60px) scale(0.3); opacity: 0; }
}

.steam {
  position: absolute;
  top: -30px;
  left: 50%;
  transform: translateX(-50%);
  width: 80px;
  height: 50px;
}

.steam-particle {
  position: absolute;
  bottom: 0;
  left: var(--x);
  width: 20px;
  height: 30px;
  background: rgba(168, 85, 247, 0.3);
  border-radius: 50%;
  filter: blur(5px);
  animation: steam-rise 2s var(--delay) infinite;
}

@keyframes steam-rise {
  0% { transform: translateY(0) scale(1); opacity: 0.6; }
  100% { transform: translateY(-50px) scale(1.5); opacity: 0; }
}

.potions {
  display: flex;
  gap: 40px;
  margin-top: 20px;
}

.potion {
  position: relative;
  width: 40px;
  height: 60px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.potion .liquid {
  position: absolute;
  bottom: 5px;
  width: 30px;
  height: 35px;
  border-radius: 0 0 15px 15px;
  animation: liquid-shake 2s infinite;
}

.potion.save .liquid {
  background: linear-gradient(to bottom, #86efac 0%, #22c55e 100%);
  box-shadow: 0 0 15px rgba(34, 197, 94, 0.6);
}

.potion.poison .liquid {
  background: linear-gradient(to bottom, #c084fc 0%, #9333ea 100%);
  box-shadow: 0 0 15px rgba(147, 51, 234, 0.6);
}

.potion span {
  font-size: 1.5rem;
  animation: potion-glow 1.5s infinite alternate;
}

@keyframes liquid-shake {
  0%, 100% { transform: rotate(-2deg); }
  50% { transform: rotate(2deg); }
}

@keyframes potion-glow {
  0% { filter: brightness(1); }
  100% { filter: brightness(1.3); }
}

/* ==================== 守卫动画 ==================== */
.guard-action {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

.shield-container {
  position: relative;
  width: 120px;
  height: 150px;
}

.shield {
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 0 20px rgba(234, 179, 8, 0.6));
  animation: shield-pulse 2s infinite;
}

.shield-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 140px;
  height: 170px;
  transform: translate(-50%, -50%);
  background: radial-gradient(ellipse, rgba(234, 179, 8, 0.3) 0%, transparent 70%);
  animation: glow-pulse 1.5s infinite;
}

@keyframes shield-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

@keyframes glow-pulse {
  0%, 100% { opacity: 0.5; transform: translate(-50%, -50%) scale(1); }
  50% { opacity: 1; transform: translate(-50%, -50%) scale(1.1); }
}

.protection-rings {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.ring {
  position: absolute;
  width: var(--size);
  height: var(--size);
  border: 2px solid rgba(234, 179, 8, 0.5);
  border-radius: 50%;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation: ring-expand 2s var(--delay) infinite;
}

@keyframes ring-expand {
  0% { transform: translate(-50%, -50%) scale(0.5); opacity: 1; }
  100% { transform: translate(-50%, -50%) scale(2); opacity: 0; }
}

/* ==================== 预言家动画 ==================== */
.seer-action {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

.crystal-ball {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.crystal-ball .ball {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.4) 0%, rgba(59, 130, 246, 0.3) 40%, rgba(59, 130, 246, 0.6) 100%);
  box-shadow: 0 0 40px rgba(59, 130, 246, 0.6), inset 0 0 30px rgba(255, 255, 255, 0.3);
  position: relative;
  overflow: hidden;
}

.crystal-ball .inner-glow {
  position: absolute;
  inset: 10px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.4) 0%, transparent 70%);
  animation: inner-glow 3s infinite;
}

@keyframes inner-glow {
  0%, 100% { opacity: 0.5; transform: scale(0.9); }
  50% { opacity: 1; transform: scale(1.1); }
}

.visions {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.vision {
  position: absolute;
  font-size: 2rem;
  animation: vision-fade 4s infinite;
}

.vision.good { animation-delay: 0s; }
.vision.evil { animation-delay: 2s; }

@keyframes vision-fade {
  0%, 45%, 100% { opacity: 0; transform: scale(0.5); }
  50%, 95% { opacity: 1; transform: scale(1); }
}

.ball-stand {
  width: 60px;
  height: 20px;
  background: linear-gradient(to bottom, #6b7280 0%, #374151 100%);
  border-radius: 5px;
  margin-top: -5px;
}

.magic-stars {
  position: absolute;
  width: 200px;
  height: 200px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.star {
  position: absolute;
  left: var(--x);
  top: var(--y);
  transform: translate(-50%, -50%);
  animation: star-twinkle 1.5s var(--delay) infinite;
}

@keyframes star-twinkle {
  0%, 100% { opacity: 0; transform: translate(-50%, -50%) scale(0.5); }
  50% { opacity: 1; transform: translate(-50%, -50%) scale(1.2); }
}
</style>

