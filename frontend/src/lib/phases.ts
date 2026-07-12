// Shared phase helpers + seat-selection derivation. Replaces the several
// divergent "is it night" / "which selection mode" copies across components.
import type { GamePhase, Player, SelectionMode } from '../types'
import { isWolfRole } from '../types'

const NIGHT_PHASES: readonly GamePhase[] = [
  'NIGHT_START', 'NIGHT_WOLF_DISCUSS', 'NIGHT_WOLF_VOTE',
  'NIGHT_SEER', 'NIGHT_WITCH', 'NIGHT_GUARD', 'NIGHT_RESOLVE',
]

const NIGHT_ACTION_PHASES: readonly GamePhase[] = [
  'NIGHT_WOLF_DISCUSS', 'NIGHT_WOLF_VOTE', 'NIGHT_SEER', 'NIGHT_WITCH', 'NIGHT_GUARD',
]

// Phases whose voting flows through VoteModal (single vote surface).
const VOTE_PHASES: readonly GamePhase[] = ['DAY_VOTE', 'DAY_PK_VOTE', 'SHERIFF_VOTE']

export function isNightPhase(phase: string): boolean {
  return (NIGHT_PHASES as readonly string[]).includes(phase)
}

export function isNightActionPhase(phase: string): boolean {
  return (NIGHT_ACTION_PHASES as readonly string[]).includes(phase)
}

export function isVotePhase(phase: string): boolean {
  return (VOTE_PHASES as readonly string[]).includes(phase)
}

/** Strip a leading "N号:" / "N号：" speaker prefix from a log/message line. */
export function stripSpeakerPrefix(content: string, playerId?: number): string {
  if (!playerId) return content
  return content.replace(new RegExp(`^${playerId}号[：:]\\s*`), '')
}

/**
 * Derive the table's seat-click selection mode from the current phase and the
 * human's role/state. Vote phases return 'none' because VoteModal is the vote
 * surface (its overlay covers the table).
 */
export function getSelectionMode(
  phase: string,
  me: Player | null,
): SelectionMode {
  if (!me) return 'none'
  const role = me.role
  switch (phase) {
    case 'NIGHT_WOLF_VOTE':
      return isWolfRole(role) ? 'kill' : 'none'
    case 'NIGHT_SEER':
      return role === 'seer' ? 'check' : 'none'
    case 'NIGHT_WITCH':
      // Poison targets a seat; the antidote (save) is a separate no-target button.
      return role === 'witch' ? 'poison' : 'none'
    case 'NIGHT_GUARD':
      return role === 'guard' ? 'protect' : 'none'
    case 'HUNTER_SKILL':
      return (role === 'hunter' || role === 'wolf_king') && !me.is_alive ? 'shoot' : 'none'
    case 'SHERIFF_TRANSFER':
      return me.is_sheriff ? 'vote' : 'none'
    default:
      return 'none'
  }
}
