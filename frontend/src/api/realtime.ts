import type { ConnectionStatus, GameState } from '../types'
import { API_BASE_URL, gameApi, parseApiError } from './index'

export interface RealtimeCallbacks {
  /** Called with a freshly fetched full game state. */
  onUpdate: (state: GameState) => void
  /** Called whenever the transport health changes. */
  onStatus: (status: ConnectionStatus) => void
  /** Called once on an unrecoverable condition (game gone / auth lost). */
  onFatal: (message: string) => void
}

const POLL_INTERVAL_MS = 2000
const REFETCH_DEBOUNCE_MS = 200
// While the SSE stream is live we still do a low-frequency safety re-fetch so
// state can never drift more than this even if some named events are missed.
const SAFETY_REFETCH_MS = 10000
const MAX_MISSED_SAFETY = 2
// After this many consecutive SSE failures, fall back to polling for the session.
const SSE_MAX_FAILURES = 3
const POLL_FAILURES_BEFORE_LOST = 2
const BACKOFF_BASE_MS = 1000
const BACKOFF_MAX_MS = 15000

const GAME_GONE_MSG = '游戏不存在，已退出该对局'
const AUTH_LOST_MSG = '登录已失效，请重新开始游戏'

function backoffDelay(attempt: number): number {
  const exp = Math.min(BACKOFF_MAX_MS, BACKOFF_BASE_MS * 2 ** Math.max(0, attempt - 1))
  // Full jitter to avoid reconnect thundering herds.
  return Math.round(exp / 2 + Math.random() * (exp / 2))
}

function sseEventsUrl(sessionId: string, viewerId: number, ticket: string): string {
  const params = new URLSearchParams({
    session_id: sessionId,
    viewer_id: String(viewerId),
    ticket,
  })
  return `${API_BASE_URL}/sse/events?${params.toString()}`
}

/**
 * SSE-first realtime connection with an automatic polling fallback.
 *
 * Strategy: hydrate once via GET, then open an authenticated EventSource
 * (ticket -> stream). Any event is treated as a "something changed" signal and
 * triggers a debounced, single-flight full-state re-fetch. On SSE failure it
 * reconnects with a fresh single-use ticket and exponential backoff; after
 * repeated failures (or if the ticket endpoint is absent) it falls back to
 * polling. A single failure policy is shared: 404/403 -> fatal (caller clears
 * the session); network/5xx -> backoff + a visible "reconnecting" status.
 */
export class RealtimeConnection {
  private sessionId: string | null = null
  private playerToken: string | null = null
  private viewerId = 0
  private cb: RealtimeCallbacks | null = null

  // Monotonically bumped on start()/stop() to invalidate stale async work.
  private generation = 0
  private es: EventSource | null = null

  private refetchTimer: ReturnType<typeof setTimeout> | null = null
  private heartbeatTimer: ReturnType<typeof setTimeout> | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private pollTimer: ReturnType<typeof setTimeout> | null = null

  private refetchInFlight = false
  private refetchQueued = false

  private sseFailures = 0
  private pollFailures = 0
  private missedSafety = 0
  private status: ConnectionStatus = 'offline'

  start(sessionId: string, playerToken: string | null, cb: RealtimeCallbacks): void {
    this.stop()
    const gen = ++this.generation
    this.sessionId = sessionId
    this.playerToken = playerToken
    this.cb = cb
    this.sseFailures = 0
    this.pollFailures = 0
    this.missedSafety = 0
    this.status = 'offline'
    this.setStatus('connecting')
    void this.bootstrap(gen)
  }

  stop(): void {
    this.generation++
    this.clearTimers()
    this.closeEventSource()
    this.cb = null
    this.sessionId = null
    this.playerToken = null
    this.status = 'offline'
  }

  private isCurrent(gen: number): boolean {
    return gen === this.generation && this.cb !== null
  }

  private setStatus(status: ConnectionStatus): void {
    if (this.status === status) return
    this.status = status
    this.cb?.onStatus(status)
  }

