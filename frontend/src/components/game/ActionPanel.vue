<template>
  <div class="action-panel">
    <!-- Player Role Portrait (Bottom Left) -->
    <div 
      v-if="gameStore.myPlayer" 
      class="role-portrait"
      @click="showRoleCard = true"
    >
      <img
        :src="getRoleCardUrl(gameStore.myPlayer.role)"
        :alt="gameStore.myPlayer.role"
      />
      <div class="portrait-overlay">
        <span>点击查看身份牌</span>
      </div>
      <div class="portrait-border"></div>
    </div>

    <!-- Role Card Overlay -->
    <Transition name="role-card-pop">
      <div 
        v-if="showRoleCard && gameStore.myPlayer"
        class="role-card-modal"
        @click="showRoleCard = false"
      >
        <img
          :src="getRoleIdentityCardUrl(gameStore.myPlayer.role)"
          :alt="gameStore.myPlayer.role"
        />
        <div class="role-card-info">
          <h3>{{ getRoleName(gameStore.myPlayer.role) }}</h3>
          <p>{{ getRoleDescription(gameStore.myPlayer.role) }}</p>
        </div>
        <div class="close-hint">点击关闭</div>
      </div>
    </Transition>

    <!-- Action Buttons Container -->
    <div class="action-container">
      <template v-if="gameStore.myPlayer?.is_alive">
        <!-- Common Confirm Button -->
        <button
          v-if="canConfirm"
          @click="gameStore.submitAction('confirm')"
          class="btn btn-primary btn-glow"
        >
          <span class="btn-icon">✨</span>
          <span>{{ confirmText }}</span>
        </button>

        <!-- Wolf Action - 讨论阶段 -->
        <div v-if="gameStore.currentPhase === 'NIGHT_WOLF_DISCUSS' && isWolf" class="action-group wolf wide-group">
          <span class="action-label">🐺 狼人密谋</span>
          <div class="input-group wide">
            <input
              v-model="speechContent"
              type="text"
              placeholder="与狼队友商量今晚的目标..."
              class="input-field flex-1"
              @keyup.enter="submitWolfAction"
            />
            <button @click="submitWolfAction" class="btn btn-danger">发言</button>
            <button @click="gameStore.submitAction('pass')" class="btn btn-secondary">跳过</button>
          </div>
        </div>

        <!-- Wolf Action - 投票阶段 -->
        <div v-if="gameStore.currentPhase === 'NIGHT_WOLF_VOTE' && isWolf" class="action-group wolf">
          <span class="action-label">🐺 狼人击杀</span>
          <div class="input-group">
            <input
              v-model.number="targetId"
              type="number"
              placeholder="目标ID"
              min="1"
              max="12"
              class="input-field"
            />
            <button @click="submitAction('kill')" class="btn btn-danger">
              <span class="btn-icon">🗡️</span>击杀
            </button>
          </div>
        </div>

        <!-- Seer Action -->
        <div v-if="isSeerPhase && isSeer" class="action-group seer">
          <span class="action-label">🔮 预言家行动</span>
          <div class="input-group">
            <input
              v-model.number="targetId"
              type="number"
              placeholder="查验ID"
              min="1"
              max="12"
              class="input-field"
            />
            <button 
              @click="submitSeerCheck" 
              class="btn btn-purple"
              :disabled="!targetId || targetId < 1 || targetId > 12"
            >
              查验
            </button>
            <button @click="submitAction('pass')" class="btn btn-secondary">跳过</button>
          </div>
          <div v-if="seerCheckError" class="error-hint">{{ seerCheckError }}</div>
        </div>

        <!-- Witch Action -->
        <div v-if="isWitchPhase && isWitch" class="action-group witch">
          <span class="action-label">🧪 女巫行动</span>
          <div class="input-group">
            <button @click="submitAction('save')" class="btn btn-success">
              <span class="btn-icon">💚</span>解药
            </button>
            <input
              v-model.number="targetId"
              type="number"
              placeholder="毒杀ID"
              min="1"
              max="12"
              class="input-field small"
            />
            <button @click="submitAction('poison')" class="btn btn-poison">
              <span class="btn-icon">💀</span>毒药
            </button>
            <button @click="submitAction('pass')" class="btn btn-secondary">跳过</button>
          </div>
        </div>

        <!-- Guard Action -->
        <div v-if="isGuardPhase && isGuard" class="action-group guard">
          <span class="action-label">🛡️ 守卫行动</span>
          <div class="input-group">
            <input
              v-model.number="targetId"
              type="number"
              placeholder="守护ID"
              min="1"
              max="12"
              class="input-field"
            />
            <button @click="submitAction('guard')" class="btn btn-gold">守护</button>
            <button @click="submitAction('pass')" class="btn btn-secondary">空守</button>
          </div>
        </div>

        <!-- Day Discussion Speech -->
        <div v-if="isDayDiscussPhase" class="action-group speech wide-group">
          <div class="speech-header">
            <span class="action-label">💬 发言</span>
            <button @click="showQuickPhrases = !showQuickPhrases" class="btn-toggle-phrases">
              {{ showQuickPhrases ? '收起' : '快捷短语' }} ⚡
            </button>
          </div>
          
          <!-- 快捷短语面板 -->
          <Transition name="phrases-slide">
            <div v-if="showQuickPhrases" class="quick-phrases">
              <button 
                v-for="phrase in quickPhrases" 
                :key="phrase.text"
                @click="insertPhrase(phrase.text)"
                class="phrase-btn"
                :class="phrase.type"
              >
                {{ phrase.icon }} {{ phrase.label }}
              </button>
            </div>
          </Transition>
          
          <div class="input-group wide">
            <input
              v-model="speechContent"
              type="text"
              placeholder="输入发言内容..."
              class="input-field flex-1"
              @keyup.enter="submitSpeech"
            />
            <button @click="submitSpeech" class="btn btn-primary">发言</button>
            <button @click="submitAction('confirm')" class="btn btn-secondary">结束</button>
          </div>
        </div>

        <!-- Vote Action -->
        <div v-if="isVotePhase" class="action-group vote">
          <span class="action-label">🗳️ 投票放逐</span>
          <div class="input-group">
            <input
              v-model.number="targetId"
              type="number"
              placeholder="目标ID"
              min="1"
              max="12"
              class="input-field"
            />
            <button @click="submitAction('vote')" class="btn btn-primary">投票</button>
            <button @click="submitAction('vote', 0)" class="btn btn-secondary">弃票</button>
          </div>
        </div>

        <!-- Sheriff Election -->
        <div v-if="isSheriffElectionPhase" class="action-group sheriff">
          <span class="action-label">👮 警长竞选</span>
          <div class="input-group">
            <button @click="submitAction('run_for_sheriff')" class="btn btn-gold btn-glow">
              <span class="btn-icon">⭐</span>上警
            </button>
            <button @click="submitAction('pass')" class="btn btn-secondary">不竞选</button>
          </div>
        </div>

        <!-- Sheriff Speech -->
        <div v-if="isSheriffSpeechPhase && gameStore.isCandidate" class="action-group sheriff-speech">
          <span class="action-label">🎤 竞选发言</span>
          <div class="input-group wide">
            <input
              v-model="speechContent"
              type="text"
              placeholder="竞选发言..."
              class="input-field flex-1"
              @keyup.enter="submitSpeech"
            />
            <button @click="submitSpeech" class="btn btn-primary">发言</button>
            <button @click="submitAction('withdraw')" class="btn btn-danger">退水</button>
            <button v-if="isWolf" @click="submitAction('self_explode')" class="btn btn-explode">
              💥 自爆
            </button>
          </div>
        </div>

        <!-- Sheriff Vote -->
        <div v-if="isSheriffVotePhase && !gameStore.isCandidate" class="action-group vote">
          <span class="action-label">🗳️ 警长投票</span>
          <div class="input-group">
            <input
              v-model.number="targetId"
              type="number"
              placeholder="目标ID"
              min="1"
              max="12"
              class="input-field"
            />
            <button @click="submitAction('vote')" class="btn btn-gold">投票</button>
            <button @click="submitAction('vote', 0)" class="btn btn-secondary">弃票</button>
          </div>
        </div>

        <!-- Hunter Skill -->
        <div v-if="isHunterSkillPhase && canShoot" class="action-group hunter">
          <span class="action-label">🎯 猎人技能</span>
          <div class="input-group">
            <input
              v-model.number="targetId"
              type="number"
              placeholder="目标ID"
              min="1"
              max="12"
              class="input-field"
            />
            <button @click="submitAction('shoot')" class="btn btn-danger btn-glow">
              <span class="btn-icon">🔫</span>开枪
            </button>
            <button @click="submitAction('pass')" class="btn btn-secondary">不开枪</button>
          </div>
        </div>

        <!-- Sheriff Transfer -->
        <div v-if="isSheriffTransferPhase && gameStore.myPlayer?.is_sheriff" class="action-group sheriff">
          <span class="action-label">👮 移交警徽</span>
          <div class="input-group">
            <input
              v-model.number="targetId"
              type="number"
              placeholder="目标ID"
              min="1"
              max="12"
              class="input-field"
            />
            <button @click="submitAction('vote')" class="btn btn-gold">移交</button>
            <button @click="submitAction('vote', 0)" class="btn btn-danger">撕警徽</button>
          </div>
        </div>
      </template>

      <!-- Dead Player View -->
      <div v-else-if="gameStore.myPlayer" class="dead-message">
        <span class="dead-icon">👻</span>
        <span>你已死亡，正在观战...</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useGameStore } from '../../stores/gameStore'
