import { useState, useEffect, useRef, useMemo } from 'react'
import { MessageCircle, X, Users } from 'lucide-react'
import { cn } from '../../lib/utils'

interface Message {
  id?: string
  speakerName: string
  content: string
  /** Optional parsed tag, e.g. "竞选发言" — rendered as a small chip. */
  tag?: string | null
}

interface DiscussionDialogProps {
  messages: Message[]
  visible: boolean
  /** During the wolf phase this is the private wolf channel: distinct dark-red
      treatment + a "仅狼人可见" tag. */
  isWolfChannel?: boolean
}

/**
 * The single live discussion feed at the bottom of the board. It is the one
 * surface for wolf密谋 AND day discussion — the wolf channel is just this feed
 * with a red-tinted rail and a visibility tag, so there is never a competing
 * modal composer (the composer lives in ActionPanel only).
 */
export function DiscussionDialog({ messages, visible, isWolfChannel = false }: DiscussionDialogProps) {
  const dialogTitle = useMemo(() => (isWolfChannel ? '狼人密谋' : '玩家讨论'), [isWolfChannel])

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
          className="fixed bottom-36 left-1/2 -translate-x-1/2 z-[60] bg-[#141210]/92 backdrop-blur-md border border-[color:var(--border-gilded)] rounded-full px-5 py-3 text-[#c5a059] cursor-pointer flex items-center gap-2 shadow-[var(--shadow-ambient)] transition-all hover:bg-[#1c1913]/95 hover:-translate-y-0.5 hover:shadow-[0_0_16px_rgba(197,160,89,0.32)] pointer-events-auto animate-slide-up-fade"
          title="显示讨论"
        >
          <MessageCircle className="w-5 h-5" strokeWidth={1.5} />
          {newMessageCount > 0 && (
            <span className="bg-[#8b6914] text-[#f4d9a0] text-[0.7rem] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center animate-[pulse-badge_2s_infinite]">
              {newMessageCount}
            </span>
          )}
        </button>
      )}

      {visible && messages.length > 0 && !isHidden && (
        // bottom-36 keeps the overlay clear of the h-32 ActionPanel — it must never
        // cover the speech composer during discussion phases
        <div className="fixed bottom-36 left-1/2 -translate-x-1/2 z-[60] max-w-[800px] w-[calc(100%-40px)] pointer-events-auto animate-slide-up-fade">
          <div className={cn(
            "backdrop-blur-xl rounded-[10px] border shadow-[var(--shadow-ambient)] overflow-hidden flex flex-col max-h-[400px]",
            isWolfChannel
              ? "bg-[#1a1210]/85 border-red-900/50"
              : "bg-[#141210]/85 border-[color:var(--border-gilded)]"
          )}>

            <div className={cn(
              "flex items-center justify-between px-4 py-3 border-b",
              isWolfChannel ? "border-red-900/40 bg-red-950/25" : "border-[color:var(--border-gilded)] bg-white/[0.03]"
            )}>
              <div className="flex items-center gap-2">
                <MessageCircle className={cn("w-4 h-4", isWolfChannel ? "text-red-400" : "text-[#c5a059]")} strokeWidth={1.5} />
                <span className={cn("font-display font-bold text-[0.95rem] tracking-wide", isWolfChannel ? "text-red-300" : "text-[#c5a059]")}>
                  {dialogTitle}
                </span>
                {isWolfChannel && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-500/15 border border-red-500/30 text-red-300/90 font-normal">
                    仅狼人可见
                  </span>
                )}
                {messages.length > 0 && (
                  <span className="bg-[#8b6914]/40 border border-[#c5a059]/30 text-parchment text-[0.75rem] px-2 py-0.5 rounded-full font-semibold">
                    {messages.length}
                  </span>
                )}
              </div>
              <button
                onClick={toggleVisibility}
                className="bg-transparent border-none text-parchment-dim cursor-pointer p-1 rounded hover:bg-white/10 hover:text-parchment transition-all flex items-center justify-center"
                title="隐藏对话框"
              >
                <X className="w-4 h-4" strokeWidth={1.5} />
              </button>
            </div>

            <div className="p-4 overflow-y-auto overflow-x-hidden flex-1 max-h-[330px] scroll-smooth" ref={messagesContainerRef}>
              {messages.map((message, index) => (
                <div
                  key={message.id ?? index}
                  className={cn(
                    "mb-3 last:mb-0 pl-3 border-l-2 animate-slide-up-fade",
                    isWolfChannel ? "border-red-700/60" : "border-[#c5a059]/30"
                  )}
                >
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className={cn(
                      "inline-flex items-center gap-1 text-[0.72rem] font-bold px-1.5 py-0.5 rounded",
                      isWolfChannel ? "text-red-300 bg-red-500/15" : "text-[#f4d9a0] bg-[#8b6914]/30"
                    )}>
                      <Users className="w-3 h-3" strokeWidth={1.5} />
                      {message.speakerName}
                    </span>
                    {message.tag && (
                      <span className="text-[0.68rem] px-1.5 py-0.5 rounded-full bg-white/5 border border-[color:var(--border-gilded)] text-parchment-dim">
                        {message.tag}
                      </span>
                    )}
                  </div>
                  <div className="text-parchment text-[0.95rem] leading-relaxed break-words">
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
