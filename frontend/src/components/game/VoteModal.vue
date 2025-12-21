<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="isVisible"
        class="fixed inset-0 z-50 flex items-center justify-center"
      >
        <!-- 背景遮罩 -->
        <div
          class="absolute inset-0 bg-black/80 backdrop-blur-sm"
          @click="handleBackdropClick"
        ></div>

        <!-- 弹窗主体 -->
        <div class="vote-modal relative w-full max-w-4xl mx-4 animate-scale-in">
          <!-- 标题栏 -->
          <div class="modal-header">
            <div class="flex items-center space-x-3">
              <div class="header-icon">
                <span>🗳️</span>
              </div>
              <div>
                <h2 class="text-xl font-bold text-white">{{ title }}</h2>
                <p class="text-sm text-gray-400">{{ description }}</p>
              </div>
            </div>

            <!-- 倒计时 -->
            <div class="countdown-wrapper">
              <div class="countdown-circle" :class="countdownColorClass">
                <svg viewBox="0 0 36 36" class="w-14 h-14">
                  <path
                    class="circle-bg"
                    d="M18 2.0845
                      a 15.9155 15.9155 0 0 1 0 31.831
                      a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="3"
                    opacity="0.2"
                  />
                  <path
                    class="circle-progress"
                    d="M18 2.0845
                      a 15.9155 15.9155 0 0 1 0 31.831
                      a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="3"
                    stroke-linecap="round"
                    :stroke-dasharray="`${countdownProgress}, 100`"
                  />
                </svg>
                <span class="countdown-text">{{ timeRemaining }}s</span>
              </div>
            </div>
          </div>

          <!-- 投票进度条 -->
          <div class="vote-progress-bar">
            <div class="progress-info">
              <span class="text-gray-400 text-sm">投票进度</span>
              <span class="text-white text-sm font-bold">{{ votedCount }}/{{ totalVoters }}</span>
            </div>
            <div class="progress-track">
              <div
                class="progress-fill"
                :style="{ width: `${voteProgressPercent}%` }"
              ></div>
            </div>
          </div>

          <!-- 主体内容 -->
          <div class="modal-body">
            <!-- 候选人区域 -->
            <div class="candidates-section">
              <h3 class="section-title">
                <span class="icon">👥</span>
                {{ voteType === 'sheriff' ? '警长候选人' : '投票目标' }}
              </h3>

              <div class="candidates-grid">
                <div
                  v-for="candidate in voteCandidates"
                  :key="candidate.id"
                  class="candidate-card"
                  :class="{
                    'is-selected': selectedTarget === candidate.id,
                    'is-leading': isLeadingCandidate(candidate.id),
                    'has-my-vote': hasMyVote(candidate.id)
                  }"
                  @click="selectTarget(candidate.id)"
                >
                  <!-- 头像 - 改为数字显示 -->
                  <div class="candidate-avatar">
                    <span class="avatar-number">{{ candidate.id }}</span>
                    <!-- 死亡遮罩（理论上候选人都是存活的，但作为保护） -->
                    <div v-if="!candidate.is_alive" class="death-overlay">
                      <span>💀</span>
                    </div>
                  </div>

                  <!-- 玩家信息 -->
                  <div class="candidate-info">
                    <span class="candidate-number">{{ candidate.id }}号</span>
                    <span class="candidate-name">{{ candidate.name }}</span>
                  </div>

                  <!-- 票数显示 -->
                  <div class="vote-count" :class="{ 'has-votes': getVoteCount(candidate.id) > 0 }">
                    <span class="count-number">{{ getVoteCount(candidate.id) }}</span>
                    <span class="count-label">票</span>
                  </div>

                  <!-- 警长标识 -->
                  <div v-if="candidate.is_sheriff" class="sheriff-badge" title="警长">
                    <span>👮</span>
                  </div>

                  <!-- 选中指示器 -->
                  <div v-if="selectedTarget === candidate.id" class="selected-indicator">
                    <span>✓</span>
                  </div>

                  <!-- 领先标识 -->
                  <div v-if="isLeadingCandidate(candidate.id)" class="leading-badge">
                    领先
                  </div>
                </div>
              </div>

              <!-- 弃票选项 -->
              <div
                class="abstain-option"
                :class="{ 'is-selected': selectedTarget === 0 }"
                @click="selectTarget(0)"
              >
                <span class="abstain-icon">🚫</span>
                <span class="abstain-text">弃票</span>
                <span class="abstain-count" v-if="abstainCount > 0">
                  ({{ abstainCount }}人弃票)
                </span>
              </div>
            </div>

            <!-- 投票记录区域 -->
            <div class="vote-records-section">
              <h3 class="section-title">
                <span class="icon">📊</span>
                投票记录
              </h3>

              <div class="records-list" ref="recordsListRef">
                <TransitionGroup name="record-list">
                  <div
                    v-for="record in sortedVoteRecords"
                    :key="record.voterId"
                    class="vote-record"
                    :class="{ 'is-mine': record.voterId === myPlayerId }"
                  >
                    <!-- 投票者 -->
                    <div class="voter-info">
                      <span class="voter-number">{{ record.voterId }}号</span>
                      <span v-if="record.weight > 1" class="weight-badge">x{{ record.weight }}</span>
                    </div>

                    <!-- 箭头 -->
                    <div class="vote-arrow">
                      <span>→</span>
                    </div>

                    <!-- 目标 -->
                    <div class="target-info" :class="{ 'is-abstain': record.targetId === null || record.targetId === 0 }">
                      <span v-if="record.targetId && record.targetId !== 0">
                        {{ record.targetId }}号
                      </span>
                      <span v-else class="abstain-label">弃票</span>
                    </div>
                  </div>
                </TransitionGroup>

                <!-- 空状态 -->
                <div v-if="voteRecords.length === 0" class="empty-records">
                  <span class="empty-icon">⏳</span>
                  <span class="empty-text">等待玩家投票...</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 底部操作栏 -->
          <div class="modal-footer">
            <!-- 警长提示 -->
            <div v-if="isSheriff" class="sheriff-notice">
              <span class="notice-icon">👮</span>
              <span class="notice-text">你是警长，你的票数为 <strong>2票</strong></span>
            </div>

            <!-- 已投票提示 -->
            <div v-if="hasVoted" class="voted-notice">
              <span class="notice-icon">✓</span>
              <span class="notice-text">
                你已投票给
                <strong v-if="myVoteTarget && myVoteTarget !== 0">{{ myVoteTarget }}号</strong>
                <strong v-else>弃票</strong>
              </span>
            </div>

            <!-- 操作按钮 -->
            <div class="action-buttons">
              <button
                class="btn-cancel"
                @click="close"
                :disabled="isSubmitting"
              >
                {{ hasVoted ? '关闭' : '取消' }}
              </button>

              <button
                v-if="!hasVoted"
                class="btn-confirm"
                :disabled="selectedTarget === null || isSubmitting"
                @click="confirmVote"
              >
                <span v-if="isSubmitting" class="loading-spinner"></span>
                <span v-else>确认投票</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useGameStore } from '../../stores/gameStore'

