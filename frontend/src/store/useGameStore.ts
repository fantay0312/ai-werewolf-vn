import { create } from 'zustand'
import { gameApi, GameStatePoller } from '../api'
import type { ActionType, GameState, WolfDiscussMessage } from '../types'

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
  loadingText: string
  loadingStartTime: number
  error: string | null
  currentActionType: string

  // Actions
  setError: (message: string | null) => void
  startLoading: (text?: string) => void
  stopLoading: () => void
  cancelLoading: () => void
  createGame: () => Promise<void>
  fetchGameState: () => Promise<void>
  submitAction: (type: ActionType | string, targetId?: number | null, content?: string) => Promise<void>
  startPolling: () => void
  stopPolling: () => void
  recoverSession: () => void
  clearSession: () => void
}

const poller = new GameStatePoller()
let errorTimeout: ReturnType<typeof setTimeout> | null = null
let loadingTimeout: ReturnType<typeof setTimeout> | null = null

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

  return {
    gameState: null,
    sessionId: null,
    playerToken: null,
    loadingCount: 0,
    loadingText: DEFAULT_LOADING_TEXT,
    loadingStartTime: 0,
    error: null,
    currentActionType: '',

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

    startLoading: (text = DEFAULT_LOADING_TEXT) => {
      set((state) => {
        const newCount = state.loadingCount + 1
        if (newCount === 1) {
          watchLoading(true, state.currentActionType)
        }
        return {
          loadingCount: newCount,
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
            loadingText: DEFAULT_LOADING_TEXT,
            loadingStartTime: 0,
          }
        }
        return { loadingCount: newCount }
      })
    },

    cancelLoading: () => {
      set({
        loadingCount: 0,
        loadingText: DEFAULT_LOADING_TEXT,
        loadingStartTime: 0,
      })
      watchLoading(false, '')
    },

    createGame: async () => {
      const { startLoading, stopLoading, setError, startPolling } = get()
      startLoading('正在创建游戏...')
      setError(null)
      try {
        const response = await gameApi.createGame()
        set({
          gameState: response.state,
          sessionId: response.state.session_id,
          playerToken: response.player_token || null
        })
        localStorage.setItem(SESSION_STORAGE_KEY, response.state.session_id)
        if (response.player_token) {
          localStorage.setItem(PLAYER_TOKEN_STORAGE_KEY, response.player_token)
        } else {
          localStorage.removeItem(PLAYER_TOKEN_STORAGE_KEY)
        }
        startPolling()
      } catch (err: any) {
        setError(err.response?.data?.detail || '创建游戏失败')
        throw err
      } finally {
        stopLoading()
      }
    },

    fetchGameState: async () => {
      let { sessionId, playerToken } = get()
      if (!sessionId) {
        const storedSessionId = localStorage.getItem(SESSION_STORAGE_KEY)
        if (storedSessionId) {
          sessionId = storedSessionId
          set({ sessionId })
        } else {
          return
        }
      }

      try {
        if (!playerToken) {
          playerToken = localStorage.getItem(PLAYER_TOKEN_STORAGE_KEY)
          set({ playerToken })
        }

        const state = await gameApi.getGameState(sessionId, playerToken)
        set({ gameState: state })
      } catch (err: any) {
        if (err.response?.status === 404) {
          get().setError('游戏不存在')
          localStorage.removeItem(SESSION_STORAGE_KEY)
          localStorage.removeItem(PLAYER_TOKEN_STORAGE_KEY)
          set({ sessionId: null, playerToken: null })
        } else {
          get().setError(err.response?.data?.detail || '获取游戏状态失败')
        }
        console.error('Failed to fetch game state:', err)
      }
    },

    submitAction: async (type, targetId, content) => {
      const { sessionId, playerToken, setError, startLoading, stopLoading, fetchGameState, gameState } = get()
      const myPlayer = gameState?.players.find(p => p.is_human)
      
      if (!sessionId || !myPlayer) {
        setError('无效的游戏状态或玩家')
        return
      }

      const text = ACTION_LOADING_TEXT[type as string] || '处理中...'
      set({ currentActionType: type as string })
      startLoading(text)
      setError(null)
      try {
        const token = playerToken || localStorage.getItem(PLAYER_TOKEN_STORAGE_KEY)
        await gameApi.submitAction(sessionId, {
          player_id: myPlayer.id,
          type: type as ActionType,
          target_id: targetId ?? undefined,
          content,
          timestamp: Date.now() / 1000
        }, token)
        await fetchGameState()
      } catch (err: any) {
        setError(err.response?.data?.detail || '提交操作失败')
        throw err
      } finally {
        stopLoading()
        set({ currentActionType: '' })
      }
    },

    startPolling: () => {
      const { sessionId, playerToken } = get()
      if (!sessionId) return
      poller.start(
        sessionId,
        playerToken,
        (state) => {
          set({ gameState: state })
        },
        (err) => {
          console.error('Polling error:', err)
        },
        2000
      )
    },

    stopPolling: () => {
      poller.stop()
    },

    recoverSession: () => {
      const storedSessionId = localStorage.getItem(SESSION_STORAGE_KEY)
      if (storedSessionId) {
        set({
          sessionId: storedSessionId,
          playerToken: localStorage.getItem(PLAYER_TOKEN_STORAGE_KEY)
        })
        get().fetchGameState()
        get().startPolling()
      }
    },

    clearSession: () => {
      get().stopPolling()
      set({
        gameState: null,
        sessionId: null,
        playerToken: null,
        error: null,
      })
      localStorage.removeItem(SESSION_STORAGE_KEY)
      localStorage.removeItem(PLAYER_TOKEN_STORAGE_KEY)
    }
  }
})

// Selectors for computed properties
export const useIsLoading = () => useGameStore(state => state.loadingCount > 0)
export const usePlayers = () => useGameStore(state => state.gameState?.players || [])
export const useMyPlayer = () => useGameStore(state => state.gameState?.players.find(p => p.is_human))
export const useCurrentPhase = () => useGameStore(state => state.gameState?.phase || '')
export const useCurrentDay = () => useGameStore(state => state.gameState?.day || 1)
export const useGameLogs = () => useGameStore(state => state.gameState?.game_logs || [])
export const usePublicLogs = () => useGameStore(state => (state.gameState?.game_logs || []).filter(log => log.is_public))
export const useWolfDiscussMessages = () => useGameStore(state => state.gameState?.wolf_discuss_messages || [])
export const useWinner = () => useGameStore(state => state.gameState?.winner)
export const useIsGameOver = () => useGameStore(state => !!state.gameState?.phase && state.gameState.phase === 'GAME_END')
export const useSheriffId = () => useGameStore(state => state.gameState?.sheriff_id)
export const useSheriffCandidates = () => useGameStore(state => state.gameState?.sheriff_candidate_ids || [])
export const useIsCandidate = () => {
  const myPlayer = useMyPlayer()
  const candidates = useSheriffCandidates()
  return myPlayer ? candidates.includes(myPlayer.id) : false
}
