import axios from 'axios'
import type {
  ActionRequest,
  CreateGameResponse,
  GameState,
  GameStateView,
} from '../types'

// Configure axios defaults
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

const PLAYER_TOKEN_HEADER = 'X-Player-Token'
const ADMIN_TOKEN_HEADER = 'X-Admin-Token'
const ADMIN_TOKEN = import.meta.env.VITE_ADMIN_TOKEN

function buildRequestHeaders(playerToken?: string | null) {
  const headers: Record<string, string> = {}
  if (playerToken) {
    headers[PLAYER_TOKEN_HEADER] = playerToken
  }
  if (ADMIN_TOKEN) {
    headers[ADMIN_TOKEN_HEADER] = ADMIN_TOKEN
  }
  return Object.keys(headers).length > 0 ? headers : undefined
}

function isCreateGameResponse(data: unknown): data is CreateGameResponse {
  return Boolean(
    data &&
    typeof data === 'object' &&
    'player_token' in data &&
    'state' in data
  )
}

function normalizeCreateGameResponse(data: GameStateView | CreateGameResponse): CreateGameResponse {
  if (isCreateGameResponse(data)) {
    return data
  }

  return {
    player_token: '',
    state: data,
  }
}

// API response types
export interface ApiResponse<T> {
  data: T
  success: boolean
  message?: string
}

// Game API
export const gameApi = {
  // Create a new game
  async createGame(): Promise<CreateGameResponse> {
    const response = await apiClient.post<CreateGameResponse | GameStateView>('/game/create')
    return normalizeCreateGameResponse(response.data)
  },

  // Get game state
  async getGameState(sessionId: string, playerToken?: string | null): Promise<GameState> {
    const response = await apiClient.get<GameState>(`/game/${sessionId}`, {
      headers: buildRequestHeaders(playerToken),
    })
    return response.data
  },

  // Submit player action
  async submitAction(sessionId: string, action: ActionRequest, playerToken?: string | null): Promise<void> {
    await apiClient.post(`/player/${sessionId}/action`, action, {
      headers: buildRequestHeaders(playerToken),
    })
  }
}

// LLM配置类型
export interface LLMConfigResponse {
  api_key_set: boolean
  api_base: string | null
  model: string
  max_tokens: number
  temperature: number
}

export interface LLMConfigRequest {
  api_key?: string
  api_base?: string
  model?: string
  max_tokens?: number
  temperature?: number
}

export interface LLMTestResponse {
  success: boolean
  message: string
  model?: string
  response?: string
}

export interface LLMModelsResponse {
  success: boolean
  message: string
  models: Array<{ id: string; owned_by: string }>
}

// Config API
export const configApi = {
  // 获取LLM配置
  async getLLMConfig(): Promise<LLMConfigResponse> {
    const response = await apiClient.get<LLMConfigResponse>('/config/llm', {
      headers: buildRequestHeaders(),
    })
    return response.data
  },

  // 更新LLM配置
  async setLLMConfig(config: LLMConfigRequest): Promise<LLMConfigResponse> {
    const response = await apiClient.post<LLMConfigResponse>('/config/llm', config, {
      headers: buildRequestHeaders(),
    })
    return response.data
  },

  // 测试LLM连接
  async testLLMConnection(): Promise<LLMTestResponse> {
    const response = await apiClient.post<LLMTestResponse>('/config/llm/test', undefined, {
      headers: buildRequestHeaders(),
    })
    return response.data
  },

  // 获取可用模型列表
  async fetchModels(): Promise<LLMModelsResponse> {
    const response = await apiClient.get<LLMModelsResponse>('/config/llm/models', {
      headers: buildRequestHeaders(),
    })
    return response.data
  }
}

// Polling helper for game state updates
export class GameStatePoller {
  private intervalId: number | null = null
  private sessionId: string | null = null
  private playerToken: string | null = null
  private onUpdate: ((state: GameState) => void) | null = null
  private onError: ((error: Error) => void) | null = null

  start(
    sessionId: string,
    playerToken: string | null,
    onUpdate: (state: GameState) => void,
    onError?: (error: Error) => void,
    intervalMs: number = 2000
  ) {
    this.stop()
    this.sessionId = sessionId
    this.playerToken = playerToken
    this.onUpdate = onUpdate
    this.onError = onError || (() => {})

    this.poll()
    this.intervalId = window.setInterval(() => this.poll(), intervalMs)
  }

  stop() {
    if (this.intervalId) {
      window.clearInterval(this.intervalId)
      this.intervalId = null
    }
  }

  private async poll() {
    if (!this.sessionId || !this.onUpdate) return

    try {
      const state = await gameApi.getGameState(this.sessionId, this.playerToken)
      this.onUpdate(state)
    } catch (error) {
      if (this.onError) {
        this.onError(error as Error)
      }
    }
  }
}

export default gameApi
