<template>
  <Transition name="dialog-slide">
    <div v-if="showDialog && currentLog" class="dialog-overlay">
      <!-- 对话框区域 -->
      <div class="dialog-box">
        <div class="dialog-container">
          <!-- 头部信息 -->
          <div class="dialog-header">
            <div class="speaker-info">
              <div class="speaker-avatar" :class="getSpeakerClass()">
                {{ getSpeakerNumber() }}
              </div>
              <div class="speaker-details">
                <span class="speaker-name">{{ speakerName }}</span>
                <div class="speaker-badges">
                  <span v-if="speaker?.id" class="badge badge-id">#{{ speaker.id }}</span>
                  <span v-if="showRoleBadge" :class="['badge', roleBadgeClass]">
                    {{ getRoleName(speaker?.role || 'villager') }}
                  </span>
                  <span v-if="speaker?.is_sheriff" class="badge badge-sheriff">👑 警长</span>
                </div>
              </div>
            </div>
            
            <div class="dialog-meta">
              <span class="meta-item">📅 第 {{ currentLog.day }} 天</span>
              <span class="meta-item">{{ formatPhase(currentLog.phase) }}</span>
            </div>
          </div>

          <!-- 对话内容 -->
          <div class="dialog-content">
            <div class="content-text">
              <TypeWriter
                :key="currentLog.id"
                :text="highlightKeywords(currentLog.content)"
                :speed="25"
                @finished="onTypingFinished"
              />
            </div>
          </div>

          <!-- 底部操作栏 -->
          <div class="dialog-footer">
            <div class="typing-status">
              <span v-if="!isTypingComplete" class="status-typing">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
              </span>
              <span v-else class="status-continue">
                按任意键继续 ▶
              </span>
            </div>
            <button @click="closeDialog" class="btn-close">跳过</button>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { useGameStore } from '../../stores/gameStore'
import TypeWriter from '../ui/TypeWriter.vue'
import { PHASE_NAMES, ROLE_NAMES, type Role, getRoleCamp } from '../../types'

const gameStore = useGameStore()
const currentLog = ref<any>(null)
const isTypingComplete = ref(false)
const showDialog = ref(true)

// 获取最新的发言日志
const latestSpeechLog = computed(() => {
  const logs = gameStore.gameState?.game_logs || []
  return logs.slice().reverse().find(log => log.player_id && log.is_public && log.type === 'speech')
})

// 说话者信息
const speaker = computed(() => {
  if (!currentLog.value?.player_id) return null
  return gameStore.players.find(p => p.id === currentLog.value.player_id)
})

// 说话者名称
const speakerName = computed(() => {
  if (speaker.value) {
    return `${speaker.value.id}号 ${speaker.value.name}`
  }
  return '法官'
})

// 是否显示角色徽章
const showRoleBadge = computed(() => {
  if (!speaker.value) return false
  return speaker.value.is_human || !speaker.value.is_alive
})

// 角色徽章样式
const roleBadgeClass = computed(() => {
  if (!speaker.value) return ''
  const camp = getRoleCamp(speaker.value.role as Role)
  return camp === 'wolf' ? 'badge-wolf' : 'badge-good'
})

// 获取说话者样式类
function getSpeakerClass(): string {
  if (!speaker.value) return 'avatar-judge'
  if (speaker.value.is_human) return 'avatar-me'
  if (showRoleBadge.value) {
    const camp = getRoleCamp(speaker.value.role as Role)
    return camp === 'wolf' ? 'avatar-wolf' : 'avatar-good'
  }
  return 'avatar-default'
}

// 获取说话者编号
function getSpeakerNumber(): string {
  if (!speaker.value) return '⚖️'
  return String(speaker.value.id)
}

// 关键词高亮
function highlightKeywords(text: string): string {
  // 玩家编号高亮
  text = text.replace(/(\d+号)/g, '<span class="highlight-player">$1</span>')
  // 角色名高亮
  const roles = ['狼人', '预言家', '女巫', '守卫', '猎人', '狼王', '村民', '好人', '神职']
  roles.forEach(role => {
    text = text.replace(new RegExp(role, 'g'), `<span class="highlight-role">${role}</span>`)
  })
  // 动作词高亮
  const actions = ['击杀', '毒杀', '查验', '守护', '投票', '放逐', '自爆', '开枪']
  actions.forEach(action => {
    text = text.replace(new RegExp(action, 'g'), `<span class="highlight-action">${action}</span>`)
  })
  return text
}