// 投票记录接口
interface VoteRecord {
  voterId: number
  targetId: number | null
  weight: number
}

// Props
interface Props {
  modelValue: boolean
  voteType?: 'sheriff' | 'exile'
  timeRemaining?: number
  voteRecords?: VoteRecord[]
  allowClose?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  voteType: 'exile',
  timeRemaining: 60,
  voteRecords: () => [],
  allowClose: true
})

// Emits
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'vote', targetId: number | null): void
  (e: 'close'): void
}>()

const gameStore = useGameStore()

// 本地状态
const selectedTarget = ref<number | null>(null)
const isSubmitting = ref(false)
const recordsListRef = ref<HTMLElement | null>(null)

// 计算属性：弹窗可见性
const isVisible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// 计算属性：标题
const title = computed(() => {
  return props.voteType === 'sheriff' ? '警长投票' : '放逐投票'
})

// 计算属性：描述
const description = computed(() => {
  if (props.voteType === 'sheriff') {
    return '请为你支持的警长候选人投票'
  }
  return '请选择你要放逐的玩家'
})

// 计算属性：我的玩家ID
const myPlayerId = computed(() => gameStore.myPlayer?.id)

// 计算属性：是否是警长
const isSheriff = computed(() => gameStore.myPlayer?.is_sheriff)

