import axios from 'axios'
import type { GameState, ActionRequest } from '../types'

// Configure axios defaults
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// API response types
export interface ApiResponse<T> {
  data: T
  success: boolean
  message?: string
}

// Game API
export const gameApi = {
  // Create a new game
  async createGame(): Promise<GameState> {
    const response = await apiClient.post<GameState>('/game/create')
    return response.data
  },

  // Get game state
  async getGameState(sessionId: string): Promise<GameState> {
    const response = await apiClient.get<GameState>(`/game/${sessionId}`)
    return response.data
  },

  // Submit player action
  async submitAction(sessionId: string, action: ActionRequest): Promise<void> {
    await apiClient.post(`/player/${sessionId}/action`, action)
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

// Config API
export const configApi = {
  // 获取LLM配置
  async getLLMConfig(): Promise<LLMConfigResponse> {
    const response = await apiClient.get<LLMConfigResponse>('/config/llm')
    return response.data
  },

  // 更新LLM配置
  async setLLMConfig(config: LLMConfigRequest): Promise<LLMConfigResponse> {
    const response = await apiClient.post<LLMConfigResponse>('/config/llm', config)
    return response.data
  },

  // 测试LLM连接
  async testLLMConnection(): Promise<LLMTestResponse> {
    const response = await apiClient.post<LLMTestResponse>('/config/llm/test')
    return response.data
  }
}

// Polling helper for game state updates
export class GameStatePoller {
  private intervalId: number | null = null
  private sessionId: string | null = null
  private onUpdate: ((state: GameState) => void) | null = null
  private onError: ((error: Error) => void) | null = null

  start(
    sessionId: string,
    onUpdate: (state: GameState) => void,
    onError?: (error: Error) => void,
    intervalMs: number = 2000
  ) {
    this.stop()
    this.sessionId = sessionId
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
      const state = await gameApi.getGameState(this.sessionId)
      this.onUpdate(state)
    } catch (error) {
      if (this.onError) {
        this.onError(error as Error)
      }
    }
  }
}

export default gameApi
