<template>
  <div class="judge-area">
    <!-- 阶段信息 -->
    <div class="phase-info">
      <!-- 日夜图标 -->
      <div class="phase-icon" :class="isNight ? 'night' : 'day'">
        {{ isNight ? '🌙' : '☀️' }}
      </div>
      <div class="phase-text">
        <span class="day-label">第 {{ gameStore.currentDay }} 天</span>
        <span class="phase-name" :class="isNight ? 'night' : 'day'">{{ phaseText }}</span>
      </div>
    </div>

    <!-- 广播消息区域 -->
    <div class="broadcast-area">
      <!-- 法官头像区域 -->
      <div class="judge-avatar">
        <div class="judge-icon">⚖️</div>
        <span class="judge-label">法官</span>
      </div>
      
      <!-- 消息内容区域 -->
      <div class="broadcast-content">
        <div class="broadcasts-container" ref="broadcastContainer">
          <TransitionGroup name="broadcast" tag="div" class="broadcasts-list">
            <div
              v-for="(log, index) in recentBroadcasts"
              :key="`${log.day}-${log.phase}-${index}`"
              :class="['broadcast-item', `type-${log.type}`]"
            >
              <!-- 消息类型图标 -->
              <div class="message-type-icon">
                {{ getMessageTypeIcon(log) }}
              </div>
              <!-- 发言者头像 -->
              <div :class="['speaker-avatar', getSpeakerAvatarClass(log)]">
                {{ getSpeakerDisplay(log) }}
              </div>
              <!-- 消息内容 -->
              <div class="message-wrapper">
                <span class="speaker-name">{{ getSpeakerName(log) }}</span>
                <span class="log-content">{{ formatContent(log) }}</span>
              </div>
            </div>
          </TransitionGroup>
          <div v-if="recentBroadcasts.length === 0" class="empty-broadcast">
            <span class="empty-icon">📜</span>
            等待游戏开始...
          </div>
        </div>
      </div>
    </div>

    <!-- 倒计时 -->
    <div class="timer-area" v-if="showTimer" :class="timerColorClass">
      <div class="timer-wrapper">
        <svg class="timer-ring" viewBox="0 0 36 36">
          <path
            class="timer-bg"
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          />
          <path
            :class="['timer-progress', timerColorClass]"
            :stroke-dasharray="`${timerProgress}, 100`"
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          />
        </svg>
        <span :class="['timer-value', timerColorClass]">{{ displayTime }}</span>
        <!-- 紧急警告提示 -->
        <div v-if="displayTime <= 10 && displayTime > 0" class="timer-warning">
          <span class="warning-icon">⚠️</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onUnmounted, nextTick } from 'vue'
import { useGameStore } from '../../stores/gameStore'
import { PHASE_NAMES } from '../../types'

const gameStore = useGameStore()
const broadcastContainer = ref<HTMLElement | null>(null)

// 阶段时间限制
const PHASE_TIME_LIMITS: Record<string, number> = {
  NIGHT_WOLF_DISCUSS: 45,
  NIGHT_WOLF_VOTE: 30,
  NIGHT_SEER: 30,
  NIGHT_WITCH: 30,
  NIGHT_GUARD: 30,
  DAY_DISCUSS: 60,
  DAY_VOTE: 30,
  SHERIFF_SPEECH: 60,
  SHERIFF_VOTE: 30,
  DAY_LAST_WORDS: 30
}

// 本地倒计时状态
const localTimeRemaining = ref(60)
let timerInterval: ReturnType<typeof setInterval> | null = null

// 是否显示计时器
const showTimer = computed(() => gameStore.currentPhase in PHASE_TIME_LIMITS)

// 显示的时间（使用本地倒计时，后端值只用于初始化）
const displayTime = computed(() => {
  return localTimeRemaining.value
})

// 倒计时进度
const timerProgress = computed(() => {
  const maxTime = PHASE_TIME_LIMITS[gameStore.currentPhase] || 60
  return (displayTime.value / maxTime) * 100
})

// 倒计时颜色
const timerColorClass = computed(() => {
  const progress = timerProgress.value
  if (progress > 60) return 'green'
  if (progress > 30) return 'yellow'
  return 'red'
})

// 是否为夜晚
const isNight = computed(() => gameStore.currentPhase.startsWith('NIGHT_'))

// 阶段文本
const phaseText = computed(() => {
  return PHASE_NAMES[gameStore.currentPhase as keyof typeof PHASE_NAMES] || gameStore.currentPhase
})

