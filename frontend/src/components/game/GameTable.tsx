import { useCallback, useMemo, useState, type CSSProperties, type MouseEvent, type ReactNode } from 'react'
import { Moon, Sun, Vote, Swords, Eye, Shield, Skull, Heart, Crosshair, type LucideIcon } from 'lucide-react'
import { cn } from '../../lib/utils'
import { useGameStore } from '../../store/useGameStore'
import { PlayerSeat, type BubbleAlign } from './PlayerSeat'
import type { Player, SelectionMode } from '../../types'
import { isWolfRole } from '../../types'
import { isNightPhase, parseSpeechLine } from '../../lib/phases'

interface GameTableProps {
  selectionMode?: SelectionMode
  selectedTargetId?: number | null
  currentSpeakerId?: number | null
  onSelectPlayer?: (playerId: number) => void
  onHoverPlayer?: (playerId: number | null) => void
  onRightClickPlayer?: (playerId: number, e: MouseEvent) => void
  children?: ReactNode
}

const PLAYER_COUNT = 12
const ANGLE_PER_PLAYER = 360 / PLAYER_COUNT

// Seat positions depend only on the (fixed) player id, so precompute them once
// at module scope. Passing a stable style reference keeps memo(PlayerSeat)
// effective — a fresh object literal per render would defeat it.
const SEAT_POSITIONS: Record<number, CSSProperties> = (() => {
  const positions: Record<number, CSSProperties> = {}
  const radius = 42
  for (let id = 1; id <= PLAYER_COUNT; id++) {
    const angleRadians = ((id - 1) * ANGLE_PER_PLAYER - 90) * (Math.PI / 180)
    positions[id] = {
      left: `${50 + radius * Math.cos(angleRadians)}%`,
      top: `${50 + radius * Math.sin(angleRadians)}%`,
    }
  }
  return positions
})()

function getPlayerPositionStyle(playerId: number): CSSProperties {
  return SEAT_POSITIONS[playerId] ?? { left: '50%', top: '50%' }
}

// Anchor the seat speech bubble inward for edge seats so it never runs off the
// board: left-side seats extend right ('start'), right-side seats extend left
// ('end'), top/bottom-centre seats stay centred.
const SEAT_BUBBLE_ALIGN: Record<number, BubbleAlign> = {
  1: 'center', 7: 'center',
  8: 'start', 9: 'start', 10: 'start', 11: 'start', 12: 'start',
  2: 'end', 3: 'end', 4: 'end', 5: 'end', 6: 'end',
}

