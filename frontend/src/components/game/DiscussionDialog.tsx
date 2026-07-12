import { useState, useEffect, useRef, useMemo } from 'react'
import { useGameStore } from '../../store/useGameStore'

interface Message {
  id?: string
  speakerName: string
  content: string
  timestamp?: number
}

interface DiscussionDialogProps {
  messages: Message[]
  visible: boolean
}

export function DiscussionDialog({ messages, visible }: DiscussionDialogProps) {
  const gameStore = useGameStore()
  const currentPhase = gameStore.gameState?.phase
  
  const dialogTitle = useMemo(() => {
    if (currentPhase === 'NIGHT_WOLF_DISCUSS') return '狼人讨论'
    if (currentPhase === 'DAY_DISCUSS') return '玩家讨论'
    return '讨论'
  }, [currentPhase])

  const [isHidden, setIsHidden] = useState(false)
  const [lastMessageCount, setLastMessageCount] = useState(0)
  
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  const newMessageCount = isHidden ? Math.max(0, messages.length - lastMessageCount) : 0

  function toggleVisibility() {
    if (isHidden) {
      setIsHidden(false)
      return
    }
    setLastMessageCount(messages.length)
    setIsHidden(true)
  }

  function formatTime(timestamp: number) {
    const d = new Date(timestamp)
    return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
  }

  useEffect(() => {
    setTimeout(() => {
      if (messagesContainerRef.current) {
        messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight
      }
    }, 50)
  }, [messages, visible, isHidden])

  return (
    <>
      {isHidden && visible && messages.length > 0 && (
        <button
          onClick={toggleVisibility}
          className="fixed bottom-5 left-1/2 -translate-x-1/2 z-50 bg-slate-900/80 backdrop-blur-md border border-white/15 rounded-full px-5 py-3 text-sky-400 cursor-pointer flex items-center gap-2 shadow-[0_4px_20px_rgba(0,0,0,0.4),0_0_15px_rgba(56,189,248,0.2)] transition-all hover:bg-slate-900/95 hover:-translate-y-0.5 hover:shadow-[0_6px_25px_rgba(0,0,0,0.5),0_0_20px_rgba(56,189,248,0.4)] pointer-events-auto animate-slide-up-fade"
          title="显示讨论"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          {newMessageCount > 0 && (
            <span className="bg-red-700 text-white text-[0.7rem] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center animate-[pulse-badge_2s_infinite]">
              {newMessageCount}
            </span>
          )}
        </button>
      )}

      {visible && messages.length > 0 && !isHidden && (
        <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-[60] max-w-[800px] w-[calc(100%-40px)] pointer-events-auto animate-slide-up-fade">
          <div className="bg-slate-900/65 backdrop-blur-xl rounded-[20px] border border-white/10 shadow-[0_10px_40px_rgba(0,0,0,0.6),inset_0_0_30px_rgba(255,255,255,0.02)] overflow-hidden flex flex-col max-h-[400px]">
            
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-white/5">
              <div className="flex items-center gap-2">
                <span className="text-[1.2rem]">💬</span>
                <span className="font-bold text-[0.95rem] text-[#c5a059]">{dialogTitle}</span>
                {messages.length > 0 && (
                  <span className="bg-violet-500/30 text-white/80 text-[0.75rem] px-2 py-0.5 rounded-full font-semibold">
                    {messages.length}
                  </span>
                )}
              </div>
              <button
                onClick={toggleVisibility}
                className="bg-transparent border-none text-white/60 cursor-pointer p-1 rounded hover:bg-white/10 hover:text-white/90 transition-all flex items-center justify-center"
                title="隐藏对话框"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-4 overflow-y-auto overflow-x-hidden flex-1 max-h-[330px] scroll-smooth scrollbar-thin scrollbar-thumb-white/15 hover:scrollbar-thumb-white/25 scrollbar-track-black/20" ref={messagesContainerRef}>
              {messages.map((message, index) => (
                <div key={message.id || index} className="mb-3 last:mb-0 animate-slide-up-fade">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-bold text-[0.9rem] text-sky-400 tracking-[0.5px]">{message.speakerName}</span>
                    {message.timestamp ? (
                      <span className="text-[0.75rem] text-white/50">{formatTime(message.timestamp)}</span>
                    ) : null}
                  </div>
                  <div className="text-white/95 text-[0.95rem] leading-relaxed break-words">
                    {message.content}
                  </div>
                </div>
              ))}
            </div>

          </div>
        </div>
      )}
    </>
  )
}
