import { useEffect, useMemo, useState } from 'react'
import { useGameStore } from '../../store/useGameStore'
import { TypeWriter } from '../ui/TypeWriter'
import { ROLE_NAMES, type Role, getRoleCamp } from '../../types'

export function DialogBox() {
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

  // Auto-expand when new speech arrives
  useEffect(() => {
    if (currentLog) {
      setMinimized(false)
    }
  }, [currentLog?.id])

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
    return getRoleCamp(speaker.role as Role) === 'wolf' ? 'badge-wolf' : 'badge-good'
  }, [speaker])

  const isTypingComplete = currentLog ? completedLogId === currentLog.id : false

  useEffect(() => {
    function handleKeyPress() {
      if (currentLog && isTypingComplete && !minimized) {
        setDismissedLogId(currentLog.id)
        setCompletedLogId(null)
      }
    }
    window.addEventListener('keypress', handleKeyPress)
    return () => window.removeEventListener('keypress', handleKeyPress)
  }, [currentLog, isTypingComplete, minimized])

  if (!currentLog) return null

  // Minimized: small floating button
  if (minimized) {
    return (
      <button
        onClick={() => setMinimized(false)}
        className="fixed bottom-36 left-[140px] z-[45] flex items-center gap-2 px-3 py-2 bg-slate-900/80 backdrop-blur-md border border-white/15 rounded-full text-sm text-sky-400 shadow-lg hover:bg-slate-800/90 hover:scale-105 transition-all cursor-pointer"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
        <span>{speakerLabel}号发言</span>
      </button>
    )
  }

  // Expanded: compact dialog
  return (
    <div className="fixed bottom-36 left-[140px] z-[45] w-[420px] max-w-[calc(100vw-480px)] animate-fade-in-up">
      <div className="bg-slate-900/80 backdrop-blur-xl border border-white/10 rounded-xl shadow-[0_8px_30px_rgba(0,0,0,0.5)] overflow-hidden">
        {/* Header - compact */}
        <div className="flex items-center justify-between px-3 py-2 bg-white/5 border-b border-white/10">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-white border border-white/20 bg-gradient-to-br from-slate-600 to-slate-800 shrink-0">
              {speaker ? speaker.id : '⚖️'}
            </div>
            <span className="text-sm font-bold text-white truncate">{speakerLabel}</span>
            {showRoleBadge && (
              <span className={`${roleBadgeClass} text-[10px] px-1.5 py-0.5`}>
                {ROLE_NAMES[speaker?.role as Role]}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1 shrink-0 ml-2">
            <button
              onClick={() => setMinimized(true)}
              className="w-6 h-6 flex items-center justify-center rounded text-white/40 hover:text-white/80 hover:bg-white/10 transition-colors"
              title="最小化"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <button
              onClick={() => {
                setDismissedLogId(currentLog.id)
                setCompletedLogId(null)
              }}
              className="w-6 h-6 flex items-center justify-center rounded text-white/40 hover:text-white/80 hover:bg-white/10 transition-colors"
              title="关闭"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content - compact */}
        <div className="px-3 py-2.5">
          <div className="text-sm leading-relaxed text-white/90">
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
            <span className="text-white/30 text-xs">按任意键关闭</span>
          )}
        </div>
      </div>
    </div>
  )
}
