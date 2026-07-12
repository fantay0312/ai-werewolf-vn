import { memo, type CSSProperties, type MouseEvent } from 'react'
import { Skull, Crown } from 'lucide-react'
import { cn } from '../../lib/utils'
import type { Player, SelectionMode } from '../../types'
import { isWolfRole } from '../../types'
import { getPortraitUrl, getRoleName } from '../../lib/roles'

interface PlayerSeatProps {
  player: Player
  isCurrentSpeaker?: boolean
  isSelected?: boolean
  isHovered?: boolean
  isMe?: boolean
  showRole?: boolean
  canSelect?: boolean
  selectionMode?: SelectionMode
  onClick?: (player: Player) => void
  onMouseEnter?: (id: number) => void
  onMouseLeave?: () => void
  onContextMenu?: (player: Player, e: MouseEvent) => void
  className?: string
  style?: CSSProperties
}

const selectionModeIcons: Record<SelectionMode, string> = {
  none: '',
  vote: '✓',
  kill: '🐺',
  check: '🔮',
  protect: '🛡️',
  poison: '☠️',
  save: '💚',
  shoot: '🔫',
}

const selectedFrameColors: Record<SelectionMode, string> = {
  none: 'rgba(100, 116, 139, 0.5)',
  vote: 'rgba(59, 130, 246, 1)',
  kill: 'rgba(244, 63, 94, 1)',
  check: 'rgba(217, 70, 239, 1)',
  protect: 'rgba(6, 182, 212, 1)',
  poison: 'rgba(225, 29, 72, 1)',
  save: 'rgba(16, 185, 129, 1)',
  shoot: 'rgba(249, 115, 22, 1)',
}

