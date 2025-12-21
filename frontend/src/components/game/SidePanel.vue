<template>
  <div class="side-panel">
    <!-- 装饰性顶部边框 -->
    <div class="panel-header-decor">
      <div class="decor-line"></div>
      <div class="decor-gem"></div>
      <div class="decor-line"></div>
    </div>

    <!-- 顶部信息栏 -->
    <div class="panel-header">
      <div class="text-center">
        <h2 class="phase-title">{{ phaseText }}</h2>
        <p class="day-info">第 {{ gameStore.currentDay }} 天</p>
      </div>
      <!-- 警长徽章 -->
      <div v-if="gameStore.sheriffId" class="sheriff-badge">
        <span class="sheriff-icon">👮</span>
        <span>警长: {{ gameStore.sheriffId }}号</span>
      </div>
    </div>

    <!-- Tab 切换 -->
    <div class="tab-container">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        @click="activeTab = tab.id"
        :class="['tab-btn', activeTab === tab.id ? 'active' : '']"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        <span class="tab-label">{{ tab.label }}</span>
        <span v-if="tab.id === 'wolf' && !showWolfTab" class="lock-icon">🔒</span>
      </button>
    </div>

    <!-- Tab 内容区域 -->
    <div class="tab-content">
      <!-- 玩家列表 Tab -->
      <div v-if="activeTab === 'players'" class="player-list">
        <div
          v-for="(player, index) in sortedPlayers"
          :key="player.id"
          :class="['player-item', { 
            'is-dead': !player.is_alive, 
            'is-me': player.is_human,
            'even': index % 2 === 0
          }]"
        >
          <!-- 玩家编号徽章 -->
          <div :class="['player-badge', { 
            'is-sheriff': player.is_sheriff,
            'is-dead': !player.is_alive 
          }]">
            <span class="badge-number">{{ player.id }}</span>
            <div v-if="player.is_sheriff" class="sheriff-crown">👑</div>
          </div>

          <!-- 玩家信息 -->
          <div class="player-info">
            <div class="player-name-row">
              <span :class="['player-name', { 'dead': !player.is_alive }]">
                {{ player.name }}
              </span>
              <span v-if="player.is_human" class="you-tag">(你)</span>
            </div>
            <div v-if="showRole(player)" class="player-role">
              <span :class="getRoleBadgeClass(player.role)">{{ getRoleName(player.role) }}</span>
            </div>
          </div>

          <!-- 状态图标 -->
          <div class="player-status">
            <span v-if="!player.is_alive" class="status-dead">💀</span>
            <span v-else-if="player.has_acted" class="status-acted">✓</span>
          </div>
        </div>
      </div>

      <!-- 游戏记录 Tab -->
      <div v-if="activeTab === 'logs'" class="log-list" ref="logListRef">
        <div
          v-for="log in publicLogs"
          :key="log.id"
          :class="['log-item', `log-${log.type}`]"
        >
          <div class="log-content">
            <!-- 数字头像 -->
            <div :class="['log-avatar', log.player_id ? getLogAvatarClass(log.player_id) : 'avatar-system']">
              {{ log.player_id || '📢' }}
            </div>
            <div class="log-text">
              <span v-if="log.player_id" class="log-speaker">{{ log.player_id }}号玩家</span>
              <span v-else class="log-speaker system">系统</span>
              <span class="log-message">{{ formatLogContent(log.content, log.player_id) }}</span>
            </div>
          </div>
          <div class="log-meta">
            第{{ log.day }}天 · {{ formatPhase(log.phase) }}
          </div>
        </div>
        <div v-if="publicLogs.length === 0" class="empty-state">
          <span class="empty-icon">📜</span>
          <p>暂无记录</p>
        </div>
      </div>

      <!-- 狼人密谋 Tab -->
      <div v-if="activeTab === 'wolf'" class="wolf-tab">
        <div v-if="showWolfTab" class="wolf-chat">
          <div class="wolf-header">
            <span class="wolf-icon">🐺</span>
            <span>狼人密谋频道</span>
            <button 
              v-if="isWolfPhase"
              @click="$emit('open-wolf-modal')" 
              class="open-modal-btn"
            >
              💬 打开讨论
            </button>
          </div>
          <div class="wolf-messages">
            <div
              v-for="(msg, index) in wolfMessages"
              :key="index"
              class="wolf-message"
            >
              <span class="wolf-sender">{{ msg.speaker_id }}号:</span>
              <span class="wolf-text">{{ msg.content }}</span>
              <div class="wolf-meta">第{{ msg.round }}轮</div>
            </div>
            <div v-if="wolfMessages.length === 0" class="empty-state wolf-empty">
              <span class="empty-icon">🌙</span>
              <p>暂无狼人讨论</p>
            </div>
          </div>
        </div>
        <div v-else class="locked-tab">
          <span class="lock-big">🔒</span>
          <p>仅狼人可查看</p>
        </div>
      </div>
    </div>

    <!-- 底部统计 -->
    <div class="stats-bar">
      <div class="stat-item alive">
        <span class="stat-label">存活</span>
        <span class="stat-value">{{ aliveCount }}</span>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item dead">
        <span class="stat-label">死亡</span>
        <span class="stat-value">{{ deadCount }}</span>
      </div>
    </div>

    <!-- 阶段提示 -->
    <div class="hint-bar">
      <div class="hint-icon">💡</div>
      <div class="hint-content">
        <span class="hint-label">当前阶段提示:</span>
        <p class="hint-text">{{ phaseHint }}</p>
      </div>
    </div>

    <!-- 装饰性底部边框 -->
    <div class="panel-footer-decor">
      <div class="decor-line"></div>
      <div class="decor-gem small"></div>
      <div class="decor-line"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue'