  private fatal(gen: number, message: string): void {
    if (!this.isCurrent(gen)) return
    const cb = this.cb
    this.stop()
    cb?.onFatal(message)
  }

  // --- Bootstrap / transport selection -------------------------------------

  private async bootstrap(gen: number): Promise<void> {
    const ok = await this.hydrate(gen)
    if (!this.isCurrent(gen)) return
    if (!ok) {
      // Initial fetch failed (non-fatal): degrade straight to the polling loop,
      // which keeps retrying with backoff and recovers if the backend returns.
      this.startPolling(gen)
      return
    }
    void this.connectSse(gen)
  }

  private async hydrate(gen: number): Promise<boolean> {
    const sessionId = this.sessionId
    if (!sessionId) return false
    try {
      const state = await gameApi.getGameState(sessionId, this.playerToken)
      if (!this.isCurrent(gen)) return false
      this.viewerId = state.players.find((p) => p.is_human)?.id ?? 0
      this.pollFailures = 0
      this.cb?.onUpdate(state)
      return true
    } catch (err) {
      if (!this.isCurrent(gen)) return false
      const { status } = parseApiError(err)
      if (status === 404) {
        this.fatal(gen, GAME_GONE_MSG)
      } else if (status === 403) {
        this.fatal(gen, AUTH_LOST_MSG)
      } else {
        this.pollFailures++
        this.setStatus('reconnecting')
      }
      return false
    }
  }

  // --- SSE -----------------------------------------------------------------

  private async connectSse(gen: number): Promise<void> {
    const sessionId = this.sessionId
    if (!sessionId) return

    let ticket: string
    try {
      const res = await gameApi.fetchSseTicket(this.playerToken)
      if (!this.isCurrent(gen)) return
      ticket = res.ticket
    } catch (err) {
      if (!this.isCurrent(gen)) return
      const { status } = parseApiError(err)
      if (status === 404) {
        // Ticket endpoint missing (backend without SSE yet): permanent polling.
        this.startPolling(gen)
      } else if (status === 403) {
        this.fatal(gen, AUTH_LOST_MSG)
      } else {
        this.onSseFailure(gen)
      }
      return
    }

    let es: EventSource
    try {
      es = new EventSource(sseEventsUrl(sessionId, this.viewerId, ticket))
    } catch {
      // EventSource unsupported/blocked in this environment.
      this.startPolling(gen)
      return
    }
    this.es = es

    const onEvent = () => {
      if (!this.isCurrent(gen)) return
      this.missedSafety = 0
      this.armSafetyRefetch(gen)
      this.scheduleRefetch(gen)
    }

    es.onopen = () => {
      if (!this.isCurrent(gen)) return
      this.sseFailures = 0
      this.missedSafety = 0
      this.setStatus('live')
      this.armSafetyRefetch(gen)
      this.scheduleRefetch(gen) // catch up any events missed before open
    }
    es.onmessage = onEvent
    // Backend uses named EventPresenter events; register the likely names so a
    // named event still triggers a re-fetch. The safety re-fetch backstops any
    // name we do not list.
    for (const name of ['update', 'game', 'state', 'phase', 'event', 'game_event']) {
      es.addEventListener(name, onEvent)
    }
    es.onerror = () => {
      if (!this.isCurrent(gen)) return
      // The ticket is single-use, so native EventSource retry would reuse a
      // spent ticket. Tear down and reconnect with a fresh ticket ourselves.
      this.closeEventSource()
      this.onSseFailure(gen)
    }
  }

  private armSafetyRefetch(gen: number): void {
    if (this.heartbeatTimer) clearTimeout(this.heartbeatTimer)
    this.heartbeatTimer = setTimeout(() => {
      if (!this.isCurrent(gen)) return
      this.missedSafety++
      this.scheduleRefetch(gen)
      if (this.missedSafety >= MAX_MISSED_SAFETY) {
        // No events for too long -> treat the stream as dead and reconnect.
        this.closeEventSource()
        this.onSseFailure(gen)
        return
      }
      this.armSafetyRefetch(gen)
    }, SAFETY_REFETCH_MS)
  }

