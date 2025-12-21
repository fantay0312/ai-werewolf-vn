<template>
  <div
    class="player-seat-container"
    :class="containerClasses"
  >
    <!-- 发言中声波效果 -->
    <div v-if="isCurrentSpeaker && player.is_alive" class="speaker-wave-container">
      <div class="speaker-wave"></div>
      <div class="speaker-wave" style="animation-delay: 0.3s"></div>
      <div class="speaker-wave" style="animation-delay: 0.6s"></div>
    </div>

    <!-- 主体座位徽章 -->
    <div class="player-seat" :class="seatClasses">
      <!-- 徽章装饰边框 -->
      <div class="badge-frame">
        <svg viewBox="0 0 100 100" class="frame-svg">
          <defs>
            <linearGradient id="goldGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style="stop-color:#d4af37"/>
              <stop offset="50%" style="stop-color:#f4d03f"/>
              <stop offset="100%" style="stop-color:#d4af37"/>
            </linearGradient>
            <linearGradient id="silverGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style="stop-color:#6b7280"/>
              <stop offset="50%" style="stop-color:#9ca3af"/>
              <stop offset="100%" style="stop-color:#6b7280"/>
            </linearGradient>
          </defs>
          <!-- 盾形路径 -->
          <path 
            d="M50 5 L90 20 L90 55 Q90 75 50 95 Q10 75 10 55 L10 20 Z"
            :fill="!player.is_alive ? 'rgba(0,0,0,0.6)' : 'rgba(20,10,30,0.8)'"
            :stroke="frameStroke"
            stroke-width="3"
          />
        </svg>
      </div>

      <!-- 玩家编号 -->
      <div class="seat-number">{{ player.id }}</div>

      <!-- 死亡标记 -->
      <Transition name="death-fade">
        <div v-if="!player.is_alive" class="death-overlay">
          <span class="death-icon">💀</span>
        </div>
      </Transition>

      <!-- 选中指示图标 -->
      <Transition name="indicator-pop">
        <div v-if="isSelected" class="selection-indicator" :class="selectionIndicatorClass">
          <span>{{ selectionIcon }}</span>
        </div>
      </Transition>

      <!-- 警长徽章 -->
      <Transition name="badge-pop">
        <div v-if="player.is_sheriff" class="sheriff-badge">
          <span>👑</span>
        </div>
      </Transition>

      <!-- 角色徽章 -->
      <Transition name="role-fade">
        <div v-if="showRole" class="role-badge" :class="roleBadgeClass">
          {{ roleName }}
        </div>
      </Transition>
    </div>

    <!-- 玩家名称 -->
    <div class="player-name" :class="{ dead: !player.is_alive }">
      <span class="name-text">{{ player.name }}</span>
      <span v-if="isMe" class="me-tag">(你)</span>
    </div>

    <!-- 标记系统 -->
    <div v-if="markers && markers.length > 0" class="markers-container">
      <div
        v-for="marker in markers"
        :key="marker.type"
        class="player-marker"
        :class="getMarkerClass(marker)"
        :title="marker.label || marker.type"
      >
        {{ getMarkerIcon(marker) }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Player, Role } from '../../types'
import { ROLE_NAMES, isWolfRole } from '../../types'

interface PlayerMarker {
  type: 'wolf' | 'good' | 'suspicious' | 'trusted' | 'custom'
  label?: string
  color?: string
}

type SelectionMode = 'none' | 'vote' | 'kill' | 'check' | 'protect' | 'poison' | 'save' | 'shoot'

interface Props {
  player: Player
  isCurrentSpeaker?: boolean
  isSelected?: boolean
  isHovered?: boolean
  isMe?: boolean
  showRole?: boolean
  canSelect?: boolean
  selectionMode?: SelectionMode
  markers?: PlayerMarker[]
}

const props = withDefaults(defineProps<Props>(), {
  isCurrentSpeaker: false,
  isSelected: false,
  isHovered: false,
  isMe: false,
  showRole: false,
  canSelect: false,
  selectionMode: 'none',
  markers: () => []
})

const containerClasses = computed(() => ({
  'is-dead': !props.player.is_alive,
  'is-speaking': props.isCurrentSpeaker && props.player.is_alive,
  'is-selected': props.isSelected,
  'is-hovered': props.isHovered && props.canSelect,
  'is-me': props.isMe,
  'can-select': props.canSelect && props.player.is_alive
}))

