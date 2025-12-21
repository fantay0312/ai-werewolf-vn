<template>
  <!-- 隐藏状态下的恢复按钮 -->
  <Transition name="button-fade">
    <button
      v-if="isHidden && visible && messages.length > 0"
      @click="toggleVisibility"
      class="restore-button"
      title="显示讨论"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
      <span class="badge" v-if="newMessageCount > 0">{{ newMessageCount }}</span>
    </button>
  </Transition>

  <!-- 对话框主体 -->
  <Transition name="dialog-fade">
    <div
      v-if="visible && messages.length > 0 && !isHidden"
      class="discussion-dialog"
    >
      <div class="dialog-content">
        <!-- 标题栏 -->
        <div class="dialog-header">
          <div class="header-left">
            <span class="dialog-icon">💬</span>
            <span class="dialog-title">{{ dialogTitle }}</span>
            <span class="message-count" v-if="messages.length > 0">{{ messages.length }}</span>
          </div>
          <div class="header-actions">
            <button
              @click="toggleVisibility"
              class="hide-button"
              title="隐藏对话框"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 消息列表 -->
        <div class="messages-container" ref="messagesContainer">
          <div
            v-for="(message, index) in displayedMessages"
            :key="message.id || index"
            class="message-item"
            :class="{ 'is-typing': message.isTyping }"
          >
            <div class="message-header">
              <span class="speaker-name">{{ message.speakerName }}</span>
              <span class="message-time">{{ formatTime(message.timestamp) }}</span>
            </div>
            <div class="message-text">
              <span v-if="!message.isTyping">{{ message.content }}</span>
              <span v-else class="typing-text">{{ message.displayedText }}<span class="cursor">|</span></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted, computed, nextTick } from 'vue'
import { useGameStore } from '../../stores/gameStore'

interface Message {
  id?: string
  speakerName: string
  content: string
  timestamp: number
  isTyping?: boolean
  displayedText?: string
}

const props = defineProps<{
  messages: Message[]
  visible: boolean
  typingSpeed?: number // 打字速度（毫秒/字符）
}>()

const gameStore = useGameStore()

// 根据当前阶段计算对话框标题
const dialogTitle = computed(() => {
  const phase = gameStore.currentPhase
  if (phase === 'NIGHT_WOLF_DISCUSS') {
    return '狼人讨论'
  } else if (phase === 'DAY_DISCUSS') {
    return '玩家讨论'
  }
  return '讨论'
})

const displayedMessages = ref<Message[]>([])
const typingSpeed = props.typingSpeed || 30 // 默认30ms/字符
const isHidden = ref(false)
const lastMessageCount = ref(0)
const messagesContainer = ref<HTMLElement | null>(null)
let typingTimer: ReturnType<typeof setInterval> | null = null

// 计算新消息数量（当对话框隐藏时）
const newMessageCount = computed(() => {
  if (!isHidden.value) return 0
  return Math.max(0, props.messages.length - lastMessageCount.value)
})

// 切换显示/隐藏
function toggleVisibility() {
  isHidden.value = !isHidden.value
  if (!isHidden.value) {
    // 恢复显示时，更新最后消息数量
    lastMessageCount.value = props.messages.length
  }
}

