import { create } from 'zustand'
import { gameApi, parseApiError } from '../api'
import { RealtimeConnection } from '../api/realtime'
import type {
  ActionType,
  ConnectionStatus,
  GameLog,
  GamePhase,
  GameState,
  Player,
  Winner,
  WolfDiscussMessage,
} from '../types'

const DEFAULT_LOADING_TEXT = '加载中...'
const ERROR_DISPLAY_MS = 3000
const SESSION_STORAGE_KEY = 'werewolf_session_id'
const PLAYER_TOKEN_STORAGE_KEY = 'werewolf_player_token'

const ACTION_TIMEOUTS: Record<string, number> = {
  speech: 45,
  confirm: 15,
  pass: 15,
  vote: 20,
  kill: 25,
  check: 30,
  save: 25,
  poison: 25,
  guard: 25,
  shoot: 20,
  run_for_sheriff: 20,
  withdraw: 15,
  self_explode: 15,
}
const DEFAULT_TIMEOUT = 35

const ACTION_LOADING_TEXT: Record<string, string> = {
  confirm: '正在确认...',
  vote: '正在投票...',
  kill: '正在执行行动...',
  check: '正在查验...',
  save: '正在使用解药...',
  poison: '正在使用毒药...',
  guard: '正在守护...',
  speech: '正在发言...',
  run_for_sheriff: '正在竞选警长...',
  withdraw: '正在退水...',
  shoot: '正在开枪...',
  pass: '正在跳过...',
}

interface GameStoreState {
  gameState: GameState | null
  sessionId: string | null
  playerToken: string | null
  loadingCount: number
  isLoading: boolean
  loadingText: string
  loadingStartTime: number
  error: string | null
  connectionStatus: ConnectionStatus
  currentActionType: string
  myPlayer: Player | null
  currentPhase: GamePhase | ''
  currentDay: number
  gameLogs: GameLog[]
  wolfDiscussMessages: WolfDiscussMessage[]
  winner: Winner | null
  sheriffId: number | null
  sheriffCandidates: number[]
  isCandidate: boolean

  // Actions
  setError: (message: string | null) => void
  setLoading: (loading: boolean, text?: string) => void
  startLoading: (text?: string) => void
  stopLoading: () => void
  cancelLoading: () => void
  createGame: () => Promise<void>
  fetchGameState: () => Promise<void>
  submitAction: (type: ActionType | string, targetId?: number | null, content?: string) => Promise<void>
  connectRealtime: () => void
  disconnectRealtime: () => void
  recoverSession: () => void
  clearSession: () => void
}

const realtime = new RealtimeConnection()
let errorTimeout: ReturnType<typeof setTimeout> | null = null
let loadingTimeout: ReturnType<typeof setTimeout> | null = null

export function getStoredSessionId(): string | null {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(SESSION_STORAGE_KEY)
}

export function getStoredPlayerToken(): string | null {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(PLAYER_TOKEN_STORAGE_KEY)
}

export function hasStoredSession(): boolean {
  return Boolean(getStoredSessionId())
}

function persistSession(sessionId: string, playerToken: string | null) {
  if (typeof window === 'undefined') return

  window.localStorage.setItem(SESSION_STORAGE_KEY, sessionId)
  if (playerToken) {
    window.localStorage.setItem(PLAYER_TOKEN_STORAGE_KEY, playerToken)
  } else {
    window.localStorage.removeItem(PLAYER_TOKEN_STORAGE_KEY)
  }
}

function clearPersistedSession() {
  if (typeof window === 'undefined') return

  window.localStorage.removeItem(SESSION_STORAGE_KEY)
  window.localStorage.removeItem(PLAYER_TOKEN_STORAGE_KEY)
}