import { useGameStore } from '../../stores/gameStore'
import { PHASE_NAMES, ROLE_NAMES, type Player, type Role } from '../../types'

const gameStore = useGameStore()
const activeTab = ref<'players' | 'logs' | 'wolf'>('players')
const logListRef = ref<HTMLElement | null>(null)

// Emit
defineEmits<{
  (e: 'open-wolf-modal'): void
}>()

// 自动滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (logListRef.value) {
      logListRef.value.scrollTop = logListRef.value.scrollHeight
    }
  })
}

// 当切换到记录tab或有新日志时滚动到底部
watch(activeTab, (newTab) => {
  if (newTab === 'logs') {
    scrollToBottom()
  }
})

watch(() => gameStore.gameState?.game_logs?.length, () => {
  if (activeTab.value === 'logs') {
    scrollToBottom()
  }
})

// 是否为狼人阶段
const isWolfPhase = computed(() => {
  return ['NIGHT_WOLF_DISCUSS', 'NIGHT_WOLF_VOTE'].includes(gameStore.currentPhase)
})

// Tab配置
const tabs = [
  { id: 'players' as const, label: '玩家', icon: '👥' },
  { id: 'logs' as const, label: '记录', icon: '📜' },
  { id: 'wolf' as const, label: '密谋', icon: '🐺' }
]

// 是否显示狼人Tab
const showWolfTab = computed(() => {
  const myRole = gameStore.myPlayer?.role
  return myRole === 'wolf' || myRole === 'wolf_king'
})

// 排序后的玩家列表
const sortedPlayers = computed(() => {
  return [...gameStore.players].sort((a, b) => a.id - b.id)
})

// 公开日志及玩家自己的私有日志（预言家查验结果等）
const publicLogs = computed(() => {
  const logs = gameStore.gameState?.game_logs || []
  const myId = gameStore.myPlayer?.id
  return logs
    .filter(log => log.is_public || (myId && log.player_id === myId))
    .slice(-20)
})

