import { useGameStore } from '../../store/useGameStore'
import { RolePortrait } from './action/RolePortrait'
import { PhaseActions } from './action/PhaseActions'

interface ActionPanelProps {
  /** Shared "pending target" — also set by seat clicks on GameTable. */
  selectedTargetId: number | null
  onSelectTarget: (id: number | null) => void
  /** Open the (single) vote surface for vote phases. */
  onOpenVoteModal: () => void
}

/**
 * Thin container: role portrait + phase-specific controls. The 450-line
 * conditional wall now lives in focused subcomponents (RolePortrait,
 * SpeechComposer, PhaseActions) driven by a phase/role config table.
 */
export function ActionPanel({ selectedTargetId, onSelectTarget, onOpenVoteModal }: ActionPanelProps) {
  const myPlayer = useGameStore(state => state.myPlayer)
  const currentPhase = useGameStore(state => state.currentPhase)
  const isCandidate = useGameStore(state => state.isCandidate)
  const submitAction = useGameStore(state => state.submitAction)

  return (
    <div className="action-panel relative h-32 p-4 px-6 bg-slate-900/60 backdrop-blur-xl border-t border-white/10 shadow-[0_-8px_32px_rgba(0,0,0,0.4)]">
      {myPlayer && <RolePortrait role={myPlayer.role} />}

      <div className="action-container pl-[160px] flex items-center justify-center gap-4 flex-wrap h-full">
        <PhaseActions
          phase={currentPhase}
          myPlayer={myPlayer}
          isCandidate={isCandidate}
          selectedTargetId={selectedTargetId}
          onSelectTarget={onSelectTarget}
          submitAction={submitAction}
          onOpenVoteModal={onOpenVoteModal}
        />
      </div>
    </div>
  )
}