// 计算属性：投票候选人列表
const voteCandidates = computed(() => {
  if (props.voteType === 'sheriff') {
    // 警长投票：只能投给竞选者
    return gameStore.players.filter(
      p => p.is_alive && gameStore.sheriffCandidates.includes(p.id)
    )
  }
  // 放逐投票：可以投给除自己外的存活玩家
  return gameStore.players.filter(
    p => p.is_alive && p.id !== myPlayerId.value
  )
})

// 计算属性：总投票人数
const totalVoters = computed(() => {
  return gameStore.players.filter(p => p.is_alive).length
})

// 计算属性：已投票人数
const votedCount = computed(() => {
  return props.voteRecords.length
})

// 计算属性：投票进度百分比
const voteProgressPercent = computed(() => {
  if (totalVoters.value === 0) return 0
  return Math.round((votedCount.value / totalVoters.value) * 100)
})

// 计算属性：倒计时进度
const countdownProgress = computed(() => {
  const maxTime = 60 // 假设最大60秒
  return Math.round((props.timeRemaining / maxTime) * 100)
})

// 计算属性：倒计时颜色
const countdownColorClass = computed(() => {
  if (props.timeRemaining <= 10) return 'text-red-500'
  if (props.timeRemaining <= 30) return 'text-yellow-500'
  return 'text-green-500'
})

// 计算属性：票数统计
const voteCountMap = computed(() => {
  const counts: Record<number, number> = {}
  const sheriffId = gameStore.sheriffId

  for (const record of props.voteRecords) {
    if (record.targetId === null || record.targetId === 0) continue
    const weight = record.voterId === sheriffId ? 2 : 1
    counts[record.targetId] = (counts[record.targetId] || 0) + weight
  }

  return counts
})

// 计算属性：弃票人数
const abstainCount = computed(() => {
  return props.voteRecords.filter(r => r.targetId === null || r.targetId === 0).length
})

// 计算属性：领先候选人ID
const leadingCandidateId = computed(() => {
  let maxVotes = 0
  let leaderId: number | null = null

  for (const [candidateId, votes] of Object.entries(voteCountMap.value)) {
    if (votes > maxVotes) {
      maxVotes = votes
      leaderId = Number(candidateId)
    }
  }

  return leaderId
})

// 计算属性：排序后的投票记录
const sortedVoteRecords = computed(() => {
  return [...props.voteRecords].sort((a, b) => {
    // 自己的投票排在最前面
    if (a.voterId === myPlayerId.value) return -1
    if (b.voterId === myPlayerId.value) return 1
    return a.voterId - b.voterId
  })
})

// 计算属性：是否已投票
const hasVoted = computed(() => {
  return props.voteRecords.some(r => r.voterId === myPlayerId.value)
})

// 计算属性：我的投票目标
const myVoteTarget = computed(() => {
  const myRecord = props.voteRecords.find(r => r.voterId === myPlayerId.value)
  return myRecord?.targetId
})

// 方法：获取票数
function getVoteCount(candidateId: number): number {
  return voteCountMap.value[candidateId] || 0
}

// 方法：是否是领先候选人
function isLeadingCandidate(candidateId: number): boolean {
  return leadingCandidateId.value === candidateId && getVoteCount(candidateId) > 0
}

// 方法：是否有我的投票
function hasMyVote(candidateId: number): boolean {
  return myVoteTarget.value === candidateId
}

// 方法：选择目标
function selectTarget(playerId: number) {
  if (hasVoted.value) return
  selectedTarget.value = playerId
}

