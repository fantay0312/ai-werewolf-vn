import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { gameApi, GameStatePoller } from '../api'
import type { GameState, ActionType } from '../types'

const DEFAULT_LOADING_TEXT = '加载中...'
const ERROR_DISPLAY_MS = 3000

// Timeout per action type (seconds)
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

// Loading text per action type
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

export const useGameStore = defineStore('game', () => {
  // State
  const gameState = ref<GameState | null>(null)
  const sessionId = ref<string | null>(null)
  const loadingCount = ref(0)
  const isLoading = computed(() => loadingCount.value > 0)
  const loadingText = ref<string>(DEFAULT_LOADING_TEXT)
  const loadingStartTime = ref<number>(0)
  const error = ref<string | null>(null)
  const poller = new GameStatePoller()
  let errorTimeout: ReturnType<typeof setTimeout> | null = null

  function setError(message: string | null) {
    if (errorTimeout) {
      clearTimeout(errorTimeout)
      errorTimeout = null
    }
    error.value = message
    if (message) {
      errorTimeout = setTimeout(() => { error.value = null }, ERROR_DISPLAY_MS)
    }
  }

  function startLoading(text: string = DEFAULT_LOADING_TEXT) {
    loadingCount.value++
    loadingText.value = text
    loadingStartTime.value = Date.now()
  }

  function stopLoading() {
    loadingCount.value = Math.max(0, loadingCount.value - 1)
    if (loadingCount.value === 0) {
      loadingText.value = DEFAULT_LOADING_TEXT
      loadingStartTime.value = 0
    }
  }

  function cancelLoading() {
    loadingCount.value = 0
    loadingText.value = DEFAULT_LOADING_TEXT
    loadingStartTime.value = 0
  }

  // Safety timeout to prevent stuck loading
  let loadingTimeout: ReturnType<typeof setTimeout> | null = null
  const currentActionType = ref<string>('')

  watch(isLoading, (loading: boolean) => {
    if (loading) {
      if (loadingTimeout) clearTimeout(loadingTimeout)
      const timeoutMs = (ACTION_TIMEOUTS[currentActionType.value] ?? DEFAULT_TIMEOUT) * 1000
      loadingTimeout = setTimeout(() => {
        if (isLoading.value) {
          cancelLoading()
          setError('操作超时，请重试。如果问题持续，请刷新页面。')
        }
      }, timeoutMs)
    } else {
      if (loadingTimeout) {
        clearTimeout(loadingTimeout)
        loadingTimeout = null
      }
      currentActionType.value = ''
    }
  })

  // Computed
  const players = computed(() => gameState.value?.players || [])
  const myPlayer = computed(() => players.value.find(p => p.is_human))
  const currentPhase = computed(() => gameState.value?.phase || '')
  const currentDay = computed(() => gameState.value?.day || 1)
  const gameLogs = computed(() => gameState.value?.game_logs || [])
  const publicLogs = computed(() => gameLogs.value.filter(log => log.is_public))
  const winner = computed(() => gameState.value?.winner)
  const isGameOver = computed(() => currentPhase.value === 'GAME_END')
  const sheriffId = computed(() => gameState.value?.sheriff_id)
  const sheriffCandidates = computed(() => gameState.value?.sheriff_candidate_ids || [])
  const isCandidate = computed(() => {
    const myId = myPlayer.value?.id
    return myId ? sheriffCandidates.value.includes(myId) : false
  })

  // Actions
  async function createGame() {
    startLoading('正在创建游戏...')
    setError(null)
    try {
      const state = await gameApi.createGame()
      gameState.value = state
      sessionId.value = state.session_id
      localStorage.setItem('werewolf_session_id', state.session_id)
      startPolling()
    } catch (err: any) {
      setError(err.response?.data?.detail || '创建游戏失败')
      throw err
    } finally {
      stopLoading()
    }
  }

  async function fetchGameState() {
    if (!sessionId.value) {
      const storedSessionId = localStorage.getItem('werewolf_session_id')
      if (storedSessionId) {
        sessionId.value = storedSessionId
      } else {
        return
      }
    }

    try {
      const state = await gameApi.getGameState(sessionId.value)
      gameState.value = state
      // Don't clear error here - let it auto-clear after timeout
    } catch (err: any) {
      if (err.response?.status === 404) {
        setError('游戏不存在')
        localStorage.removeItem('werewolf_session_id')
        sessionId.value = null
      } else {
        setError(err.response?.data?.detail || '获取游戏状态失败')
      }
      console.error('Failed to fetch game state:', err)
    }
  }

  async function submitAction(type: ActionType | string, targetId?: number | null, content?: string) {
    if (!sessionId.value || !myPlayer.value) {
      setError('无效的游戏状态或玩家')
      return
    }

    const text = ACTION_LOADING_TEXT[type] || '处理中...'
    currentActionType.value = type
    startLoading(text)
    setError(null)
    try {
      await gameApi.submitAction(sessionId.value, {
        player_id: myPlayer.value.id,
        type: type as ActionType,
        target_id: targetId ?? undefined,
        content,
        timestamp: Date.now() / 1000
      })
      await fetchGameState()
    } catch (err: any) {
      setError(err.response?.data?.detail || '提交操作失败')
      throw err
    } finally {
      stopLoading()
      currentActionType.value = ''
    }
  }

  function startPolling() {
    if (!sessionId.value) return
    poller.start(
      sessionId.value,
      (state) => {
        gameState.value = state
      },
      (err) => {
        console.error('Polling error:', err)
      },
      2000
    )
  }

  function stopPolling() {
    poller.stop()
  }

  function recoverSession() {
    const storedSessionId = localStorage.getItem('werewolf_session_id')
    if (storedSessionId) {
      sessionId.value = storedSessionId
      fetchGameState()
      startPolling()
    }
  }

  function clearSession() {
    stopPolling()
    gameState.value = null
    sessionId.value = null
    setError(null)
    localStorage.removeItem('werewolf_session_id')
  }

  return {
    // State
    gameState,
    sessionId,
    isLoading,
    loadingText,
    loadingStartTime,
    error,
    // Computed
    players,
    myPlayer,
    currentPhase,
    currentDay,
    gameLogs,
    publicLogs,
    winner,
    isGameOver,
    sheriffId,
    sheriffCandidates,
    isCandidate,
    // Actions
    createGame,
    fetchGameState,
    submitAction,
    startPolling,
    stopPolling,
    recoverSession,
    clearSession,
    cancelLoading
  }
})
