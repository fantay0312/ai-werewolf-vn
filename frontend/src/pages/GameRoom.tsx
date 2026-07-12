import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getStoredSessionId, useGameStore } from '../store/useGameStore'
import { cn } from '../lib/utils'
import { GameTable } from '../components/game/GameTable'
import { ActionPanel } from '../components/game/ActionPanel'
import { JudgeArea } from '../components/game/JudgeArea'
import { DialogBox } from '../components/common/DialogBox'
import { SidePanel } from '../components/game/SidePanel'
import { WolfDiscussionModal } from '../components/game/WolfDiscussionModal'
import { VoteModal } from '../components/game/VoteModal'
import { NightActionAnimation } from '../components/game/NightActionAnimation'
import { DiscussionDialog } from '../components/game/DiscussionDialog'
import { GameOverOverlay } from '../components/game/GameOverOverlay'
import { getSelectionMode, isNightActionPhase, isNightPhase } from '../lib/phases'
import type { GameLog, VoteRecord, WolfDiscussMessage } from '../types'

const RECOVERY_TIMEOUT_MS = 12000

export function GameRoom() {
  const navigate = useNavigate()
  const cancelLoading = useGameStore(state => state.cancelLoading)
  const clearSession = useGameStore(state => state.clearSession)
  const currentPhase = useGameStore(state => state.currentPhase)
  const error = useGameStore(state => state.error)
  const gameLogs = useGameStore(state => state.gameLogs)
  const gameState = useGameStore(state => state.gameState)
  const isCandidate = useGameStore(state => state.isCandidate)
  const isLoading = useGameStore(state => state.isLoading)
  const loadingStartTime = useGameStore(state => state.loadingStartTime)
  const loadingText = useGameStore(state => state.loadingText)
  const myPlayer = useGameStore(state => state.myPlayer)
  const recoverSession = useGameStore(state => state.recoverSession)
  const connectRealtime = useGameStore(state => state.connectRealtime)
  const disconnectRealtime = useGameStore(state => state.disconnectRealtime)
  const sessionId = useGameStore(state => state.sessionId)
  const sheriffId = useGameStore(state => state.sheriffId)
  const winner = useGameStore(state => state.winner)
  const wolfDiscussMessages = useGameStore(state => state.wolfDiscussMessages)

  const [loadingElapsed, setLoadingElapsed] = useState(0)
  const [recoveryFailed, setRecoveryFailed] = useState(false)
  const [retryNonce, setRetryNonce] = useState(0)
  
  const [showWolfModal, setShowWolfModal] = useState(false)
  const [showVoteModal, setShowVoteModal] = useState(false)
  const [voteType, setVoteType] = useState<'exile' | 'sheriff' | 'pk'>('exile')

  // Single source of truth for the pending seat target. Seat clicks (GameTable)
  // and the ActionPanel controls both read/write this — one confirm path.
  const [selectedTargetId, setSelectedTargetId] = useState<number | null>(null)

  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | undefined
    if (isLoading) {
      setLoadingElapsed(0)
      timer = setInterval(() => {
        if (loadingStartTime > 0) {
          setLoadingElapsed(Math.floor((Date.now() - loadingStartTime) / 1000))
        }
      }, 1000)
    } else {
      setLoadingElapsed(0)
    }
    return () => {
      if (timer) clearInterval(timer)
    }
  }, [isLoading, loadingStartTime])

  const isInNightActionPhase = isNightActionPhase(currentPhase)

  // Table selection wiring: which seat-selection mode is active, and whose turn
  // it is to speak.
  const selectionMode = useMemo(() => getSelectionMode(currentPhase, myPlayer), [currentPhase, myPlayer])

  const currentSpeakerId = useMemo(() => {
    const order = gameState?.speaking_order
    const idx = gameState?.current_speaker_index
    if (!order || idx === undefined || idx < 0 || idx >= order.length) return null
    return order[idx] ?? null
  }, [gameState?.speaking_order, gameState?.current_speaker_index])

  // Clear the pending target whenever the phase changes.
  useEffect(() => {
    setSelectedTargetId(null)
  }, [currentPhase])

  const isCurrentActionRole = useMemo(() => {
    const phase = currentPhase
    const role = myPlayer?.role || ''
    
    if (phase === 'NIGHT_WOLF_DISCUSS' || phase === 'NIGHT_WOLF_VOTE') {
      return ['wolf', 'wolf_king'].includes(role)
    }
    if (phase === 'NIGHT_SEER') return role === 'seer'
    if (phase === 'NIGHT_WITCH') return role === 'witch'
    if (phase === 'NIGHT_GUARD') return role === 'guard'
    return false
  }, [currentPhase, myPlayer?.role])

  const shouldShowLoading = useMemo(() => {
    if (!isLoading) return false
    if (isInNightActionPhase && !isCurrentActionRole) return false
    return true
  }, [isLoading, isInNightActionPhase, isCurrentActionRole])

  const showDiscussionDialog = useMemo(() => {
    const phase = currentPhase
    const myRole = myPlayer?.role || ''
    const isWolfPlayer = ['wolf', 'wolf_king'].includes(myRole)
    if (phase === 'NIGHT_WOLF_DISCUSS' && isWolfPlayer) return true
    if (phase === 'DAY_DISCUSS') return true
    return false
  }, [currentPhase, myPlayer?.role])

  const discussionMessages = useMemo(() => {
    const phase = currentPhase
    const myRole = myPlayer?.role || ''
    const isWolfPlayer = ['wolf', 'wolf_king'].includes(myRole)
    
    if (phase === 'NIGHT_WOLF_DISCUSS' && isWolfPlayer) {
      return wolfDiscussMessages.map((message: WolfDiscussMessage) => ({
        id: message.id,
        speakerName: `${message.speaker_id}号`,
        content: message.content,
      }))
    }
    
    if (phase === 'DAY_DISCUSS') {
      const dayLogs = gameLogs.filter(
        (log: GameLog) => log.phase === 'DAY_DISCUSS' && 
               log.type === 'speech' && 
               log.content &&
               log.is_public
      )
      
      return dayLogs.map((log: GameLog) => {
        const match = log.content.match(/^(\d+)号:\s*(.+)$/)
        if (match) {
          return {
            id: log.id,
            speakerName: `${match[1]}号`,
            content: match[2],
          }
        }
        return {
          id: log.id,
          speakerName: log.player_id ? `${log.player_id}号` : '未知',
          content: log.content,
        }
      })
    }
    return []
  }, [currentPhase, myPlayer?.role, wolfDiscussMessages, gameLogs])

  const voteRecords = useMemo<VoteRecord[]>(() => {
    const votes = gameState?.votes || {}
    const pkVotes = gameState?.pk_votes || {}

    const currentVotes = currentPhase === 'DAY_PK_VOTE' || currentPhase === 'DAY_PK_RESULT'
      ? pkVotes
      : votes

    return Object.entries(currentVotes).map(([voterId, targetId]) => ({
      voterId: Number(voterId),
      targetId: targetId as number | null,
      weight: Number(voterId) === sheriffId ? 2 : 1
    }))
  }, [currentPhase, gameState?.pk_votes, gameState?.votes, sheriffId])

  const timeRemaining = gameState?.time_remaining || 60

  const isNight = isNightPhase(currentPhase)

  // Watch for phase changes to auto-open modals
  useEffect(() => {
    const myRole = myPlayer?.role || ''
    const isWolfPlayer = ['wolf', 'wolf_king'].includes(myRole)
    const phase = currentPhase

    if (isWolfPlayer && ['NIGHT_WOLF_DISCUSS', 'NIGHT_WOLF_VOTE'].includes(phase)) {
       setShowWolfModal(true)
    }
    if (!phase.startsWith('NIGHT_')) {
      setShowWolfModal(false)
    }

    if (phase === 'DAY_VOTE') {
      setVoteType('exile')
      setShowVoteModal(true)
    } else if (phase === 'DAY_PK_VOTE') {
      setVoteType('pk')
      setShowVoteModal(true)
    } else if (phase === 'SHERIFF_VOTE' && !isCandidate) {
      setVoteType('sheriff')
      setShowVoteModal(true)
    } else if (!['DAY_VOTE_RESULT', 'DAY_PK_RESULT'].includes(phase)) {
      setShowVoteModal(false)
    }
  }, [currentPhase, isCandidate, myPlayer?.role])

  const openWolfModal = () => {
    const myRole = myPlayer?.role || ''
    const isWolfPlayer = ['wolf', 'wolf_king'].includes(myRole)
    if (!isWolfPlayer) {
      // Show error some way (need to sync with gameStore if it handles error string)
      return
    }
    setShowWolfModal(true)
  }

  const returnToHome = () => {
    clearSession()
    navigate('/')
  }

  const handleRetry = () => {
    setRecoveryFailed(false)
    setRetryNonce((n) => n + 1)
    connectRealtime()
  }

  // Session + realtime lifecycle: recover identity from storage if needed, then
  // connect the realtime manager and tear it down on unmount.
  useEffect(() => {
    if (!sessionId) {
      if (getStoredSessionId()) {
        recoverSession()
        return
      }
      navigate('/')
      return
    }
    connectRealtime()
    return () => {
      disconnectRealtime()
    }
  }, [sessionId, recoverSession, connectRealtime, disconnectRealtime, navigate])

  // Recovery watchdog: if no game state arrives within the timeout, surface an
  // explicit failure state with retry / return-home actions instead of an
  // inescapable "正在恢复游戏..." spinner.
  useEffect(() => {
    if (gameState) {
      setRecoveryFailed(false)
      return
    }
    setRecoveryFailed(false)
    const timer = setTimeout(() => setRecoveryFailed(true), RECOVERY_TIMEOUT_MS)
    return () => clearTimeout(timer)
  }, [gameState, retryNonce])

  // Show loading screen while recovering session; on timeout, offer an escape.
  if (!gameState) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-950 relative overflow-hidden">
        <img src="/images/game-bg.webp" className="absolute inset-0 w-full h-full object-cover opacity-40" alt="" />
        <div className="absolute inset-0 bg-black/50" />
        <div className="relative z-10 flex flex-col items-center gap-4 px-6 text-center">
          {!recoveryFailed ? (
            <>
              <div className="w-12 h-12 border-2 border-transparent border-t-amber-400 border-l-amber-400/30 rounded-full animate-spin" />
              <span className="text-white/70 text-sm tracking-wide">正在恢复游戏...</span>
            </>
          ) : (
            <>
              <div className="text-4xl">📡</div>
              <div className="flex flex-col items-center gap-1">
                <span className="text-white/90 text-base font-medium">无法连接到服务器</span>
                <span className="text-white/50 text-sm max-w-xs">
                  {error || '连接超时，请检查网络后重试，或返回首页重新开始。'}
                </span>
              </div>
              <div className="flex items-center gap-3 mt-2">
                <button
                  onClick={handleRetry}
                  className="px-6 py-2 rounded-full bg-amber-500/15 border border-amber-500/50 text-amber-200 text-sm font-medium tracking-wide transition-all hover:bg-amber-500/25 hover:border-amber-400"
                >
                  重试
                </button>
                <button
                  onClick={returnToHome}
                  className="px-6 py-2 rounded-full bg-white/5 border border-white/20 text-white/70 text-sm font-medium tracking-wide transition-all hover:bg-white/10 hover:text-white"
                >
                  返回首页
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex relative overflow-hidden text-slate-100">

      {/* Background Image - switches between night/day */}
      <img
        src="/images/game-bg.webp"
        className={cn(
          "absolute inset-0 w-full h-full object-cover z-0 transition-opacity duration-1000",
          isNight ? "opacity-100" : "opacity-0"
        )}
        alt=""
      />
      <img
        src="/images/game-bg2.webp"
        className={cn(
          "absolute inset-0 w-full h-full object-cover z-0 transition-opacity duration-1000",
          isNight ? "opacity-0" : "opacity-100"
        )}
        alt=""
      />
      {/* Dark overlay for UI readability */}
      <div className={cn(
        "absolute inset-0 z-0 transition-all duration-1000",
        isNight ? "bg-black/45" : "bg-black/30"
      )} />
      {/* Vignette effect */}
      <div className="absolute inset-0 z-0 pointer-events-none bg-[radial-gradient(ellipse_at_center,transparent_0%,rgba(0,0,0,0.2)_50%,rgba(0,0,0,0.6)_100%)]" />

      {/* Spectator banner: the human is out but information keeps flowing. */}
      {myPlayer && !myPlayer.is_alive && !winner && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-30 flex items-center gap-2 rounded-full border border-white/10 bg-slate-900/80 px-4 py-1.5 text-sm text-white/70 shadow-lg backdrop-blur-md">
          <span>👻</span>
          <span>你已出局，进入观战模式 · 仍可查看公开信息</span>
        </div>
      )}

      {/* Main Game Area */}
      <div className="flex-1 flex flex-col relative z-10 min-w-0 overflow-hidden">
        <div className="h-[100px] shrink-0 z-10 w-full max-w-5xl mx-auto mt-4 px-4">
          <JudgeArea />
        </div>

        <div className="flex-1 relative flex items-center justify-center py-4 px-8 overflow-hidden w-full h-full max-w-6xl mx-auto">
          <div className="w-full h-full flex items-center justify-center transform scale-90 sm:scale-100 lg:scale-105 transition-transform duration-500">
            <GameTable
              selectionMode={selectionMode}
              selectedTargetId={selectedTargetId}
              currentSpeakerId={currentSpeakerId}
              onSelectPlayer={(id) => setSelectedTargetId(prev => (prev === id ? null : id))}
            />
          </div>
        </div>

        <div className="z-20 w-full shrink-0">
          <ActionPanel
            selectedTargetId={selectedTargetId}
            onSelectTarget={setSelectedTargetId}
            onOpenVoteModal={() => setShowVoteModal(true)}
          />
        </div>
      </div>

      <DialogBox />

      <div className="relative z-10">
        <SidePanel onOpenWolfModal={openWolfModal} />
      </div>

      <WolfDiscussionModal isOpen={showWolfModal} onClose={() => setShowWolfModal(false)} />

      <VoteModal
        isOpen={showVoteModal}
        voteType={voteType}
        voteRecords={voteRecords}
        timeRemaining={timeRemaining}
        onVote={() => setShowVoteModal(false)}
        onClose={() => setShowVoteModal(false)}
      />

      {/* Game End: winner + full role reveal + play again */}
      {winner && (
        <GameOverOverlay
          winner={winner}
          players={gameState.players}
          onPlayAgain={returnToHome}
        />
      )}

      {/* Loading Overlay */}
      {shouldShowLoading && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 transition-opacity duration-400 ease-in-out">
          <div className="flex flex-col items-center justify-center bg-slate-900/70 backdrop-blur-md p-10 rounded-3xl border border-white/10 shadow-[0_25px_50px_-12px_rgba(0,0,0,0.5)]">
            <div className="relative w-[120px] h-[120px]">
              <div className="absolute inset-0 border-2 border-transparent border-t-sky-400 border-l-sky-400/30 rounded-full animate-[spin_2s_linear_infinite]"></div>
              <div className="absolute inset-[12px] border-2 border-transparent border-b-purple-400 border-r-purple-400/30 rounded-full animate-[spin_3s_linear_infinite_reverse]"></div>
              <div className="absolute inset-[24px] border-2 border-transparent border-t-amber-400 border-l-amber-400/30 rounded-full animate-[spin_4s_linear_infinite]"></div>
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-[2rem] animate-[moonPulse_3s_ease-in-out_infinite]">🌙</div>
            </div>
            <div className="mt-6 text-[1.1rem] font-medium tracking-[0.1em] text-slate-50 text-center uppercase animate-[pulse_2s_ease-in-out_infinite]">
              {loadingText}
            </div>
            {loadingElapsed > 3 && (
              <div className="mt-2 text-[0.875rem] text-slate-400 tabular-nums">
                已等待 {loadingElapsed} 秒
              </div>
            )}
            {loadingElapsed > 5 && (
              <button 
                onClick={() => cancelLoading()}
                className="mt-6 px-8 py-2 bg-red-500/10 border border-red-500/40 rounded-full text-red-300 text-[0.875rem] font-medium tracking-wide transition-all hover:bg-red-500/20 hover:border-red-500/80 hover:shadow-[0_0_15px_rgba(239,68,68,0.3)] hover:-translate-y-px active:translate-y-px"
              >
                取消
              </button>
            )}
          </div>
        </div>
      )}

      <NightActionAnimation />

      <DiscussionDialog
        messages={discussionMessages}
        visible={showDiscussionDialog}
      />

    </div>
  )
}