// 方法：确认投票
async function confirmVote() {
  if (selectedTarget.value === null || isSubmitting.value || hasVoted.value) return

  isSubmitting.value = true
  try {
    const targetId = selectedTarget.value === 0 ? null : selectedTarget.value
    await gameStore.submitAction('vote', targetId)
    emit('vote', targetId)
    selectedTarget.value = null
  } catch (error) {
    console.error('投票失败:', error)
  } finally {
    isSubmitting.value = false
  }
}

// 方法：关闭弹窗
function close() {
  if (!props.allowClose && !hasVoted.value) return
  emit('close')
  isVisible.value = false
  selectedTarget.value = null
}

// 方法：背景点击
function handleBackdropClick() {
  if (props.allowClose || hasVoted.value) {
    close()
  }
}

// 监听投票记录变化，自动滚动
watch(() => props.voteRecords.length, () => {
  nextTick(() => {
    if (recordsListRef.value) {
      recordsListRef.value.scrollTop = recordsListRef.value.scrollHeight
    }
  })
})
</script>

<style scoped>
/* 弹窗动画 */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: all 0.3s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-from .vote-modal,
.modal-fade-leave-to .vote-modal {
  transform: scale(0.9);
}

/* 缩放进入动画 */
.animate-scale-in {
  animation: scaleIn 0.3s ease-out;
}

@keyframes scaleIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* 弹窗主体 */
.vote-modal {
  background: linear-gradient(180deg, #1a1028 0%, #0f0a1a 100%);
  border: 2px solid rgba(59, 130, 246, 0.5);
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5),
              0 0 40px rgba(59, 130, 246, 0.2);
  overflow: hidden;
}

/* 标题栏 */
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  background: linear-gradient(90deg, rgba(59, 130, 246, 0.2) 0%, transparent 100%);
  border-bottom: 1px solid rgba(59, 130, 246, 0.3);
}

.header-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

/* 倒计时 */
.countdown-wrapper {
  position: relative;
}

.countdown-circle {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.countdown-circle svg {
  transform: rotate(-90deg);
}

.circle-progress {
  transition: stroke-dasharray 1s linear;
}

.countdown-text {
  position: absolute;
  font-size: 14px;
  font-weight: bold;
}

/* 投票进度条 */
.vote-progress-bar {
  padding: 12px 24px;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.progress-track {
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 100%);
  border-radius: 4px;
  transition: width 0.5s ease;
}

/* 主体内容 */
.modal-body {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  padding: 20px 24px;
  max-height: 50vh;
  overflow: hidden;
}

/* 区域标题 */
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #9ca3af;
  margin-bottom: 16px;
}

.section-title .icon {
  font-size: 16px;
}

/* 候选人区域 */
.candidates-section {
  overflow-y: auto;
}

.candidates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

/* 候选人卡片 */
.candidate-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 2px solid transparent;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.candidate-card:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(139, 92, 246, 0.5);
  transform: translateY(-2px);
}

.candidate-card.is-selected {
  background: rgba(59, 130, 246, 0.2);
  border-color: #3b82f6;
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.3);
}

.candidate-card.is-leading {
  border-color: #fbbf24;
}

.candidate-card.has-my-vote {
  background: rgba(34, 197, 94, 0.1);
  border-color: #22c55e;
}

.candidate-avatar {
  position: relative;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  overflow: hidden;
  margin-bottom: 8px;
  border: 2px solid rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
}

.avatar-number {
  font-size: 24px;
  font-weight: bold;
  color: white;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.death-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.candidate-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.candidate-number {
  font-size: 14px;
  font-weight: bold;
  color: white;
}

.candidate-name {
  font-size: 11px;
  color: #9ca3af;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 票数显示 */
.vote-count {
  position: absolute;
  top: -8px;
  right: -8px;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px 8px;
  background: #374151;
  border-radius: 12px;
  font-size: 11px;
  color: #9ca3af;
  transition: all 0.3s ease;
}

.vote-count.has-votes {
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
  color: white;
  animation: voteCountPop 0.3s ease;
}

@keyframes voteCountPop {
  0% { transform: scale(1); }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); }
}

.count-number {
  font-weight: bold;
}