// 监听新日志
watch(latestSpeechLog, (newLog: any) => {
  if (newLog && newLog.id !== currentLog.value?.id) {
    currentLog.value = newLog
    isTypingComplete.value = false
    showDialog.value = true
  }
})

function onTypingFinished() {
  isTypingComplete.value = true
}

function closeDialog() {
  showDialog.value = false
  currentLog.value = null
}

function getRoleName(role: string): string {
  return ROLE_NAMES[role as Role] || role
}

function formatPhase(phase: string): string {
  return PHASE_NAMES[phase as keyof typeof PHASE_NAMES] || phase
}

function handleKeyPress(_e: KeyboardEvent) {
  if (currentLog.value && isTypingComplete.value) {
    closeDialog()
  }
}

onMounted(() => {
  window.addEventListener('keypress', handleKeyPress)
})

onUnmounted(() => {
  window.removeEventListener('keypress', handleKeyPress)
})
</script>

<style scoped>
/* ========== 遮罩层 ========== */
.dialog-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 30;
}

/* ========== 对话框主体 ========== */
.dialog-box {
  position: absolute;
  bottom: 120px;
  left: 50%;
  transform: translateX(-50%);
  width: 90%;
  max-width: 800px;
  pointer-events: auto;
}

.dialog-container {
  background: linear-gradient(
    135deg,
    rgba(20, 10, 35, 0.95) 0%,
    rgba(30, 15, 50, 0.95) 100%
  );
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(138, 92, 246, 0.3);
  border-radius: 16px;
  padding: 20px;
  box-shadow: 
    0 0 40px rgba(138, 92, 246, 0.2),
    0 20px 60px rgba(0, 0, 0, 0.5);
}

/* ========== 头部 ========== */
.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.speaker-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.speaker-avatar {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  font-weight: 700;
  color: white;
  border: 2px solid;
}

.avatar-default {
  background: linear-gradient(135deg, #374151 0%, #1f2937 100%);
  border-color: rgba(255, 255, 255, 0.2);
}

.avatar-me {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border-color: #60a5fa;
  box-shadow: 0 0 15px rgba(59, 130, 246, 0.4);
}

.avatar-wolf {
  background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
  border-color: #f87171;
  box-shadow: 0 0 15px rgba(239, 68, 68, 0.4);
}

.avatar-good {
  background: linear-gradient(135deg, #22c55e 0%, #15803d 100%);
  border-color: #4ade80;
  box-shadow: 0 0 15px rgba(34, 197, 94, 0.4);
}

.avatar-judge {
  background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%);
  border-color: #f4d03f;
  box-shadow: 0 0 15px rgba(212, 175, 55, 0.4);
}

.speaker-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.speaker-name {
  font-size: 1.25rem;
  font-weight: 700;
  color: white;
}

.speaker-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.badge {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 600;
}

.badge-id {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.6);
}

.badge-wolf {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.badge-good {
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.badge-sheriff {
  background: rgba(212, 175, 55, 0.2);
  color: #f4d03f;
  border: 1px solid rgba(212, 175, 55, 0.3);
}

.dialog-meta {
  display: flex;
  gap: 12px;
}

.meta-item {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.5);
}

/* ========== 内容区域 ========== */
.dialog-content {
  min-height: 80px;
  margin-bottom: 16px;
}

.content-text {
  font-size: 1.1rem;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.95);
  letter-spacing: 0.5px;
}

/* 关键词高亮 */
.content-text :deep(.highlight-player) {
  color: #60a5fa;
  font-weight: 600;
}

.content-text :deep(.highlight-role) {
  color: #c084fc;
  font-weight: 600;
}

.content-text :deep(.highlight-action) {
  color: #f87171;
  font-weight: 600;
}

/* ========== 底部 ========== */
.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.typing-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-typing {
  display: flex;
  gap: 4px;
}

.typing-dot {
  width: 6px;
  height: 6px;
  background: #a78bfa;
  border-radius: 50%;
  animation: typingBounce 1.4s infinite ease-in-out;
}

.typing-dot:nth-child(1) { animation-delay: 0s; }
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typingBounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40% { transform: translateY(-6px); opacity: 1; }
}

.status-continue {
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.85rem;
  animation: continuePulse 1.5s ease-in-out infinite;
}

@keyframes continuePulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

.btn-close {
  padding: 6px 16px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-close:hover {
  background: rgba(255, 255, 255, 0.15);
  color: white;
}

/* ========== 动画 ========== */
.dialog-slide-enter-active {
  transition: all 0.3s ease-out;
}
.dialog-slide-leave-active {
  transition: all 0.2s ease-in;
}
.dialog-slide-enter-from {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
}
.dialog-slide-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
}
</style>