// 狼人消息
const wolfMessages = computed(() => {
  return gameStore.gameState?.wolf_discuss_messages || []
})

// 存活/死亡统计
const aliveCount = computed(() => gameStore.players.filter(p => p.is_alive).length)
const deadCount = computed(() => gameStore.players.filter(p => !p.is_alive).length)

// 阶段文本
const phaseText = computed(() => {
  return PHASE_NAMES[gameStore.currentPhase as keyof typeof PHASE_NAMES] || gameStore.currentPhase
})

// 阶段提示
const phaseHint = computed(() => {
  const hints: Record<string, string> = {
    GAME_START: '游戏即将开始，请确认你的身份。',
    NIGHT_START: '夜晚降临，请闭眼。',
    NIGHT_WOLF_DISCUSS: '狼人请睁眼，讨论今晚的目标。',
    NIGHT_WOLF_VOTE: '狼人请选择击杀目标。',
    NIGHT_SEER: '预言家请睁眼，选择要查验的玩家。',
    NIGHT_WITCH: '女巫请睁眼，决定是否使用药水。',
    NIGHT_GUARD: '守卫请睁眼，选择要守护的玩家。',
    NIGHT_RESOLVE: '夜晚结束，正在结算...',
    DAY_START: '天亮了，查看昨晚的情况。',
    DAY_LAST_WORDS: '请死亡的玩家发表遗言。',
    SHERIFF_ELECTION: '警长竞选开始，选择是否上警。',
    SHERIFF_SPEECH: '候选人发表竞选演讲。',
    SHERIFF_VOTE: '请为警长候选人投票。',
    DAY_DISCUSS: '白天讨论时间，自由发言。',
    DAY_VOTE: '投票时间，选择要放逐的玩家。',
    DAY_VOTE_RESULT: '投票结束，公布结果。',
    DAY_PK_SPEECH: '平票PK，候选人进行PK发言。',
    DAY_PK_VOTE: 'PK投票，请在候选人中选择。',
    DAY_PK_RESULT: 'PK投票结束，公布结果。',
    HUNTER_SKILL: '猎人/狼王可以发动技能。',
    SHERIFF_TRANSFER: '警长移交警徽。',
    GAME_END: '游戏结束！'
  }
  return hints[gameStore.currentPhase] || '等待中...'
})

// 是否显示角色
function showRole(player: Player): boolean {
  return player.is_human || !player.is_alive
}

// 获取角色名称
function getRoleName(role: string): string {
  return ROLE_NAMES[role as Role] || role
}

// 获取角色徽章样式
function getRoleBadgeClass(role: string): string {
  const classes: Record<string, string> = {
    wolf: 'role-wolf',
    wolf_king: 'role-wolf-king',
    seer: 'role-seer',
    witch: 'role-witch',
    guard: 'role-guard',
    hunter: 'role-hunter',
    villager: 'role-villager'
  }
  return classes[role] || 'role-villager'
}

// 格式化阶段
function formatPhase(phase: string): string {
  return PHASE_NAMES[phase as keyof typeof PHASE_NAMES] || phase
}

// 获取日志头像样式
function getLogAvatarClass(playerId: number): string {
  const player = gameStore.players.find(p => p.id === playerId)
  if (!player) return 'avatar-default'
  if (player.is_human) return 'avatar-me'
  if (!player.is_alive) {
    const role = player.role
    if (role === 'wolf' || role === 'wolf_king') return 'avatar-wolf'
    return 'avatar-good'
  }
  return 'avatar-default'
}

// 格式化日志内容（去掉开头的"X号:"）
function formatLogContent(content: string, playerId: number | undefined): string {
  if (playerId) {
    // 去掉开头的 "X号:" 或 "X号: " 格式
    return content.replace(new RegExp(`^${playerId}号[：::]\\s*`), '')
  }
  return content
}
</script>

