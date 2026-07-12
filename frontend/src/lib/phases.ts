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

export interface ParsedSpeech {
  /** e.g. "9号", or null when no speaker could be parsed. */
  speaker: string | null
  /** e.g. "竞选发言" from a "9号(竞选发言): ..." prefix, else null. */
  tag: string | null
  /** The speech body with the "N号(tag):" prefix removed. */
  text: string
}

/**
 * Defensive parser for a speech line. Handles the raw log/message shapes the
 * backend emits — "9号: ...", "9号：...", "9号(竞选发言): ..." — and degrades
 * gracefully to the whole line when the format is unexpected (never throws).
 * Used to render a speaker chip + small tag instead of a raw text prefix.
 */
export function parseSpeechLine(content: string, playerId?: number): ParsedSpeech {
  if (!content) return { speaker: playerId ? `${playerId}号` : null, tag: null, text: '' }
  const match = content.match(/^\s*(\d+号)\s*(?:[（(]([^）)]*)[）)])?\s*[：:]\s*([\s\S]*)$/)
  if (match) {
    return { speaker: match[1], tag: match[2]?.trim() || null, text: match[3].trim() }
  }
  return {
    speaker: playerId ? `${playerId}号` : null,
    tag: null,
    text: stripSpeakerPrefix(content, playerId),
  }
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