// 格式化时间
function formatTime(timestamp: number): string {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

// 打字机效果
function typeMessage(message: Message, index: number) {
  if (!message.content) return
  
  message.isTyping = true
  message.displayedText = ''
  let charIndex = 0
  
  const typeChar = () => {
    if (charIndex < message.content.length) {
      message.displayedText = message.content.substring(0, charIndex + 1)
      charIndex++
      typingTimer = setTimeout(typeChar, typingSpeed)
    } else {
      message.isTyping = false
      if (typingTimer) {
        clearTimeout(typingTimer)
        typingTimer = null
      }
    }
  }
  
  // 延迟开始，让前一条消息先完成
  setTimeout(() => {
    typeChar()
  }, index * 500) // 每条消息间隔500ms
}

// 自动滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 监听新消息
watch(
  () => props.messages,
  (newMessages, oldMessages) => {
    if (!props.visible) return
    
    // 找出新增的消息
    const oldIds = new Set((oldMessages || []).map(m => m.id || `${m.speakerName}-${m.timestamp}`))
    const newItems = newMessages.filter(m => {
      const id = m.id || `${m.speakerName}-${m.timestamp}`
      return !oldIds.has(id)
    })
    
    // 添加新消息到显示列表
    newItems.forEach((msg) => {
      const messageCopy = { ...msg, isTyping: false, displayedText: '' }
      const msgIndex = displayedMessages.value.length
      displayedMessages.value.push(messageCopy)
      
      // 如果是新消息，使用打字机效果
      if (newItems.length > 0) {
        typeMessage(messageCopy, msgIndex)
      }
    })
    
    // 新消息添加后自动滚动到底部
    if (newItems.length > 0) {
      scrollToBottom()
    }
  },
  { deep: true, immediate: true }
)

// 监听可见性变化
watch(
  () => props.visible,
  (visible) => {
    if (visible && props.messages.length > 0) {
      // 重置显示列表
      displayedMessages.value = []
      lastMessageCount.value = props.messages.length
      
      // 延迟一点再开始显示，让动画更流畅
      setTimeout(() => {
        props.messages.forEach((msg, msgIndex) => {
          const messageCopy = { ...msg, isTyping: false, displayedText: '' }
          displayedMessages.value.push(messageCopy)
          typeMessage(messageCopy, msgIndex)
        })
        // 显示完成后滚动到底部
        scrollToBottom()
      }, 300)
    } else {
      // 清理定时器
      if (typingTimer) {
        clearTimeout(typingTimer)
        typingTimer = null
      }
      displayedMessages.value = []
      isHidden.value = false
    }
  },
  { immediate: true }
)

// 监听消息变化，更新新消息计数
watch(
  () => props.messages.length,
  (newLength) => {
    if (isHidden.value && newLength > lastMessageCount.value) {
      // 有新消息但对话框隐藏，不更新lastMessageCount，让badge显示
    } else if (!isHidden.value) {
      lastMessageCount.value = newLength
    }
  }
)

onUnmounted(() => {
  if (typingTimer) {
    clearTimeout(typingTimer)
  }
})
</script>

<style scoped>
.discussion-dialog {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 60;
  max-width: 800px;
  width: calc(100% - 40px);
  pointer-events: auto;
}

.dialog-content {
  background: linear-gradient(
    135deg,
    rgba(20, 10, 40, 0.75) 0%,
    rgba(40, 20, 60, 0.75) 100%
  );
  backdrop-filter: blur(25px);
  -webkit-backdrop-filter: blur(25px);
  border-radius: 20px;
  border: 1px solid rgba(138, 92, 246, 0.3);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.5),
    0 0 60px rgba(138, 92, 246, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  max-height: 400px;
  transition: all 0.3s ease;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(138, 92, 246, 0.2);
  background: rgba(0, 0, 0, 0.2);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dialog-icon {
  font-size: 1.2rem;
}

.dialog-title {
  font-weight: 700;
  font-size: 0.95rem;
  color: #fbbf24;
  text-shadow: 0 0 8px rgba(251, 191, 36, 0.5);
}

.message-count {
  background: rgba(138, 92, 246, 0.3);
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.hide-button {
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hide-button:hover {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.9);
}

.messages-container {
  padding: 12px 16px;
  overflow-y: auto;
  overflow-x: hidden;
  flex: 1;
  max-height: 330px;
  scroll-behavior: smooth;
}

.messages-container::-webkit-scrollbar {
  width: 8px;
}

.messages-container::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
  margin: 4px 0;
}

.messages-container::-webkit-scrollbar-thumb {
  background: linear-gradient(
    180deg,
    rgba(138, 92, 246, 0.6) 0%,
    rgba(138, 92, 246, 0.4) 100%
  );
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: background 0.2s ease;
}

.messages-container::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(
    180deg,
    rgba(138, 92, 246, 0.8) 0%,
    rgba(138, 92, 246, 0.6) 100%
  );
}

/* 恢复按钮样式 */
.restore-button {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 60;
  background: linear-gradient(
    135deg,
    rgba(20, 10, 40, 0.9) 0%,
    rgba(40, 20, 60, 0.9) 100%
  );
  backdrop-filter: blur(15px);
  border: 1px solid rgba(138, 92, 246, 0.4);
  border-radius: 50px;
  padding: 12px 20px;
  color: #fbbf24;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 
    0 4px 16px rgba(0, 0, 0, 0.4),
    0 0 30px rgba(138, 92, 246, 0.2);
  transition: all 0.3s ease;
  pointer-events: auto;
}

.restore-button:hover {
  background: linear-gradient(
    135deg,
    rgba(30, 15, 50, 0.95) 0%,
    rgba(50, 25, 70, 0.95) 100%
  );
  transform: translateX(-50%) translateY(-2px);
  box-shadow: 
    0 6px 20px rgba(0, 0, 0, 0.5),
    0 0 40px rgba(138, 92, 246, 0.3);
}

.restore-button .badge {
  background: #ef4444;
  color: white;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
  animation: pulse-badge 2s infinite;
}

@keyframes pulse-badge {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.message-item {
  margin-bottom: 12px;
  animation: slideInUp 0.4s ease-out;
}

.message-item:last-child {
  margin-bottom: 0;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.speaker-name {
  font-weight: 700;
  font-size: 0.9rem;
  color: #fbbf24;
  text-shadow: 0 0 8px rgba(251, 191, 36, 0.5);
}

.message-time {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.5);
}

.message-text {
  color: rgba(255, 255, 255, 0.95);
  font-size: 0.95rem;
  line-height: 1.6;
  word-wrap: break-word;
}

.typing-text {
  display: inline-block;
}

.cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background: #fbbf24;
  margin-left: 2px;
  animation: blink 1s infinite;
  vertical-align: baseline;
}

.message-item.is-typing .message-text {
  color: rgba(255, 255, 255, 0.9);
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 淡入淡出过渡 */
.dialog-fade-enter-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.dialog-fade-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.dialog-fade-enter-from {
  opacity: 0;
  transform: translateX(-50%) translateY(30px) scale(0.95);
}

.dialog-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px) scale(0.98);
}

.dialog-fade-enter-to,
.dialog-fade-leave-from {
  opacity: 1;
  transform: translateX(-50%) translateY(0) scale(1);
}

/* 恢复按钮过渡 */
.button-fade-enter-active,
.button-fade-leave-active {
  transition: all 0.3s ease;
}

.button-fade-enter-from,
.button-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(10px) scale(0.9);
}

.button-fade-enter-to,
.button-fade-leave-from {
  opacity: 1;
  transform: translateX(-50%) translateY(0) scale(1);
}
</style>

