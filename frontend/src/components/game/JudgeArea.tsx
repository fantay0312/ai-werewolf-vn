import { useEffect, useMemo, useRef, type ReactNode } from 'react'
import { Moon, Sun, Gavel, Megaphone } from 'lucide-react'
import { useGameStore } from '../../store/useGameStore'
import { PHASE_NAMES, type GameLog } from '../../types'
import { cn } from '../../lib/utils'
import { isNightPhase, stripSpeakerPrefix } from '../../lib/phases'
import { usePhaseCountdown } from '../../hooks/usePhaseCountdown'

// Phases that show a countdown ring. The actual budget comes from the server
// snapshot (usePhaseCountdown), which is the authoritative per-phase limit.
const TIMED_PHASES = new Set([
  'NIGHT_WOLF_DISCUSS',
  'NIGHT_WOLF_VOTE',
  'NIGHT_SEER',
  'NIGHT_WITCH',
  'NIGHT_GUARD',
  'DAY_DISCUSS',
  'DAY_VOTE',
  'SHERIFF_SPEECH',
  'SHERIFF_VOTE',
  'DAY_LAST_WORDS',
])

export function JudgeArea() {
  const broadcastContainerRef = useRef<HTMLDivElement>(null)

  // Narrow subscriptions: only re-render when these slices change.
  const currentPhase = useGameStore(state => state.gameState?.phase || '')
  const currentDay = useGameStore(state => state.gameState?.day || 1)
  const gameLogs = useGameStore(state => state.gameState?.game_logs)
  const players = useGameStore(state => state.gameState?.players)
  const { remaining: localTimeRemaining, budget: maxTime } = usePhaseCountdown()

  const showTimer = TIMED_PHASES.has(currentPhase)
  const isNight = isNightPhase(currentPhase)
  const phaseText = PHASE_NAMES[currentPhase as keyof typeof PHASE_NAMES] || currentPhase

  const timerProgress = Math.min(100, (localTimeRemaining / (maxTime || 60)) * 100)
  const timerColorClass = timerProgress > 60 ? 'text-green-400 stroke-green-400' : timerProgress > 30 ? 'text-yellow-400 stroke-yellow-400' : 'text-red-400 stroke-red-400 animate-pulse'

  // The judge banner carries judge/system broadcasts ONLY. Player speech lives in
  // the DiscussionDialog feed + a short seat bubble, so excluding speech here
  // removes the three-copies-of-one-sentence redundancy on screen.
  const recentBroadcasts = useMemo(() => {
    const logs = gameLogs || []
    return logs.filter(log => log.is_public && log.type !== 'speech').slice(-8)
  }, [gameLogs])

  useEffect(() => {
    if (broadcastContainerRef.current) {
      setTimeout(() => {
        if (broadcastContainerRef.current) {
          broadcastContainerRef.current.scrollTop = broadcastContainerRef.current.scrollHeight
        }
      }, 50)
    }
  }, [recentBroadcasts.length])

  function getSpeakerDisplay(log: GameLog): ReactNode {
    if (log.player_id) return String(log.player_id)
    return <Megaphone className="w-3.5 h-3.5" strokeWidth={1.5} />
  }

  function getSpeakerAvatarClass(log: GameLog) {
    if (!log.player_id) return 'bg-gradient-to-br from-yellow-500 to-yellow-700 border-yellow-500/60 text-[0.75rem]'
    const player = players?.find(p => p.id === log.player_id)
    if (!player) return 'bg-gradient-to-br from-gray-700 to-gray-900 border-white/15'
    if (player.is_human) return 'bg-gradient-to-br from-blue-500 to-blue-800 border-blue-400'
    if (!player.is_alive) return 'bg-gradient-to-br from-gray-600 to-gray-800 border-white/15 opacity-60'
    return 'bg-gradient-to-br from-gray-700 to-gray-900 border-white/15'
  }

  function getSpeakerName(log: GameLog) {
    return log.player_id ? `${log.player_id}号` : '系统'
  }

  function formatContent(log: GameLog) {
    return stripSpeakerPrefix(log.content, log.player_id)
  }

  function getTypeBorderClass(type: string) {
    switch(type) {
      case 'death': return 'border-l-red-400/60'
      case 'vote': return 'border-l-blue-400/60'
      case 'skill': return 'border-l-amber-600/60'
      case 'system': return 'border-l-yellow-400/50'
      case 'speech': return 'border-l-white/15'
      case 'judge': return 'border-l-yellow-500/50'
      case 'broadcast': return 'border-l-yellow-400/50'
      default: return 'border-l-transparent'
    }
  }

  function getTypeTextColor(type: string) {
     if (type === 'death') return 'text-red-400/90'
     return 'text-white/85'
  }

  function getTypeSpeakerColor(type: string) {
     if (type === 'death') return 'text-red-400/80'
     return 'text-[#f4d03f]/80'
  }

  return (
    <div className="judge-area flex items-center gap-4 py-2.5 px-5 h-full bg-[#141210]/92 border-b border-[color:var(--border-gilded)] shadow-[0_2px_12px_rgba(0,0,0,0.3)]">

      {/* Phase Info */}
      <div className="phase-info flex items-center gap-2.5 shrink-0">
        <div className={cn(isNight ? "text-[#93b4e8] drop-shadow-[0_0_6px_rgba(96,165,250,0.4)]" : "text-[#d4a83c] drop-shadow-[0_0_6px_rgba(197,160,89,0.4)]")}>
          {isNight
            ? <Moon className="w-7 h-7" fill="currentColor" strokeWidth={1} />
            : <Sun className="w-7 h-7" fill="currentColor" strokeWidth={1.5} />}
        </div>
        <div className="flex flex-col">
          <span className="text-[0.7rem] text-parchment-dim tracking-[1px]">第 {currentDay} 天</span>
          <span className={cn("font-display text-[1.2rem] font-bold tracking-[2px]", isNight ? "text-[#93b4e8]" : "text-[#d4a83c]")}>{phaseText}</span>
        </div>
      </div>

      {/* Broadcast Area — the tabletop host's banner */}
      <div className="flex-1 flex items-stretch gap-3 bg-black/25 border border-[color:var(--border-gilded)] rounded-[10px] px-3 py-2 h-20 overflow-hidden">
        <div className="flex flex-col items-center justify-center shrink-0 w-12">
          <div className="w-[38px] h-[38px] flex items-center justify-center bg-gradient-to-br from-[#8b6914] to-[#5a4410] rounded-lg border border-[#c5a059]/60 text-[#f4d9a0]">
            <Gavel className="w-5 h-5" strokeWidth={1.5} />
          </div>
          <span className="text-[0.6rem] text-[#f4d03f]/70 mt-[3px] tracking-[1px] font-display">法官</span>
        </div>

        <div className="flex-1 min-w-0 flex flex-col justify-center">
          <div className="overflow-y-auto overflow-x-hidden max-h-[72px] scroll-smooth pr-1 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent" ref={broadcastContainerRef}>
            <div className="flex flex-col gap-[3px]">
              {recentBroadcasts.map((log) => (
                <div key={log.id} className={cn("flex items-center gap-2 px-2 py-1 rounded-md bg-white/5 border-l-2 animate-slide-in", getTypeBorderClass(log.type))}>
                  <div className={cn("w-6 h-6 min-w-[24px] rounded-[5px] flex items-center justify-center text-[0.7rem] font-bold text-white border-[1.5px] shrink-0", getSpeakerAvatarClass(log))}>
                    {getSpeakerDisplay(log)}
                  </div>
                  <div className="flex-1 min-w-0 flex items-center gap-1.5">
                    <span className={cn("text-[0.7rem] font-semibold whitespace-nowrap shrink-0", getTypeSpeakerColor(log.type))}>{getSpeakerName(log)}</span>
                    <span className={cn("text-[0.75rem] leading-snug whitespace-nowrap overflow-hidden text-ellipsis flex-1", getTypeTextColor(log.type))}>{formatContent(log)}</span>
                  </div>
                </div>
              ))}
              {recentBroadcasts.length === 0 && (
                <div className="flex items-center justify-center text-[0.75rem] text-white/25 p-3">
                  等待游戏开始...
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Timer Area */}
      {showTimer && (
        <div className="relative w-14 h-14 shrink-0">
          <div className="relative w-full h-full">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
              <path className="fill-none stroke-white/10 stroke-[3px]" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              <path className={cn("fill-none stroke-[3px] stroke-linecap-round transition-[stroke-dasharray] duration-1000 linear", timerColorClass.split(' ')[1])} strokeDasharray={`${timerProgress}, 100`} d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
            </svg>
            <span className={cn("absolute inset-0 flex items-center justify-center text-base font-bold", timerColorClass.split(' ')[0])}>{localTimeRemaining}</span>
          </div>
        </div>
      )}

    </div>
  )
}
