import { useEffect, useRef, useState } from 'react'
import { Vote, Users, BarChart3, Ban, Crown, Check, Clock } from 'lucide-react'
import { useGameStore } from '../../store/useGameStore'
import { cn } from '../../lib/utils'
import type { VoteRecord } from '../../types'

type VoteType = 'sheriff' | 'exile' | 'pk'

interface VoteModalProps {
  isOpen: boolean
  onClose: () => void
  onVote?: (targetId: number | null) => void
  voteType?: VoteType
  timeRemaining?: number
  maxTime?: number
  voteRecords?: VoteRecord[]
}

export function VoteModal({
  isOpen,
  onClose,
  onVote,
  voteType = 'exile',
  timeRemaining = 60,
  maxTime = 60,
  voteRecords = [],
}: VoteModalProps) {
  const [selectedTarget, setSelectedTarget] = useState<number | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const recordsListRef = useRef<HTMLDivElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)

  // Narrow subscriptions so store churn (loading ticks, error, etc.) doesn't
  // re-render the whole modal.
  const players = useGameStore(state => state.gameState?.players)
  const sheriffCandidateIds = useGameStore(state => state.gameState?.sheriff_candidate_ids)
  const pkCandidates = useGameStore(state => state.gameState?.pk_candidates)
  const submitAction = useGameStore(state => state.submitAction)

  const me = players?.find(p => p.is_human)
  const myPlayerId = me?.id

  const title = voteType === 'sheriff' ? '警长投票' : voteType === 'pk' ? 'PK投票' : '放逐投票'
  const description =
    voteType === 'sheriff' ? '请为你支持的警长候选人投票'
      : voteType === 'pk' ? '请在PK候选人中选择'
        : '请选择你要放逐的玩家'

  // PK rounds MUST be restricted to the tied candidates; previously this fell
  // through to "all alive players", inviting an illegal vote.
  const voteCandidates = (players || []).filter(p => {
    if (!p.is_alive) return false
    if (voteType === 'sheriff') return sheriffCandidateIds?.includes(p.id) ?? false
    if (voteType === 'pk') return pkCandidates?.includes(p.id) ?? false
    return p.id !== myPlayerId
  })

  // Progress under the votes-privacy contract: other players' ballots are hidden
  // during collection, so count who has acted (day/sheriff vote phases report
  // has_acted truthfully) rather than counting visible ballots.
  const totalVoters = players?.filter(p => p.is_alive).length ?? 0
  const votedCount = players?.filter(p => p.is_alive && p.has_acted).length ?? 0
  const voteProgressPercent = totalVoters === 0 ? 0 : Math.round((votedCount / totalVoters) * 100)
  const countdownProgress = Math.min(100, Math.round((timeRemaining / (maxTime || 60)) * 100))

  const countdownColorClass = timeRemaining <= 10 ? 'text-red-500' : timeRemaining <= 30 ? 'text-yellow-500' : 'text-green-500'

  const { voteCountMap, leadingCandidateId } = (() => {
    const counts: Record<number, number> = {}
    const sheriffId = players?.find(p => p.is_sheriff)?.id
    let maxVotes = 0
    let leaderId: number | null = null

    for (const record of voteRecords) {
      if (record.targetId === null || record.targetId === 0) continue
      const weight = record.voterId === sheriffId ? 2 : 1
      counts[record.targetId] = (counts[record.targetId] || 0) + weight
    }

    for (const [candidateId, votes] of Object.entries(counts)) {
      if (votes > maxVotes) {
        maxVotes = votes
        leaderId = Number(candidateId)
      }
    }
    return { voteCountMap: counts, leadingCandidateId: leaderId }
  })()

  const abstainCount = voteRecords.filter(r => r.targetId === null || r.targetId === 0).length

  const sortedVoteRecords = [...voteRecords].sort((a, b) => {
    if (a.voterId === myPlayerId) return -1
    if (b.voterId === myPlayerId) return 1
    return a.voterId - b.voterId
  })

  // Own ballot may already be present in `votes`; has_acted is the reliable
  // signal once the vote is submitted (before the tally log lands).
  const hasVoted = voteRecords.some(r => r.voterId === myPlayerId) || Boolean(me?.has_acted)
  const myVoteTarget = voteRecords.find(r => r.voterId === myPlayerId)?.targetId
  const isSheriff = players?.find(p => p.id === myPlayerId)?.is_sheriff

  useEffect(() => {
    if (recordsListRef.current) {
      recordsListRef.current.scrollTop = recordsListRef.current.scrollHeight
    }
  }, [voteRecords.length])

  // Move focus into the dialog on open (basic a11y).
  useEffect(() => {
    if (isOpen) dialogRef.current?.focus()
  }, [isOpen])

  function getVoteCount(candidateId: number) {
    return voteCountMap[candidateId] || 0
  }

  function handleSelectTarget(id: number) {
    if (hasVoted) return
    setSelectedTarget(id)
  }

  async function confirmVote() {
    if (selectedTarget === null || isSubmitting || hasVoted) return
    setIsSubmitting(true)
    try {
      // Abstain (0) maps to no target_id — the single abstain encoding for votes.
      const targetId = selectedTarget === 0 ? null : selectedTarget
      await submitAction('vote', targetId ?? undefined)
      onVote?.(targetId)
      setSelectedTarget(null)
    } catch {
      console.error('投票失败')
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleClose() {
    onClose()
    setSelectedTarget(null)
  }

  // Escape closes the modal (dismissal is always legal — GameRoom re-opens it on
  // the next state sync, and ActionPanel offers a reopen button).
  useEffect(() => {
    if (!isOpen) return
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        onClose()
        setSelectedTarget(null)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center animate-fade-in">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={handleClose}></div>
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className="relative w-full max-w-4xl mx-4 bg-gradient-to-b from-[#1a1712] to-[#0d0b08] border border-[color:var(--border-gilded-strong)] rounded-2xl shadow-[0_8px_24px_rgba(0,0,0,0.5)] overflow-hidden animate-scale-in outline-none"
      >

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 bg-gradient-to-r from-[#8b6914]/20 to-transparent border-b border-[color:var(--border-gilded)]">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-gradient-to-br from-[#8b6914] to-[#5a4410] rounded-xl flex items-center justify-center text-[#f4d9a0]">
              <Vote className="w-6 h-6" strokeWidth={1.5} />
            </div>
            <div>
              <h2 className="font-display text-xl font-bold text-parchment tracking-wide">{title}</h2>
              <p className="text-sm text-parchment-dim">{description}</p>
            </div>
          </div>
          <div className="relative flex items-center justify-center">
            <div className={cn("relative flex items-center justify-center", countdownColorClass)}>
              <svg viewBox="0 0 36 36" className="w-14 h-14 -rotate-90">
                <path className="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3" opacity="0.2" />
                <path className="circle-progress transition-[stroke-dasharray] duration-1000 linear" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeDasharray={`${countdownProgress}, 100`} />
              </svg>
              <span className="absolute text-sm font-bold">{timeRemaining}s</span>
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="px-6 py-3 bg-black/30 border-b border-[color:var(--border-gilded)]">
          <div className="flex justify-between mb-2">
            <span className="text-parchment-dim text-sm">投票进度</span>
            <span className="text-parchment text-sm font-bold">{votedCount}/{totalVoters}</span>
          </div>
          <div className="h-2 bg-white/10 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-[#8b6914] to-[#c5a059] rounded-full transition-all duration-500" style={{ width: `${voteProgressPercent}%` }}></div>
          </div>
        </div>

        {/* Body */}
        <div className="grid grid-cols-[2fr_1fr] gap-5 p-6 max-h-[50vh] overflow-hidden">

          <div className="candidates-section overflow-y-auto">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-parchment-dim mb-4">
              <Users className="w-4 h-4" strokeWidth={1.5} />
              {voteType === 'sheriff' ? '警长候选人' : voteType === 'pk' ? 'PK候选人' : '投票目标'}
            </h3>

            <div className="grid grid-cols-[repeat(auto-fill,minmax(100px,1fr))] gap-3 mb-4">
              {voteCandidates.map(candidate => (
                <button
                  type="button"
                  key={candidate.id}
                  onClick={() => handleSelectTarget(candidate.id)}
                  disabled={hasVoted}
                  aria-pressed={selectedTarget === candidate.id}
                  className={cn(
                    "relative flex flex-col items-center p-4 bg-white/5 border-2 border-transparent rounded-xl cursor-pointer transition-all hover:-translate-y-0.5 hover:bg-white/10 hover:border-[#c5a059]/50 disabled:cursor-not-allowed disabled:hover:translate-y-0",
                    selectedTarget === candidate.id && "bg-[#8b6914]/25 border-[#c5a059] shadow-[0_2px_8px_rgba(0,0,0,0.3)]",
                    leadingCandidateId === candidate.id && "border-yellow-500/80",
                    myVoteTarget === candidate.id && "bg-green-500/10 border-green-500"
                  )}
                >
                  <div className="relative w-14 h-14 rounded-full overflow-hidden border-2 border-white/20 flex items-center justify-center bg-gradient-to-br from-blue-500 to-blue-800 mb-2">
                    <span className="text-2xl font-bold text-white drop-shadow-[0_2px_4px_rgba(0,0,0,0.3)]">{candidate.id}</span>
                  </div>
                  <div className="flex flex-col items-center gap-0.5">
                    <span className="text-sm font-bold text-white">{candidate.id}号</span>
                    <span className="text-[11px] text-gray-400 max-w-[80px] overflow-hidden text-ellipsis whitespace-nowrap">{candidate.name}</span>
                  </div>

                  {getVoteCount(candidate.id) > 0 && (
                    <div className="absolute -top-2 -right-2 flex items-center gap-0.5 px-2 py-1 bg-gradient-to-br from-red-500 to-red-800 rounded-xl text-[11px] text-white animate-fade-in shadow-md">
                      <span className="font-bold">{getVoteCount(candidate.id)}</span>
                      <span>票</span>
                    </div>
                  )}

                  {candidate.is_sheriff && (
                    <div className="absolute -top-1 -left-1 w-6 h-6 bg-gradient-to-br from-yellow-400 to-yellow-600 rounded-full flex items-center justify-center shadow-md text-black"><Crown className="w-3.5 h-3.5" strokeWidth={2} /></div>
                  )}

                  {selectedTarget === candidate.id && (
                    <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-6 h-6 bg-[#c5a059] rounded-full flex items-center justify-center text-black animate-bounce shadow-md"><Check className="w-3.5 h-3.5" strokeWidth={2.5} /></div>
                  )}

                  {leadingCandidateId === candidate.id && getVoteCount(candidate.id) > 0 && (
                    <div className="absolute top-2 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-gradient-to-r from-yellow-400 to-yellow-600 text-gray-900 text-[10px] font-bold rounded-lg whitespace-nowrap">领先</div>
                  )}

                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={() => handleSelectTarget(0)}
              disabled={hasVoted}
              aria-pressed={selectedTarget === 0}
              className={cn(
                "w-full flex items-center justify-center gap-2 p-3 bg-white/5 border-2 border-dashed border-white/20 rounded-lg cursor-pointer transition-colors hover:bg-white/10 disabled:cursor-not-allowed",
                selectedTarget === 0 && "bg-[#8b6914]/25 border-[#c5a059]"
              )}
            >
              <Ban className="w-4 h-4 text-parchment-dim" strokeWidth={1.5} />
              <span className="text-parchment font-medium">弃票</span>
              {abstainCount > 0 && <span className="text-parchment-dim text-sm">({abstainCount}人弃票)</span>}
            </button>
          </div>

          <div className="vote-records-section pl-5 border-l border-[color:var(--border-gilded)] flex flex-col">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-parchment-dim mb-4">
              <BarChart3 className="w-4 h-4" strokeWidth={1.5} />
              投票记录
            </h3>

            <div className="flex-1 overflow-y-auto space-y-2 pr-2" ref={recordsListRef}>
              {sortedVoteRecords.map((record) => (
                <div key={record.voterId} className={cn(
                  "flex items-center gap-3 p-2 bg-white/5 rounded-lg border border-transparent",
                  record.voterId === myPlayerId && "border-blue-500/50 bg-blue-500/10"
                )}>
                  <div className="flex flex-col flex-1 items-center">
                    <span className="font-bold text-white text-sm">{record.voterId}号</span>
                    {record.weight > 1 && <span className="text-[10px] text-yellow-400 font-bold px-1.5 py-0.5 bg-yellow-400/20 rounded">x{record.weight}</span>}
                  </div>
                  <div className="text-gray-500 text-sm">→</div>
                  <div className="flex-1 flex justify-center">
                    {(record.targetId && record.targetId !== 0) ? (
                      <span className="text-blue-400 font-bold px-2 py-1 bg-blue-500/20 rounded">{record.targetId}号</span>
                    ) : (
                      <span className="text-gray-400 font-bold px-2 py-1 bg-gray-500/20 rounded border border-dashed border-gray-500/50">弃票</span>
                    )}
                  </div>
                </div>
              ))}

              {voteRecords.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-parchment-dim py-10">
                  <Clock className="w-7 h-7 mb-2 opacity-50" strokeWidth={1.5} />
                  <span className="text-sm">等待玩家投票...</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 bg-black/40 border-t border-white/10">
          <div className="flex items-center">
            {isSheriff && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-yellow-500/20 border border-yellow-500/30 rounded-lg mr-3">
                <Crown className="w-4 h-4 text-yellow-500" strokeWidth={1.5} />
                <span className="text-sm text-yellow-500/90">你是警长，你的票数为 <strong>2票</strong></span>
              </div>
            )}
            {hasVoted && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-green-500/20 border border-green-500/30 rounded-lg">
                <Check className="w-4 h-4 text-green-500" strokeWidth={2} />
                <span className="text-sm text-green-500/90">你已投票给 {(myVoteTarget && myVoteTarget !== 0) ? <strong>{myVoteTarget}号</strong> : <strong>弃票</strong>}</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleClose}
              disabled={isSubmitting}
              className="px-6 py-2 rounded-lg bg-white/10 text-white/80 hover:bg-white/20 transition-colors disabled:opacity-50"
            >
              {hasVoted ? '关闭' : '取消'}
            </button>
            {!hasVoted && (
              <button
                disabled={selectedTarget === null || isSubmitting}
                onClick={confirmVote}
                className="px-6 py-2 rounded bg-[#8b6914] text-[#f4d9a0] font-bold border border-[color:var(--border-gilded-strong)] hover:bg-[#a07a1a] transition-colors disabled:opacity-50 disabled:bg-black/40 disabled:text-parchment-dim flex items-center justify-center min-w-[120px]"
              >
                {isSubmitting ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                ) : (
                  <span>确认投票</span>
                )}
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  )
}
