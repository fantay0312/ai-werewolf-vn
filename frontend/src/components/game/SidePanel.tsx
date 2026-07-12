import { useState, useRef, useEffect, useMemo } from 'react'
import { GameIcon } from '../common/GameIcon'
import { useGameStore } from '../../store/useGameStore'
import { cn } from '../../lib/utils'
import { PHASE_NAMES, ROLE_NAMES, type Player, type Role } from '../../types'

type TabType = 'players' | 'logs' | 'wolf'

interface SidePanelProps {
  onOpenWolfModal?: () => void
}

export function SidePanel({ onOpenWolfModal }: SidePanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>('players')
  const logListRef = useRef<HTMLDivElement>(null)

  const currentPhase = useGameStore(state => state.gameState?.phase || '')
  const currentDay = useGameStore(state => state.gameState?.day || 1)
  const players = useGameStore(state => state.gameState?.players || [])
  const gameLogs = useGameStore(state => state.gameState?.game_logs || [])
  const isGameOver = useGameStore(state => state.gameState?.phase === 'GAME_END')
  const wolfDiscussMessages = useGameStore(state => state.gameState?.wolf_discuss_messages || [])

  const myPlayer = players.find(p => p.is_human)
  const sheriffId = players.find(p => p.is_sheriff)?.id

  // Scroll logic
  function scrollToBottom() {
    setTimeout(() => {
      if (logListRef.current) {
        logListRef.current.scrollTop = logListRef.current.scrollHeight
      }
    }, 10)
  }

  useEffect(() => {
    if (activeTab === 'logs') {
      scrollToBottom()
    }
  }, [activeTab, gameLogs.length])

  const isWolfPhase = ['NIGHT_WOLF_DISCUSS', 'NIGHT_WOLF_VOTE'].includes(currentPhase)
  const showWolfTab = myPlayer?.role === 'wolf' || myPlayer?.role === 'wolf_king'

  const sortedPlayers = useMemo(() => {
    return [...players].sort((a, b) => a.id - b.id)
  }, [players])

  const publicLogs = useMemo(() => {
    return gameLogs.filter(log => log.is_public).slice(-20)
  }, [gameLogs])

  const aliveCount = players.filter(p => p.is_alive).length
  const deadCount = players.filter(p => !p.is_alive).length

  const phaseText = PHASE_NAMES[currentPhase as keyof typeof PHASE_NAMES] || currentPhase

  const phaseHint = (() => {
    const hints: Record<string, string> = {
      GAME_START: '游戏即将开始，请确认你的身份。',
      NIGHT_START: '夜晚降临，请闭眼。',
      NIGHT_WOLF_DISCUSS: '狼人请睁眼，讨论今晚的目标。',
      NIGHT_WOLF_VOTE: '狼人请选择击杀目标。',
      NIGHT_SEER: '预言家请睁眼，选择要查验的玩家。',
      NIGHT_WITCH: '女巫请睁眼，决定是否使用药水。',
      NIGHT_GUARD: '守卫请睁眼，选择要守护的玩家。',
      NIGHT_RESOLVE: '夜晚结束，正在结算...',
      DAY_START: '天亮了，查看昨晚的情况。',
      DAY_LAST_WORDS: '请死亡的玩家发表遗言。',
      SHERIFF_ELECTION: '警长竞选开始，选择是否上警。',
      SHERIFF_SPEECH: '候选人发表竞选演讲。',
      SHERIFF_VOTE: '请为警长候选人投票。',
      DAY_DISCUSS: '白天讨论时间，自由发言。',
      DAY_VOTE: '投票时间，选择要放逐的玩家。',
      DAY_VOTE_RESULT: '投票结束，公布结果。',
      DAY_PK_SPEECH: '平票PK，候选人进行PK发言。',
      DAY_PK_VOTE: 'PK投票，请在候选人中选择。',
      DAY_PK_RESULT: 'PK投票结束，公布结果。',
      HUNTER_SKILL: '猎人/狼王可以发动技能。',
      SHERIFF_TRANSFER: '警长移交警徽。',
      GAME_END: '游戏结束！'
    }
    return hints[currentPhase] || '等待中...'
  })()

  function shouldShowRole(player: Player): boolean {
    if (player.is_human) return true
    if (isGameOver) return true
    return false
  }

  function getRoleBadgeClass(role: string): string {
    const classes: Record<string, string> = {
      wolf: 'role-wolf',
      wolf_king: 'role-wolf-king',
      seer: 'role-seer',
      witch: 'role-witch',
      guard: 'role-guard',
      hunter: 'role-hunter',
      villager: 'role-villager'
    }
    return classes[role] || 'role-villager'
  }

  function getLogAvatarClass(playerId: number): string {
    const player = players.find(p => p.id === playerId)
    if (!player) return 'avatar-default'
    if (player.is_human) return 'avatar-me'
    if (!player.is_alive) return 'avatar-dead'
    return 'avatar-default'
  }

  function formatLogContent(content: string, playerId: number | undefined): string {
    if (playerId) {
      return content.replace(new RegExp(`^${playerId}号[：::]\\s*`), '')
    }
    return content
  }

  const tabs: {id: TabType, label: string, icon: string}[] = [
    { id: 'players', label: '玩家', icon: 'players' },
    { id: 'logs', label: '记录', icon: 'logs' },
    { id: 'wolf', label: '密谋', icon: 'wolf' }
  ]

  return (
    <div className="side-panel w-[300px] min-w-[300px] h-full flex flex-col bg-slate-900/55 backdrop-blur-xl border-l border-white/10 shadow-[-8px_0_30px_rgba(0,0,0,0.5)]">
      
      <div className="panel-header-decor flex items-center justify-center py-2 px-4 gap-2">
        <div className="decor-line"></div>
        <div className="decor-gem"></div>
        <div className="decor-line"></div>
      </div>

      <div className="panel-header p-4 pb-0 items-center flex flex-col bg-gradient-to-b from-white/5 to-transparent border-b border-white/10">
        <div className="text-center w-full">
          <h2 className="phase-title">{phaseText}</h2>
          <p className="day-info mb-3">第 {currentDay} 天</p>
        </div>
        
        {sheriffId && (
          <div className="sheriff-badge mb-3">
            <GameIcon name="crown" size="sm" color="#c5a059" />
            <span>警长: {sheriffId}号</span>
          </div>
        )}
      </div>

      <div className="tab-container flex border-b border-white/10">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn('tab-btn', activeTab === tab.id ? 'active' : '')}
          >
            <GameIcon name={tab.icon} size="sm" className="tab-icon" />
            <span className="tab-label">{tab.label}</span>
            {tab.id === 'wolf' && !showWolfTab && <GameIcon name="lock" size="xs" className="lock-icon" />}
          </button>
        ))}
      </div>

      <div className="tab-content flex-1 overflow-hidden">
        {activeTab === 'players' && (
          <div className="player-list h-full overflow-y-auto p-2">
            {sortedPlayers.map((player, index) => (
              <div
                key={player.id}
                className={cn('player-item', 
                  !player.is_alive && 'is-dead', 
                  player.is_human && 'is-me',
                  index % 2 === 0 && 'even'
                )}
              >
                <div className={cn('player-badge', player.is_sheriff && 'is-sheriff', !player.is_alive && 'is-dead')}>
                  <span className="badge-number">{player.id}</span>
                  {player.is_sheriff && <GameIcon name="crown" size="xs" color="#c5a059" className="sheriff-crown" />}
                </div>

                <div className="player-info flex-1 min-w-0">
                  <div className="player-name-row flex items-center gap-1.5">
                    <span className={cn('player-name', !player.is_alive && 'dead')}>
                      {player.name}
                    </span>
                    {player.is_human && <span className="you-tag">(你)</span>}
                  </div>
                  {shouldShowRole(player) && (
                    <div className="player-role mt-0.5 text-xs font-medium">
                      <span className={getRoleBadgeClass(player.role)}>{ROLE_NAMES[player.role as Role] || player.role}</span>
                    </div>
                  )}
                </div>

                <div className="player-status text-base">
                  {!player.is_alive ? (
                    <GameIcon name="skull" size="sm" className="status-dead" color="#ef4444" />
                  ) : player.has_acted ? (
                    <span className="status-acted text-green-500">✓</span>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'logs' && (
          <div className="log-list h-full overflow-y-auto p-2" ref={logListRef}>
            {publicLogs.map(log => (
              <div key={log.id} className={`log-item log-${log.type}`}>
                <div className="log-content flex gap-2.5 items-start">
                  <div className={`log-avatar ${log.player_id ? getLogAvatarClass(log.player_id) : 'avatar-system'}`}>
                    {log.player_id ? log.player_id : <GameIcon name="announce" size="sm" />}
                  </div>
                  <div className="log-text flex-1 leading-snug min-w-0">
                    <span className={cn('log-speaker block font-semibold text-xs mb-0.5', !log.player_id ? 'system' : 'text-[#c5a059]')}>
                      {log.player_id ? `${log.player_id}号玩家` : '系统'}
                    </span>
                    <span className="log-message block text-white/85 text-sm word-break">
                      {formatLogContent(log.content, log.player_id)}
                    </span>
                  </div>
                </div>
                <div className="log-meta mt-1.5 text-[10px] text-white/40 text-right">
                  第{log.day}天 · {PHASE_NAMES[log.phase as keyof typeof PHASE_NAMES] || log.phase}
                </div>
              </div>
            ))}
            {publicLogs.length === 0 && (
              <div className="empty-state text-center mt-10 text-slate-500">
                <GameIcon name="logs" size="lg" className="mx-auto opacity-50 mb-2" />
                <p>暂无记录</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'wolf' && (
          <div className="wolf-tab h-full">
            {showWolfTab ? (
              <div className="wolf-chat h-full flex flex-col bg-gradient-to-b from-red-900/10 to-transparent">
                <div className="wolf-header flex items-center justify-center gap-2 p-3 text-red-500 font-semibold border-b border-red-500/20 flex-wrap">
                  <GameIcon name="wolf" size="sm" />
                  <span>狼人密谋频道</span>
                  {isWolfPhase && (
                    <button onClick={onOpenWolfModal} className="open-modal-btn px-3 py-1 text-xs bg-gradient-to-br from-red-800 to-red-900 text-white rounded-full hover:scale-105 transition-transform">
                      <GameIcon name="chat" size="xs" className="inline mr-1" /> 打开讨论
                    </button>
                  )}
                </div>
                <div className="wolf-messages flex-1 overflow-y-auto p-2">
                  {wolfDiscussMessages.map((msg, index) => (
                    <div key={index} className="wolf-message p-2 mb-2 bg-red-500/10 border border-red-500/20 rounded-lg">
                      <span className="wolf-sender text-red-400 font-bold mr-1">{msg.speaker_id}号:</span>
                      <span className="wolf-text text-white/90">{msg.content}</span>
                      <div className="wolf-meta text-[10px] text-red-400/50 mt-1">第{msg.round}轮</div>
                    </div>
                  ))}
                  {wolfDiscussMessages.length === 0 && (
                    <div className="empty-state text-center mt-10 text-slate-500">
                      <GameIcon name="moon" size="lg" className="mx-auto opacity-50 mb-2" />
                      <p>暂无狼人讨论</p>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="locked-tab flex flex-col items-center justify-center h-full text-slate-500">
                <GameIcon name="lock" size="xl" className="opacity-50 mb-2" />
                <p>仅狼人可查看</p>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="stats-bar flex justify-around p-3 bg-white/5 border-t border-white/10 mt-auto">
        <div className="stat-item flex flex-col items-center">
          <span className="stat-label text-[10px] text-white/50">存活</span>
          <span className="stat-value text-green-400 font-bold">{aliveCount}</span>
        </div>
        <div className="stat-divider w-px bg-white/10"></div>
        <div className="stat-item flex flex-col items-center">
          <span className="stat-label text-[10px] text-white/50">死亡</span>
          <span className="stat-value text-red-400 font-bold">{deadCount}</span>
        </div>
      </div>

      <div className="hint-bar flex items-start gap-3 p-3 bg-amber-500/5 border-t border-white/5">
        <div className="hint-icon mt-0.5"><GameIcon name="announce" size="sm" color="#c5a059" /></div>
        <div className="hint-content">
          <span className="hint-label block text-xs font-semibold text-amber-500/80 mb-0.5">当前阶段提示:</span>
          <p className="hint-text text-xs text-white/70 leading-relaxed">{phaseHint}</p>
        </div>
      </div>

      <div className="panel-footer-decor flex items-center justify-center py-2 px-4 gap-2">
        <div className="decor-line"></div>
        <div className="decor-gem small"></div>
        <div className="decor-line"></div>
      </div>
    </div>
  )
}
