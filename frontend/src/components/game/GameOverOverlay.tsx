import { Swords, Bird } from 'lucide-react'
import type { Player, Winner } from '../../types'
import { cn } from '../../lib/utils'
import { getRoleName, getRoleTextClass } from '../../lib/roles'

interface GameOverOverlayProps {
  winner: Winner
  players: Player[]
  onPlayAgain: () => void
}

/**
 * End-of-game screen: winner announcement + full role reveal of every player +
 * a "再来一局" action. Replaces the old stub overlay that only showed the
 * winner text and left the table visually stalled.
 */
export function GameOverOverlay({ winner, players, onPlayAgain }: GameOverOverlayProps) {
  const isWolfWin = winner === 'wolf'
  const title = isWolfWin ? '狼人阵营胜利!' : '好人阵营胜利!'
  const titleClass = isWolfWin ? 'text-red-500' : 'text-green-500'
  const ordered = [...players].sort((a, b) => a.id - b.id)

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="游戏结束"
      className="fixed inset-0 z-[70] flex items-center justify-center bg-black/85 p-4 backdrop-blur-sm animate-fade-in"
    >
      <div className="w-full max-w-2xl overflow-hidden rounded-2xl border border-[color:var(--border-gilded-strong)] bg-gradient-to-b from-[#1a1712] to-[#0d0b08] shadow-2xl animate-scale-in">
        <div className="border-b border-[color:var(--border-gilded)] p-6 text-center">
          <div className={cn('mb-3 flex justify-center', titleClass)}>
            {isWolfWin
              ? <Swords className="w-12 h-12" strokeWidth={1.5} />
              : <Bird className="w-12 h-12" strokeWidth={1.5} />}
          </div>
          <h1 className={cn('font-display text-3xl font-bold tracking-wide', titleClass)}>{title}</h1>
          <p className="mt-1 text-sm text-parchment-dim">全部身份已揭晓</p>
        </div>

        <div className="grid max-h-[45vh] grid-cols-2 gap-2 overflow-y-auto p-4 sm:grid-cols-3">
          {ordered.map(player => (
            <div
              key={player.id}
              className={cn(
                'flex items-center gap-2 rounded-lg border px-3 py-2',
                player.is_alive
                  ? 'border-white/10 bg-white/5'
                  : 'border-white/5 bg-black/40 opacity-70'
              )}
            >
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-700 text-xs font-bold text-white">
                {player.id}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1">
                  <span className="truncate text-sm text-parchment">{player.name}</span>
                  {player.is_human && <span className="text-[10px] font-bold text-sky-400">(你)</span>}
                </div>
                <div className="text-xs font-medium">
                  <span className={getRoleTextClass(player.role)}>{getRoleName(player.role)}</span>
                </div>
              </div>
              {!player.is_alive && <span className="shrink-0 text-xs text-rose-400">阵亡</span>}
            </div>
          ))}
        </div>

        <div className="flex justify-center border-t border-[color:var(--border-gilded)] p-5">
          <button
            onClick={onPlayAgain}
            className="rounded bg-[#8b6914] px-8 py-3 font-bold text-[#f4d9a0] border border-[color:var(--border-gilded-strong)] transition-all hover:bg-[#a07a1a] hover:shadow-[var(--glow-warm)]"
          >
            再来一局
          </button>
        </div>
      </div>
    </div>
  )
}
