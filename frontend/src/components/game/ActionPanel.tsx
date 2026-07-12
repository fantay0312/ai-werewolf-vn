import { useState } from 'react'
import { useGameStore } from '../../store/useGameStore'
import { ROLE_DESCRIPTIONS, ROLE_NAMES, type Role } from '../../types'

export function ActionPanel() {
  const [targetId, setTargetId] = useState<number | ''>('')
  const [speechContent, setSpeechContent] = useState('')
  const [showRoleCard, setShowRoleCard] = useState(false)
  const [showQuickPhrases, setShowQuickPhrases] = useState(false)
  const [seerCheckError, setSeerCheckError] = useState('')

  const gameState = useGameStore(state => state.gameState)
  const currentPhase = gameState?.phase || ''
  const myPlayer = gameState?.players.find(p => p.is_human)
  const isCandidate = Boolean(
    myPlayer && gameState?.sheriff_candidate_ids?.includes(myPlayer.id)
  )
  const submitActionMethod = useGameStore(state => state.submitAction)

  const quickPhrases = [
    { icon: '🔍', label: '查验结果', text: '我查验了X号，是好人/狼人', type: 'seer' },
    { icon: '🎯', label: '怀疑', text: '我怀疑X号是狼人', type: 'suspect' },
    { icon: '✅', label: '认同', text: '我认同X号的发言', type: 'agree' },
    { icon: '❌', label: '反对', text: '我不认同X号的观点', type: 'disagree' },
    { icon: '🛡️', label: '自证', text: '我是好人，请相信我', type: 'defend' },
    { icon: '🗳️', label: '投票', text: '我建议投X号', type: 'vote' },
    { icon: '⚠️', label: '警告', text: '大家小心X号，他的逻辑有问题', type: 'warn' },
    { icon: '🤝', label: '站边', text: '我选择相信X号', type: 'trust' },
  ]

  const isWolf = ['wolf', 'wolf_king'].includes(myPlayer?.role || '')
  const isSeer = myPlayer?.role === 'seer'
  const isWitch = myPlayer?.role === 'witch'
  const isGuard = myPlayer?.role === 'guard'
  const isHunterOrWolfKing = ['hunter', 'wolf_king'].includes(myPlayer?.role || '')

  const isSeerPhase = currentPhase === 'NIGHT_SEER'
  const isWitchPhase = currentPhase === 'NIGHT_WITCH'
  const isGuardPhase = currentPhase === 'NIGHT_GUARD'
  const isDayDiscussPhase = currentPhase === 'DAY_DISCUSS'
  const isVotePhase = currentPhase === 'DAY_VOTE'
  const isSheriffElectionPhase = currentPhase === 'SHERIFF_ELECTION'
  const isSheriffSpeechPhase = currentPhase === 'SHERIFF_SPEECH'
  const isSheriffVotePhase = currentPhase === 'SHERIFF_VOTE'
  const isHunterSkillPhase = currentPhase === 'HUNTER_SKILL'
  const isSheriffTransferPhase = currentPhase === 'SHERIFF_TRANSFER'

  const canShoot = isHunterOrWolfKing && !myPlayer?.is_alive

  const canConfirm = ['GAME_START', 'NIGHT_RESOLVE', 'DAY_START', 'DAY_VOTE_RESULT'].includes(currentPhase)

  const confirmText = (() => {
    const phaseTexts: Record<string, string> = {
      GAME_START: '准备就绪',
      NIGHT_RESOLVE: '继续',
      DAY_START: '确认',
      DAY_VOTE_RESULT: '继续'
    }
    return phaseTexts[currentPhase] || '确认'
  })()

  async function submitAction(type: string, tid?: number | '') {
    const finalTarget = tid !== undefined ? tid : targetId
    await submitActionMethod(type, finalTarget === '' ? undefined : finalTarget)
    setTargetId('')
    setSeerCheckError('')
  }

  async function submitSeerCheck() {
    setSeerCheckError('')
    if (targetId === '' || targetId < 1 || targetId > 12) {
      setSeerCheckError('请输入有效的玩家ID (1-12)')
      return
    }
    const target = gameState?.players.find(p => p.id === targetId)
    if (!target) {
      setSeerCheckError(`玩家 ${targetId}号 不存在`)
      return
    }
    if (!target.is_alive) {
      setSeerCheckError(`玩家 ${targetId}号 已死亡，无法查验`)
      return
    }
    try {
      await submitAction('check')
    } catch {
      setSeerCheckError('查验失败，请重试')
    }
  }

  async function submitSpeech() {
    if (speechContent.trim()) {
      await submitActionMethod('speech', undefined, speechContent)
      setSpeechContent('')
    }
  }

  async function submitWolfAction() {
    if (currentPhase === 'NIGHT_WOLF_DISCUSS') {
      if (speechContent.trim()) {
        await submitActionMethod('speech', undefined, speechContent)
        setSpeechContent('')
      }
    } else {
      await submitAction('kill')
    }
  }

  const KNOWN_ROLES = new Set(['villager', 'wolf', 'wolf_king', 'seer', 'witch', 'guard', 'hunter'])

  function getRoleCardUrl(role: string): string {
    return `/images/portraits/${KNOWN_ROLES.has(role) ? role : 'villager'}.webp`
  }

  function getRoleIdentityCardUrl(role: string): string {
    return KNOWN_ROLES.has(role) ? `/images/role-cards/${role}.webp` : '/images/role-cards/back.webp'
  }

  return (
    <div className="action-panel relative h-32 p-4 px-6 bg-slate-900/60 backdrop-blur-xl border-t border-white/10 shadow-[0_-8px_32px_rgba(0,0,0,0.4)]">
      
      {myPlayer && (
        <div 
          className="role-portrait absolute left-5 bottom-4 w-[120px] h-[180px] cursor-pointer z-50 transition-transform hover:scale-105 group"
          onClick={() => setShowRoleCard(true)}
        >
          <img
            src={getRoleCardUrl(myPlayer.role)}
            alt={ROLE_NAMES[myPlayer.role as Role]}
            className="w-full h-full object-cover rounded-xl"
          />
          <div className="portrait-overlay absolute inset-0 flex items-center justify-center bg-transparent rounded-xl transition-colors group-hover:bg-black/40">
            <span className="text-xs text-white opacity-0 transition-opacity group-hover:opacity-100">点击查看身份牌</span>
          </div>
          <div className="portrait-border absolute -inset-[2px] border-2 border-[#c5a059]/40 rounded-[14px]"></div>
        </div>
      )}

      {showRoleCard && myPlayer && (
        <div 
          className="role-card-modal fixed left-5 bottom-4 w-[360px] h-[540px] rounded-2xl overflow-hidden cursor-pointer z-[100] shadow-[0_10px_40px_rgba(0,0,0,0.6),0_0_20px_rgba(139,92,246,0.3)] border border-white/10 bg-slate-900 animate-scale-in"
          onClick={() => setShowRoleCard(false)}
        >
          <img
            src={getRoleIdentityCardUrl(myPlayer.role)}
            alt={ROLE_NAMES[myPlayer.role as Role]}
            className="w-full h-full object-cover"
          />
          <div className="role-card-info absolute bottom-0 inset-x-0 p-5 bg-gradient-to-t from-black/90 to-transparent">
            <h3 className="text-2xl font-bold text-[#f4d03f] mb-2 drop-shadow-md">
              {ROLE_NAMES[myPlayer.role as Role] || '未知'}
            </h3>
            <p className="text-sm text-white/85 leading-relaxed">
              {ROLE_DESCRIPTIONS[myPlayer.role as keyof typeof ROLE_DESCRIPTIONS]}
            </p>
          </div>
          <div className="close-hint absolute top-3 right-3 px-3 py-1 bg-black/60 rounded-full text-xs text-white/70 backdrop-blur-md">点击关闭</div>
        </div>
      )}

      <div className="action-container pl-[160px] flex items-center justify-center gap-4 flex-wrap h-full">
        {myPlayer?.is_alive && (
          <>
            {canConfirm && (
              <button onClick={() => submitAction('confirm')} className="btn btn-primary btn-glow">
                <span className="btn-icon">✨</span>
                <span>{confirmText}</span>
              </button>
            )}

            {/* Wolf Discuss Phase */}
            {currentPhase === 'NIGHT_WOLF_DISCUSS' && isWolf && (
              <div className="action-group wolf wide-group flex-col items-stretch">
                <span className="action-label">🐺 狼人密谋</span>
                <div className="input-group wide flex-1 w-full max-w-lg">
                  <input
                    value={speechContent}
                    onChange={e => setSpeechContent(e.target.value)}
                    type="text"
                    placeholder="与狼队友商量今晚的目标..."
                    className="input-field flex-1"
                    onKeyDown={e => e.key === 'Enter' && submitWolfAction()}
                  />
                  <button onClick={submitWolfAction} className="btn btn-danger">发言</button>
                  <button onClick={() => submitAction('pass')} className="btn btn-secondary">跳过</button>
                </div>
              </div>
            )}

            {/* Wolf Vote Phase */}
            {currentPhase === 'NIGHT_WOLF_VOTE' && isWolf && (
              <div className="action-group wolf">
                <span className="action-label">🐺 狼人击杀</span>
                <div className="input-group">
                  <input
                    value={targetId}
                    onChange={e => setTargetId(e.target.value === '' ? '' : Number(e.target.value))}
                    type="number" placeholder="目标ID" min="1" max="12"
                    className="input-field"
                  />
                  <button onClick={() => submitAction('kill')} className="btn btn-danger">
                    <span className="btn-icon">🗡️</span>击杀
                  </button>
                </div>
              </div>
            )}

            {/* Seer Phase */}
            {isSeerPhase && isSeer && (
              <div className="action-group seer flex-col">
                <div className="flex items-center gap-3">
                  <span className="action-label">🔮 预言家行动</span>
                  <div className="input-group">
                    <input
                      value={targetId}
                      onChange={e => setTargetId(e.target.value === '' ? '' : Number(e.target.value))}
                      type="number" placeholder="查验ID" min="1" max="12"
                      className="input-field"
                    />
                    <button 
                      onClick={submitSeerCheck} 
                      className="btn btn-purple"
                      disabled={targetId === '' || targetId < 1 || targetId > 12}
                    >
                      查验
                    </button>
                    <button onClick={() => submitAction('pass')} className="btn btn-secondary">跳过</button>
                  </div>
                </div>
                {seerCheckError && <div className="error-hint text-red-400 text-xs mt-1">{seerCheckError}</div>}
              </div>
            )}

            {/* Witch Phase */}
            {isWitchPhase && isWitch && (
              <div className="action-group witch">
                <span className="action-label">🧪 女巫行动</span>
                <div className="input-group">
                  <button onClick={() => submitAction('save')} className="btn btn-success">
                    <span className="btn-icon">💚</span>解药
                  </button>
                  <input
                    value={targetId}
                    onChange={e => setTargetId(e.target.value === '' ? '' : Number(e.target.value))}
                    type="number" placeholder="毒杀ID" min="1" max="12"
                    className="input-field small w-[70px]"
                  />
                  <button onClick={() => submitAction('poison')} className="btn btn-poison">
                    <span className="btn-icon">💀</span>毒药
                  </button>
                  <button onClick={() => submitAction('pass')} className="btn btn-secondary">跳过</button>
                </div>
              </div>
            )}

            {/* Guard Phase */}
            {isGuardPhase && isGuard && (
              <div className="action-group guard">
                <span className="action-label">🛡️ 守卫行动</span>
                <div className="input-group">
                  <input
                    value={targetId}
                    onChange={e => setTargetId(e.target.value === '' ? '' : Number(e.target.value))}
                    type="number" placeholder="守护ID" min="1" max="12"
                    className="input-field"
                  />
                  <button onClick={() => submitAction('guard')} className="btn btn-gold">守护</button>
                  <button onClick={() => submitAction('pass')} className="btn btn-secondary">空守</button>
                </div>
              </div>
            )}

            {/* Day Discuss */}
            {isDayDiscussPhase && (
              <div className="action-group speech wide-group flex-col items-stretch max-w-[600px] w-full">
                <div className="speech-header flex justify-between items-center w-full mb-2">
                  <span className="action-label">💬 发言</span>
                  <button 
                    onClick={() => setShowQuickPhrases(!showQuickPhrases)} 
                    className="btn-toggle-phrases px-3 py-1 text-xs bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded-full hover:bg-purple-500/30 transition-colors"
                  >
                    {showQuickPhrases ? '收起' : '快捷短语'} ⚡
                  </button>
                </div>
                
                {showQuickPhrases && (
                  <div className="quick-phrases flex flex-wrap gap-1.5 p-2 bg-black/30 rounded-lg w-full mb-2 animate-fade-in">
                    {quickPhrases.map(phrase => (
                      <button 
                        key={phrase.text}
                        onClick={() => setSpeechContent(phrase.text)}
                        className={`phrase-btn px-3 py-1 text-xs bg-white/5 border border-white/10 rounded-full text-white/80 hover:bg-white/10 ${phrase.type}`}
                      >
                        {phrase.icon} {phrase.label}
                      </button>
                    ))}
                  </div>
                )}
                
                <div className="input-group wide w-full flex">
                  <input
                    value={speechContent}
                    onChange={e => setSpeechContent(e.target.value)}
                    type="text"
                    placeholder="输入发言内容..."
                    className="input-field flex-1"
                    onKeyDown={e => e.key === 'Enter' && submitSpeech()}
                  />
                  <button onClick={submitSpeech} className="btn btn-primary">发言</button>
                  <button onClick={() => submitAction('confirm')} className="btn btn-secondary">结束</button>
                </div>
              </div>
            )}

            {/* Vote Phase */}
            {isVotePhase && (
              <div className="action-group vote">
                <span className="action-label">🗳️ 投票放逐</span>
                <div className="input-group">
                  <input
                    value={targetId}
                    onChange={e => setTargetId(e.target.value === '' ? '' : Number(e.target.value))}
                    type="number" placeholder="目标ID" min="1" max="12"
                    className="input-field"
                  />
                  <button onClick={() => submitAction('vote')} className="btn btn-primary">投票</button>
                  <button onClick={() => submitAction('vote', 0)} className="btn btn-secondary">弃票</button>
                </div>
              </div>
            )}

            {/* Sheriff Election */}
            {isSheriffElectionPhase && (
              <div className="action-group sheriff">
                <span className="action-label">👮 警长竞选</span>
                <div className="input-group">
                  <button onClick={() => submitAction('run_for_sheriff')} className="btn btn-gold btn-glow">
                    <span className="btn-icon">⭐</span>上警
                  </button>
                  <button onClick={() => submitAction('pass')} className="btn btn-secondary">不竞选</button>
                </div>
              </div>
            )}

            {/* Sheriff Speech */}
            {isSheriffSpeechPhase && isCandidate && (
              <div className="action-group sheriff-speech wide-group flex-col w-full max-w-[500px]">
                <span className="action-label mb-2 block">🎤 竞选发言</span>
                <div className="input-group wide w-full flex">
                  <input
                    value={speechContent}
                    onChange={e => setSpeechContent(e.target.value)}
                    type="text" placeholder="竞选发言..."
                    className="input-field flex-1"
                    onKeyDown={e => e.key === 'Enter' && submitSpeech()}
                  />
                  <button onClick={submitSpeech} className="btn btn-primary">发言</button>
                  <button onClick={() => submitAction('withdraw')} className="btn btn-danger">退水</button>
                  {isWolf && (
                    <button onClick={() => submitAction('self_explode')} className="btn btn-explode">
                      💥 自爆
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Sheriff Vote */}
            {isSheriffVotePhase && !isCandidate && (
              <div className="action-group vote">
                <span className="action-label">🗳️ 警长投票</span>
                <div className="input-group">
                  <input
                    value={targetId}
                    onChange={e => setTargetId(e.target.value === '' ? '' : Number(e.target.value))}
                    type="number" placeholder="目标ID" min="1" max="12"
                    className="input-field"
                  />
                  <button onClick={() => submitAction('vote')} className="btn btn-gold">投票</button>
                  <button onClick={() => submitAction('vote', 0)} className="btn btn-secondary">弃票</button>
                </div>
              </div>
            )}

            {/* Hunter Skill */}
            {isHunterSkillPhase && canShoot && (
              <div className="action-group hunter">
                <span className="action-label">🎯 猎人技能</span>
                <div className="input-group">
                  <input
                    value={targetId}
                    onChange={e => setTargetId(e.target.value === '' ? '' : Number(e.target.value))}
                    type="number" placeholder="目标ID" min="1" max="12"
                    className="input-field"
                  />
                  <button onClick={() => submitAction('shoot')} className="btn btn-danger btn-glow">
                    <span className="btn-icon">🔫</span>开枪
                  </button>
                  <button onClick={() => submitAction('pass')} className="btn btn-secondary">不开枪</button>
                </div>
              </div>
            )}

          </>
        )}

        {/* Sheriff Transfer - Independent of alive state */}
        {isSheriffTransferPhase && myPlayer?.is_sheriff && (
          <div className="action-group sheriff">
            <span className="action-label">👮 移交警徽</span>
            <div className="input-group">
              <input
                value={targetId}
                onChange={e => setTargetId(e.target.value === '' ? '' : Number(e.target.value))}
                type="number" placeholder="目标ID" min="1" max="12"
                className="input-field"
              />
              <button onClick={() => submitAction('vote')} className="btn btn-gold">移交</button>
              <button onClick={() => submitAction('vote', 0)} className="btn btn-danger">撕警徽</button>
            </div>
          </div>
        )}

        {/* Dead Player View */}
        {myPlayer && !myPlayer.is_alive && !isSheriffTransferPhase && (
          <div className="dead-message flex items-center gap-2 text-white/50 bg-black/30 px-6 py-3 rounded-full border border-white/5">
            <span className="text-xl">👻</span>
            <span>你已死亡，正在观战...</span>
          </div>
        )}
      </div>
    </div>
  )
}
