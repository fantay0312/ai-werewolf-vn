import { useState, useRef, useEffect, useMemo } from 'react'
import { useGameStore } from '../../store/useGameStore'
import { cn } from '../../lib/utils'
import { isWolfRole } from '../../types'

interface WolfDiscussionModalProps {
  isOpen: boolean
  onClose: () => void
}

export function WolfDiscussionModal({ isOpen, onClose }: WolfDiscussionModalProps) {
  const [messageInput, setMessageInput] = useState('')
  const [selectedTarget, setSelectedTarget] = useState<number | null>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)

  // Narrow subscriptions instead of the whole store.
  const players = useGameStore(state => state.gameState?.players)
  const phase = useGameStore(state => state.gameState?.phase)
  const wolfDiscussMessages = useGameStore(state => state.gameState?.wolf_discuss_messages)
  const submitAction = useGameStore(state => state.submitAction)

  const myRole = players?.find(p => p.is_human)?.role
  const isWolf = myRole ? isWolfRole(myRole) : false
  const isVotePhase = phase === 'NIGHT_WOLF_VOTE'

  const wolfTeam = (players || []).filter(p => isWolfRole(p.role))
  const eligibleTargets = (players || []).filter(p => p.is_alive)

  const wolfMessages = useMemo(() => {
    return (wolfDiscussMessages || []).map((msg, index) => ({
      id: msg.id || `${msg.speaker_id}-${msg.round}-${index}`,
      playerName: `${msg.speaker_id}号`,
      content: msg.content,
      round: msg.round,
    }))
  }, [wolfDiscussMessages])

  // Ensure only wolves can view this.
  useEffect(() => {
    if (isOpen && !isWolf) {
      onClose()
    }
  }, [isOpen, isWolf, onClose])

  // Escape closes the modal.
  useEffect(() => {
    if (!isOpen) return
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [isOpen, onClose])

  useEffect(() => {
    if (isOpen) dialogRef.current?.focus()
  }, [isOpen])

  useEffect(() => {
    setTimeout(() => {
      if (messagesContainerRef.current) {
        messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight
      }
    }, 10)
  }, [wolfMessages.length, isOpen])

  async function sendMessage() {
    if (!isWolf) return
    if (!messageInput.trim()) return

    await submitAction('speech', undefined, messageInput)
    setMessageInput('')
  }

  async function confirmKill() {
    if (!selectedTarget) return

    await submitAction('kill', selectedTarget)
    setSelectedTarget(null)
    onClose()
  }

  if (!isOpen || !isWolf) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center animate-fade-in">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose}></div>

      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="狼人密谋"
        tabIndex={-1}
        className="relative bg-gray-900 rounded-lg shadow-2xl border border-red-800 w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col animate-scale-in outline-none"
      >

        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-red-800 bg-red-900/30 rounded-t-lg">
          <div className="flex items-center space-x-2">
            <span className="text-2xl">🐺</span>
            <h2 className="text-xl font-bold text-red-400">狼人密谋</h2>
          </div>
          <button onClick={onClose} aria-label="关闭" className="text-gray-400 hover:text-white transition-colors">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Wolf Team Info */}
        <div className="p-4 border-b border-gray-700 bg-gray-800/50">
          <h3 className="text-sm font-bold text-gray-400 mb-2">狼队成员</h3>
          <div className="flex flex-wrap gap-2">
            {wolfTeam.map(wolf => (
              <div key={wolf.id} className={cn(
                "flex items-center px-3 py-1 rounded-full text-sm",
                wolf.is_alive ? "bg-red-900/50 text-red-300" : "bg-gray-700 text-gray-500 line-through"
              )}>
                <span className="font-bold mr-1">{wolf.id}号</span>
                <span className="text-xs opacity-75">{wolf.role === 'wolf_king' ? '狼王' : '狼人'}</span>
                {!wolf.is_alive && <span className="ml-1">💀</span>}
              </div>
            ))}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[200px]" ref={messagesContainerRef}>
          {wolfMessages.map(msg => (
            <div key={msg.id} className="p-3 rounded-lg bg-red-900/30">
              <div className="flex items-center mb-1">
                <span className="font-bold text-red-400">{msg.playerName}</span>
                <span className="text-xs text-gray-500 ml-2">第{msg.round}轮</span>
              </div>
              <p className="text-white">{msg.content}</p>
            </div>
          ))}

          {wolfMessages.length === 0 && (
            <div className="text-center text-gray-500 py-8">
              <p>狼人频道已开启</p>
              <p className="text-sm mt-1">与你的队友讨论今晚的目标...</p>
            </div>
          )}
        </div>

        {/* Target Selection or Input Area */}
        {isVotePhase ? (
          <div className="p-4 border-t border-gray-700 bg-gray-800/50">
            <h3 className="text-sm font-bold text-yellow-400 mb-3">选择击杀目标</h3>
            <p className="text-xs text-gray-500 mb-3">可选择任意存活玩家，包括自己或狼队友</p>
            <div className="grid grid-cols-4 gap-2">
              {eligibleTargets.map(player => (
                <button
                  key={player.id}
                  onClick={() => setSelectedTarget(player.id)}
                  aria-pressed={selectedTarget === player.id}
                  className={cn(
                    "p-2 rounded text-sm font-bold transition-all",
                    selectedTarget === player.id
                      ? "bg-red-600 text-white ring-2 ring-red-400"
                      : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                  )}
                >
                  {player.id}号
                </button>
              ))}
            </div>
            <button
              onClick={confirmKill}
              disabled={!selectedTarget}
              className={cn(
                "w-full mt-4 py-3 rounded font-bold transition-colors",
                selectedTarget
                  ? "bg-red-600 hover:bg-red-500 text-white"
                  : "bg-gray-700 text-gray-500 cursor-not-allowed"
              )}
            >
              确认击杀
            </button>
          </div>
        ) : (
          <div className="p-4 border-t border-gray-700">
            <div className="flex space-x-2">
              <input
                value={messageInput}
                onChange={e => setMessageInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && sendMessage()}
                type="text"
                placeholder="输入讨论内容..."
                aria-label="狼人讨论内容"
                className="flex-1 px-4 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-red-500"
              />
              <button
                onClick={sendMessage}
                className="px-6 py-2 bg-red-600 hover:bg-red-500 rounded-lg font-bold text-white transition-colors"
              >
                发送
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-2">* 此频道仅狼人可见</p>
          </div>
        )}

      </div>
    </div>
  )
}