import { ROLE_DESCRIPTIONS, ROLE_NAMES } from '../../types'

const gameStore = useGameStore()
const targetId = ref<number | null>(null)
const speechContent = ref('')
const showRoleCard = ref(false)
const showQuickPhrases = ref(false)
const seerCheckError = ref<string>('')

// 快捷短语
const quickPhrases = [
  { icon: '🔍', label: '查验结果', text: '我查验了X号，是好人/狼人', type: 'seer' },
  { icon: '🎯', label: '怀疑', text: '我怀疑X号是狼人', type: 'suspect' },
  { icon: '✅', label: '认同', text: '我认同X号的发言', type: 'agree' },
  { icon: '❌', label: '反对', text: '我不认同X号的观点', type: 'disagree' },
  { icon: '🛡️', label: '自证', text: '我是好人，请相信我', type: 'defend' },
  { icon: '🗳️', label: '投票', text: '我建议投X号', type: 'vote' },
  { icon: '⚠️', label: '警告', text: '大家小心X号，他的逻辑有问题', type: 'warn' },
  { icon: '🤝', label: '站边', text: '我选择相信X号', type: 'trust' },
]

function insertPhrase(text: string) {
  speechContent.value = text
}

// Role Checks
const isWolf = computed(() => ['wolf', 'wolf_king'].includes(gameStore.myPlayer?.role || ''))
const isSeer = computed(() => gameStore.myPlayer?.role === 'seer')
const isWitch = computed(() => gameStore.myPlayer?.role === 'witch')
const isGuard = computed(() => gameStore.myPlayer?.role === 'guard')
const isHunterOrWolfKing = computed(() => ['hunter', 'wolf_king'].includes(gameStore.myPlayer?.role || ''))