const seatClasses = computed(() => {
  const classes: string[] = []
  if (!props.player.is_alive) classes.push('dead')
  if (props.isSelected) {
    classes.push('selected', `selected-${props.selectionMode}`)
  }
  if (props.player.is_sheriff) classes.push('is-sheriff')
  if (props.isCurrentSpeaker && props.player.is_alive) classes.push('speaking')
  if (props.isMe) classes.push('is-human')
  if (props.canSelect && props.player.is_alive) classes.push('selectable')
  return classes
})

const frameStroke = computed(() => {
  if (!props.player.is_alive) return '#7f1d1d'
  if (props.player.is_sheriff) return 'url(#goldGradient)'
  if (props.isMe) return '#3b82f6'
  if (props.isSelected) {
    const colors: Record<SelectionMode, string> = {
      none: '#6b7280',
      vote: '#3b82f6',
      kill: '#dc2626',
      check: '#8b5cf6',
      protect: '#06b6d4',
      poison: '#dc2626',
      save: '#22c55e',
      shoot: '#f97316'
    }
    return colors[props.selectionMode]
  }
  return 'url(#silverGradient)'
})

const roleBadgeClass = computed(() => {
  return isWolfRole(props.player.role) ? 'role-wolf' : 'role-good'
})

const roleName = computed(() => {
  return ROLE_NAMES[props.player.role as Role] || props.player.role
})

const selectionIcon = computed(() => {
  const icons: Record<SelectionMode, string> = {
    none: '',
    vote: '✓',
    kill: '🐺',
    check: '🔮',
    protect: '🛡️',
    poison: '☠️',
    save: '💚',
    shoot: '🔫'
  }
  return icons[props.selectionMode]
})

const selectionIndicatorClass = computed(() => `indicator-${props.selectionMode}`)

function getMarkerClass(marker: PlayerMarker): string {
  const classes: Record<string, string> = {
    wolf: 'marker-wolf',
    good: 'marker-good',
    suspicious: 'marker-suspicious',
    trusted: 'marker-trusted',
    custom: 'marker-custom'
  }
  return classes[marker.type] || 'marker-custom'
}

function getMarkerIcon(marker: PlayerMarker): string {
  const icons: Record<string, string> = {
    wolf: '🐺',
    good: '😇',
    suspicious: '❓',
    trusted: '✓',
    custom: '📌'
  }
  return icons[marker.type] || '📌'
}
</script>

<style scoped>
/* ========== 容器 ========== */
.player-seat-container {
  position: relative;
  width: 50px;
  height: 60px;
  transition: all 0.3s ease;
  z-index: 1;
}

.player-seat-container.is-speaking { z-index: 10; }
.player-seat-container.is-selected { z-index: 5; }

.player-seat-container.can-select {
  cursor: pointer;
}

.player-seat-container.can-select:hover .player-seat {
  transform: scale(1.15);
}

.player-seat-container.can-select:hover .badge-frame {
  filter: brightness(1.3);
}

/* ========== 座位主体 ========== */
.player-seat {
  position: relative;
  width: 50px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.badge-frame {
  position: absolute;
  inset: 0;
  transition: filter 0.3s ease;
}

.frame-svg {
  width: 100%;
  height: 100%;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
}

/* ========== 编号 ========== */
.seat-number {
  position: relative;
  z-index: 2;
  font-size: 18px;
  font-weight: 700;
  color: white;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
  margin-top: -4px;
}

/* ========== 死亡状态 ========== */
.death-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3;
}

.death-icon {
  font-size: 24px;
  filter: grayscale(0.5);
  animation: deathFloat 3s ease-in-out infinite;
}

@keyframes deathFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-3px); }
}

.player-seat.dead .badge-frame {
  filter: grayscale(0.8) brightness(0.6);
}

.player-seat.dead .seat-number {
  opacity: 0.3;
}

/* ========== 发言状态 ========== */
.player-seat.speaking {
  animation: speakerPulse 2s ease-in-out infinite;
}

@keyframes speakerPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.speaker-wave-container {
  position: absolute;
  inset: -10px;
  pointer-events: none;
}

.speaker-wave {
  position: absolute;
  inset: 0;
  border: 2px solid rgba(244, 208, 63, 0.6);
  border-radius: 50%;
  animation: waveExpand 1.5s ease-out infinite;
}

@keyframes waveExpand {
  0% { transform: scale(0.8); opacity: 0.8; }
  100% { transform: scale(1.6); opacity: 0; }
}

/* ========== 选中状态 ========== */
.player-seat.selected { transform: scale(1.1); }

.selection-indicator {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  z-index: 4;
  box-shadow: 0 0 15px currentColor;
}