function PlayerSeatComponent({
  player,
  isCurrentSpeaker = false,
  isSelected = false,
  isHovered = false,
  isMe = false,
  showRole = false,
  canSelect = false,
  selectionMode = 'none',
  onClick,
  onMouseEnter,
  onMouseLeave,
  onContextMenu,
  className,
  style,
}: PlayerSeatProps) {
  const isDead = !player.is_alive
  const roleName = getRoleName(player.role)
  const portraitUrl = showRole ? getPortraitUrl(player.role) : null

  const cssFrameColor = (() => {
    if (isDead) return 'rgba(159, 18, 57, 0.8)' // rose-900 border
    if (player.is_sheriff) return 'rgba(252, 211, 77, 0.9)' // amber-300
    if (isMe) return 'rgba(56, 189, 248, 1)' // sky-400
    if (isSelected) return selectedFrameColors[selectionMode]
    return 'rgba(255, 255, 255, 0.15)' // default glass border
  })()

  return (
    <div
      className={cn(
        'player-seat-container group',
        isDead ? 'is-dead' : '',
        isCurrentSpeaker && !isDead ? 'is-speaking' : '',
        isSelected ? 'is-selected' : '',
        isHovered && canSelect ? 'is-hovered' : '',
        isMe ? 'is-me' : '',
        canSelect && !isDead ? 'can-select' : '',
        className
      )}
      style={style}
      onClick={() => canSelect && onClick?.(player)}
      onMouseEnter={() => onMouseEnter?.(player.id)}
      onMouseLeave={() => onMouseLeave?.()}
      onContextMenu={(e) => {
        if (onContextMenu) {
          e.preventDefault()
          onContextMenu(player, e)
        }
      }}
    >
      {/* 发言中声波效果 */}
      {isCurrentSpeaker && !isDead && (
        <div className="speaker-wave-container">
          <div className="speaker-wave"></div>
          <div className="speaker-wave" style={{ animationDelay: '0.3s' }}></div>
          <div className="speaker-wave" style={{ animationDelay: '0.6s' }}></div>
        </div>
      )}

      {/* 主体座位徽章 */}
      <div
        className={cn(
          "player-seat relative w-16 h-16 rounded-full flex items-center justify-center transition-all duration-300",
          isDead ? 'dead' : '',
          isSelected ? `selected selected-${selectionMode}` : '',
          player.is_sheriff ? 'is-sheriff' : '',
          isCurrentSpeaker && !isDead ? 'speaking' : '',
          isMe ? 'is-human' : '',
          canSelect && !isDead ? 'selectable' : ''
        )}
      >
        {/* 玻璃态背景与渐变边框 */}
        <div className="absolute inset-0 rounded-full bg-slate-900/40 backdrop-blur-md border border-white/10 shadow-[0_4px_30px_rgba(0,0,0,0.1)] group-hover:bg-slate-800/60 transition-colors duration-300 z-0"></div>

        {/* 发光戒指特效 */}
        <div
          className="glowing-ring absolute inset-0 rounded-full z-0 transition-all duration-300"
          style={{ '--ring-color': cssFrameColor } as CSSProperties}
        ></div>

        {/* Portrait or Number */}
        {portraitUrl && !isDead ? (
          <img
            src={portraitUrl}
            alt={roleName}
            className="absolute inset-0 w-full h-full object-cover rounded-full z-[1]"
          />
        ) : (
          <div className={cn(
            "seat-number relative z-10 text-xl font-bold font-mono tracking-tighter text-white drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)]",
            isDead ? "opacity-0" : "opacity-100"
          )}>
            {player.id}
          </div>
        )}
        {/* Player ID overlay on portrait */}
        {portraitUrl && !isDead && (
          <div className="absolute bottom-0 right-0 z-10 w-5 h-5 rounded-full bg-black/70 flex items-center justify-center text-[10px] font-bold text-white border border-white/30">
            {player.id}
          </div>
        )}

        {/* 死亡标记 */}
        {isDead && (
          <div className="death-overlay absolute inset-0 z-20 flex items-center justify-center bg-black/60 rounded-full backdrop-blur-sm animate-fade-in">
            <Skull className="w-8 h-8 text-rose-500 drop-shadow-[0_0_8px_rgba(244,63,94,0.8)]" />
          </div>
        )}

        {/* 选中指示图标 */}
        {isSelected && (
          <div className={cn(
            "selection-indicator absolute z-30 flex items-center justify-center w-8 h-8 rounded-full shadow-[0_0_15px_currentColor] animate-scale-in",
            `indicator-${selectionMode}`
          )}>
            <span className="text-sm font-bold">{selectionModeIcons[selectionMode]}</span>
          </div>
        )}

        {/* 警长徽章 */}
        {player.is_sheriff && (
          <div className="sheriff-badge absolute -top-2 -right-2 z-30 w-7 h-7 bg-gradient-to-br from-amber-300 to-yellow-600 rounded-full flex items-center justify-center shadow-[0_0_15px_rgba(251,191,36,0.6)] border border-yellow-200/50 animate-scale-in">
            <Crown className="w-4 h-4 text-black drop-shadow-sm" />
          </div>
        )}

        {/* 角色徽章 (下方) */}
        {showRole && (
          <div className={cn(
            "role-badge absolute -bottom-3 left-1/2 transform -translate-x-1/2 z-30 px-2.5 py-0.5 rounded-full text-[10px] font-bold text-white shadow-lg whitespace-nowrap animate-fade-in-up",
            isWolfRole(player.role) ? 'role-wolf' : 'role-good'
          )}>
            {roleName}
          </div>
        )}
      </div>

      {/* 玩家名称 */}
      <div className={cn(
        "player-name absolute top-full left-1/2 transform -translate-x-1/2 mt-3 text-center w-24 pointer-events-none",
        isDead ? 'dead' : ''
      )}>
        <span className="name-text block text-xs font-medium text-slate-200 drop-shadow-md truncate">{player.name}</span>
        {isMe && (
          <span className="me-tag block text-[10px] text-sky-400 font-bold mt-0.5 tracking-wide uppercase">(You)</span>
        )}
      </div>
    </div>
  )
}

// Memoized so a hover (local GameTable state) or a poll refresh only re-renders
// the seats whose props actually changed, not all 12.
export const PlayerSeat = memo(PlayerSeatComponent)
