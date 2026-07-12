import { useMemo } from 'react'
import { useGameStore } from '../../store/useGameStore'
import { cn } from '../../lib/utils'

export function NightActionAnimation() {
  const currentPhase = useGameStore(state => state.gameState?.phase)
  const myPlayer = useGameStore(state => state.gameState?.players.find(p => p.is_human))
  const myRole = myPlayer?.role

  const phaseToAction = useMemo(() => {
    if (currentPhase === 'NIGHT_WOLF_DISCUSS' || currentPhase === 'NIGHT_WOLF_VOTE') return 'wolf'
    if (currentPhase === 'NIGHT_SEER') return 'seer'
    if (currentPhase === 'NIGHT_WITCH') return 'witch'
    if (currentPhase === 'NIGHT_GUARD') return 'guard'
    return null
  }, [currentPhase])

  const nightProgress = useMemo(() => {
    if (currentPhase === 'NIGHT_WOLF_DISCUSS' || currentPhase === 'NIGHT_WOLF_VOTE') return 1
    if (currentPhase === 'NIGHT_SEER') return 2
    if (currentPhase === 'NIGHT_WITCH') return 3
    if (currentPhase === 'NIGHT_GUARD') return 4
    if (currentPhase === 'NIGHT_RESOLVE') return 5
    return 0
  }, [currentPhase])

  const currentAction = useMemo(() => {
    if (!phaseToAction) return null

    const roleMapping: Record<'wolf' | 'witch' | 'guard' | 'seer', string[]> = {
      wolf: ['wolf', 'wolf_king'],
      witch: ['witch'],
      guard: ['guard'],
      seer: ['seer']
    }

    const isMyAction = roleMapping[phaseToAction]?.includes(myRole || '')
    return isMyAction ? null : phaseToAction
  }, [myRole, phaseToAction])

  const isVisible = currentAction !== null

  const progressPercent = Math.min(100, (nightProgress / 4) * 100)

  const progressSteps = [
    { key: 'wolf', label: '狼人', active: currentAction === 'wolf', done: nightProgress > 1 },
    { key: 'seer', label: '预言家', active: currentAction === 'seer', done: nightProgress > 2 },
    { key: 'witch', label: '女巫', active: currentAction === 'witch', done: nightProgress > 3 },
    { key: 'guard', label: '守卫', active: currentAction === 'guard', done: nightProgress > 4 },
  ]

  if (!isVisible) return null

  return (
    <div className="night-overlay fixed inset-0 flex flex-col items-center justify-center z-[100] pointer-events-none bg-[radial-gradient(ellipse_at_center,rgba(0,0,0,0.3)_0%,rgba(0,0,0,0.65)_100%)] animate-fade-in">
      
      {/* ProgressBar */}
      <div className="night-progress-bar absolute top-[110px] flex items-center gap-8 px-7 py-3.5 bg-slate-950/85 backdrop-blur-md rounded-full border border-white/5 shadow-[0_4px_24px_rgba(0,0,0,0.4)]">
        {progressSteps.map(step => (
          <div key={step.key} className={cn('progress-item flex flex-col items-center gap-1.5 transition-all duration-400', step.active ? 'opacity-100' : step.done ? 'opacity-50' : 'opacity-30')}>
            <div className={cn('progress-dot relative w-2 h-2 rounded-full transition-all duration-400', 
              step.active ? 'bg-white/90 shadow-[0_0_12px_rgba(255,255,255,0.4)]' : 
              step.done ? 'bg-green-400/60' : 'bg-white/30'
            )}>
              {step.active && <div className="absolute -inset-1 rounded-full border border-white/30 animate-ping opacity-60"></div>}
            </div>
            <span className={cn('progress-label text-[11px] whitespace-nowrap tracking-wide', step.active ? 'text-white/90 font-semibold' : step.done ? 'text-green-400/60' : 'text-white/50')}>
              {step.label}
            </span>
          </div>
        ))}
        <div className="progress-track absolute bottom-1.5 left-7 right-7 h-0.5 bg-white/5 rounded-full overflow-hidden">
          <div className="progress-fill h-full bg-gradient-to-r from-indigo-500/60 to-purple-500/60 transition-all duration-800" style={{ width: `${progressPercent}%` }}></div>
        </div>
      </div>

      {/* Action Stage */}
      <div className="action-stage flex items-center justify-center">
        
        {currentAction === 'wolf' && (
          <div className="stage-content flex flex-col items-center gap-5 animate-slide-up-fade">
            <div className="role-icon-container relative w-[120px] h-[120px] drop-shadow-[0_0_20px_rgba(220,38,38,0.25)]">
               <svg className="role-svg w-full h-full animate-[iconFloat_4s_ease-in-out_infinite]" viewBox="0 0 80 80">
                <circle cx="40" cy="40" r="36" fill="rgba(220, 38, 38, 0.1)" stroke="rgba(220, 38, 38, 0.3)" strokeWidth="1"/>
                <circle cx="40" cy="40" r="28" fill="rgba(220, 38, 38, 0.05)" stroke="rgba(220, 38, 38, 0.15)" strokeWidth="1"/>
                <g transform="translate(40,40)" className="animate-[pawPress_2s_ease-in-out_infinite]">
                  <ellipse cx="0" cy="4" rx="6" ry="8" fill="rgba(220, 38, 38, 0.8)"/>
                  <ellipse cx="-7" cy="-6" rx="3" ry="4" fill="rgba(220, 38, 38, 0.7)" transform="rotate(-15)"/>
                  <ellipse cx="7" cy="-6" rx="3" ry="4" fill="rgba(220, 38, 38, 0.7)" transform="rotate(15)"/>
                  <ellipse cx="-12" cy="-1" rx="2.5" ry="3.5" fill="rgba(220, 38, 38, 0.6)" transform="rotate(-30)"/>
                  <ellipse cx="12" cy="-1" rx="2.5" ry="3.5" fill="rgba(220, 38, 38, 0.6)" transform="rotate(30)"/>
                </g>
              </svg>
            </div>
            <p className="stage-text text-[1.1rem] font-medium tracking-[2px] m-0 text-red-400/90">狼人正在行动</p>
            <div className="stage-dots flex gap-1.5">
              <span className="w-1 h-1 rounded-full bg-red-400/50 animate-[dotBounce_1.4s_ease-in-out_infinite]" style={{ animationDelay: '0s' }}></span>
              <span className="w-1 h-1 rounded-full bg-red-400/50 animate-[dotBounce_1.4s_ease-in-out_infinite]" style={{ animationDelay: '0.2s' }}></span>
              <span className="w-1 h-1 rounded-full bg-red-400/50 animate-[dotBounce_1.4s_ease-in-out_infinite]" style={{ animationDelay: '0.4s' }}></span>
            </div>
          </div>
        )}

        {currentAction === 'seer' && (
          <div className="stage-content flex flex-col items-center gap-5 animate-slide-up-fade">
            <div className="role-icon-container relative w-[120px] h-[120px] drop-shadow-[0_0_20px_rgba(99,102,241,0.25)]">
              <svg className="role-svg w-full h-full animate-[iconFloat_4s_ease-in-out_infinite]" viewBox="0 0 80 80">
                <circle cx="40" cy="40" r="36" fill="rgba(99, 102, 241, 0.1)" stroke="rgba(99, 102, 241, 0.3)" strokeWidth="1"/>
                <circle cx="40" cy="40" r="28" fill="rgba(99, 102, 241, 0.05)" stroke="rgba(99, 102, 241, 0.15)" strokeWidth="1"/>
                <g transform="translate(40,36)">
                  <circle cx="0" cy="0" r="14" fill="none" stroke="rgba(129, 140, 248, 0.6)" strokeWidth="1.5" className="animate-[crystalRotate_6s_linear_infinite] origin-center shadow-[0_0_10px_rgba(129,140,248,0.5)]"/>
                  <circle cx="0" cy="0" r="10" fill="rgba(99, 102, 241, 0.15)"/>
                  <circle cx="-3" cy="-3" r="3" fill="rgba(255, 255, 255, 0.15)"/>
                  <path d="M-8,14 Q-6,10 0,10 Q6,10 8,14" fill="rgba(129, 140, 248, 0.3)" stroke="rgba(129, 140, 248, 0.4)" strokeWidth="1"/>
                </g>
              </svg>
            </div>
            <p className="stage-text text-[1.1rem] font-medium tracking-[2px] m-0 text-indigo-400/90">预言家正在查验</p>
            <div className="stage-dots flex gap-1.5">
              <span className="w-1 h-1 rounded-full bg-indigo-400/50 animate-[dotBounce_1.4s_ease-in-out_infinite]" style={{ animationDelay: '0s' }}></span>
              <span className="w-1 h-1 rounded-full bg-indigo-400/50 animate-[dotBounce_1.4s_ease-in-out_infinite]" style={{ animationDelay: '0.2s' }}></span>
              <span className="w-1 h-1 rounded-full bg-indigo-400/50 animate-[dotBounce_1.4s_ease-in-out_infinite]" style={{ animationDelay: '0.4s' }}></span>
            </div>
          </div>
        )}

        {currentAction === 'witch' && (
          <div className="stage-content flex flex-col items-center gap-5 animate-slide-up-fade">
            <div className="role-icon-container relative w-[120px] h-[120px] drop-shadow-[0_0_20px_rgba(168,85,247,0.25)]">
              <svg className="role-svg w-full h-full animate-[iconFloat_4s_ease-in-out_infinite]" viewBox="0 0 80 80">
                <circle cx="40" cy="40" r="36" fill="rgba(168, 85, 247, 0.1)" stroke="rgba(168, 85, 247, 0.3)" strokeWidth="1"/>
                <circle cx="40" cy="40" r="28" fill="rgba(168, 85, 247, 0.05)" stroke="rgba(168, 85, 247, 0.15)" strokeWidth="1"/>
                <g transform="translate(30,34)">
                  <rect x="2" y="0" width="6" height="4" rx="1" fill="rgba(34, 197, 94, 0.5)" stroke="rgba(34, 197, 94, 0.6)" strokeWidth="0.8"/>
                  <rect x="0" y="4" width="10" height="14" rx="2" fill="rgba(34, 197, 94, 0.3)" stroke="rgba(34, 197, 94, 0.5)" strokeWidth="0.8"/>
                </g>
                <g transform="translate(44,34)">
                  <rect x="2" y="0" width="6" height="4" rx="1" fill="rgba(168, 85, 247, 0.5)" stroke="rgba(168, 85, 247, 0.6)" strokeWidth="0.8"/>
                  <rect x="0" y="4" width="10" height="14" rx="2" fill="rgba(168, 85, 247, 0.3)" stroke="rgba(168, 85, 247, 0.5)" strokeWidth="0.8"/>
                </g>
              </svg>
            </div>
            <p className="stage-text text-[1.1rem] font-medium tracking-[2px] m-0 text-purple-400/90">女巫正在行动</p>
            <div className="stage-dots flex gap-1.5">
              <span className="w-1 h-1 rounded-full bg-purple-400/50 animate-[dotBounce_1.4s_ease-in-out_infinite]" style={{ animationDelay: '0s' }}></span>
              <span className="w-1 h-1 rounded-full bg-purple-400/50 animate-[dotBounce_1.4s_ease-in-out_infinite]" style={{ animationDelay: '0.2s' }}></span>
              <span className="w-1 h-1 rounded-full bg-purple-400/50 animate-[dotBounce_1.4s_ease-in-out_infinite]" style={{ animationDelay: '0.4s' }}></span>
            </div>
          </div>
        )}

        {currentAction === 'guard' && (
          <div className="stage-content flex flex-col items-center gap-5 animate-slide-up-fade">
            <div className="role-icon-container relative w-[120px] h-[120px] drop-shadow-[0_0_20px_rgba(234,179,8,0.25)]">
              <svg className="role-svg w-full h-full animate-[iconFloat_4s_ease-in-out_infinite]" viewBox="0 0 80 80">
                <circle cx="40" cy="40" r="36" fill="rgba(234, 179, 8, 0.1)" stroke="rgba(234, 179, 8, 0.3)" strokeWidth="1"/>
                <circle cx="40" cy="40" r="28" fill="rgba(234, 179, 8, 0.05)" stroke="rgba(234, 179, 8, 0.15)" strokeWidth="1"/>
                <g transform="translate(40,40)">
                  <path d="M0,-16 L14,-8 L12,6 Q8,16 0,20 Q-8,16 -12,6 L-14,-8 Z"
                    fill="rgba(234, 179, 8, 0.2)" stroke="rgba(234, 179, 8, 0.6)" strokeWidth="1.5"/>
                  <path d="M0,-10 L8,-5 L7,3 Q5,9 0,12 Q-5,9 -7,3 L-8,-5 Z"
                    fill="none" stroke="rgba(234, 179, 8, 0.3)" strokeWidth="0.8"/>
                </g>
              </svg>
            </div>
            <p className="stage-text text-[1.1rem] font-medium tracking-[2px] m-0 text-yellow-400/90">守卫正在守护</p>
            <div className="stage-dots flex gap-1.5">
              <span className="w-1 h-1 rounded-full bg-yellow-400/50 animate-[dotBounce_1.4s_ease-in-out_infinite]" style={{ animationDelay: '0s' }}></span>
              <span className="w-1 h-1 rounded-full bg-yellow-400/50 animate-[dotBounce_1.4s_ease-in-out_infinite]" style={{ animationDelay: '0.2s' }}></span>
              <span className="w-1 h-1 rounded-full bg-yellow-400/50 animate-[dotBounce_1.4s_ease-in-out_infinite]" style={{ animationDelay: '0.4s' }}></span>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
