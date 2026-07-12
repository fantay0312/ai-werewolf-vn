import { useState, useRef, useEffect, useMemo } from 'react'
import { useGameStore } from '../../store/useGameStore'
import { cn } from '../../lib/utils'

interface WolfDiscussionModalProps {
  isOpen?: boolean
  visible?: boolean
  onClose: () => void
}

export function WolfDiscussionModal({ isOpen, visible, onClose }: WolfDiscussionModalProps) {
  const isVisible = isOpen ?? visible ?? false
  const [messageInput, setMessageInput] = useState('')
  const [selectedTarget, setSelectedTarget] = useState<number | null>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  const gameStore = useGameStore()
  const myRole = gameStore.gameState?.players.find(p => p.is_human)?.role || ''
  const isWolf = ['wolf', 'wolf_king'].includes(myRole)

  const isVotePhase = gameStore.gameState?.phase === 'NIGHT_WOLF_VOTE'

  const wolfTeam = gameStore.gameState?.players.filter(p => ['wolf', 'wolf_king'].includes(p.role)) || []

  const wolfMessages = useMemo(() => {
    return (gameStore.gameState?.wolf_discuss_messages || []).map((msg, index) => ({
      id: msg.id || `${msg.speaker_id}-${msg.round}-${index}`,
      playerName: `${msg.speaker_id}号`,
      content: msg.content,
      round: msg.round,
      isSystem: false,
    }))
  }, [gameStore.gameState?.wolf_discuss_messages])

  const eligibleTargets = gameStore.gameState?.players.filter(p => p.is_alive) || []

  // Ensure only wolves can view this
  useEffect(() => {
    if (isVisible && !isWolf) {
      onClose()
    }
  }, [isVisible, isWolf, onClose])

  useEffect(() => {
    setTimeout(() => {
      if (messagesContainerRef.current) {
        messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight
      }
    }, 10)
  }, [wolfMessages.length, isVisible])

  async function sendMessage() {
    if (!isWolf) return
    if (!messageInput.trim()) return

    await gameStore.submitAction('speech', undefined, messageInput)
    setMessageInput('')
  }

  async function confirmKill() {
    if (!selectedTarget) return

    await gameStore.submitAction('kill', selectedTarget)
    setSelectedTarget(null)
    onClose()
  }

  if (!isVisible || !isWolf) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center animate-fade-in">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose}></div>

      <div className="relative bg-gray-900 rounded-lg shadow-2xl border border-red-800 w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col animate-scale-in">
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-red-800 bg-red-900/30 rounded-t-lg">
          <div className="flex items-center space-x-2">
            <span className="text-2xl">🐺</span>
            <h2 className="text-xl font-bold text-red-400">狼人密谋</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
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
            <div key={msg.id} className={cn(
              "p-3 rounded-lg",
              msg.isSystem ? "bg-gray-800 text-gray-400 text-sm italic" : "bg-red-900/30"
             )}>
               {!msg.isSystem && (
                 <div className="flex items-center mb-1">
                   <span className="font-bold text-red-400">{msg.playerName}</span>
                   <span className="text-xs text-gray-500 ml-2">第{msg.round}轮</span>
                 </div>
               )}
               <p className={!msg.isSystem ? "text-white" : ""}>{msg.content}</p>
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