// Phase Checks
// Wolf phases are now checked directly in template
const isSeerPhase = computed(() => gameStore.currentPhase === 'NIGHT_SEER')
const isWitchPhase = computed(() => gameStore.currentPhase === 'NIGHT_WITCH')
const isGuardPhase = computed(() => gameStore.currentPhase === 'NIGHT_GUARD')
const isDayDiscussPhase = computed(() => gameStore.currentPhase === 'DAY_DISCUSS')
const isVotePhase = computed(() => gameStore.currentPhase === 'DAY_VOTE')
const isSheriffElectionPhase = computed(() => gameStore.currentPhase === 'SHERIFF_ELECTION')
const isSheriffSpeechPhase = computed(() => gameStore.currentPhase === 'SHERIFF_SPEECH')
const isSheriffVotePhase = computed(() => gameStore.currentPhase === 'SHERIFF_VOTE')
const isHunterSkillPhase = computed(() => gameStore.currentPhase === 'HUNTER_SKILL')
const isSheriffTransferPhase = computed(() => gameStore.currentPhase === 'SHERIFF_TRANSFER')

const canShoot = computed(() => {
  return isHunterOrWolfKing.value && !gameStore.myPlayer?.is_alive
})

const canConfirm = computed(() => {
  return ['GAME_START', 'NIGHT_RESOLVE', 'DAY_START', 'DAY_VOTE_RESULT'].includes(gameStore.currentPhase)
})