// 最近的广播消息（增加到5条）
const recentBroadcasts = computed(() => {
  const logs = gameStore.gameState?.game_logs || []
  const publicLogs = logs.filter(log => log.is_public)
  return publicLogs.slice(-5)
})

// 获取发言者头像显示内容
function getSpeakerDisplay(log: any): string {
  if (log.player_id) {
    return String(log.player_id)
  }
  return '📢'
}

// 获取发言者头像样式类
function getSpeakerAvatarClass(log: any): string {
  if (!log.player_id) return 'avatar-system'
  const player = gameStore.players.find(p => p.id === log.player_id)
  if (!player) return 'avatar-default'
  if (player.is_human) return 'avatar-me'
  if (!player.is_alive) {
    const role = player.role
    if (role === 'wolf' || role === 'wolf_king') return 'avatar-wolf'
    return 'avatar-good'
  }
  return 'avatar-default'
}

// 获取发言者名称
function getSpeakerName(log: any): string {
  if (log.player_id) {
    return `${log.player_id}号`
  }
  return '系统'
}

// 格式化消息内容（去掉开头的"X号:"）
function formatContent(log: any): string {
  let content = log.content
  if (log.player_id) {
    // 去掉开头的 "X号:" 或 "X号: " 格式
    content = content.replace(new RegExp(`^${log.player_id}号[：::]\\s*`), '')
  }
  return content
}

// 获取消息类型图标
function getMessageTypeIcon(log: any): string {
  const type = log.type || 'system'
  const iconMap: Record<string, string> = {
    'death': '💀',
    'vote': '🗳️',
    'skill': '✨',
    'system': '📢',
    'speech': '💬',
    'judge': '⚖️'
  }
  return iconMap[type] || '📢'
}

// 开始本地倒计时
function startLocalTimer() {
  stopLocalTimer()
  const currentPhase = gameStore.currentPhase
  const maxTime = PHASE_TIME_LIMITS[currentPhase]
  
  if (maxTime) {
    // 使用后端提供的初始时间（如果有），否则使用配置的最大时间
    const backendTime = gameStore.gameState?.time_remaining
    if (typeof backendTime === 'number' && backendTime > 0 && backendTime <= maxTime) {
      localTimeRemaining.value = backendTime
    } else {
      localTimeRemaining.value = maxTime
    }
    
    // 每秒递减
    timerInterval = setInterval(() => {
      if (localTimeRemaining.value > 0) {
        localTimeRemaining.value--
      }
    }, 1000)
  }
}

// 停止本地倒计时
function stopLocalTimer() {
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

// 监听阶段变化，重置倒计时
watch(
  () => gameStore.currentPhase,
  (newPhase) => {
    if (newPhase in PHASE_TIME_LIMITS) {
      startLocalTimer()
    } else {
      stopLocalTimer()
    }
  },
  { immediate: true }
)

// 自动滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (broadcastContainer.value) {
      broadcastContainer.value.scrollTop = broadcastContainer.value.scrollHeight
    }
  })
}

// 监听广播消息变化，自动滚动
watch(
  () => recentBroadcasts.value.length,
  () => {
    scrollToBottom()
  }
)

// 组件卸载时清理
onUnmounted(() => {
  stopLocalTimer()
})
</script>

<style scoped>
.judge-area {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 12px 24px;
  height: 100%;
  
  /* 玻璃态背景 */
  background: linear-gradient(
    90deg,
    rgba(20, 10, 30, 0.8) 0%,
    rgba(30, 15, 45, 0.7) 50%,
    rgba(20, 10, 30, 0.8) 100%
  );
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  
  /* 底部边框发光 */
  border-bottom: 2px solid transparent;
  border-image: linear-gradient(90deg, 
    transparent 0%, 
    rgba(212, 175, 55, 0.6) 20%,
    rgba(212, 175, 55, 0.8) 50%,
    rgba(212, 175, 55, 0.6) 80%,
    transparent 100%
  ) 1;
  
  box-shadow: 0 4px 30px rgba(212, 175, 55, 0.1);
}

/* 阶段信息 */
.phase-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.phase-icon {
  font-size: 2rem;
  filter: drop-shadow(0 0 8px currentColor);
}

.phase-icon.night {
  color: #60a5fa;
  animation: moonGlow 3s ease-in-out infinite;
}

.phase-icon.day {
  color: #fbbf24;
  animation: sunGlow 3s ease-in-out infinite;
}

@keyframes moonGlow {
  0%, 100% { filter: drop-shadow(0 0 8px rgba(96, 165, 250, 0.5)); }
  50% { filter: drop-shadow(0 0 16px rgba(96, 165, 250, 0.8)); }
}

