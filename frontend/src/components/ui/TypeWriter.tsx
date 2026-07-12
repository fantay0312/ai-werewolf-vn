import { useState, useEffect, useRef } from 'react'

interface TypeWriterProps {
  text: string
  speed?: number
  onFinished?: () => void
  highlight?: boolean
}

// Compiled once at module scope (previously rebuilt on every character tick,
// re-parsing/re-compiling several RegExps per part per render).
const ROLE_KEYWORDS = '狼人|预言家|女巫|守卫|猎人|狼王|村民|好人|神职'
const ACTION_KEYWORDS = '击杀|毒杀|查验|守护|投票|放逐|自爆|开枪'
const PLAYER_KEYWORD = '\\d+号'

const SPLIT_PATTERN = new RegExp(`(${ROLE_KEYWORDS}|${ACTION_KEYWORDS}|${PLAYER_KEYWORD})`, 'g')
const PLAYER_RE = new RegExp(`^(?:${PLAYER_KEYWORD})$`)
const ROLE_RE = new RegExp(`^(?:${ROLE_KEYWORDS})$`)
const ACTION_RE = new RegExp(`^(?:${ACTION_KEYWORDS})$`)

// React version of highlightKeywords that returns React nodes
function highlightText(fullText: string) {
  const parts = fullText.split(SPLIT_PATTERN)

  return parts.map((part, i) => {
    if (PLAYER_RE.test(part)) {
      return <span key={i} className="highlight-player text-sky-400 font-semibold">{part}</span>
    }
    if (ROLE_RE.test(part)) {
      return <span key={i} className="highlight-role text-purple-400 font-semibold">{part}</span>
    }
    if (ACTION_RE.test(part)) {
      return <span key={i} className="highlight-action text-rose-400 font-semibold">{part}</span>
    }
    return part
  })
}

export function TypeWriter({ text, speed = 30, onFinished, highlight = true }: TypeWriterProps) {
  const [displayedLength, setDisplayedLength] = useState(0)
  const [isTyping, setIsTyping] = useState(false)
  const onFinishedRef = useRef(onFinished)

  useEffect(() => {
    onFinishedRef.current = onFinished
  }, [onFinished])

  useEffect(() => {
    setDisplayedLength(0)
    setIsTyping(true)

    if (!text) {
      setIsTyping(false)
      onFinishedRef.current?.()
      return
    }

    let currentLength = 0
    let timeoutId: ReturnType<typeof setTimeout>

    const typeNext = () => {
      if (currentLength < text.length) {
        currentLength++
        setDisplayedLength(currentLength)
        timeoutId = setTimeout(typeNext, speed)
      } else {
        setIsTyping(false)
        onFinishedRef.current?.()
      }
    }

    timeoutId = setTimeout(typeNext, speed)

    return () => clearTimeout(timeoutId)
  }, [text, speed])

  const displayedText = text.substring(0, displayedLength)

  return (
    <span>
      {highlight ? highlightText(displayedText) : displayedText}
      {isTyping && <span className="animate-pulse">|</span>}
    </span>
  )
}
