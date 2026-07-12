import { useEffect, useState } from 'react'
import {
  Check, Swords, Eye, Shield, Target, Crosshair, FlaskConical, Heart, Skull,
  Award, Star, MessageCircle, Flame, Mic, Bomb, Vote, Ghost, type LucideIcon,
} from 'lucide-react'
import { cn } from '../../../lib/utils'
import type { ActionType, GamePhase, Player } from '../../../types'
import { isWolfRole } from '../../../types'
import { SpeechComposer } from './SpeechComposer'

type SubmitAction = (
  type: ActionType | string,
  targetId?: number | null,
  content?: string
) => Promise<void>

interface PhaseActionsProps {
  phase: GamePhase | ''
  myPlayer: Player | null
  isCandidate: boolean
  /** Players out this round — the eligible last-words speakers (may be dead humans). */
  deadPlayers: number[]
  /** Tied candidates who must give a PK speech (alive). */
  pkCandidates: number[]
  selectedTargetId: number | null
  onSelectTarget: (id: number | null) => void
  submitAction: SubmitAction
  onOpenVoteModal: () => void
}

// Phases whose only control is a single "continue/confirm" button.
const CONFIRM_TEXT: Partial<Record<GamePhase, string>> = {
  GAME_START: '准备就绪',
  NIGHT_RESOLVE: '继续',
  DAY_START: '确认',
  DAY_VOTE_RESULT: '继续',
}

interface TargetActionDef {
  match: (me: Player) => boolean
  groupClass: string
  Icon: LucideIcon
  label: string
  action: ActionType
  confirmLabel: string
  confirmClass: string
  confirmIcon?: LucideIcon
  secondary?: { label: string; className: string; action: ActionType }
}

// The ~identical "pick a seat + confirm/pass" groups, as data instead of
// repeated JSX. Each renders one <TargetActionGroup>.
const TARGET_ACTIONS: Partial<Record<GamePhase, TargetActionDef>> = {
  NIGHT_WOLF_VOTE: {
    match: me => isWolfRole(me.role),
    groupClass: 'wolf', Icon: Swords, label: '狼人击杀', action: 'kill',
    confirmLabel: '击杀', confirmClass: 'btn-danger', confirmIcon: Swords,
  },
  NIGHT_SEER: {
    match: me => me.role === 'seer',
    groupClass: 'seer', Icon: Eye, label: '预言家行动', action: 'check',
    confirmLabel: '查验', confirmClass: 'btn-purple',
    secondary: { label: '跳过', className: 'btn-secondary', action: 'pass' },
  },
  NIGHT_GUARD: {
    match: me => me.role === 'guard',
    groupClass: 'guard', Icon: Shield, label: '守卫行动', action: 'guard',
    confirmLabel: '守护', confirmClass: 'btn-gold',
    secondary: { label: '空守', className: 'btn-secondary', action: 'pass' },
  },
  HUNTER_SKILL: {
    match: me => (me.role === 'hunter' || me.role === 'wolf_king') && !me.is_alive,
    groupClass: 'hunter', Icon: Target, label: '猎人技能', action: 'shoot',
    confirmLabel: '开枪', confirmClass: 'btn-danger btn-glow', confirmIcon: Crosshair,
    secondary: { label: '不开枪', className: 'btn-secondary', action: 'pass' },
  },
}

interface TargetActionGroupProps {
  def: TargetActionDef
  selectedTargetId: number | null
  onSelectTarget: (id: number | null) => void
  onConfirm: (action: ActionType) => void
  onSecondary: (action: ActionType) => void
}

function TargetActionGroup({ def, selectedTargetId, onSelectTarget, onConfirm, onSecondary }: TargetActionGroupProps) {
  const secondary = def.secondary
  const ConfirmIcon = def.confirmIcon
  return (
    <div className={cn('action-group', def.groupClass)}>
      <span className="action-label"><def.Icon className="w-4 h-4" strokeWidth={1.5} />{def.label}</span>
      <div className="input-group">
        <input
          type="number" min={1} max={12} placeholder="目标ID"
          aria-label={`${def.confirmLabel}目标`}
          className="input-field"
          value={selectedTargetId ?? ''}
          onChange={e => onSelectTarget(e.target.value === '' ? null : Number(e.target.value))}
        />
        <button
          onClick={() => onConfirm(def.action)}
          className={cn('btn', def.confirmClass)}
          disabled={selectedTargetId === null}
        >
          {ConfirmIcon && <ConfirmIcon className="w-4 h-4" strokeWidth={1.5} />}
          {def.confirmLabel}
        </button>
        {secondary && (
          <button onClick={() => onSecondary(secondary.action)} className={cn('btn', secondary.className)}>
            {secondary.label}
          </button>
        )}
      </div>
    </div>
  )
}