<style scoped>
/* ========== 主面板样式 - 玻璃态设计 ========== */
.side-panel {
  width: 300px;
  min-width: 300px;
  height: 100%;
  display: flex;
  flex-direction: column;
  
  /* 玻璃态效果 */
  background: linear-gradient(
    135deg,
    rgba(20, 10, 30, 0.85) 0%,
    rgba(30, 15, 45, 0.9) 50%,
    rgba(25, 12, 38, 0.85) 100%
  );
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  
  /* 边框发光 */
  border-left: 1px solid rgba(138, 92, 246, 0.3);
  box-shadow: 
    -5px 0 30px rgba(138, 92, 246, 0.1),
    inset 1px 0 0 rgba(255, 255, 255, 0.05);
}

/* ========== 装饰边框 ========== */
.panel-header-decor,
.panel-footer-decor {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  gap: 8px;
}

.decor-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, 
    transparent 0%, 
    rgba(212, 175, 55, 0.5) 50%, 
    transparent 100%
  );
}

.decor-gem {
  width: 12px;
  height: 12px;
  background: linear-gradient(135deg, #d4af37 0%, #f4d03f 50%, #d4af37 100%);
  transform: rotate(45deg);
  box-shadow: 0 0 10px rgba(212, 175, 55, 0.5);
  animation: gemGlow 2s ease-in-out infinite;
}

.decor-gem.small {
  width: 8px;
  height: 8px;
}

@keyframes gemGlow {
  0%, 100% { box-shadow: 0 0 10px rgba(212, 175, 55, 0.5); }
  50% { box-shadow: 0 0 20px rgba(212, 175, 55, 0.8); }
}

/* ========== 顶部信息栏 ========== */
.panel-header {
  padding: 16px 20px;
  background: linear-gradient(180deg, 
    rgba(138, 92, 246, 0.1) 0%, 
    transparent 100%
  );
  border-bottom: 1px solid rgba(138, 92, 246, 0.2);
}

.phase-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #f4d03f;
  text-shadow: 0 0 20px rgba(244, 208, 63, 0.5);
  letter-spacing: 2px;
  margin: 0;
}

.day-info {
  font-size: 0.875rem;
  color: rgba(255, 255, 255, 0.6);
  margin-top: 4px;
  letter-spacing: 1px;
}

.sheriff-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  padding: 6px 14px;
  background: linear-gradient(135deg, rgba(212, 175, 55, 0.2) 0%, rgba(212, 175, 55, 0.1) 100%);
  border: 1px solid rgba(212, 175, 55, 0.4);
  border-radius: 20px;
  font-size: 0.8rem;
  color: #f4d03f;
}

.sheriff-icon {
  font-size: 1rem;
}

/* ========== Tab 切换 ========== */
.tab-container {
  display: flex;
  border-bottom: 1px solid rgba(138, 92, 246, 0.2);
}

.tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 12px 8px;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
}

.tab-btn:hover {
  color: rgba(255, 255, 255, 0.8);
  background: rgba(138, 92, 246, 0.1);
}

.tab-btn.active {
  color: #a78bfa;
  background: rgba(138, 92, 246, 0.15);
}

.tab-btn.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 20%;
  right: 20%;
  height: 2px;
  background: linear-gradient(90deg, transparent, #a78bfa, transparent);
}

.tab-icon {
  font-size: 1rem;
}

.lock-icon {
  font-size: 0.7rem;
  margin-left: 2px;
}

/* ========== Tab 内容区域 ========== */
.tab-content {
  flex: 1;
  overflow: hidden;
}

/* ========== 玩家列表 ========== */
.player-list {
  height: 100%;
  overflow-y: auto;
  padding: 8px;
}

.player-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: 8px;
  transition: all 0.2s ease;
  background: rgba(255, 255, 255, 0.02);
}

.player-item.even {
  background: rgba(138, 92, 246, 0.05);
}

