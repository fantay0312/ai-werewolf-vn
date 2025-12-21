import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { gameApi, GameStatePoller } from '../api'
import type { GameState, ActionType } from '../types'

export const useGameStore = defineStore('game', () => {
  // State
  const gameState = ref<GameState | null>(null)
  const sessionId = ref<string | null>(null)
  const loadingCount = ref(0)
  const isLoading = computed(() => loadingCount.value > 0)
  const loadingText = ref<string>('加载中...')
  const loadingStartTime = ref<number>(0)
  const error = ref<string | null>(null)
  const poller = new GameStatePoller()
  let errorTimeout: ReturnType<typeof setTimeout> | null = null

  // Auto-clear error after 3 seconds
  function setError(message: string | null) {
    if (errorTimeout) {
      clearTimeout(errorTimeout)
      errorTimeout = null
    }
    error.value = message
    if (message) {
      errorTimeout = setTimeout(() => {
        error.value = null
      }, 3000)
    }
  }

  // 设置加载状态
  function startLoading(text: string = '加载中...') {
    loadingCount.value++
    loadingText.value = text
    loadingStartTime.value = Date.now()
  }

  function stopLoading() {
    loadingCount.value = Math.max(0, loadingCount.value - 1)
    if (loadingCount.value === 0) {
      loadingText.value = '加载中...'
      loadingStartTime.value = 0
    }
  }

  // 强制取消加载
  function cancelLoading() {
    console.warn('用户取消加载')
    loadingCount.value = 0
    loadingText.value = '加载中...'
    loadingStartTime.value = 0
  }

  // 根据操作类型设置不同的超时时间（秒）
  const getTimeoutForAction = (actionType: string): number => {
    const timeoutMap: Record<string, number> = {
      'speech': 45,      // 发言可能需要AI生成，需要更长时间
      'confirm': 15,     // 确认操作通常很快
      'pass': 15,        // 跳过操作很快
      'vote': 20,        // 投票需要思考
      'kill': 25,        // 击杀需要讨论
      'check': 30,       // 查验需要AI思考
      'save': 25,        // 使用解药需要判断
      'poison': 25,      // 使用毒药需要判断
      'guard': 25,       // 守护需要判断
      'shoot': 20,       // 开枪需要判断
      'run_for_sheriff': 20, // 竞选需要思考
      'withdraw': 15,    // 退水很快
      'self_explode': 15 // 自爆很快
    }
    return timeoutMap[actionType] || 35 // 默认35秒（比API的30秒多5秒）
  }

  // Safety timeout to prevent stuck loading (根据操作类型动态设置)
  let loadingTimeout: ReturnType<typeof setTimeout> | null = null
  let currentActionType = ref<string>('')
  
  watch(isLoading, (loading: boolean) => {
    if (loading) {
      if (loadingTimeout) clearTimeout(loadingTimeout)
      const timeoutMs = getTimeoutForAction(currentActionType.value) * 1000
      loadingTimeout = setTimeout(() => {
        if (isLoading.value) {
          console.warn(`Loading stuck for too long (${currentActionType.value}), forcing reset`)
          loadingCount.value = 0
          loadingText.value = '加载中...'
          loadingStartTime.value = 0
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
    console.log('createGame: start loading')
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
      console.error('Failed to create game:', err)
      throw err
    } finally {
      console.log('createGame: stop loading')
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

    // 根据操作类型显示不同的加载提示
    const loadingTextMap: Record<string, string> = {
      'confirm': '正在确认...',
      'vote': '正在投票...',
      'kill': '正在执行行动...',
      'check': '正在查验...',
      'save': '正在使用解药...',
      'poison': '正在使用毒药...',
      'guard': '正在守护...',
      'speech': '正在发言...',
      'run_for_sheriff': '正在竞选警长...',
      'withdraw': '正在退水...',
      'shoot': '正在开枪...',
      'pass': '正在跳过...'
    }
    const text = loadingTextMap[type] || '处理中...'
    
    // 记录当前操作类型，用于设置超时时间
    currentActionType.value = type
    
    console.log(`submitAction(${type}): start loading`)
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
      console.error('Failed to submit action:', err)
      throw err
    } finally {
      console.log(`submitAction(${type}): stop loading`)
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