const confirmText = computed(() => {
  const phaseTexts: Record<string, string> = {
    GAME_START: '准备就绪',
    NIGHT_RESOLVE: '继续',
    DAY_START: '确认',
    DAY_VOTE_RESULT: '继续'
  }
  return phaseTexts[gameStore.currentPhase] || '确认'
})

async function submitAction(type: string, tid?: number) {
  const finalTarget = tid !== undefined ? tid : targetId.value
  await gameStore.submitAction(type, finalTarget)
  targetId.value = null
  seerCheckError.value = ''
}

async function submitSeerCheck() {
  seerCheckError.value = ''
  
  if (!targetId.value || targetId.value < 1 || targetId.value > 12) {
    seerCheckError.value = '请输入有效的玩家ID (1-12)'
    return
  }
  
  // 检查目标是否存活
  const target = gameStore.players.find(p => p.id === targetId.value)
  if (!target) {
    seerCheckError.value = `玩家 ${targetId.value}号 不存在`
    return
  }
  
  if (!target.is_alive) {
    seerCheckError.value = `玩家 ${targetId.value}号 已死亡，无法查验`
    return
  }
  
  // 检查是否已经查验过（可选，如果需要的话）
  // 这里暂时不限制重复查验，因为游戏规则可能允许
  
  try {
    await submitAction('check')
  } catch (error) {
    seerCheckError.value = '查验失败，请重试'
  }
}

async function submitSpeech() {
  if (speechContent.value.trim()) {
    await gameStore.submitAction('speech', undefined, speechContent.value)
    speechContent.value = ''
  }
}

async function submitWolfAction() {
  if (gameStore.currentPhase === 'NIGHT_WOLF_DISCUSS') {
    if (speechContent.value.trim()) {
      await gameStore.submitAction('speech', undefined, speechContent.value)
      speechContent.value = ''
    } else {
      // 如果没有输入内容，显示提示而不是直接跳过
      return
    }
  } else {
    await submitAction('kill')
  }
}

function getRoleCardUrl(role: string): string {
  const roleMap: Record<string, string> = {
    'villager': '村民.jpg',
    'wolf': '狼人.png',
    'wolf_king': '狼王.png',
    'seer': '预言家.jpg',
    'witch': '女巫.png',
    'guard': '守卫.png',
    'hunter': '猎人.png'
  }
  const filename = roleMap[role] || 'back.png'
  return `/images/portraits/${filename}`
}

function getRoleDescription(role: string): string {
  return ROLE_DESCRIPTIONS[role as keyof typeof ROLE_DESCRIPTIONS] || '未知角色'
}

function getRoleIdentityCardUrl(role: string): string {
  const roleMap: Record<string, string> = {
    'villager': '村民.png',
    'wolf': '狼人.png',
    'wolf_king': '狼王.png',
    'seer': '预言家.png',
    'witch': '女巫.png',
    'guard': '守卫.png',
    'hunter': '猎人.png'
  }
  const filename = roleMap[role] || '反面.png'
  return `/images/role-cards/${filename}`
}

function getRoleName(role: string): string {
  return ROLE_NAMES[role as keyof typeof ROLE_NAMES] || '未知'
}
</script>

<style scoped>
/* ========== 主面板 ========== */
.action-panel {
  position: relative;
  height: 100%;
  padding: 16px 24px;
  
  /* 玻璃态背景 */
  background: linear-gradient(
    180deg,
    rgba(20, 10, 30, 0.7) 0%,
    rgba(30, 15, 45, 0.85) 100%
  );
  backdrop-filter: blur(15px);
  -webkit-backdrop-filter: blur(15px);
  
  /* 顶部边框发光 */
  border-top: 2px solid transparent;
  border-image: linear-gradient(90deg, 
    transparent 0%, 
    rgba(138, 92, 246, 0.5) 20%,
    rgba(138, 92, 246, 0.7) 50%,
    rgba(138, 92, 246, 0.5) 80%,
    transparent 100%
  ) 1;
}

