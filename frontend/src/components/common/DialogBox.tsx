import { useEffect, useMemo, useState } from 'react'
import { MessageCircle, ChevronDown, X, Gavel } from 'lucide-react'
import { useGameStore } from '../../store/useGameStore'
import { TypeWriter } from '../ui/TypeWriter'
import type { Role } from '../../types'
import { getCampBadgeClass, getRoleName } from '../../lib/roles'

interface DialogBoxProps {
  /** Hide the VN box while the DiscussionDialog feed owns the same speech,
      so the line never renders in two colliding surfaces at once. */
  suppressed?: boolean
}

export function DialogBox({ suppressed = false }: DialogBoxProps) {
  const [dismissedLogId, setDismissedLogId] = useState<string | null>(null)
  const [completedLogId, setCompletedLogId] = useState<string | null>(null)
  const [minimized, setMinimized] = useState(false)

  const gameLogs = useGameStore(state => state.gameState?.game_logs || [])
  const players = useGameStore(state => state.gameState?.players || [])
  const isGameOver = useGameStore(state => state.gameState?.phase === 'GAME_END')

  const latestSpeechLog = useMemo(() => {
    return [...gameLogs].reverse().find(log => log.player_id && log.is_public && log.type === 'speech')
  }, [gameLogs])

  const currentLog = useMemo(() => {
    if (!latestSpeechLog || latestSpeechLog.id === dismissedLogId) return null
    return latestSpeechLog
  }, [latestSpeechLog, dismissedLogId])

  // Auto-expand when new speech arrives. Depend only on the log id (the sole
  // value read) so the effect satisfies exhaustive-deps without suppression.
  const currentLogId = currentLog?.id
  useEffect(() => {
    if (currentLogId) {
      setMinimized(false)
    }
  }, [currentLogId])

  const speaker = useMemo(() => {
    if (!currentLog?.player_id) return null
    return players.find(p => p.id === currentLog.player_id) || null
  }, [currentLog, players])

  const speakerLabel = useMemo(() => {
    if (!speaker) return '法官'
    return `${speaker.id}号`
  }, [speaker])

  const showRoleBadge = useMemo(() => {
    if (!speaker) return false
    if (speaker.is_human) return true
    return isGameOver
  }, [speaker, isGameOver])

  const roleBadgeClass = useMemo(() => {
    if (!speaker) return ''
    return getCampBadgeClass(speaker.role as Role)
  }, [speaker])

  const isTypingComplete = currentLog ? completedLogId === currentLog.id : false

  // Dismiss the finished dialog on any key. Uses keydown (not keypress) so that
  // Escape — which keypress never fires — also closes it.
  useEffect(() => {
    function handleKeyDown() {
      if (currentLog && isTypingComplete && !minimized) {
        setDismissedLogId(currentLog.id)
        setCompletedLogId(null)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [currentLog, isTypingComplete, minimized])

  if (!currentLog || suppressed) return null

  // Minimized: small floating button
  if (minimized) {
    return (
      <button
        onClick={() => setMinimized(false)}
        className="fixed bottom-36 left-[140px] z-[45] flex items-center gap-2 px-3 py-2 bg-[#141210]/90 backdrop-blur-md border border-[color:var(--border-gilded)] rounded-full text-sm text-[#c5a059] shadow-[var(--shadow-ambient)] hover:bg-[#1c1913]/95 hover:scale-105 transition-all cursor-pointer"
      >
        <MessageCircle className="w-4 h-4" strokeWidth={1.5} />
        <span>{speakerLabel}发言</span>
      </button>
    )
  }

  // Expanded: compact dialog
  return (
    <div className="fixed bottom-36 left-[140px] z-[45] w-[420px] max-w-[calc(100vw-480px)] animate-fade-in-up">
      <div className="bg-[#141210]/90 backdrop-blur-xl border border-[color:var(--border-gilded)] rounded-[10px] shadow-[var(--shadow-ambient)] overflow-hidden">
        {/* Header - compact */}
        <div className="flex items-center justify-between px-3 py-2 bg-white/[0.04] border-b border-[color:var(--border-gilded)]">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-white border border-[color:var(--border-gilded)] bg-gradient-to-br from-slate-700 to-slate-900 shrink-0">
              {speaker ? speaker.id : <Gavel className="w-3.5 h-3.5 text-[#c5a059]" strokeWidth={1.5} />}
            </div>
            <span className="text-sm font-bold text-parchment truncate font-display">{speakerLabel}</span>
            {showRoleBadge && (
              <span className={`${roleBadgeClass} text-[10px] px-1.5 py-0.5`}>
                {getRoleName(speaker?.role ?? '')}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1 shrink-0 ml-2">
            <button
              onClick={() => setMinimized(true)}
              className="w-6 h-6 flex items-center justify-center rounded text-parchment-dim hover:text-parchment hover:bg-white/10 transition-colors"
              title="最小化"
            >
              <ChevronDown className="w-3.5 h-3.5" strokeWidth={1.5} />
            </button>
            <button
              onClick={() => {
                setDismissedLogId(currentLog.id)
                setCompletedLogId(null)
              }}
              className="w-6 h-6 flex items-center justify-center rounded text-parchment-dim hover:text-parchment hover:bg-white/10 transition-colors"
              title="关闭"
            >
              <X className="w-3.5 h-3.5" strokeWidth={1.5} />
            </button>
          </div>
        </div>

        {/* Content - compact */}
        <div className="px-3 py-2.5">
          <div className="text-sm leading-relaxed text-parchment">
            <TypeWriter
              key={currentLog.id}
              text={currentLog.content}
              speed={15}
              onFinished={() => setCompletedLogId(currentLog.id)}
              highlight
            />
          </div>
        </div>

        {/* Footer - minimal */}
        <div className="flex items-center justify-end px-3 py-1.5 border-t border-white/5">
          {!isTypingComplete ? (
            <span className="flex gap-1">
              <span className="typing-dot"></span>
              <span className="typing-dot" style={{ animationDelay: '0.2s' }}></span>
              <span className="typing-dot" style={{ animationDelay: '0.4s' }}></span>
            </span>
          ) : (
            <span className="text-parchment-dim/70 text-xs">按任意键关闭</span>
          )}
        </div>
      </div>
    </div>
  )
}
