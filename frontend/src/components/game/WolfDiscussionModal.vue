<template>
  <Teleport to="body">
    <div
      v-if="isVisible"
      class="fixed inset-0 z-50 flex items-center justify-center"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black bg-opacity-70" @click="close"></div>

      <!-- Modal Content -->
      <div class="relative bg-gray-900 rounded-lg shadow-2xl border border-red-800 w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between p-4 border-b border-red-800 bg-red-900 bg-opacity-30 rounded-t-lg">
          <div class="flex items-center space-x-2">
            <span class="text-2xl">🐺</span>
            <h2 class="text-xl font-bold text-red-400">狼人密谋</h2>
          </div>
          <button
            @click="close"
            class="text-gray-400 hover:text-white transition-colors"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Wolf Team Info -->
        <div class="p-4 border-b border-gray-700 bg-gray-800 bg-opacity-50">
          <h3 class="text-sm font-bold text-gray-400 mb-2">狼队成员</h3>
          <div class="flex flex-wrap gap-2">
            <div
              v-for="wolf in wolfTeam"
              :key="wolf.id"
              :class="[
                'flex items-center px-3 py-1 rounded-full text-sm',
                wolf.is_alive ? 'bg-red-900 bg-opacity-50 text-red-300' : 'bg-gray-700 text-gray-500 line-through'
              ]"
            >
              <span class="font-bold mr-1">{{ wolf.id }}号</span>
              <span class="text-xs opacity-75">{{ wolf.role === 'wolf_king' ? '狼王' : '狼人' }}</span>
              <span v-if="!wolf.is_alive" class="ml-1">💀</span>
            </div>
          </div>
        </div>

        <!-- Discussion Messages -->
        <div class="flex-1 overflow-y-auto p-4 space-y-3 min-h-[200px]" ref="messagesContainer">
          <div
            v-for="(message, index) in wolfMessages"
            :key="index"
            :class="[
              'p-3 rounded-lg',
              message.isSystem ? 'bg-gray-800 text-gray-400 text-sm italic' : 'bg-red-900 bg-opacity-30'
            ]"
          >
            <div v-if="!message.isSystem" class="flex items-center mb-1">
              <span class="font-bold text-red-400">{{ message.playerName }}</span>
              <span class="text-xs text-gray-500 ml-2">{{ formatTime(message.timestamp) }}</span>
            </div>
            <p :class="message.isSystem ? '' : 'text-white'">{{ message.content }}</p>
          </div>

          <div v-if="wolfMessages.length === 0" class="text-center text-gray-500 py-8">
            <p>狼人频道已开启</p>
            <p class="text-sm mt-1">与你的队友讨论今晚的目标...</p>
          </div>
        </div>

        <!-- Target Selection (During Vote Phase) -->
        <div v-if="isVotePhase" class="p-4 border-t border-gray-700 bg-gray-800 bg-opacity-50">
          <h3 class="text-sm font-bold text-yellow-400 mb-3">选择击杀目标</h3>
          <div class="grid grid-cols-4 gap-2">
            <button
              v-for="player in eligibleTargets"
              :key="player.id"
              @click="selectTarget(player.id)"
              :class="[
                'p-2 rounded text-sm font-bold transition-all',
                selectedTarget === player.id
                  ? 'bg-red-600 text-white ring-2 ring-red-400'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              ]"
            >
              {{ player.id }}号
            </button>
          </div>
          <button
            @click="confirmKill"
            :disabled="!selectedTarget"
            :class="[
              'w-full mt-4 py-3 rounded font-bold transition-colors',
              selectedTarget
                ? 'bg-red-600 hover:bg-red-500 text-white'
                : 'bg-gray-700 text-gray-500 cursor-not-allowed'
            ]"
          >
            确认击杀
          </button>
        </div>

        <!-- Input Area (During Discuss Phase) -->
        <div v-else class="p-4 border-t border-gray-700">
          <div class="flex space-x-2">
            <input
              v-model="messageInput"
              type="text"
              placeholder="输入讨论内容..."
              class="flex-1 px-4 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-red-500"
              @keyup.enter="sendMessage"
            />
            <button
              @click="sendMessage"
              class="px-6 py-2 bg-red-600 hover:bg-red-500 rounded-lg font-bold text-white transition-colors"
            >
              发送
            </button>
          </div>
          <p class="text-xs text-gray-500 mt-2">
            * 此频道仅狼人可见
          </p>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useGameStore } from '../../stores/gameStore'

interface WolfMessage {
  playerName: string
  content: string
  timestamp: number
  isSystem: boolean
}

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const gameStore = useGameStore()
const messageInput = ref('')
const selectedTarget = ref<number | null>(null)
const messagesContainer = ref<HTMLElement | null>(null)

// Local messages (would be synced with backend in real implementation)
const wolfMessages = ref<WolfMessage[]>([])

// 检查当前玩家是否是狼人
const isWolf = computed(() => {
  const myRole = gameStore.myPlayer?.role || ''
  return ['wolf', 'wolf_king'].includes(myRole)
})

const isVisible = computed({
  get: () => props.modelValue && isWolf.value, // 只有狼人才能看到
  set: (value) => {
    // 如果不是狼人，不允许打开
    if (!isWolf.value) {
      return
    }
    emit('update:modelValue', value)
  }
})

const isVotePhase = computed(() => gameStore.currentPhase === 'NIGHT_WOLF_VOTE')

const wolfTeam = computed(() => {
  return gameStore.players.filter(p => ['wolf', 'wolf_king'].includes(p.role))
})

const eligibleTargets = computed(() => {
  return gameStore.players.filter(p => p.is_alive && !['wolf', 'wolf_king'].includes(p.role))
})

function close() {
  isVisible.value = false
}

function sendMessage() {
  // 权限检查：只有狼人才能发送消息
  if (!isWolf.value) {
    console.warn('非狼人玩家尝试发送狼人消息')
    return
  }
  
  if (!messageInput.value.trim()) return

  const myPlayer = gameStore.myPlayer
  if (!myPlayer) return

  wolfMessages.value.push({
    playerName: `${myPlayer.id}号`,
    content: messageInput.value,
    timestamp: Date.now(),
    isSystem: false
  })

  // Submit to backend
  gameStore.submitAction('speech', undefined, messageInput.value)

  messageInput.value = ''
  scrollToBottom()
}

function selectTarget(playerId: number) {
  selectedTarget.value = playerId
}

async function confirmKill() {
  if (!selectedTarget.value) return

  await gameStore.submitAction('kill', selectedTarget.value)

  wolfMessages.value.push({
    playerName: '',
    content: `已选择击杀 ${selectedTarget.value}号`,
    timestamp: Date.now(),
    isSystem: true
  })

  selectedTarget.value = null
  close()
}

function formatTime(timestamp: number): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// Watch for new messages from game logs
watch(
  () => gameStore.gameLogs,
  (logs) => {
    // Filter wolf-related logs and convert to local messages
    logs
      .filter(log => log.phase === 'NIGHT_WOLF_DISCUSS' && log.type === 'speech')
      .forEach(log => {
        const exists = wolfMessages.value.some(
          m => m.content === log.content && m.playerName === `${log.player_id}号`
        )
        if (!exists && log.player_id) {
          wolfMessages.value.push({
            playerName: `${log.player_id}号`,
            content: log.content,
            timestamp: Date.now(),
            isSystem: false
          })
        }
      })
  },
  { deep: true }
)
</script>