export function GameTable({
  selectionMode = 'none',
  selectedTargetId = null,
  currentSpeakerId = null,
  onSelectPlayer,
  onHoverPlayer,
  onRightClickPlayer,
  children
}: GameTableProps) {
  const [hoveredPlayerId, setHoveredPlayerId] = useState<number | null>(null)

  // Connect to global store
  const players = useGameStore(state => state.gameState?.players || [])
  const myPlayer = useGameStore(state => state.gameState?.players.find(p => p.is_human))
  const currentPhase = useGameStore(state => state.gameState?.phase || '')
  const isGameOver = useGameStore(state => state.gameState?.phase === 'GAME_END')
  const gameLogs = useGameStore(state => state.gameState?.game_logs)

  const isNight = isNightPhase(currentPhase)

  // The current speaker's latest public speech, as a short seat-bubble excerpt.
  // Full text always lives in the DiscussionDialog feed; the bubble is capped by
  // CSS to ~220px + 2 lines so it can never span the board.
  const speakerExcerpt = useMemo(() => {
    if (!currentSpeakerId || !gameLogs) return null
    for (let i = gameLogs.length - 1; i >= 0; i--) {
      const log = gameLogs[i]
      if (log.player_id === currentSpeakerId && log.is_public && log.type === 'speech') {
        return parseSpeechLine(log.content, log.player_id).text || null
      }
    }
    return null
  }, [currentSpeakerId, gameLogs])

  // Stable seat callbacks so hovering one seat re-renders only the two affected
  // seats (enter + leave), not all 12.
  const handleSeatClick = useCallback(
    (player: Player) => onSelectPlayer?.(player.id),
    [onSelectPlayer]
  )
  const handleSeatEnter = useCallback((id: number) => {
    setHoveredPlayerId(id)
    onHoverPlayer?.(id)
  }, [onHoverPlayer])
  const handleSeatLeave = useCallback(() => {
    setHoveredPlayerId(null)
    onHoverPlayer?.(null)
  }, [onHoverPlayer])
  const handleSeatContext = useCallback(
    (player: Player, e: MouseEvent) => onRightClickPlayer?.(player.id, e),
    [onRightClickPlayer]
  )

  const selectionModeStyle = (() => {
    const styles: Record<SelectionMode, { Icon: LucideIcon | null; text: string; glowClass: string; textClass: string }> = {
      none: { Icon: null, text: '', glowClass: '', textClass: '' },
      vote: { Icon: Vote, text: '选择要投票的玩家', glowClass: 'ring-2 ring-blue-500/50 shadow-[0_0_15px_rgba(59,130,246,0.5)]', textClass: 'text-blue-400 font-bold' },
      kill: { Icon: Swords, text: '选择今晚要击杀的目标', glowClass: 'ring-2 ring-rose-500/50 shadow-[0_0_15px_rgba(244,63,94,0.5)]', textClass: 'text-rose-400 font-bold' },
      check: { Icon: Eye, text: '选择要查验的玩家', glowClass: 'ring-2 ring-[#c5a059]/50 shadow-[0_0_15px_rgba(197,160,89,0.5)]', textClass: 'text-[#c5a059] font-bold' },
      protect: { Icon: Shield, text: '选择要守护的玩家', glowClass: 'ring-2 ring-cyan-500/50 shadow-[0_0_15px_rgba(6,182,212,0.5)]', textClass: 'text-cyan-400 font-bold' },
      poison: { Icon: Skull, text: '选择要毒杀的玩家', glowClass: 'ring-2 ring-rose-600/50 shadow-[0_0_15px_rgba(225,29,72,0.5)]', textClass: 'text-rose-500 font-bold' },
      save: { Icon: Heart, text: '选择要救的玩家', glowClass: 'ring-2 ring-emerald-500/50 shadow-[0_0_15px_rgba(16,185,129,0.5)]', textClass: 'text-emerald-400 font-bold' },
      shoot: { Icon: Crosshair, text: '选择要开枪带走的玩家', glowClass: 'ring-2 ring-orange-500/50 shadow-[0_0_15px_rgba(249,115,22,0.5)]', textClass: 'text-orange-400 font-bold' }
    }
    return styles[selectionMode] || styles['none']
  })()
  const HintIcon = selectionModeStyle.Icon

  function shouldShowRole(player: Player): boolean {
    if (player.is_human) return true
    if (isGameOver) return true
    if (myPlayer && isWolfRole(myPlayer.role) && isWolfRole(player.role)) return true
    return false
  }

  function canSelectPlayer(player: Player): boolean {
    if (selectionMode === 'none') return false
    if (!player.is_alive) return false
    if (!myPlayer) return false

    switch (selectionMode) {
      case 'vote': return player.id !== myPlayer.id
      case 'kill': return true
      case 'check': return player.id !== myPlayer.id
      case 'protect': return true
      case 'poison': return player.id !== myPlayer.id
      case 'save': return true
      case 'shoot': return player.id !== myPlayer.id
      default: return false
    }
  }

  return (
    <div className={cn("game-table", isNight ? "night-mode" : "day-mode")}>
      {/* 放射状布局容器 */}
      <div className="radial-layout">
        {/* 中心装饰圆环 */}
        <div className="center-decor">
          <svg className="center-ring" viewBox="0 0 200 200">
            <defs>
              <linearGradient id="dayGlow" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style={{ stopColor: '#f59e0b', stopOpacity: 0.8 }} />
                <stop offset="50%" style={{ stopColor: '#fcd34d', stopOpacity: 1 }} />
                <stop offset="100%" style={{ stopColor: '#f59e0b', stopOpacity: 0.8 }} />
              </linearGradient>
              <linearGradient id="nightGlow" x1="0%" y1="100%" x2="100%" y2="0%">
                <stop offset="0%" style={{ stopColor: '#38bdf8', stopOpacity: 0.7 }} />
                <stop offset="50%" style={{ stopColor: '#c084fc', stopOpacity: 1 }} />
                <stop offset="100%" style={{ stopColor: '#38bdf8', stopOpacity: 0.7 }} />
              </linearGradient>
              <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>
            
            <circle 
              cx="100" cy="100" r="95" 
              fill="none" 
              stroke={isNight ? 'rgba(56, 189, 248, 0.1)' : 'rgba(251, 191, 36, 0.1)'} 
              strokeWidth="1"
              className="outermost-ring"
            />

            <circle 
              cx="100" cy="100" r="85" 
              fill="none" 
              stroke={isNight ? 'url(#nightGlow)' : 'url(#dayGlow)'} 
              strokeWidth="1.5"
              strokeDasharray="4,8"
              className="outer-ring"
              filter="url(#glow)"
            />
            
            <circle 
              cx="100" cy="100" r="65" 
              fill="none" 
              stroke={isNight ? 'rgba(192, 132, 252, 0.2)' : 'rgba(252, 211, 77, 0.2)'} 
              strokeWidth="8"
              className="middle-ring"
            />

            <circle 
              cx="100" cy="100" r="45" 
              fill="none" 
              stroke={isNight ? 'url(#nightGlow)' : 'url(#dayGlow)'} 
              strokeWidth="2"
              strokeDasharray="30,10"
              className="inner-ring"
              filter="url(#glow)"
            />
            
            <path 
              d="M100 0 L100 15 M100 185 L100 200 M0 100 L15 100 M185 100 L200 100"
              stroke={isNight ? 'rgba(56, 189, 248, 0.4)' : 'rgba(251, 191, 36, 0.4)'}
              strokeWidth="1.5"
            />

            <g className="decor-dots">
              {Array.from({ length: 12 }).map((_, i) => (
                <circle 
                  key={i}
                  cx={100 + 75 * Math.cos((i) * 30 * Math.PI / 180 - Math.PI / 2)}
                  cy={100 + 75 * Math.sin((i) * 30 * Math.PI / 180 - Math.PI / 2)}
                  r="2.5"
                  fill={isNight ? '#38bdf8' : '#fbbf24'}
                  filter="url(#glow)"
                />
              ))}
            </g>
          </svg>
          
          <div className={cn("center-icon", isNight ? "night" : "")}>
            {isNight ? (
              <Moon className="w-12 h-12 text-blue-400" fill="currentColor" strokeWidth={1} />
            ) : (
              <Sun className="w-12 h-12 text-amber-400" fill="currentColor" strokeWidth={2} />
            )}
          </div>
        </div>

        {/* 玩家座位 */}
        {players.map(player => (
          <PlayerSeat
            key={player.id}
            player={player}
            isCurrentSpeaker={currentSpeakerId === player.id}
            isSelected={selectedTargetId === player.id}
            isHovered={hoveredPlayerId === player.id}
            isMe={myPlayer?.id === player.id}
            showRole={shouldShowRole(player)}
            canSelect={canSelectPlayer(player)}
            selectionMode={selectionMode}
            speechExcerpt={currentSpeakerId === player.id ? speakerExcerpt : null}
            bubbleAlign={SEAT_BUBBLE_ALIGN[player.id] ?? 'center'}
            className="player-seat"
            style={getPlayerPositionStyle(player.id)}
            onClick={handleSeatClick}
            onMouseEnter={handleSeatEnter}
            onMouseLeave={handleSeatLeave}
            onContextMenu={handleSeatContext}
          />
        ))}

        {/* 中央区域插槽 */}
        <div className="center-slot">
          {children}
        </div>
      </div>

      {/* 选择模式提示 */}
      {selectionMode !== 'none' && (
        <div className="selection-hint">
          <div className={cn("hint-content backdrop-blur-xl bg-[#141210]/85 shadow-[var(--shadow-ambient)] border border-[color:var(--border-gilded)] animate-fade-in-up", selectionModeStyle.glowClass)}>
            {HintIcon && <HintIcon className={cn("w-4 h-4", selectionModeStyle.textClass)} strokeWidth={1.5} />}
            <span className={cn("hint-text text-sm tracking-wide", selectionModeStyle.textClass)}>
              {selectionModeStyle.text}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
