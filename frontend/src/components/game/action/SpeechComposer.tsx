import { useState, type ReactNode } from 'react'
import { cn } from '../../../lib/utils'

const QUICK_PHRASES = [
  { icon: '🔍', label: '查验结果', text: '我查验了X号，是好人/狼人', type: 'seer' },
  { icon: '🎯', label: '怀疑', text: '我怀疑X号是狼人', type: 'suspect' },
  { icon: '✅', label: '认同', text: '我认同X号的发言', type: 'agree' },
  { icon: '❌', label: '反对', text: '我不认同X号的观点', type: 'disagree' },
  { icon: '🛡️', label: '自证', text: '我是好人，请相信我', type: 'defend' },
  { icon: '🗳️', label: '投票', text: '我建议投X号', type: 'vote' },
  { icon: '⚠️', label: '警告', text: '大家小心X号，他的逻辑有问题', type: 'warn' },
  { icon: '🤝', label: '站边', text: '我选择相信X号', type: 'trust' },
]

interface SpeechComposerProps {
  label: string
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

  return (
    <div className={cn('action-group', wrapperClassName)}>
      {quickPhrases ? (
        <div className="speech-header flex justify-between items-center w-full mb-2">
          <span className="action-label">{label}</span>
          <button
            onClick={() => setShowPhrases(!showPhrases)}
            className="btn-toggle-phrases px-3 py-1 text-xs bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded-full hover:bg-purple-500/30 transition-colors"
          >
            {showPhrases ? '收起' : '快捷短语'} ⚡
          </button>
        </div>
      ) : (
        <span className={cn('action-label', labelClassName)}>{label}</span>
      )}

      {quickPhrases && showPhrases && (
        <div className="quick-phrases flex flex-wrap gap-1.5 p-2 bg-black/30 rounded-lg w-full mb-2 animate-fade-in">
          {QUICK_PHRASES.map(phrase => (
            <button
              key={phrase.text}
              onClick={() => onChange(phrase.text)}
              className={`phrase-btn px-3 py-1 text-xs bg-white/5 border border-white/10 rounded-full text-white/80 hover:bg-white/10 ${phrase.type}`}
            >
              {phrase.icon} {phrase.label}
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