  private onSseFailure(gen: number): void {
    if (!this.isCurrent(gen)) return
    if (this.heartbeatTimer) {
      clearTimeout(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
    this.sseFailures++
    if (this.sseFailures > SSE_MAX_FAILURES) {
      // SSE is not working here; use polling for the rest of the session.
      this.startPolling(gen)
      return
    }
    this.setStatus('reconnecting')
    const delay = backoffDelay(this.sseFailures)
    this.reconnectTimer = setTimeout(() => {
      if (!this.isCurrent(gen)) return
      void this.connectSse(gen)
    }, delay)
  }

  // --- Polling fallback ----------------------------------------------------

  private startPolling(gen: number): void {
    if (!this.isCurrent(gen)) return
    this.closeEventSource()
    if (this.heartbeatTimer) {
      clearTimeout(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
    this.setStatus(this.pollFailures >= POLL_FAILURES_BEFORE_LOST ? 'reconnecting' : 'polling')
    void this.pollLoop(gen)
  }

  private async pollLoop(gen: number): Promise<void> {
    if (!this.isCurrent(gen)) return
    const sessionId = this.sessionId
    if (!sessionId) return
    try {
      const state = await gameApi.getGameState(sessionId, this.playerToken)
      if (!this.isCurrent(gen)) return
      this.pollFailures = 0
      this.setStatus('polling')
      this.cb?.onUpdate(state)
    } catch (err) {
      if (!this.isCurrent(gen)) return
      const { status } = parseApiError(err)
      if (status === 404) {
        this.fatal(gen, GAME_GONE_MSG)
        return
      }
      if (status === 403) {
        this.fatal(gen, AUTH_LOST_MSG)
        return
      }
      this.pollFailures++
      this.setStatus('reconnecting')
    }
    if (!this.isCurrent(gen)) return
    const delay = this.pollFailures > 0 ? backoffDelay(this.pollFailures) : POLL_INTERVAL_MS
    this.pollTimer = setTimeout(() => void this.pollLoop(gen), delay)
  }

  // --- Debounced, single-flight full-state re-fetch ------------------------

  private scheduleRefetch(gen: number): void {
    if (this.refetchTimer) return
    this.refetchTimer = setTimeout(() => {
      this.refetchTimer = null
      void this.doRefetch(gen)
    }, REFETCH_DEBOUNCE_MS)
  }

  private async doRefetch(gen: number): Promise<void> {
    if (!this.isCurrent(gen)) return
    if (this.refetchInFlight) {
      this.refetchQueued = true
      return
    }
    const sessionId = this.sessionId
    if (!sessionId) return
    this.refetchInFlight = true
    try {
      const state = await gameApi.getGameState(sessionId, this.playerToken)
      if (!this.isCurrent(gen)) return
      this.pollFailures = 0
      this.cb?.onUpdate(state)
    } catch (err) {
      if (!this.isCurrent(gen)) return
      const { status } = parseApiError(err)
      if (status === 404) {
        this.fatal(gen, GAME_GONE_MSG)
        return
      }
      if (status === 403) {
        this.fatal(gen, AUTH_LOST_MSG)
        return
      }
      // Transient refetch error while streaming: ignore; the next event or the
      // safety re-fetch will retry.
    } finally {
      this.refetchInFlight = false
      if (this.refetchQueued && this.isCurrent(gen)) {
        this.refetchQueued = false
        this.scheduleRefetch(gen)
      }
    }
  }

  // --- Teardown helpers ----------------------------------------------------

  private closeEventSource(): void {
    if (this.es) {
      this.es.onopen = null
      this.es.onmessage = null
      this.es.onerror = null
      this.es.close()
      this.es = null
    }
  }

  private clearTimers(): void {
    for (const t of [this.refetchTimer, this.heartbeatTimer, this.reconnectTimer, this.pollTimer]) {
      if (t) clearTimeout(t)
    }
    this.refetchTimer = null
    this.heartbeatTimer = null
    this.reconnectTimer = null
    this.pollTimer = null
    this.refetchInFlight = false
    this.refetchQueued = false
    this.missedSafety = 0
  }
}
