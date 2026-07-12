// Vote record derivation under the votes-privacy contract.
//
// During collection (DAY_VOTE / SHERIFF_VOTE / DAY_PK_VOTE) gameState.votes /
// pk_votes hold ONLY the viewer's own ballot; every other ballot is hidden until
// the result. Result phases auto-advance instantly, so clients rarely observe a
// full `votes` map in state. The authoritative tally lives in the structured
// PUBLIC result log the backend emits (data.vote_entries / data.vote_counts).
//
// So: live progress derives from players' has_acted, and the tally view derives
// from the latest matching result log — never from other players' ballots.
import type { GameLog, VoteRecord } from '../types'

export type VoteKind = 'exile' | 'sheriff' | 'pk'

// The `data.event` name of each vote's PUBLIC tally log. day-vote and PK come
// from VoteResultHandler (carry `vote_entries`); the sheriff tally carries a
// `votes` map instead.
const TALLY_EVENT: Record<VoteKind, string> = {
  exile: 'day_vote_tallied',
  sheriff: 'sheriff_vote_tallied',
  pk: 'day_pk_vote_tallied',
}

interface VoteEntry {
  voter_id: number
  target_id: number | null
  weight?: number
}

/**
 * Full ballots for the just-resolved vote, read from the latest matching PUBLIC
 * tally log on `day`. Returns null when no tally exists yet (the vote is still
 * being collected), signalling the caller to fall back to the own-ballot view.
 * Gating by day prevents a prior round's tally leaking into a fresh collection.
 */
export function deriveTallyRecords(
  gameLogs: GameLog[],
  voteType: VoteKind,
  day: number,
  sheriffId: number | null,
): VoteRecord[] | null {
  const event = TALLY_EVENT[voteType]
  let tally: GameLog | undefined
  for (const log of gameLogs) {
    if (log.day === day && log.data?.event === event) tally = log
  }
  const data = tally?.data
  if (!data) return null

  const entries = data.vote_entries
  if (Array.isArray(entries)) {
    return (entries as VoteEntry[]).map(entry => ({
      voterId: Number(entry.voter_id),
      targetId: entry.target_id == null ? null : Number(entry.target_id),
      weight: typeof entry.weight === 'number'
        ? entry.weight
        : Number(entry.voter_id) === sheriffId ? 2 : 1,
    }))
  }

  const votes = data.votes
  if (votes && typeof votes === 'object') {
    return Object.entries(votes as Record<string, number>).map(([voterId, targetId]) => ({
      voterId: Number(voterId),
      targetId: targetId == null ? null : Number(targetId),
      weight: Number(voterId) === sheriffId ? 2 : 1,
    }))
  }
  return null
}

/**
 * The viewer's own ballot — the only one exposed in state during collection —
 * so the modal can highlight "you voted X" before the tally is published.
 */
export function ownBallotRecords(
  ownVotes: Record<number, number> | undefined,
  myId: number | undefined,
  sheriffId: number | null,
): VoteRecord[] {
  if (!ownVotes || myId === undefined) return []
  const target = ownVotes[myId]
  if (target === undefined) return []
  return [{ voterId: myId, targetId: target, weight: myId === sheriffId ? 2 : 1 }]
}