@keyframes sunGlow {
  0%, 100% { filter: drop-shadow(0 0 8px rgba(251, 191, 36, 0.5)); }
  50% { filter: drop-shadow(0 0 16px rgba(251, 191, 36, 0.8)); }
}

.phase-text {
  display: flex;
  flex-direction: column;
}

.day-label {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 1px;
}

.phase-name {
  font-size: 1.3rem;
  font-weight: 700;
  letter-spacing: 2px;
  transition: all 0.3s ease;
}

.phase-name.night {
  color: #60a5fa;
  text-shadow: 0 0 20px rgba(96, 165, 250, 0.5);
}

.phase-name.day {
  color: #fbbf24;
  text-shadow: 0 0 20px rgba(251, 191, 36, 0.5);
}

/* 广播区域 */
.broadcast-area {
  flex: 1;
  display: flex;
  align-items: stretch;
  gap: 16px;
  background: linear-gradient(135deg, rgba(0, 0, 0, 0.5) 0%, rgba(20, 10, 30, 0.6) 100%);
  border: 1px solid rgba(212, 175, 55, 0.3);
  border-radius: 16px;
  padding: 12px 16px;
  height: 84px;
  overflow: hidden;
  position: relative;
  box-shadow: 
    inset 0 2px 4px rgba(0, 0, 0, 0.3),
    0 0 20px rgba(212, 175, 55, 0.1);
}

/* 法官头像区域 */
.judge-avatar {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 56px;
}

.judge-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.6rem;
  background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%);
  border-radius: 12px;
  border: 2px solid #f4d03f;
  box-shadow: 
    0 0 20px rgba(212, 175, 55, 0.6),
    0 0 40px rgba(212, 175, 55, 0.3),
    inset 0 2px 4px rgba(255, 255, 255, 0.2);
  position: relative;
  animation: judgePulse 2s ease-in-out infinite;
  transition: all 0.3s ease;
}

.judge-icon::before {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 12px;
  padding: 2px;
  background: linear-gradient(135deg, #f4d03f, #d4af37, #f4d03f);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0.6;
  animation: judgeGlow 2s ease-in-out infinite;
}

@keyframes judgePulse {
  0%, 100% { 
    transform: scale(1);
    box-shadow: 
      0 0 20px rgba(212, 175, 55, 0.6),
      0 0 40px rgba(212, 175, 55, 0.3),
      inset 0 2px 4px rgba(255, 255, 255, 0.2);
  }
  50% { 
    transform: scale(1.05);
    box-shadow: 
      0 0 30px rgba(212, 175, 55, 0.8),
      0 0 60px rgba(212, 175, 55, 0.4),
      inset 0 2px 4px rgba(255, 255, 255, 0.3);
  }
}

@keyframes judgeGlow {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

.judge-label {
  font-size: 0.65rem;
  color: #f4d03f;
  margin-top: 4px;
  letter-spacing: 1px;
  text-shadow: 0 0 10px rgba(212, 175, 55, 0.5);
}

/* 消息内容区域 */
.broadcast-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.broadcasts-container {
  overflow-y: auto;
  overflow-x: hidden;
  max-height: 80px;
  position: relative;
  scroll-behavior: smooth;
}

.broadcasts-container::-webkit-scrollbar {
  width: 4px;
}

.broadcasts-container::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 2px;
}

.broadcasts-container::-webkit-scrollbar-thumb {
  background: rgba(212, 175, 55, 0.4);
  border-radius: 2px;
}

.broadcasts-container::-webkit-scrollbar-thumb:hover {
  background: rgba(212, 175, 55, 0.6);
}

.broadcasts-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.broadcast-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  border-left: 3px solid transparent;
  animation: slideIn 0.3s ease-out;
  transition: all 0.2s ease;
}

.broadcast-item:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateX(2px);
}

/* 消息类型图标 */
.message-type-icon {
  font-size: 0.9rem;
  flex-shrink: 0;
  width: 20px;
  text-align: center;
  opacity: 0.8;
}