/**
 * Phase-specific controls, driven by config tables instead of a long conditional
 * wall. Target-based actions read/write the shared `selectedTargetId` (the same
 * value seat clicks on GameTable set) so there is one source of truth for the
 * pending target and exactly one submit path per action.
 */
export function PhaseActions({
  phase,
  myPlayer,
  isCandidate,
  deadPlayers,
  pkCandidates,
  selectedTargetId,
  onSelectTarget,
  submitAction,
  onOpenVoteModal,
}: PhaseActionsProps) {
  const [speech, setSpeech] = useState('')

  // Drop any draft when the phase changes.
  useEffect(() => { setSpeech('') }, [phase])

  if (!myPlayer) return null

  const isWolf = isWolfRole(myPlayer.role)
  const isAlive = myPlayer.is_alive
  const myId = myPlayer.id

  const runTarget = async (action: ActionType) => {
    await submitAction(action, selectedTargetId ?? undefined)
    onSelectTarget(null)
  }
  const runSimple = async (action: ActionType, target?: number) => {
    await submitAction(action, target)
    onSelectTarget(null)
  }
  const runSpeech = async () => {
    if (!speech.trim()) return
    await submitAction('speech', undefined, speech)
    setSpeech('')
  }

  const confirmText = CONFIRM_TEXT[phase as GamePhase]
  const targetDef = TARGET_ACTIONS[phase as GamePhase]
  const showVoteOpener =
    phase === 'DAY_VOTE' ||
    phase === 'DAY_PK_VOTE' ||
    (phase === 'SHERIFF_VOTE' && !isCandidate)

  // Per-phase eligibility. A blanket `isAlive &&` gate deadlocked phases whose
  // actor is a *dead* human (hunter/wolf-king shooting, last words) and lacked
  // any branch for PK speech. Gate each surface by who the backend actually
  // waits on this phase instead.
  //
  // HUNTER_SKILL.match already requires !is_alive (the shooter is out); every
  // other target phase (wolf kill / seer / guard) is a living-actor action.
  const targetVisible =
    !!targetDef && targetDef.match(myPlayer) && (phase === 'HUNTER_SKILL' || isAlive)
  const isLastWordsSpeaker =
    phase === 'DAY_LAST_WORDS' && !isAlive && deadPlayers.includes(myId)
  const isPkSpeaker =
    phase === 'DAY_PK_SPEECH' && pkCandidates.includes(myId)
  const isSheriffTransfer =
    phase === 'SHERIFF_TRANSFER' && myPlayer.is_sheriff

  // When a dead-player action surface is live, the spectator banner must yield.
  const deadActionActive = targetVisible || isLastWordsSpeaker || isSheriffTransfer

  return (
    <>
      {isAlive && confirmText && (
        <button onClick={() => runSimple('confirm')} className="btn btn-primary btn-glow">
          <Check className="w-4 h-4" strokeWidth={1.5} />
          <span>{confirmText}</span>
        </button>
      )}

      {isAlive && phase === 'NIGHT_WOLF_DISCUSS' && isWolf && (
        <SpeechComposer
          label="狼人密谋"
          icon={Swords}
          wrapperClassName="wolf wide-group flex-col items-stretch"
          inputGroupClassName="wide flex-1 w-full max-w-lg"
          value={speech}
          onChange={setSpeech}
          onSubmit={runSpeech}
          placeholder="与狼队友商量今晚的目标..."
          submitClassName="btn-danger"
          trailing={<button onClick={() => runSimple('pass')} className="btn btn-secondary">跳过</button>}
        />
      )}

      {targetVisible && targetDef && (
        <TargetActionGroup
          def={targetDef}
          selectedTargetId={selectedTargetId}
          onSelectTarget={onSelectTarget}
          onConfirm={runTarget}
          onSecondary={runSimple}
        />
      )}

      {isAlive && phase === 'NIGHT_WITCH' && myPlayer.role === 'witch' && (
        <div className="action-group witch">
          <span className="action-label"><FlaskConical className="w-4 h-4" strokeWidth={1.5} />女巫行动</span>
          <div className="input-group">
            <button onClick={() => runSimple('save')} className="btn btn-success">
              <Heart className="w-4 h-4" strokeWidth={1.5} />解药
            </button>
            <input
              type="number" min={1} max={12} placeholder="毒杀ID"
              aria-label="毒杀目标"
              className="input-field small w-[70px]"
              value={selectedTargetId ?? ''}
              onChange={e => onSelectTarget(e.target.value === '' ? null : Number(e.target.value))}
            />
            <button onClick={() => runTarget('poison')} className="btn btn-poison" disabled={selectedTargetId === null}>
              <Skull className="w-4 h-4" strokeWidth={1.5} />毒药
            </button>
            <button onClick={() => runSimple('pass')} className="btn btn-secondary">跳过</button>
          </div>
        </div>
      )}

      {isAlive && phase === 'DAY_DISCUSS' && (
        <SpeechComposer
          label="发言"
          icon={MessageCircle}
          wrapperClassName="speech wide-group flex-col items-stretch max-w-[600px] w-full"
          inputGroupClassName="wide w-full flex"
          value={speech}
          onChange={setSpeech}
          onSubmit={runSpeech}
          placeholder="输入发言内容..."
          quickPhrases
          trailing={<button onClick={() => runSimple('confirm')} className="btn btn-secondary">结束</button>}
        />
      )}

      {/* Dead human's turn to speak: the backend makes them the current speaker
          and accepts SPEECH + CONFIRM, so without this they deadlock the game. */}
      {isLastWordsSpeaker && (
        <SpeechComposer
          label="遗言"
          icon={Flame}
          wrapperClassName="speech wide-group flex-col items-stretch max-w-[600px] w-full"
          inputGroupClassName="wide w-full flex"
          value={speech}
          onChange={setSpeech}
          onSubmit={runSpeech}
          placeholder="留下你的遗言..."
          trailing={<button onClick={() => runSimple('confirm')} className="btn btn-secondary">结束遗言</button>}
        />
      )}

      {/* Alive PK candidate's speech turn — no composer existed, so a human PK
          candidate deadlocked on their turn. */}
      {isPkSpeaker && (
        <SpeechComposer
          label="PK发言"
          icon={Mic}
          wrapperClassName="speech wide-group flex-col items-stretch max-w-[600px] w-full"
          inputGroupClassName="wide w-full flex"
          value={speech}
          onChange={setSpeech}
          onSubmit={runSpeech}
          placeholder="进行你的PK发言..."
          trailing={<button onClick={() => runSimple('confirm')} className="btn btn-secondary">结束发言</button>}
        />
      )}

      {isAlive && phase === 'SHERIFF_ELECTION' && (
        <div className="action-group sheriff">
          <span className="action-label"><Award className="w-4 h-4" strokeWidth={1.5} />警长竞选</span>
          <div className="input-group">
            <button onClick={() => runSimple('run_for_sheriff')} className="btn btn-gold btn-glow">
              <Star className="w-4 h-4" strokeWidth={1.5} />上警
            </button>
            <button onClick={() => runSimple('pass')} className="btn btn-secondary">不竞选</button>
          </div>
        </div>
      )}

      {isAlive && phase === 'SHERIFF_SPEECH' && isCandidate && (
        <SpeechComposer
          label="竞选发言"
          icon={Mic}
          wrapperClassName="sheriff-speech wide-group flex-col w-full max-w-[500px]"
          labelClassName="mb-2 block"
          inputGroupClassName="wide w-full flex"
          value={speech}
          onChange={setSpeech}
          onSubmit={runSpeech}
          placeholder="竞选发言..."
          trailing={
            <>
              <button onClick={() => runSimple('withdraw')} className="btn btn-danger">退水</button>
              {isWolf && (
                <button onClick={() => runSimple('self_explode')} className="btn btn-explode"><Bomb className="w-4 h-4" strokeWidth={1.5} />自爆</button>
              )}
            </>
          }
        />
      )}

      {isAlive && showVoteOpener && (
        <div className="action-group vote">
          <span className="action-label"><Vote className="w-4 h-4" strokeWidth={1.5} />投票</span>
          <div className="input-group">
            <button onClick={onOpenVoteModal} className="btn btn-primary">打开投票面板</button>
          </div>
        </div>
      )}

      {/* Sheriff transfer stays available even when the sheriff is dead — the
          dying sheriff is exactly who operates it. */}
      {isSheriffTransfer && (
        <div className="action-group sheriff">
          <span className="action-label"><Award className="w-4 h-4" strokeWidth={1.5} />移交警徽</span>
          <div className="input-group">
            <input
              type="number" min={1} max={12} placeholder="目标ID"
              aria-label="移交警徽目标"
              className="input-field"
              value={selectedTargetId ?? ''}
              onChange={e => onSelectTarget(e.target.value === '' ? null : Number(e.target.value))}
            />
            <button onClick={() => runTarget('vote')} className="btn btn-gold" disabled={selectedTargetId === null}>移交</button>
            <button onClick={() => runSimple('vote', 0)} className="btn btn-danger">撕警徽</button>
          </div>
        </div>
      )}

      {!isAlive && !deadActionActive && (
        <div className="dead-message flex items-center gap-2 text-parchment-dim bg-black/30 px-6 py-3 rounded-full border border-white/5">
          <Ghost className="w-5 h-5" strokeWidth={1.5} />
          <span>你已死亡，正在观战...</span>
        </div>
      )}
    </>
  )
}
