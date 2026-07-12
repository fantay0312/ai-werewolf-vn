import axios from 'axios'
import type {
  ActionRequest,
  ActionResponse,
  CreateGameResponse,
  GameState,
} from '../types'

/**
 * Resolve the API base URL:
 *  1. VITE_API_BASE_URL env override always wins.
 *  2. On the Vite dev server (import.meta.env.DEV) the backend runs separately
 *     on :8000, so default to that.
 *  3. In a production build (served by the backend / nginx) use a same-origin
 *     relative base so no host is hard-coded.
 */
function resolveApiBaseUrl(): string {
  const override = import.meta.env.VITE_API_BASE_URL
  if (override) return override
  if (import.meta.env.DEV) return 'http://127.0.0.1:8000/api'
  return '/api'
}

export const API_BASE_URL = resolveApiBaseUrl()

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

/** Normalized transport error, so consumers never poke at axios internals. */
export interface ApiError {
  status?: number
  message: string
}

export function parseApiError(error: unknown, fallback = '请求失败'): ApiError {
  if (axios.isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: string } | undefined)?.detail
    return {
      status: error.response?.status,
      message: detail || error.message || fallback,
    }
  }
  if (error instanceof Error) {
    return { message: error.message || fallback }
  }
  return { message: fallback }
}

// SSE ticket response (POST /api/sse/ticket)
export interface SseTicketResponse {
  ticket: string
  expires_in: number
}

// Game API
export const gameApi = {
  // Create a new game
  async createGame(): Promise<CreateGameResponse> {
    const response = await apiClient.post<CreateGameResponse>('/game/create')
    const data = response.data
    if (!data?.player_token) {
      throw new Error('创建游戏失败：服务器未返回玩家令牌')
    }
    return data
  },

  // Get game state
  async getGameState(sessionId: string, playerToken?: string | null): Promise<GameState> {
    const response = await apiClient.get<GameState>(`/game/${sessionId}`, {
      headers: buildRequestHeaders(playerToken),
    })
    return response.data
  },

  // Submit player action
  async submitAction(
    sessionId: string,
    action: ActionRequest,
    playerToken?: string | null
  ): Promise<ActionResponse> {
    const response = await apiClient.post<ActionResponse>(`/player/${sessionId}/action`, action, {
      headers: buildRequestHeaders(playerToken),
    })
    return response.data ?? { success: true }
  },

  // Request a short-lived, single-use SSE ticket for EventSource auth.
  // Backend expects session_id (and optional viewer_id) as query params; auth
  // still travels in the X-Player-Token header.
  async fetchSseTicket(
    sessionId: string,
    playerToken?: string | null,
    viewerId?: number
  ): Promise<SseTicketResponse> {
    const params: Record<string, string> = { session_id: sessionId }
    if (viewerId !== undefined) {
      params.viewer_id = String(viewerId)
    }
    const response = await apiClient.post<SseTicketResponse>('/sse/ticket', undefined, {
      params,
      headers: buildRequestHeaders(playerToken),
    })
    return response.data
  },
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

export default gameApi