.indicator-vote { background: rgba(59, 130, 246, 0.9); color: #3b82f6; }
.indicator-kill { background: rgba(220, 38, 38, 0.9); color: #dc2626; }
.indicator-check { background: rgba(139, 92, 246, 0.9); color: #8b5cf6; }
.indicator-protect { background: rgba(6, 182, 212, 0.9); color: #06b6d4; }
.indicator-poison { background: rgba(220, 38, 38, 0.9); color: #dc2626; }
.indicator-save { background: rgba(34, 197, 94, 0.9); color: #22c55e; }
.indicator-shoot { background: rgba(249, 115, 22, 0.9); color: #f97316; }

/* ========== 警长徽章 ========== */
.sheriff-badge {
  position: absolute;
  top: -8px;
  right: -4px;
  width: 22px;
  height: 22px;
  background: linear-gradient(135deg, #d4af37 0%, #f4d03f 50%, #d4af37 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  z-index: 5;
  box-shadow: 0 0 12px rgba(212, 175, 55, 0.6);
  animation: crownGlow 2s ease-in-out infinite;
}

@keyframes crownGlow {
  0%, 100% { box-shadow: 0 0 12px rgba(212, 175, 55, 0.6); }
  50% { box-shadow: 0 0 20px rgba(212, 175, 55, 0.9); }
}

/* ========== 角色徽章 ========== */
.role-badge {
  position: absolute;
  bottom: -2px;
  left: 50%;
  transform: translateX(-50%);
  padding: 2px 6px;
  border-radius: 8px;
  font-size: 9px;
  font-weight: 700;
  white-space: nowrap;
  z-index: 5;
}

.role-wolf {
  background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
  color: white;
  box-shadow: 0 0 8px rgba(220, 38, 38, 0.5);
}

.role-good {
  background: linear-gradient(135deg, #22c55e 0%, #15803d 100%);
  color: white;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.5);
}

/* ========== 玩家名称 ========== */
.player-name {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-top: 4px;
  text-align: center;
  width: 70px;
  pointer-events: none;
}

.name-text {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.player-name.dead .name-text {
  color: rgba(255, 255, 255, 0.4);
  text-decoration: line-through;
}

.me-tag {
  display: block;
  font-size: 9px;
  color: #60a5fa;
  font-weight: 700;
}

/* ========== 标记系统 ========== */
.markers-container {
  position: absolute;
  top: calc(100% + 20px);
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 3px;
  pointer-events: none;
}

.player-marker {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  pointer-events: auto;
  cursor: help;
  transition: transform 0.2s ease;
}

.player-marker:hover { transform: scale(1.2); }

.marker-wolf { background: rgba(220, 38, 38, 0.8); }
.marker-good { background: rgba(34, 197, 94, 0.8); }
.marker-suspicious { background: rgba(251, 191, 36, 0.8); }
.marker-trusted { background: rgba(59, 130, 246, 0.8); }
.marker-custom { background: rgba(107, 114, 128, 0.8); }

/* ========== 动画 ========== */
.death-fade-enter-active { transition: all 0.5s ease; }
.death-fade-leave-active { transition: all 0.3s ease; }
.death-fade-enter-from, .death-fade-leave-to { opacity: 0; }

.badge-pop-enter-active { transition: all 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55); }
.badge-pop-leave-active { transition: all 0.2s ease; }
.badge-pop-enter-from, .badge-pop-leave-to { opacity: 0; transform: scale(0); }

.indicator-pop-enter-active { animation: indicatorPopIn 0.3s ease-out; }
.indicator-pop-leave-active { animation: indicatorPopOut 0.2s ease-in; }

@keyframes indicatorPopIn {
  0% { transform: translate(-50%, -50%) scale(0); }
  70% { transform: translate(-50%, -50%) scale(1.2); }
  100% { transform: translate(-50%, -50%) scale(1); }
}

@keyframes indicatorPopOut {
  0% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
  100% { transform: translate(-50%, -50%) scale(0); opacity: 0; }
}

.role-fade-enter-active { transition: all 0.3s ease; }
.role-fade-leave-active { transition: all 0.2s ease; }
.role-fade-enter-from { opacity: 0; transform: translateX(-50%) translateY(5px); }
.role-fade-leave-to { opacity: 0; }

/* ========== 响应式 ========== */
@media (max-width: 768px) {
  .player-seat-container { width: 40px; height: 50px; }
  .player-seat { width: 40px; height: 50px; }
  .seat-number { font-size: 14px; }
  .sheriff-badge { width: 18px; height: 18px; font-size: 10px; }
  .name-text { font-size: 9px; }
  .role-badge { font-size: 7px; padding: 1px 4px; }
}
</style>