.player-item:hover {
  background: rgba(138, 92, 246, 0.1);
  transform: translateX(2px);
}

.player-item.is-me {
  background: linear-gradient(90deg, 
    rgba(59, 130, 246, 0.15) 0%, 
    rgba(59, 130, 246, 0.05) 100%
  );
  border-left: 2px solid #3b82f6;
}

.player-item.is-dead {
  opacity: 0.5;
}

/* 玩家徽章 */
.player-badge {
  position: relative;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #374151 0%, #1f2937 100%);
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  transform: rotate(0deg);
  transition: all 0.3s ease;
}

.player-badge.is-sheriff {
  background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%);
  border-color: #f4d03f;
  box-shadow: 0 0 15px rgba(212, 175, 55, 0.4);
}

.player-badge.is-dead {
  background: linear-gradient(135deg, #7f1d1d 0%, #450a0a 100%);
  border-color: rgba(239, 68, 68, 0.3);
}

.badge-number {
  font-size: 0.9rem;
  font-weight: 700;
  color: white;
}

.sheriff-crown {
  position: absolute;
  top: -10px;
  right: -6px;
  font-size: 0.8rem;
  animation: crownBounce 1s ease-in-out infinite;
}

@keyframes crownBounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-2px); }
}

/* 玩家信息 */
.player-info {
  flex: 1;
  min-width: 0;
}