/* 警长标识 */
.sheriff-badge {
  position: absolute;
  top: -4px;
  left: -4px;
  width: 24px;
  height: 24px;
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  box-shadow: 0 0 10px rgba(251, 191, 36, 0.5);
}

/* 选中指示器 */
.selected-indicator {
  position: absolute;
  bottom: -4px;
  left: 50%;
  transform: translateX(-50%);
  width: 24px;
  height: 24px;
  background: #3b82f6;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 14px;
  font-weight: bold;
  animation: indicatorPop 0.3s ease;
}

@keyframes indicatorPop {
  0% { transform: translateX(-50%) scale(0); }
  70% { transform: translateX(-50%) scale(1.2); }
  100% { transform: translateX(-50%) scale(1); }
}

/* 领先标识 */
.leading-badge {
  position: absolute;
  top: 8px;
  left: 50%;
  transform: translateX(-50%);
  padding: 2px 8px;
  background: linear-gradient(90deg, #fbbf24 0%, #f59e0b 100%);
  color: #1f2937;
  font-size: 10px;
  font-weight: bold;
  border-radius: 8px;
}

/* 弃票选项 */
.abstain-option {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 2px dashed rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.abstain-option:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.3);
}

.abstain-option.is-selected {
  background: rgba(107, 114, 128, 0.3);
  border-color: #6b7280;
  border-style: solid;
}

.abstain-icon {
  font-size: 20px;
}

.abstain-text {
  color: #9ca3af;
  font-weight: 500;
}

.abstain-count {
  color: #6b7280;
  font-size: 12px;
}

/* 投票记录区域 */
.vote-records-section {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.records-list {
  flex: 1;
  overflow-y: auto;
  max-height: 300px;
}

/* 投票记录项 */
.vote-record {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  margin-bottom: 8px;
  transition: all 0.2s ease;
}

.vote-record.is-mine {
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.voter-info {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 60px;
}

.voter-number {
  font-size: 13px;
  font-weight: 600;
  color: white;
}

.weight-badge {
  padding: 1px 4px;
  background: #fbbf24;
  color: #1f2937;
  font-size: 10px;
  font-weight: bold;
  border-radius: 4px;
}

.vote-arrow {
  color: #6b7280;
  font-size: 14px;
}

.target-info {
  font-size: 13px;
  font-weight: 600;
  color: white;
}

.target-info.is-abstain {
  color: #6b7280;
}

.abstain-label {
  font-style: italic;
}

/* 记录列表动画 */
.record-list-enter-active {
  transition: all 0.3s ease;
}

.record-list-leave-active {
  transition: all 0.2s ease;
}

.record-list-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.record-list-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

/* 空状态 */
.empty-records {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  color: #6b7280;
}

.empty-icon {
  font-size: 32px;
  margin-bottom: 8px;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.empty-text {
  font-size: 14px;
}

/* 底部操作栏 */
.modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: rgba(0, 0, 0, 0.3);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

/* 提示信息 */
.sheriff-notice,
.voted-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
}

.sheriff-notice {
  background: rgba(251, 191, 36, 0.2);
  color: #fbbf24;
}

.voted-notice {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.notice-icon {
  font-size: 16px;
}

.notice-text strong {
  font-weight: bold;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 12px;
}

.btn-cancel,
.btn-confirm {
  padding: 10px 24px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 14px;
  transition: all 0.2s ease;
  border: none;
  cursor: pointer;
}

.btn-cancel {
  background: #374151;
  color: white;
}

.btn-cancel:hover:not(:disabled) {
  background: #4b5563;
}

.btn-confirm {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-confirm:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.btn-confirm:disabled {
  background: #374151;
  color: #6b7280;
  cursor: not-allowed;
}

/* 加载动画 */
.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 响应式 */
@media (max-width: 768px) {
  .modal-body {
    grid-template-columns: 1fr;
    max-height: 60vh;
  }

  .candidates-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .vote-records-section {
    max-height: 150px;
  }

  .modal-footer {
    flex-direction: column;
    gap: 12px;
  }

  .action-buttons {
    width: 100%;
  }

  .btn-cancel,
  .btn-confirm {
    flex: 1;
  }
}
</style>