/* 根据消息类型设置左边框颜色 */
.broadcast-item.type-death { border-left-color: #f87171; }
.broadcast-item.type-vote { border-left-color: #60a5fa; }
.broadcast-item.type-skill { border-left-color: #c084fc; }
.broadcast-item.type-system { border-left-color: #fbbf24; }
.broadcast-item.type-speech { border-left-color: rgba(255, 255, 255, 0.3); }
.broadcast-item.type-judge { border-left-color: #f4d03f; }

/* 发言者头像 */
.speaker-avatar {
  width: 28px;
  height: 28px;
  min-width: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 700;
  color: white;
  border: 2px solid;
  flex-shrink: 0;
}

.speaker-avatar.avatar-default {
  background: linear-gradient(135deg, #374151 0%, #1f2937 100%);
  border-color: rgba(255, 255, 255, 0.2);
}

.speaker-avatar.avatar-me {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border-color: #60a5fa;
  box-shadow: 0 0 8px rgba(59, 130, 246, 0.4);
}

.speaker-avatar.avatar-wolf {
  background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
  border-color: #f87171;
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.4);
}

.speaker-avatar.avatar-good {
  background: linear-gradient(135deg, #22c55e 0%, #15803d 100%);
  border-color: #4ade80;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.4);
}

.speaker-avatar.avatar-system {
  background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%);
  border-color: #f4d03f;
  box-shadow: 0 0 8px rgba(212, 175, 55, 0.4);
  font-size: 0.9rem;
}

/* 消息包装 */
.message-wrapper {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.speaker-name {
  font-size: 0.75rem;
  font-weight: 600;
  color: #f4d03f;
  white-space: nowrap;
  flex-shrink: 0;
}

.log-content {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.9);
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.empty-broadcast {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.3);
  text-align: center;
  padding: 12px;
}

.empty-icon {
  font-size: 1rem;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 日志类型颜色 */
.broadcast-item.type-death .log-content { color: #f87171; }
.broadcast-item.type-death .speaker-name { color: #f87171; }
.broadcast-item.type-vote .log-content { color: #60a5fa; }
.broadcast-item.type-skill .log-content { color: #c084fc; }
.broadcast-item.type-system .log-content { color: rgba(255, 255, 255, 0.85); }
.broadcast-item.type-system .speaker-name { color: #fbbf24; }
.broadcast-item.type-speech .log-content { color: rgba(255, 255, 255, 0.9); }
.broadcast-item.type-judge .log-content { color: #fbbf24; }

/* 倒计时 */
.timer-area {
  position: relative;
  width: 64px;
  height: 64px;
  flex-shrink: 0;
}

.timer-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
}

.timer-ring {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.timer-bg {
  fill: none;
  stroke: rgba(255, 255, 255, 0.1);
  stroke-width: 3;
}

.timer-progress {
  fill: none;
  stroke-width: 3;
  stroke-linecap: round;
  transition: stroke-dasharray 1s linear;
}

.timer-progress.green { 
  stroke: #4ade80; 
  filter: drop-shadow(0 0 4px rgba(74, 222, 128, 0.6));
}
.timer-progress.yellow { 
  stroke: #fbbf24; 
  filter: drop-shadow(0 0 4px rgba(251, 191, 36, 0.6));
}
.timer-progress.red { 
  stroke: #f87171; 
  animation: timerPulse 0.5s ease-in-out infinite;
  filter: drop-shadow(0 0 6px rgba(248, 113, 113, 0.8));
}

@keyframes timerPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.timer-value {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  font-weight: 700;
}

.timer-value.green { 
  color: #4ade80; 
  text-shadow: 0 0 8px rgba(74, 222, 128, 0.6);
}
.timer-value.yellow { 
  color: #fbbf24; 
  text-shadow: 0 0 8px rgba(251, 191, 36, 0.6);
}
.timer-value.red { 
  color: #f87171; 
  text-shadow: 0 0 10px rgba(248, 113, 113, 0.8);
  animation: timerTextPulse 0.5s ease-in-out infinite;
}

/* 紧急警告提示 */
.timer-warning {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 24px;
  height: 24px;
  background: #f87171;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: warningPulse 0.8s ease-in-out infinite;
  box-shadow: 0 0 10px rgba(248, 113, 113, 0.8);
}

.warning-icon {
  font-size: 0.7rem;
}

@keyframes warningPulse {
  0%, 100% { 
    transform: scale(1);
    opacity: 1;
  }
  50% { 
    transform: scale(1.2);
    opacity: 0.8;
  }
}

@keyframes timerTextPulse {
  0%, 100% { 
    transform: scale(1);
  }
  50% { 
    transform: scale(1.1);
  }
}

/* 广播动画 */
.broadcast-enter-active {
  transition: all 0.3s ease-out;
}
.broadcast-leave-active {
  transition: all 0.2s ease-in;
  position: absolute;
}
.broadcast-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}
.broadcast-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>
