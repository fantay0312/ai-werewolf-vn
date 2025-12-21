<template>
  <div
    ref="tableRef"
    class="game-table"
    :class="{ 'night-mode': isNight, 'day-mode': !isNight }"
  >
    <!-- 放射状布局容器 -->
    <div class="radial-layout">
      <!-- 中心装饰圆环 -->
      <div class="center-decor">
        <svg class="center-ring" viewBox="0 0 200 200">
          <defs>
            <!-- 日光渐变 -->
            <linearGradient id="dayGlow" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style="stop-color:#d4af37;stop-opacity:0.6"/>
              <stop offset="50%" style="stop-color:#f4d03f;stop-opacity:0.8"/>
              <stop offset="100%" style="stop-color:#d4af37;stop-opacity:0.6"/>
            </linearGradient>
            <!-- 月光渐变 -->
            <linearGradient id="nightGlow" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style="stop-color:#3b82f6;stop-opacity:0.4"/>
              <stop offset="50%" style="stop-color:#60a5fa;stop-opacity:0.6"/>
              <stop offset="100%" style="stop-color:#3b82f6;stop-opacity:0.4"/>
            </linearGradient>
          </defs>
          
          <!-- 外圈装饰 -->
          <circle 
            cx="100" cy="100" r="90" 
            fill="none" 
            :stroke="isNight ? 'url(#nightGlow)' : 'url(#dayGlow)'" 
            stroke-width="1"
            stroke-dasharray="10,5"
            class="outer-ring"
          />
          
          <!-- 内圈 -->
          <circle 
            cx="100" cy="100" r="45" 
            fill="none" 
            :stroke="isNight ? 'rgba(96, 165, 250, 0.3)' : 'rgba(251, 191, 36, 0.3)'" 
            stroke-width="2"
            class="inner-ring"
          />
          
          <!-- 装饰点 -->
          <g class="decor-dots">
            <circle 
              v-for="i in 12" 
              :key="i"
              :cx="100 + 75 * Math.cos((i - 1) * 30 * Math.PI / 180 - Math.PI / 2)"
              :cy="100 + 75 * Math.sin((i - 1) * 30 * Math.PI / 180 - Math.PI / 2)"
              r="3"
              :fill="isNight ? 'rgba(96, 165, 250, 0.6)' : 'rgba(251, 191, 36, 0.6)'"
            />
          </g>
        </svg>
        
        <!-- 中心图标 -->
        <div class="center-icon" :class="{ night: isNight }">
          {{ isNight ? '🌙' : '☀️' }}
        </div>
      </div>

      <!-- 玩家座位 -->
      <PlayerSeat
        v-for="player in players"
        :key="player.id"
        :player="player"
        :is-current-speaker="currentSpeakerId === player.id"
        :is-selected="selectedTargetId === player.id"
        :is-hovered="hoveredPlayerId === player.id"
        :is-me="myPlayerId === player.id"
        :show-role="shouldShowRole(player)"
        :can-select="canSelectPlayer(player)"
        :selection-mode="selectionMode"
        :style="getPlayerPositionStyle(player.id)"
        class="player-seat"
        @click="handlePlayerClick(player)"
        @mouseenter="handlePlayerHover(player.id)"
        @mouseleave="handlePlayerHover(null)"
        @contextmenu.prevent="handlePlayerRightClick(player, $event)"
      />

      <!-- 中央区域插槽 -->
      <div class="center-slot">
        <slot name="center"></slot>
      </div>
    </div>

    <!-- 选择模式提示 -->
    <Transition name="mode-hint">
      <div v-if="selectionMode !== 'none'" class="selection-hint">
        <div class="hint-content" :class="selectionModeStyle.borderClass">
          <span class="hint-icon">{{ selectionModeStyle.icon }}</span>
          <span class="hint-text" :class="selectionModeStyle.textClass">
            {{ selectionModeStyle.text }}
          </span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useGameStore } from '../../stores/gameStore'
import PlayerSeat from './PlayerSeat.vue'
import type { Player, GamePhase } from '../../types'
import { isWolfRole } from '../../types'

interface Props {
  selectionMode?: SelectionMode
  selectedTargetId?: number | null
  currentSpeakerId?: number | null
}

type SelectionMode = 'none' | 'vote' | 'kill' | 'check' | 'protect' | 'poison' | 'save' | 'shoot'

const props = withDefaults(defineProps<Props>(), {
  selectionMode: 'none',
  selectedTargetId: null,
  currentSpeakerId: null
})

const emit = defineEmits<{
  (e: 'select-player', playerId: number): void
  (e: 'hover-player', playerId: number | null): void
  (e: 'right-click-player', playerId: number, event: MouseEvent): void
}>()

const gameStore = useGameStore()
const hoveredPlayerId = ref<number | null>(null)
const tableRef = ref<HTMLElement | null>(null)

const PLAYER_COUNT = 12
const ANGLE_PER_PLAYER = 360 / PLAYER_COUNT

const players = computed(() => gameStore.players)
const myPlayerId = computed(() => gameStore.myPlayer?.id)

const isNight = computed(() => {
  const nightPhases: GamePhase[] = [
    'NIGHT_START', 'NIGHT_WOLF_DISCUSS', 'NIGHT_WOLF_VOTE',
    'NIGHT_SEER', 'NIGHT_WITCH', 'NIGHT_GUARD', 'NIGHT_RESOLVE'
  ]
  return nightPhases.includes(gameStore.currentPhase as GamePhase)
})