/* ========== 角色立绘 ========== */
.role-portrait {
  position: absolute;
  left: 20px;
  bottom: 16px;
  width: 120px;
  height: 180px;
  cursor: pointer;
  z-index: 50;
  transition: transform 0.3s ease;
}

.role-portrait:hover {
  transform: scale(1.05);
}

.role-portrait img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 12px;
}

.portrait-border {
  position: absolute;
  inset: -3px;
  border: 3px solid transparent;
  border-radius: 15px;
  background: linear-gradient(135deg, #d4af37, #f4d03f, #d4af37) border-box;
  -webkit-mask: linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  animation: borderGlow 2s ease-in-out infinite;
}

@keyframes borderGlow {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}

.portrait-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0);
  border-radius: 12px;
  transition: background 0.3s ease;
}

.portrait-overlay span {
  font-size: 0.75rem;
  color: white;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.role-portrait:hover .portrait-overlay {
  background: rgba(0, 0, 0, 0.4);
}

.role-portrait:hover .portrait-overlay span {
  opacity: 1;
}

/* ========== 身份牌弹窗 ========== */
.role-card-modal {
  position: absolute;
  left: 20px;
  bottom: 16px;
  width: 360px;
  height: 540px;
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
  z-index: 100;
  box-shadow: 
    0 0 40px rgba(212, 175, 55, 0.3),
    0 0 80px rgba(138, 92, 246, 0.2);
}

.role-card-modal img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.role-card-info {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 20px;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.9), transparent);
}

.role-card-info h3 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #f4d03f;
  margin-bottom: 8px;
  text-shadow: 0 0 20px rgba(244, 208, 63, 0.5);
}

.role-card-info p {
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.85);
  line-height: 1.5;
}

.close-hint {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 4px 12px;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 20px;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.7);
}

/* ========== 操作区域 ========== */
.action-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
  padding-left: 160px;
}

.action-group {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.action-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  white-space: nowrap;
}