.player-name-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.player-name {
  font-size: 0.9rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.player-name.dead {
  color: rgba(255, 255, 255, 0.4);
  text-decoration: line-through;
}

.you-tag {
  font-size: 0.7rem;
  color: #60a5fa;
  font-weight: 600;
}

.player-role {
  margin-top: 2px;
  font-size: 0.75rem;
}

/* 角色颜色 */
.role-wolf, .role-wolf-king { color: #f87171; }
.role-seer { color: #c084fc; }
.role-witch { color: #4ade80; }
.role-guard { color: #fbbf24; }
.role-hunter { color: #fb923c; }
.role-villager { color: #9ca3af; }

/* 状态图标 */
.player-status {
  font-size: 1rem;
}

.status-dead { color: #ef4444; }
.status-acted { color: #22c55e; }

/* ========== 日志列表 ========== */
.log-list {
  height: 100%;
  overflow-y: auto;
  padding: 8px;
}

.log-item {
  padding: 10px 12px;
  margin-bottom: 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
  border-left: 3px solid transparent;
  transition: all 0.2s ease;
}

.log-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.log-speech { border-left-color: #6b7280; }
.log-death { border-left-color: #ef4444; background: rgba(239, 68, 68, 0.1); }
.log-vote { border-left-color: #3b82f6; }
.log-skill { border-left-color: #a855f7; }
.log-system { border-left-color: #f4d03f; }
.log-judge { border-left-color: #f4d03f; }

.log-content {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

/* 日志数字头像 */
.log-avatar {
  width: 32px;
  height: 32px;
  min-width: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  font-weight: 700;
  color: white;
  border: 2px solid;
}

.log-avatar.avatar-default {
  background: linear-gradient(135deg, #374151 0%, #1f2937 100%);
  border-color: rgba(255, 255, 255, 0.2);
}

.log-avatar.avatar-me {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border-color: #60a5fa;
  box-shadow: 0 0 10px rgba(59, 130, 246, 0.4);
}

.log-avatar.avatar-wolf {
  background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
  border-color: #f87171;
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.4);
}

.log-avatar.avatar-good {
  background: linear-gradient(135deg, #22c55e 0%, #15803d 100%);
  border-color: #4ade80;
  box-shadow: 0 0 10px rgba(34, 197, 94, 0.4);
}

.log-avatar.avatar-system {
  background: linear-gradient(135deg, #d4af37 0%, #b8860b 100%);
  border-color: #f4d03f;
  box-shadow: 0 0 10px rgba(212, 175, 55, 0.4);
  font-size: 0.9rem;
}

.log-text {
  flex: 1;
  line-height: 1.5;
  min-width: 0;
}

.log-speaker {
  display: block;
  font-weight: 600;
  color: #f4d03f;
  font-size: 0.8rem;
  margin-bottom: 2px;
}

.log-speaker.system {
  color: #fbbf24;
}

.log-message {
  display: block;
  color: rgba(255, 255, 255, 0.85);
  font-size: 0.85rem;
  word-break: break-word;
}

.log-meta {
  margin-top: 6px;
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.4);
  text-align: right;
}

/* ========== 狼人频道 ========== */
.wolf-tab {
  height: 100%;
}

.wolf-chat {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, rgba(127, 29, 29, 0.1) 0%, transparent 100%);
}

.wolf-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  color: #f87171;
  font-weight: 600;
  border-bottom: 1px solid rgba(239, 68, 68, 0.2);
  flex-wrap: wrap;
}

.wolf-icon {
  font-size: 1rem;
}

.open-modal-btn {
  padding: 4px 12px;
  font-size: 0.75rem;
  background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
  color: white;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.open-modal-btn:hover {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  transform: scale(1.05);
}

.wolf-messages {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.wolf-message {
  padding: 10px;
  margin-bottom: 8px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 8px;
}

.wolf-sender {
  color: #f87171;
  font-weight: 600;
  margin-right: 6px;
}

.wolf-text {
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.85rem;
}

.wolf-meta {
  margin-top: 4px;
  font-size: 0.7rem;
  color: rgba(248, 113, 113, 0.5);
  text-align: right;
}

.locked-tab {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.3);
}

.lock-big {
  font-size: 3rem;
  margin-bottom: 12px;
}

/* ========== 空状态 ========== */
.empty-state {
  text-align: center;
  padding: 32px;
  color: rgba(255, 255, 255, 0.4);
}

.empty-icon {
  font-size: 2rem;
  display: block;
  margin-bottom: 8px;
}

.wolf-empty {
  color: rgba(248, 113, 113, 0.4);
}

/* ========== 底部统计 ========== */
.stats-bar {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.2);
  border-top: 1px solid rgba(138, 92, 246, 0.2);
}

.stat-item {
  flex: 1;
  text-align: center;
}

.stat-label {
  display: block;
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 2px;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
}

.stat-item.alive .stat-value { color: #4ade80; }
.stat-item.dead .stat-value { color: #f87171; }

.stat-divider {
  width: 1px;
  height: 30px;
  background: rgba(255, 255, 255, 0.1);
}

/* ========== 阶段提示 ========== */
.hint-bar {
  display: flex;
  gap: 10px;
  padding: 12px 16px;
  background: rgba(138, 92, 246, 0.05);
  border-top: 1px solid rgba(138, 92, 246, 0.1);
}

.hint-icon {
  font-size: 1.2rem;
  flex-shrink: 0;
}

.hint-content {
  flex: 1;
}

.hint-label {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.5);
}

.hint-text {
  margin-top: 2px;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.5;
}

/* ========== 滚动条样式 ========== */
.player-list::-webkit-scrollbar,
.log-list::-webkit-scrollbar,
.wolf-messages::-webkit-scrollbar {
  width: 4px;
}

.player-list::-webkit-scrollbar-track,
.log-list::-webkit-scrollbar-track,
.wolf-messages::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
}

.player-list::-webkit-scrollbar-thumb,
.log-list::-webkit-scrollbar-thumb,
.wolf-messages::-webkit-scrollbar-thumb {
  background: rgba(138, 92, 246, 0.3);
  border-radius: 2px;
}

.player-list::-webkit-scrollbar-thumb:hover,
.log-list::-webkit-scrollbar-thumb:hover,
.wolf-messages::-webkit-scrollbar-thumb:hover {
  background: rgba(138, 92, 246, 0.5);
}
</style>
