import { useState, type ReactNode } from 'react'
import { Search, Target, ThumbsUp, ThumbsDown, Shield, Vote, AlertTriangle, Handshake, Zap, type LucideIcon } from 'lucide-react'
import { cn } from '../../../lib/utils'

const QUICK_PHRASES: { Icon: LucideIcon; label: string; text: string; type: string }[] = [
  { Icon: Search, label: '查验结果', text: '我查验了X号，是好人/狼人', type: 'seer' },
  { Icon: Target, label: '怀疑', text: '我怀疑X号是狼人', type: 'suspect' },
  { Icon: ThumbsUp, label: '认同', text: '我认同X号的发言', type: 'agree' },
  { Icon: ThumbsDown, label: '反对', text: '我不认同X号的观点', type: 'disagree' },
  { Icon: Shield, label: '自证', text: '我是好人，请相信我', type: 'defend' },
  { Icon: Vote, label: '投票', text: '我建议投X号', type: 'vote' },
  { Icon: AlertTriangle, label: '警告', text: '大家小心X号，他的逻辑有问题', type: 'warn' },
  { Icon: Handshake, label: '站边', text: '我选择相信X号', type: 'trust' },
]

interface SpeechComposerProps {
  label: string
  /** Optional lucide glyph rendered before the label text. */
  icon?: LucideIcon
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  placeholder: string
  submitLabel?: string
  submitClassName?: string
  /** Variant classes appended after `action-group`. */
  wrapperClassName?: string
  labelClassName?: string
  inputGroupClassName?: string
  /** Show the day-discuss quick-phrase palette. */
  quickPhrases?: boolean
  /** Trailing buttons rendered after the primary submit (e.g. 跳过 / 结束 / 退水). */
  trailing?: ReactNode
}

/**
 * Reusable free-text speech input, shared by wolf密谋 / 白天发言 / 竞选发言.
 * Collapses three near-identical JSX blocks in the old ActionPanel.
 */
export function SpeechComposer({
  label,
  icon: Icon,
  value,
  onChange,
  onSubmit,
  placeholder,
  submitLabel = '发言',
  submitClassName = 'btn-primary',
  wrapperClassName,
  labelClassName,
  inputGroupClassName,
  quickPhrases = false,
  trailing,
}: SpeechComposerProps) {
  const [showPhrases, setShowPhrases] = useState(false)

  const labelNode = (
    <span className={cn('action-label', labelClassName)}>
      {Icon && <Icon className="w-4 h-4" strokeWidth={1.5} />}
      {label}
    </span>
  )

  return (
    <div className={cn('action-group', wrapperClassName)}>
      {quickPhrases ? (
        <div className="speech-header flex justify-between items-center w-full mb-2">
          {labelNode}
          <button
            onClick={() => setShowPhrases(!showPhrases)}
            className="btn-toggle-phrases inline-flex items-center gap-1 px-3 py-1 text-xs bg-[#8b6914]/25 text-[#c5a059] border border-[#c5a059]/35 rounded-full hover:bg-[#8b6914]/40 transition-colors"
          >
            <Zap className="w-3.5 h-3.5" strokeWidth={1.5} />
            {showPhrases ? '收起' : '快捷短语'}
          </button>
        </div>
      ) : (
        labelNode
      )}

      {quickPhrases && showPhrases && (
        <div className="quick-phrases flex flex-wrap gap-1.5 p-2 bg-black/30 rounded-lg w-full mb-2 animate-fade-in">
          {QUICK_PHRASES.map(phrase => (
            <button
              key={phrase.text}
              onClick={() => onChange(phrase.text)}
              className={`phrase-btn inline-flex items-center gap-1 px-3 py-1 text-xs bg-white/5 border border-[color:var(--border-gilded)] rounded-full text-parchment-dim hover:bg-white/10 hover:text-parchment transition-colors ${phrase.type}`}
            >
              <phrase.Icon className="w-3.5 h-3.5" strokeWidth={1.5} />
              {phrase.label}
            </button>
          ))}
        </div>
      )}

      <div className={cn('input-group', inputGroupClassName)}>
        <input
          value={value}
          onChange={e => onChange(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && onSubmit()}
          type="text"
          placeholder={placeholder}
          aria-label={label}
          className="input-field flex-1"
        />
        <button onClick={onSubmit} className={cn('btn', submitClassName)}>{submitLabel}</button>
        {trailing}
      </div>
    </div>
  )
}