.action-group.wolf .action-label { color: #f87171; }
.action-group.seer .action-label { color: #c084fc; }
.action-group.witch .action-label { color: #4ade80; }
.action-group.guard .action-label { color: #fbbf24; }
.action-group.sheriff .action-label { color: #f4d03f; }
.action-group.hunter .action-label { color: #fb923c; }

.input-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-group.wide {
  flex: 1;
  min-width: 300px;
}

/* ========== 发言区域扩展 ========== */
.wide-group {
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
}

.speech-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.btn-toggle-phrases {
  padding: 4px 12px;
  font-size: 0.75rem;
  background: rgba(138, 92, 246, 0.2);
  color: #a78bfa;
  border: 1px solid rgba(138, 92, 246, 0.3);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-toggle-phrases:hover {
  background: rgba(138, 92, 246, 0.3);
}

/* 快捷短语面板 */
.quick-phrases {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  width: 100%;
}

.phrase-btn {
  padding: 6px 12px;
  font-size: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  color: rgba(255, 255, 255, 0.8);
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.phrase-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: translateY(-1px);
}

.phrase-btn.seer { border-color: rgba(168, 85, 247, 0.4); color: #c084fc; }
.phrase-btn.suspect { border-color: rgba(239, 68, 68, 0.4); color: #f87171; }
.phrase-btn.agree { border-color: rgba(34, 197, 94, 0.4); color: #4ade80; }
.phrase-btn.disagree { border-color: rgba(239, 68, 68, 0.4); color: #f87171; }
.phrase-btn.defend { border-color: rgba(59, 130, 246, 0.4); color: #60a5fa; }
.phrase-btn.vote { border-color: rgba(251, 191, 36, 0.4); color: #fbbf24; }
.phrase-btn.warn { border-color: rgba(251, 146, 60, 0.4); color: #fb923c; }
.phrase-btn.trust { border-color: rgba(34, 197, 94, 0.4); color: #4ade80; }

/* 短语面板动画 */
.phrases-slide-enter-active {
  transition: all 0.2s ease-out;
}
.phrases-slide-leave-active {
  transition: all 0.15s ease-in;
}
.phrases-slide-enter-from,
.phrases-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* ========== 输入框 ========== */
.input-field {
  width: 80px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  color: white;
  font-size: 0.9rem;
  transition: all 0.2s ease;
}

.input-field:focus {
  outline: none;
  border-color: rgba(138, 92, 246, 0.6);
  background: rgba(138, 92, 246, 0.1);
  box-shadow: 0 0 15px rgba(138, 92, 246, 0.2);
}

.input-field.small {
  width: 70px;
}

.input-field.flex-1 {
  flex: 1;
  width: auto;
}

.input-field::placeholder {
  color: rgba(255, 255, 255, 0.3);
}

/* ========== 按钮样式 ========== */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  font-size: 0.9rem;
  font-weight: 600;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.btn:active {
  transform: scale(0.96);
}

.btn-icon {
  font-size: 1rem;
}

/* 主要按钮 */
.btn-primary {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
}

.btn-primary:hover {
  background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
  transform: translateY(-1px);
}

/* 次要按钮 */
.btn-secondary {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.15);
  color: white;
}

/* 危险按钮 */
.btn-danger {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
}

.btn-danger:hover {
  background: linear-gradient(135deg, #f87171 0%, #ef4444 100%);
  box-shadow: 0 6px 20px rgba(239, 68, 68, 0.4);
}

/* 成功按钮 */
.btn-success {
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  color: white;
  box-shadow: 0 4px 15px rgba(34, 197, 94, 0.3);
}

.btn-success:hover {
  background: linear-gradient(135deg, #4ade80 0%, #22c55e 100%);
}

/* 毒药按钮 */
.btn-poison {
  background: linear-gradient(135deg, #166534 0%, #14532d 100%);
  color: #86efac;
  border: 1px solid #22c55e;
}

.btn-poison:hover {
  background: linear-gradient(135deg, #15803d 0%, #166534 100%);
}

/* 紫色按钮 */
.btn-purple {
  background: linear-gradient(135deg, #a855f7 0%, #9333ea 100%);
  color: white;
  box-shadow: 0 4px 15px rgba(168, 85, 247, 0.3);
}

.btn-purple:hover {
  background: linear-gradient(135deg, #c084fc 0%, #a855f7 100%);
}

/* 金色按钮 */
.btn-gold {
  background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%);
  color: white;
  box-shadow: 0 4px 15px rgba(212, 175, 55, 0.3);
}

.btn-gold:hover {
  background: linear-gradient(135deg, #f4d03f 0%, #d4af37 100%);
  box-shadow: 0 6px 20px rgba(212, 175, 55, 0.5);
}

/* 自爆按钮 */
.btn-explode {
  background: linear-gradient(135deg, #7f1d1d 0%, #450a0a 100%);
  color: #fca5a5;
  border: 1px solid #ef4444;
  animation: explodePulse 1s ease-in-out infinite;
}

@keyframes explodePulse {
  0%, 100% { box-shadow: 0 0 10px rgba(239, 68, 68, 0.3); }
  50% { box-shadow: 0 0 20px rgba(239, 68, 68, 0.6); }
}

/* 发光按钮 */
.btn-glow {
  animation: btnGlow 2s ease-in-out infinite;
}

@keyframes btnGlow {
  0%, 100% { filter: brightness(1); }
  50% { filter: brightness(1.1); }
}

/* ========== 错误提示 ========== */
.error-hint {
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.4);
  border-radius: 8px;
  color: #fca5a5;
  font-size: 0.85rem;
  animation: shake 0.3s ease;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

/* ========== 死亡提示 ========== */
.dead-message {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 24px;
  background: rgba(0, 0, 0, 0.4);
  border-radius: 12px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.95rem;
}

.dead-icon {
  font-size: 1.5rem;
  animation: float 2s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}

/* ========== 身份牌动画 ========== */
.role-card-pop-enter-active {
  animation: roleCardPopIn 0.3s ease-out;
}

.role-card-pop-leave-active {
  animation: roleCardPopOut 0.2s ease-in;
}

@keyframes roleCardPopIn {
  0% {
    opacity: 0;
    transform: scale(0.33);
  }
  70% {
    transform: scale(1.02);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes roleCardPopOut {
  0% {
    opacity: 1;
    transform: scale(1);
  }
  100% {
    opacity: 0;
    transform: scale(0.33);
  }
}
</style>