function deriveState(
  gameState: GameState | null,
  loadingCount: number
): Pick<
  GameStoreState,
  | 'isLoading'
  | 'myPlayer'
  | 'currentPhase'
  | 'currentDay'
  | 'gameLogs'
  | 'wolfDiscussMessages'
  | 'winner'
  | 'sheriffId'
  | 'sheriffCandidates'
  | 'isCandidate'
> {
  const players = gameState?.players || []
  const myPlayer = players.find((player) => player.is_human) || null
  const sheriffCandidates = gameState?.sheriff_candidate_ids || []

  return {
    isLoading: loadingCount > 0,
    myPlayer,
    currentPhase: gameState?.phase || '',
    currentDay: gameState?.day || 1,
    gameLogs: gameState?.game_logs || [],
    wolfDiscussMessages: gameState?.wolf_discuss_messages || [],
    winner: gameState?.winner || null,
    sheriffId: gameState?.sheriff_id || null,
    sheriffCandidates,
    isCandidate: myPlayer ? sheriffCandidates.includes(myPlayer.id) : false,
  }
}

export const useGameStore = create<GameStoreState>((set, get) => {
  const watchLoading = (isLoading: boolean, actionType: string) => {
    if (isLoading) {
      if (loadingTimeout) clearTimeout(loadingTimeout)
      const timeoutMs = (ACTION_TIMEOUTS[actionType] ?? DEFAULT_TIMEOUT) * 1000
      loadingTimeout = setTimeout(() => {
        const state = get()
        if (state.loadingCount > 0) {
          state.cancelLoading()
          state.setError('操作超时，请重试。如果问题持续，请刷新页面。')
        }
      }, timeoutMs)
    } else {
      if (loadingTimeout) {
        clearTimeout(loadingTimeout)
        loadingTimeout = null
      }
      set({ currentActionType: '' })
    }
  }

  // Shared failure handling: game gone / auth lost -> drop the session so the
  // UI can route the player back home instead of looping forever.
  const handleFatal = (message: string) => {
    clearPersistedSession()
    set({
      gameState: null,
      sessionId: null,
      playerToken: null,
      connectionStatus: 'offline',
      ...deriveState(null, get().loadingCount),
    })
    get().setError(message)
  }

  return {
    gameState: null,
    sessionId: null,
    playerToken: null,
    loadingCount: 0,
    isLoading: false,
    loadingText: DEFAULT_LOADING_TEXT,
    loadingStartTime: 0,
    error: null,
    connectionStatus: 'offline',
    currentActionType: '',
    myPlayer: null,
    currentPhase: '',
    currentDay: 1,
    gameLogs: [],
    wolfDiscussMessages: [],
    winner: null,
    sheriffId: null,
    sheriffCandidates: [],
    isCandidate: false,

    setError: (message) => {
      if (errorTimeout) {
        clearTimeout(errorTimeout)
        errorTimeout = null
      }
      set({ error: message })
      if (message) {
        errorTimeout = setTimeout(() => { set({ error: null }) }, ERROR_DISPLAY_MS)
      }
    },

    setLoading: (loading, text = DEFAULT_LOADING_TEXT) => {
      if (loading) {
        get().startLoading(text)
      } else {
        get().cancelLoading()
      }
    },

    startLoading: (text = DEFAULT_LOADING_TEXT) => {
      set((state) => {
        const newCount = state.loadingCount + 1
        if (newCount === 1) {
          watchLoading(true, state.currentActionType)
        }
        return {
          loadingCount: newCount,
          isLoading: true,
          loadingText: text,
          loadingStartTime: Date.now(),
        }
      })
    },

    stopLoading: () => {
      set((state) => {
        const newCount = Math.max(0, state.loadingCount - 1)
        if (newCount === 0) {
          watchLoading(false, '')
          return {
            loadingCount: 0,
            isLoading: false,
            loadingText: DEFAULT_LOADING_TEXT,
            loadingStartTime: 0,
          }
        }
        return { loadingCount: newCount, isLoading: true }
      })
    },

    cancelLoading: () => {
      set({
        loadingCount: 0,
        isLoading: false,
        loadingText: DEFAULT_LOADING_TEXT,
        loadingStartTime: 0,
      })
      watchLoading(false, '')
    },

    createGame: async () => {
      const { startLoading, stopLoading, setError } = get()
      startLoading('正在创建游戏...')
      setError(null)
      try {
        const response = await gameApi.createGame()
        set({
          gameState: response.state,
          sessionId: response.state.session_id,
          playerToken: response.player_token || null,
          ...deriveState(response.state, get().loadingCount),
        })
        persistSession(response.state.session_id, response.player_token || null)
        // Realtime is connected by GameRoom on mount (single owner of the
        // connection lifecycle), so we don't start it here.
      } catch (err: unknown) {
        setError(parseApiError(err, '创建游戏失败').message)
        throw err
      } finally {
        stopLoading()
      }
    },

    fetchGameState: async () => {
      let { sessionId, playerToken } = get()
      if (!sessionId) {
        const storedSessionId = getStoredSessionId()
        if (storedSessionId) {
          sessionId = storedSessionId
          set({ sessionId })
        } else {
          return
        }
      }

      try {
        if (!playerToken) {
          playerToken = getStoredPlayerToken()
          set({ playerToken })
        }

        const state = await gameApi.getGameState(sessionId, playerToken)
        set({
          gameState: state,
          ...deriveState(state, get().loadingCount),
        })
      } catch (err: unknown) {
        const { status, message } = parseApiError(err, '获取游戏状态失败')
        if (status === 404 || status === 403) {
          realtime.stop()
          handleFatal(status === 404 ? '游戏不存在' : '登录已失效，请重新开始游戏')
        } else {
          get().setError(message)
        }
        console.error('Failed to fetch game state:', err)
      }
    },

    submitAction: async (type, targetId, content) => {
      const { sessionId, playerToken, myPlayer, setError, startLoading, stopLoading, fetchGameState } = get()

      if (!sessionId || !myPlayer) {
        setError('无效的游戏状态或玩家')
        return
      }

      const text = ACTION_LOADING_TEXT[type as string] || '处理中...'
      set({ currentActionType: type as string })
      startLoading(text)
      setError(null)
      try {
        const token = playerToken || getStoredPlayerToken()
        const result = await gameApi.submitAction(sessionId, {
          player_id: myPlayer.id,
          type: type as ActionType,
          target_id: targetId ?? undefined,
          content,
        }, token)
        if (result && result.success === false) {
          setError(result.message || '操作未被接受')
        }
        await fetchGameState()
      } catch (err: unknown) {
        setError(parseApiError(err, '提交操作失败').message)
        throw err
      } finally {
        stopLoading()
        set({ currentActionType: '' })
      }
    },

    connectRealtime: () => {
      const { sessionId, playerToken } = get()
      if (!sessionId) return
      realtime.start(sessionId, playerToken, {
        onUpdate: (state) => {
          set({
            gameState: state,
            ...deriveState(state, get().loadingCount),
          })
        },
        onStatus: (status) => set({ connectionStatus: status }),
        onFatal: (message) => handleFatal(message),
      })
    },

    disconnectRealtime: () => {
      realtime.stop()
      set({ connectionStatus: 'offline' })
    },

    // Restore session identity from storage. The realtime manager hydrates once
    // when connected (owned by GameRoom), so we do not fetch/connect here — this
    // avoids the previous double initial request.
    recoverSession: () => {
      const storedSessionId = getStoredSessionId()
      if (!storedSessionId) return
      set({
        sessionId: storedSessionId,
        playerToken: getStoredPlayerToken(),
      })
    },

    clearSession: () => {
      get().disconnectRealtime()
      set({
        gameState: null,
        sessionId: null,
        playerToken: null,
        error: null,
        connectionStatus: 'offline',
        ...deriveState(null, 0),
      })
      clearPersistedSession()
    }
  }
})
