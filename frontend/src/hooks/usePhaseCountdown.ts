import { useEffect, useState } from 'react'
import { useGameStore } from '../store/useGameStore'

/**
 * Ticking countdown for the current phase. The backend sets time_remaining
 * once per phase transition (the full phase budget) and never decrements it,
 * so the client anchors a deadline to that snapshot and derives the remaining
 * seconds locally. Anchoring to a deadline (instead of decrementing state)
 * keeps the display accurate even when a background tab throttles timers.
 *
 * While the backend reports ai_pending (some AI is still deciding), the
 * countdown holds at the full budget — the clock measures the human's
 * decision window, not LLM latency. It re-anchors when AI processing clears
 * and when the phase, day, or current speaker changes (the budget is
 * per-speech during discussion phases, so each speaker restarts the clock).
 */
export function usePhaseCountdown(fallback = 60): { remaining: number; budget: number } {
  const phase = useGameStore(state => state.gameState?.phase ?? '')
  const day = useGameStore(state => state.gameState?.day ?? 1)
  const speakerIndex = useGameStore(state => state.gameState?.current_speaker_index ?? -1)
  const serverRemaining = useGameStore(state => state.gameState?.time_remaining)
  const aiPending = useGameStore(state => state.gameState?.ai_pending ?? false)

  const budget = serverRemaining ?? fallback
  const [remaining, setRemaining] = useState(budget)

  useEffect(() => {
    setRemaining(budget)
    if (aiPending) return

    const deadline = Date.now() + budget * 1000
    const tick = () => {
      const left = Math.max(0, Math.ceil((deadline - Date.now()) / 1000))
      setRemaining(left)
      if (left <= 0) clearInterval(id)
    }
    const id = setInterval(tick, 500)
    return () => clearInterval(id)
  }, [phase, day, speakerIndex, budget, aiPending])

  return { remaining, budget }
}
