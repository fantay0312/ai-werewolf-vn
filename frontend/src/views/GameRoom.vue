<template>
  <div class="game-room h-screen flex relative overflow-hidden" :class="isNight ? 'night-bg' : 'day-bg'">
    <!-- Main Game Area -->
    <div class="flex-1 flex flex-col relative z-0 min-w-0 overflow-hidden">
      <!-- Judge Area (Top) -->
      <div class="h-[100px] flex-shrink-0 z-10">
        <JudgeArea />
      </div>

      <!-- Game Table (Center) -->
      <div class="flex-1 relative flex items-center justify-center p-4 overflow-hidden w-full h-full">
        <div class="w-full h-full flex items-center justify-center transform scale-90 sm:scale-100 transition-transform duration-300">
          <GameTable />
        </div>
      </div>

      <!-- Action Panel (Bottom) -->
      <div class="h-auto min-h-[100px] bg-gray-800 border-t border-gray-700 p-4 z-20">
        <ActionPanel />
      </div>
    </div>

    <!-- Dialog Box (Global Overlay) -->
    <div class="absolute inset-0 z-30 pointer-events-none">
      <DialogBox />
    </div>

    <!-- Side Panel (Right) -->
    <SidePanel @open-wolf-modal="openWolfModal" />

    <!-- Wolf Discussion Modal -->
    <WolfDiscussionModal
      v-model="showWolfModal"
    />

    <!-- Vote Modal -->
    <VoteModal
      v-model="showVoteModal"
      :vote-type="voteType"
      @voted="onVoted"
    />

    <!-- Game End Overlay -->
    <div
      v-if="gameStore.isGameOver"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-80"
    >
      <div class="text-center p-8 bg-gray-900 rounded-lg border-2 border-yellow-500">
        <h1 class="text-4xl font-bold mb-4" :class="winnerTextClass">
          {{ winnerText }}
        </h1>
        <p class="text-gray-400 mb-6">游戏结束</p>
        <button
          @click="returnToHome"
          class="px-8 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg font-bold text-white transition-colors"
        >
          返回首页
        </button>
      </div>
    </div>

    <!-- Loading Overlay (不在夜间非当前角色行动时显示，避免与NightActionAnimation重叠) -->
    <Transition name="loading-fade">
      <div
        v-if="shouldShowLoading"
        class="fixed inset-0 z-40 flex items-center justify-center bg-black bg-opacity-60"
      >
        <div class="loading-spinner-container">
          <div class="loading-spinner">
            <div class="spinner-ring"></div>
            <div class="spinner-ring"></div>
            <div class="spinner-ring"></div>
            <div class="spinner-moon">🌙</div>
          </div>
          <div class="loading-text">{{ gameStore.loadingText }}</div>
          <div class="loading-timer" v-if="loadingElapsed > 3">
            已等待 {{ loadingElapsed }} 秒
          </div>
          <button 
            v-if="loadingElapsed > 5"
            @click="gameStore.cancelLoading()"
            class="loading-cancel-btn"
          >
            取消
          </button>
        </div>
      </div>
    </Transition>

    <!-- Night Action Animation -->
    <NightActionAnimation />

    <!-- Discussion Dialog (Bottom Center) -->
    <DiscussionDialog
      :messages="discussionMessages"
      :visible="showDiscussionDialog"
    />

    <!-- Error Toast -->
    <div
      v-if="gameStore.error"
      class="fixed bottom-20 left-1/2 transform -translate-x-1/2 z-50 px-6 py-3 bg-red-600 text-white rounded-lg shadow-lg"
    >
      {{ gameStore.error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/gameStore'
import GameTable from '../components/game/GameTable.vue'
import ActionPanel from '../components/game/ActionPanel.vue'
import JudgeArea from '../components/game/JudgeArea.vue'
import DialogBox from '../components/game/DialogBox.vue'
import SidePanel from '../components/game/SidePanel.vue'
import WolfDiscussionModal from '../components/game/WolfDiscussionModal.vue'
import VoteModal from '../components/game/VoteModal.vue'
import NightActionAnimation from '../components/game/NightActionAnimation.vue'
import DiscussionDialog from '../components/game/DiscussionDialog.vue'

const router = useRouter()
const gameStore = useGameStore()

// 计算加载已持续的时间（秒）
const loadingElapsed = ref(0)
let loadingTimer: ReturnType<typeof setInterval> | null = null

watch(() => gameStore.isLoading, (loading) => {
  if (loading) {
    loadingElapsed.value = 0
    loadingTimer = setInterval(() => {
      if (gameStore.loadingStartTime > 0) {
        loadingElapsed.value = Math.floor((Date.now() - gameStore.loadingStartTime) / 1000)
      }
    }, 1000)
  } else {
    if (loadingTimer) {
      clearInterval(loadingTimer)
      loadingTimer = null
    }
    loadingElapsed.value = 0
  }
}, { immediate: true })

// 判断是否处于夜间行动阶段（此时NightActionAnimation会显示，不需要Loading Overlay）
const isInNightActionPhase = computed(() => {
  const nightActionPhases = [
    'NIGHT_WOLF_DISCUSS',
    'NIGHT_WOLF_VOTE', 
    'NIGHT_SEER',
    'NIGHT_WITCH',
    'NIGHT_GUARD'
  ]
  return nightActionPhases.includes(gameStore.currentPhase)
})

// 判断当前玩家是否是夜间行动的角色
const isCurrentActionRole = computed(() => {
  const phase = gameStore.currentPhase
  const role = gameStore.myPlayer?.role || ''
  
  if (phase === 'NIGHT_WOLF_DISCUSS' || phase === 'NIGHT_WOLF_VOTE') {
    return ['wolf', 'wolf_king'].includes(role)
  }
  if (phase === 'NIGHT_SEER') return role === 'seer'
  if (phase === 'NIGHT_WITCH') return role === 'witch'
  if (phase === 'NIGHT_GUARD') return role === 'guard'
  return false
})

// 是否应该显示Loading Overlay（夜间非当前角色行动时不显示，使用NightActionAnimation代替）
const shouldShowLoading = computed(() => {
  if (!gameStore.isLoading) return false
  // 如果在夜间阶段且不是当前行动角色，不显示Loading Overlay（NightActionAnimation会显示）
  if (isInNightActionPhase.value && !isCurrentActionRole.value) return false
  return true
})

// 讨论对话框相关
const showDiscussionDialog = computed(() => {
  const phase = gameStore.currentPhase
  const myRole = gameStore.myPlayer?.role || ''
  const isWolfPlayer = ['wolf', 'wolf_king'].includes(myRole)
  
  // 狼人讨论阶段：只有狼人才能看到
  if (phase === 'NIGHT_WOLF_DISCUSS' && isWolfPlayer) {
    return true
  }
  
  // 白天讨论阶段：所有玩家都能看到
  if (phase === 'DAY_DISCUSS') {
    return true
  }
  
  return false
})

// 获取讨论消息
const discussionMessages = computed(() => {
  const phase = gameStore.currentPhase
  const myRole = gameStore.myPlayer?.role || ''
  const isWolfPlayer = ['wolf', 'wolf_king'].includes(myRole)
  
  // 狼人讨论阶段：只显示非公开的狼人消息
  if (phase === 'NIGHT_WOLF_DISCUSS' && isWolfPlayer) {
    const wolfLogs = gameStore.gameLogs.filter(
      log => log.phase === 'NIGHT_WOLF_DISCUSS' && 
             log.type === 'speech' && 
             log.content &&
             !log.is_public // 只显示非公开消息（狼人专属）
    )
    
    return wolfLogs.map(log => {
      // 解析消息内容，提取玩家号和内容
      const match = log.content.match(/^(\d+)号\(狼人\):\s*(.+)$/)
      if (match) {
        return {
          id: log.id,
          speakerName: `${match[1]}号`,
          content: match[2],
          timestamp: Date.now()
        }
      }
      // 如果格式不匹配，尝试直接使用
      return {
        id: log.id,
        speakerName: log.player_id ? `${log.player_id}号` : '未知',
        content: log.content,
        timestamp: Date.now()
      }
    })
  }
  
  // 白天讨论阶段：显示所有公开的讨论消息
  if (phase === 'DAY_DISCUSS') {
    const dayLogs = gameStore.gameLogs.filter(
      log => log.phase === 'DAY_DISCUSS' && 
             log.type === 'speech' && 
             log.content &&
             log.is_public // 只显示公开消息
    )
    
    return dayLogs.map(log => {
      // 解析消息内容，提取玩家号和内容（格式：X号: 内容）
      const match = log.content.match(/^(\d+)号:\s*(.+)$/)
      if (match) {
        return {
          id: log.id,
          speakerName: `${match[1]}号`,
          content: match[2],
          timestamp: Date.now()
        }
      }
      // 如果格式不匹配，尝试直接使用
      return {
        id: log.id,
        speakerName: log.player_id ? `${log.player_id}号` : '未知',
        content: log.content,
        timestamp: Date.now()
      }
    })
  }
  
  return []
})

// Modal states
const showWolfModal = ref(false)
const showVoteModal = ref(false)
const voteType = ref<'exile' | 'sheriff'>('exile')

// Game end computed
const winnerText = computed(() => {
  if (gameStore.winner === 'wolf') return '狼人阵营胜利!'
  if (gameStore.winner === 'good') return '好人阵营胜利!'
  return '游戏结束'
})

const winnerTextClass = computed(() => {
  if (gameStore.winner === 'wolf') return 'text-red-500'
  if (gameStore.winner === 'good') return 'text-green-500'
  return 'text-yellow-500'
})

// 判断是否为夜晚阶段
const isNight = computed(() => {
  const nightPhases = [
    'NIGHT_START',
    'NIGHT_WOLF_DISCUSS',
    'NIGHT_WOLF_VOTE',
    'NIGHT_SEER',
    'NIGHT_WITCH',
    'NIGHT_GUARD',
    'NIGHT_RESOLVE'
  ]
  return nightPhases.includes(gameStore.currentPhase)
})

// Watch for phase changes to auto-open modals
watch(
  () => gameStore.currentPhase,
  (phase: string, oldPhase: string) => {
    const myRole = gameStore.myPlayer?.role || ''
    const isWolfPlayer = ['wolf', 'wolf_king'].includes(myRole)

    // Auto open wolf modal when entering wolf phases (only for wolves)
    if (isWolfPlayer && ['NIGHT_WOLF_DISCUSS', 'NIGHT_WOLF_VOTE'].includes(phase)) {
      if (!['NIGHT_WOLF_DISCUSS', 'NIGHT_WOLF_VOTE'].includes(oldPhase)) {
        // Only auto-open when first entering wolf phase
        showWolfModal.value = true
      }
    }
    // Close wolf modal when leaving night phases entirely
    if (!phase.startsWith('NIGHT_')) {
      showWolfModal.value = false
    }

    // Auto open vote modal during vote phases
    if (phase === 'DAY_VOTE') {
      voteType.value = 'exile'
      showVoteModal.value = true
    } else if (phase === 'SHERIFF_VOTE' && !gameStore.isCandidate) {
      voteType.value = 'sheriff'
      showVoteModal.value = true
    } else {
      showVoteModal.value = false
    }
  }
)

function onVoted(targetId: number) {
  console.log('Voted for:', targetId)
}

function openWolfModal() {
  const myRole = gameStore.myPlayer?.role || ''
  const isWolfPlayer = ['wolf', 'wolf_king'].includes(myRole)
  if (!isWolfPlayer) {
    // 非狼人玩家尝试打开狼人讨论，显示错误提示
    gameStore.error = '仅狼人可以使用此功能'
    setTimeout(() => {
      gameStore.error = null
    }, 3000)
    return
  }
  showWolfModal.value = true
}

function returnToHome() {
  gameStore.clearSession()
  router.push('/')
}

onMounted(() => {
  // Try to recover existing session
  gameStore.recoverSession()

  // If no session, redirect to home
  if (!gameStore.sessionId) {
    router.push('/')
  }
})

onUnmounted(() => {
  gameStore.stopPolling()
})
</script>

<style scoped>
.game-room {
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  background-attachment: fixed;
  transition: background-image 0.5s ease-in-out;
}

/* 夜晚背景 */
.night-bg {
  background-image: url('/images/game-bg.jpg');
}

/* 白天背景 */
.day-bg {
  background-image: url('/images/game-bg2.jpg');
}

/* 加载动画 */
.loading-spinner-container {
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-spinner {
  position: relative;
  width: 120px;
  height: 120px;
}

.spinner-ring {
  position: absolute;
  inset: 0;
  border: 3px solid transparent;
  border-radius: 50%;
  animation: spinnerRotate 1.5s linear infinite;
}

.spinner-ring:nth-child(1) {
  border-top-color: #d4af37;
  animation-duration: 1.5s;
}

.spinner-ring:nth-child(2) {
  inset: 10px;
  border-right-color: #8b5cf6;
  animation-duration: 2s;
  animation-direction: reverse;
}

.spinner-ring:nth-child(3) {
  inset: 20px;
  border-bottom-color: #60a5fa;
  animation-duration: 2.5s;
}

.spinner-moon {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 2.5rem;
  animation: moonPulse 2s ease-in-out infinite;
}

@keyframes spinnerRotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes moonPulse {
  0%, 100% { 
    transform: translate(-50%, -50%) scale(1);
    filter: drop-shadow(0 0 10px rgba(96, 165, 250, 0.5));
  }
  50% { 
    transform: translate(-50%, -50%) scale(1.1);
    filter: drop-shadow(0 0 20px rgba(96, 165, 250, 0.8));
  }
}

/* 加载文本 */
.loading-text {
  margin-top: 20px;
  font-size: 1.1rem;
  color: rgba(255, 255, 255, 0.9);
  text-align: center;
  animation: textPulse 2s ease-in-out infinite;
}

.loading-timer {
  margin-top: 8px;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.5);
}

.loading-cancel-btn {
  margin-top: 16px;
  padding: 8px 24px;
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.5);
  border-radius: 8px;
  color: #f87171;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.loading-cancel-btn:hover {
  background: rgba(239, 68, 68, 0.3);
  border-color: rgba(239, 68, 68, 0.8);
}

@keyframes textPulse {
  0%, 100% { opacity: 0.8; }
  50% { opacity: 1; }
}

/* 加载动画过渡 */
.loading-fade-enter-active,
.loading-fade-leave-active {
  transition: opacity 0.3s ease;
}

.loading-fade-enter-from,
.loading-fade-leave-to {
  opacity: 0;
}
</style>
