// Game Types for AI Werewolf VN

export type GamePhase =
  | 'GAME_START'
  | 'NIGHT_START'
  | 'NIGHT_WOLF_DISCUSS'
  | 'NIGHT_WOLF_VOTE'
  | 'NIGHT_SEER'
  | 'NIGHT_WITCH'
  | 'NIGHT_GUARD'
  | 'NIGHT_RESOLVE'
  | 'DAY_START'
  | 'DAY_LAST_WORDS'
  | 'SHERIFF_ELECTION'
  | 'SHERIFF_SPEECH'
  | 'SHERIFF_VOTE'
  | 'DAY_DISCUSS'
  | 'DAY_VOTE'
  | 'DAY_VOTE_RESULT'
  | 'HUNTER_SKILL'
  | 'SHERIFF_TRANSFER'
  | 'GAME_END'

export type Role =
  | 'villager'
  | 'wolf'
  | 'wolf_king'
  | 'seer'
  | 'witch'
  | 'guard'
  | 'hunter'

export type Camp = 'good' | 'wolf'

// 选择模式类型
export type SelectionMode =
  | 'none'
  | 'vote'
  | 'kill'
  | 'check'
  | 'protect'
  | 'poison'
  | 'save'
  | 'shoot'

// 玩家标记类型
export interface PlayerMarker {
  type: 'wolf' | 'good' | 'suspicious' | 'trusted' | 'custom'
  label?: string
  color?: string
}

// 投票记录类型
export interface VoteRecord {
  voterId: number
  targetId: number | null
  weight: number
}

export type ActionType =
  | 'pass'
  | 'confirm'
  | 'vote'
  | 'kill'
  | 'check'
  | 'poison'
  | 'save'
  | 'guard'
  | 'shoot'
  | 'speech'
  | 'run_for_sheriff'
  | 'withdraw'
  | 'self_explode'

export interface Player {
  id: number
  name: string
  role: Role
  portrait: string
  is_human: boolean
  is_alive: boolean
  is_sheriff: boolean
  has_acted: boolean
  poison_used?: boolean
  antidote_used?: boolean
  gun_used?: boolean
  markers?: PlayerMarker[]
}

export interface GameLog {
  id: string
  day: number
  phase: GamePhase
  content: string
  player_id?: number
  is_public: boolean
  type: 'normal' | 'broadcast' | 'speech' | 'action'
  data?: Record<string, any>
}

export interface WolfDiscussMessage {
  id: string
  speaker_id: number
  content: string
  round: number
}

export interface GameState {
  session_id: string
  day: number
  phase: GamePhase
  players: Player[]
  game_logs: GameLog[]
  time_remaining: number
  winner: string | null
  votes: Record<number, number>
  wolf_kill_target: number | null
  dead_players: number[]
  sheriff_candidate_ids: number[]
  sheriff_id: number | null
  election_explode_count: number
  pending_sheriff_election: boolean
  election_cancelled: boolean
  speaking_order: number[]
  current_speaker_index: number
  wolf_discuss_messages?: WolfDiscussMessage[]
}

export interface ActionRequest {
  player_id: number
  type: ActionType
  target_id?: number
  content?: string
  timestamp?: number
}

// Role display info
export const ROLE_NAMES: Record<Role, string> = {
  villager: '村民',
  wolf: '狼人',
  wolf_king: '狼王',
  seer: '预言家',
  witch: '女巫',
  guard: '守卫',
  hunter: '猎人'
}

export const ROLE_DESCRIPTIONS: Record<Role, string> = {
  villager: '村民：无特殊技能，靠推理和投票帮助好人阵营获胜。',
  wolf: '狼人：每晚可与队友讨论并击杀一名玩家。',
  wolf_king: '狼王：狼人身份，出局时可开枪带走一人（被毒/自爆除外）。',
  seer: '预言家：每晚可查验一名玩家的身份（好人/坏人）。',
  witch: '女巫：拥有一瓶解药和一瓶毒药，每晚只能使用一瓶。',
  guard: '守卫：每晚可守护一名玩家免受狼人击杀，不可连续守护同一人。',
  hunter: '猎人：出局时可开枪带走一人（被毒除外）。'
}

export const PHASE_NAMES: Record<GamePhase, string> = {
  GAME_START: '游戏开始',
  NIGHT_START: '夜晚开始',
  NIGHT_WOLF_DISCUSS: '狼人讨论',
  NIGHT_WOLF_VOTE: '狼人投票',
  NIGHT_SEER: '预言家行动',
  NIGHT_WITCH: '女巫行动',
  NIGHT_GUARD: '守卫行动',
  NIGHT_RESOLVE: '夜晚结算',
  DAY_START: '天亮了',
  DAY_LAST_WORDS: '遗言阶段',
  SHERIFF_ELECTION: '警长竞选',
  SHERIFF_SPEECH: '竞选发言',
  SHERIFF_VOTE: '警长投票',
  DAY_DISCUSS: '白天讨论',
  DAY_VOTE: '白天投票',
  DAY_VOTE_RESULT: '投票结果',
  HUNTER_SKILL: '猎人/狼王技能',
  SHERIFF_TRANSFER: '警徽移交',
  GAME_END: '游戏结束'
}

// Helper functions
export function isWolfRole(role: Role): boolean {
  return role === 'wolf' || role === 'wolf_king'
}

export function isGoodRole(role: Role): boolean {
  return !isWolfRole(role)
}

export function getRoleCamp(role: Role): Camp {
  return isWolfRole(role) ? 'wolf' : 'good'
}