const selectionModeStyle = computed(() => {
  const styles: Record<SelectionMode, { icon: string; text: string; borderClass: string; textClass: string }> = {
    none: { icon: '', text: '', borderClass: '', textClass: '' },
    vote: { icon: '🗳️', text: '选择要投票的玩家', borderClass: 'border-blue', textClass: 'text-blue' },
    kill: { icon: '🐺', text: '选择今晚要击杀的目标', borderClass: 'border-red', textClass: 'text-red' },
    check: { icon: '🔮', text: '选择要查验的玩家', borderClass: 'border-purple', textClass: 'text-purple' },
    protect: { icon: '🛡️', text: '选择要守护的玩家', borderClass: 'border-cyan', textClass: 'text-cyan' },
    poison: { icon: '☠️', text: '选择要毒杀的玩家', borderClass: 'border-red', textClass: 'text-red' },
    save: { icon: '💚', text: '选择要救的玩家', borderClass: 'border-green', textClass: 'text-green' },
    shoot: { icon: '🔫', text: '选择要开枪带走的玩家', borderClass: 'border-orange', textClass: 'text-orange' }
  }
  return styles[props.selectionMode] || styles['none']
})

function getPlayerPositionStyle(playerId: number) {
  const angleDegrees = (playerId - 1) * ANGLE_PER_PLAYER - 90
  const angleRadians = angleDegrees * (Math.PI / 180)
  const radius = 42
  const x = 50 + radius * Math.cos(angleRadians)
  const y = 50 + radius * Math.sin(angleRadians)
  return { left: `${x}%`, top: `${y}%` }
}

function shouldShowRole(player: Player): boolean {
  if (player.is_human) return true
  if (!player.is_alive) return true
  const myPlayer = gameStore.myPlayer
  if (myPlayer && isWolfRole(myPlayer.role) && isWolfRole(player.role)) return true
  return false
}

function canSelectPlayer(player: Player): boolean {
  if (props.selectionMode === 'none') return false
  if (!player.is_alive) return false
  const myPlayer = gameStore.myPlayer
  if (!myPlayer) return false

  switch (props.selectionMode) {
    case 'vote': return player.id !== myPlayer.id
    case 'kill': return !isWolfRole(player.role)
    case 'check': return player.id !== myPlayer.id
    case 'protect': return true
    case 'poison': return player.id !== myPlayer.id
    case 'save': return true
    case 'shoot': return player.id !== myPlayer.id
    default: return false
  }
}

function handlePlayerClick(player: Player) {
  if (canSelectPlayer(player)) {
    emit('select-player', player.id)
  }
}

function handlePlayerHover(playerId: number | null) {
  hoveredPlayerId.value = playerId
  emit('hover-player', playerId)
}

function handlePlayerRightClick(player: Player, event: MouseEvent) {
  emit('right-click-player', player.id, event)
}
</script>

<style scoped>
/* ========== 游戏桌面 ========== */
.game-table {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

/* ========== 放射状布局 ========== */
.radial-layout {
  position: relative;
  width: min(70vmin, 100%);
  height: min(70vmin, 100%);
  max-width: 520px;
  max-height: 520px;
  aspect-ratio: 1;
}

/* ========== 中心装饰 ========== */
.center-decor {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.center-ring {
  width: 100%;
  height: 100%;
}

.outer-ring {
  animation: rotateRing 60s linear infinite;
  transform-origin: center;
}

@keyframes rotateRing {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.inner-ring {
  animation: pulseRing 3s ease-in-out infinite;
}

@keyframes pulseRing {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.6; }
}

.decor-dots circle {
  animation: twinkleDot 2s ease-in-out infinite;
}

.decor-dots circle:nth-child(odd) {
  animation-delay: 0.5s;
}

@keyframes twinkleDot {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

.center-icon {
  position: absolute;
  font-size: 3rem;
  animation: floatIcon 3s ease-in-out infinite;
  filter: drop-shadow(0 0 20px rgba(251, 191, 36, 0.5));
}

.center-icon.night {
  filter: drop-shadow(0 0 20px rgba(96, 165, 250, 0.5));
}

@keyframes floatIcon {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-5px) scale(1.05); }
}

/* ========== 玩家座位 ========== */
.player-seat {
  position: absolute;
  z-index: 30;
  transform: translate(-50%, -50%);
}

/* ========== 中央插槽 ========== */
.center-slot {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 20;
}

/* ========== 选择模式提示 ========== */
.selection-hint {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 40;
}

.hint-content {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(10px);
  border-radius: 30px;
  border: 2px solid;
}

.hint-icon {
  font-size: 1.25rem;
}

.hint-text {
  font-size: 0.9rem;
  font-weight: 500;
}

/* 颜色变体 */
.border-blue { border-color: rgba(59, 130, 246, 0.6); }
.border-red { border-color: rgba(239, 68, 68, 0.6); }
.border-purple { border-color: rgba(168, 85, 247, 0.6); }
.border-cyan { border-color: rgba(6, 182, 212, 0.6); }
.border-green { border-color: rgba(34, 197, 94, 0.6); }
.border-orange { border-color: rgba(249, 115, 22, 0.6); }

.text-blue { color: #60a5fa; }
.text-red { color: #f87171; }
.text-purple { color: #c084fc; }
.text-cyan { color: #22d3ee; }
.text-green { color: #4ade80; }
.text-orange { color: #fb923c; }

/* ========== 提示动画 ========== */
.mode-hint-enter-active {
  animation: hintSlideIn 0.3s ease-out;
}

.mode-hint-leave-active {
  animation: hintSlideOut 0.2s ease-in;
}

@keyframes hintSlideIn {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

@keyframes hintSlideOut {
  from {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
  to {
    opacity: 0;
    transform: translateX(-50%) translateY(20px);
  }
}

/* ========== 日夜模式 ========== */
.night-mode, .day-mode {
  background: transparent;
}
</style>
