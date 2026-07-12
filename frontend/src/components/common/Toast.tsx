import { AlertTriangle, Loader2 } from 'lucide-react'
import { useGameStore } from '../../store/useGameStore'
import { cn } from '../../lib/utils'

/**
 * App-level, non-blocking feedback layer.
 *
 * - Error banner: subscribes to the store's `error` (set on many failure paths
 *   that previously had no consumer). The store auto-clears it after ~3s.
 * - Connection indicator: shows a "reconnecting" pill when the realtime
 *   transport is retrying, so a dropped backend is visible instead of silent.
 */
export function Toast() {
  const error = useGameStore((s) => s.error)
  const connectionStatus = useGameStore((s) => s.connectionStatus)

  const showReconnecting = connectionStatus === 'reconnecting'

  return (
    <>
      {/* Error banner (top center) */}
      <div
        className="pointer-events-none fixed inset-x-0 top-4 z-[60] flex justify-center px-4"
        aria-live="assertive"
      >
        {error && (
          <div
            role="alert"
            className={cn(
              'pointer-events-auto flex max-w-md items-start gap-3 rounded-xl px-4 py-3',
              'border border-red-500/40 bg-red-950/85 text-red-100 shadow-2xl backdrop-blur-md',
              'animate-fade-in-down'
            )}
          >
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" />
            <span className="text-sm leading-relaxed">{error}</span>
          </div>
        )}
      </div>

      {/* Connection status (bottom center) */}
      <div
        className="pointer-events-none fixed inset-x-0 bottom-4 z-[60] flex justify-center px-4"
        aria-live="polite"
      >
        {showReconnecting && (
          <div
            className={cn(
              'pointer-events-auto flex items-center gap-2 rounded-full px-4 py-2',
              'border border-amber-500/40 bg-amber-950/85 text-amber-100 shadow-xl backdrop-blur-md',
              'animate-fade-in-up'
            )}
          >
            <Loader2 className="h-4 w-4 shrink-0 animate-spin text-amber-400" />
            <span className="text-xs font-medium tracking-wide">连接已断开，正在重新连接…</span>
          </div>
        )}
      </div>
    </>
  )
}

export default Toast
