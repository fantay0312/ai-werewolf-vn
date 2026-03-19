import React, { useState, useEffect, useMemo } from 'react'
import { useGameStore } from '../../store/useGameStore'
import { TypeWriter } from '../ui/TypeWriter'
import { PHASE_NAMES, ROLE_NAMES, type Role, getRoleCamp } from '../../types'

export function DialogBox() {
  const [currentLog, setCurrentLog] = useState<any>(null)
  const [isTypingComplete, setIsTypingComplete] = useState(false)
  const [showDialog, setShowDialog] = useState(true)

  const gameLogs = useGameStore(state => state.gameState?.game_logs || [])
  const players = useGameStore(state => state.gameState?.players || [])
  const isGameOver = useGameStore(state => state.gameState?.phase === 'GAME_END')

  // Find latest speech log
  const latestSpeechLog = useMemo(() => {
    return [...gameLogs].reverse().find(log => log.player_id && log.is_public && log.type === 'speech')
  }, [gameLogs])

  // React to new logs
  useEffect(() => {
    if (latestSpeechLog && latestSpeechLog.id !== currentLog?.id) {
      setCurrentLog(latestSpeechLog)
      setIsTypingComplete(false)
      setShowDialog(true)
    }
  }, [latestSpeechLog, currentLog?.id])

  const speaker = useMemo(() => {
    if (!currentLog?.player_id) return null
    return players.find(p => p.id === currentLog.player_id)
  }, [currentLog, players])

  const speakerName = useMemo(() => {
    if (speaker) {
      return `${speaker.id}号 ${speaker.name}`
    }
    return '法官'
  }, [speaker])

  const showRoleBadge = useMemo(() => {
    if (!speaker) return false
    if (speaker.is_human) return true
    if (isGameOver) return true
    return false
  }, [speaker, isGameOver])

  const roleBadgeClass = useMemo(() => {
    if (!speaker) return ''
    const camp = getRoleCamp(speaker.role as Role)
    return camp === 'wolf' ? 'badge-wolf' : 'badge-good'
  }, [speaker])

  function getSpeakerClass() {
    if (!speaker) return 'avatar-judge'
    if (speaker.is_human) return 'avatar-me'
    if (!speaker.is_alive) return 'avatar-dead'
    return 'avatar-default'
  }

  function getSpeakerNumber() {
    if (!speaker) return '⚖️'
    return String(speaker.id)
  }

  function closeDialog() {
    setShowDialog(false)
    setCurrentLog(null)
  }

  useEffect(() => {
    function handleKeyPress() {
      if (currentLog && isTypingComplete) {
        closeDialog()
      }
    }
    window.addEventListener('keypress', handleKeyPress)
    return () => window.removeEventListener('keypress', handleKeyPress)
  }, [currentLog, isTypingComplete])

  if (!showDialog || !currentLog) return null

  return (
    <div className="dialog-overlay animate-slide-up">
      <div className="dialog-box pointer-events-auto mx-auto w-[90%] max-w-[800px] absolute bottom-[120px] left-1/2 -translate-x-1/2">
        <div className="dialog-container bg-slate-900/65 backdrop-blur-xl border border-white/10 border-t-white/20 rounded-2xl p-6 shadow-[0_10px_40px_rgba(0,0,0,0.5),inset_0_0_40px_rgba(255,255,255,0.02)]">
          
          <div className="dialog-header flex justify-between items-center mb-4 pb-3 border-b border-white/10">
            <div className="speaker-info flex items-center gap-3">
              <div className={`speaker-avatar w-12 h-12 rounded-xl flex items-center justify-center text-xl font-bold text-white border-2 ${getSpeakerClass()}`}>
                {getSpeakerNumber()}
              </div>
              <div className="speaker-details flex flex-col gap-1">
                <span className="speaker-name text-xl font-bold text-white">{speakerName}</span>
                <div className="speaker-badges flex gap-1.5 flex-wrap">
                  {speaker?.id && <span className="badge badge-id">#{speaker.id}</span>}
                  {showRoleBadge && (
                    <span className={`badge ${roleBadgeClass}`}>
                      {ROLE_NAMES[speaker?.role as Role] || speaker?.role || 'villager'}
                    </span>
                  )}
                  {speaker?.is_sheriff && <span className="badge badge-sheriff">👑 警长</span>}
                </div>
              </div>
            </div>
            
            <div className="dialog-meta flex gap-3">
              <span className="meta-item text-sm text-white/50">📅 第 {currentLog.day} 天</span>
              <span className="meta-item text-sm text-white/50">{PHASE_NAMES[currentLog.phase as keyof typeof PHASE_NAMES] || currentLog.phase}</span>
            </div>
          </div>

          <div className="dialog-content min-h-[80px] mb-4">
            <div className="content-text text-lg leading-relaxed text-white/95 tracking-wide">
              <TypeWriter
                key={currentLog.id}
                text={currentLog.content}
                speed={12}
                onFinished={() => setIsTypingComplete(true)}
                highlight={true}
              />
            </div>
          </div>

          <div className="dialog-footer flex justify-between items-center pt-3 border-t border-white/10">
            <div className="typing-status flex items-center gap-2">
              {!isTypingComplete ? (
                <span className="status-typing flex gap-1">
                  <span className="typing-dot"></span>
                  <span className="typing-dot" style={{ animationDelay: '0.2s' }}></span>
                  <span className="typing-dot" style={{ animationDelay: '0.4s' }}></span>
                </span>
              ) : (
                <span className="status-continue text-white/50 text-sm animate-pulse">
                  按任意键继续 ▶
                </span>
              )}
            </div>
            <button 
              onClick={closeDialog} 
              className="btn-close px-4 py-1.5 bg-white/10 border border-white/20 rounded-lg text-white/70 text-sm hover:bg-white/15 hover:text-white transition-all"
            >
              跳过
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
