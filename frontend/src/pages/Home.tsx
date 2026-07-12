import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { hasStoredSession, useGameStore } from '../store/useGameStore'
import { configApi } from '../api'
import { SettingsModal } from '../components/common/SettingsModal'

// Pixel art data (from existing logic)
const iconMatrix = [
  [1,0,0,0,0,0,0,0,0,0,1],
  [1,1,0,0,0,0,0,0,0,1,1],
  [1,1,1,0,0,0,0,0,1,1,1],
  [0,1,1,1,0,0,0,1,1,1,0],
  [0,1,1,1,1,0,1,1,1,1,0],
  [0,0,1,1,1,1,1,1,1,0,0],
  [0,0,1,0,1,1,1,0,1,0,0],
  [0,0,0,1,1,1,1,1,0,0,0],
  [0,0,0,0,1,0,1,0,0,0,0],
  [0,0,0,0,1,1,1,0,0,0,0],
  [0,0,0,0,0,1,0,0,0,0,0],
]

const textMatrix = [
  [0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0],
  [1,0,0,1, 1,0,0,1, 1,0,0,1, 1,1,1,1],
  [1,0,0,1, 1,0,0,1, 1,1,0,1, 0,1,0,0],
  [1,1,1,1, 1,0,0,1, 1,0,1,1, 0,1,0,0],
  [1,0,0,1, 1,0,0,1, 1,0,0,1, 0,1,0,0],
  [1,0,0,1, 0,1,1,0, 1,0,0,1, 0,1,0,0],
]

const wolfSilhouette = [
  [0,0,0,0,0,0,0,0,0,0,0,1,1,0],
  [0,0,0,0,0,0,0,0,0,0,1,1,0,0],
  [0,0,0,0,0,0,0,0,0,1,1,1,0,0],
  [0,0,0,0,0,0,0,0,1,1,1,1,0,0],
  [0,0,0,0,0,0,0,1,1,1,1,1,0,0],
  [0,0,0,0,0,1,0,1,1,1,1,0,0,0],
  [0,0,0,0,1,1,1,1,1,1,1,0,0,0],
  [0,0,0,0,0,1,0,1,1,1,0,0,0,0],
  [0,0,0,0,1,1,1,1,1,1,0,0,0,0],
  [0,0,0,1,1,1,1,1,1,1,0,0,0,0],
  [0,0,1,1,1,1,1,1,1,1,1,0,0,0],
  [0,1,1,1,1,1,1,1,1,1,1,0,0,0],
  [1,1,1,1,1,1,1,1,1,1,1,1,0,0],
  [0,0,1,1,1,1,1,1,1,1,1,1,1,0],
  [1,1,1,0,1,1,0,0,1,1,0,0,0,0],
  [1,1,0,0,1,1,0,0,1,1,0,0,0,0],
  [1,0,0,0,1,1,0,0,1,1,0,0,0,0],
  [0,0,0,0,1,1,0,0,1,1,0,0,0,0],
  [0,0,0,1,1,1,0,1,1,1,0,0,0,0],
  [0,0,0,1,1,0,0,0,1,1,0,0,0,0],
]

function buildBrandSVG() {
  const px = 4
  const iW = iconMatrix[0].length * px
  const iH = iconMatrix.length * px
  const tW = textMatrix[0].length * px
  const tH = textMatrix.length * px
  const totalW = iW + tW + 16
  const totalH = Math.max(iH, tH)

  let svgContent = ''
  iconMatrix.forEach((row, y) => {
    row.forEach((v, x) => {
      if (v) svgContent += `<rect x="${x*px}" y="${y*px}" width="${px}" height="${px}" fill="#FFF"/>`
    })
  })

  const tX = iW + 16
  const tY = (iH - tH) / 2 + 2
  textMatrix.forEach((row, y) => {
    row.forEach((v, x) => {
      if (v) svgContent += `<rect x="${tX+x*px}" y="${tY+y*px}" width="${px}" height="${px}" fill="#FFF"/>`
    })
  })

  return { __html: `<svg id="logo-svg" width="${totalW}" height="${totalH}" viewBox="0 0 ${totalW} ${totalH}" xmlns="http://www.w3.org/2000/svg" style="shape-rendering:crispEdges">${svgContent}</svg>` }
}

export function Home() {
  const navigate = useNavigate()
  const createGame = useGameStore(state => state.createGame)
  
  const [showSettings, setShowSettings] = useState(false)
  const [apiKeySet, setApiKeySet] = useState(false)
  const [hasSavedSession, setHasSavedSession] = useState(false)
  const [startError, setStartError] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [simStatus, setSimStatus] = useState<ReactNode>('BOOTING...')
  const [simPhase, setSimPhase] = useState('0.0000')

  const canvasRef = useRef<HTMLCanvasElement>(null)

  const checkApiKey = async () => {
    try {
      const config = await configApi.getLLMConfig()
      setApiKeySet(config.api_key_set)
    } catch { /* fallback */ }
  }

  const refreshSavedSessionState = () => {
    setHasSavedSession(hasStoredSession())
  }

  useEffect(() => {
    checkApiKey()
    refreshSavedSessionState()
  }, [])

  const startGame = async () => {
    // Guard against double-create: a second click while the first request is in
    // flight would spin up a second game and orphan the first.
    if (isCreating) return
    setStartError('')
    setIsCreating(true)
    try {
      await createGame()
      navigate('/game')
    } catch {
      setStartError('[ERR] 无法连接后端服务，请确认服务已启动')
      setTimeout(() => { setStartError('') }, 4000)
      setIsCreating(false)
    }
  }

  const continueGame = () => {
    refreshSavedSessionState()
    navigate('/game')
  }

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d', { alpha: false })
    if (!ctx) return
    const parent = canvas.parentElement
    if (!parent) return

    let animId = 0
    let cols = 0, rows = 0, time = 0
    const CELL = 14
    const densityChars = ['@','#','&','%','*','+','=','-',':','.',' ']
    const simStartTime = Date.now() + 1500
    let phase = 'INIT'

    const wolfCenterCol = Math.floor(wolfSilhouette[0].length / 2)
    const wolfRows = wolfSilhouette.length
    const wolfBlocks: Array<{x:number, y:number, t:number}> = []
    for (let r = wolfRows - 1; r >= 0; r--) {
      const t = 0.15 + 0.70 * ((wolfRows - 1 - r) / (wolfRows - 1))
      for (let c = 0; c < wolfSilhouette[r].length; c++) {
        if (wolfSilhouette[r][c] === 1) {
          wolfBlocks.push({ x: c - wolfCenterCol, y: r - (wolfRows - 1), t })
        }
      }
    }

    const MOON_R = 5
    const moonBlocks: Array<{x:number, y:number, t:number, bright:number}> = []
    for (let dy = -MOON_R; dy <= MOON_R; dy++) {
      for (let dx = -MOON_R; dx <= MOON_R; dx++) {
        const dist = Math.sqrt(dx*dx + dy*dy)
        if (dist <= MOON_R + 0.3) {
          const t = 0.02 + 0.25 * (dist / MOON_R)
          const bright = dist <= MOON_R * 0.6 ? 1.0 : 0.85 - 0.15 * ((dist - MOON_R * 0.6) / (MOON_R * 0.4))
          moonBlocks.push({ x: dx, y: dy, t, bright })
        }
      }
    }

    interface Star { col: number; row: number; speed: number; phase: number; bright: number }
    let stars: Star[] = []

    function generateStars() {
      stars = []
      const skyH = Math.floor(rows * 0.60)
      for (let i = 0; i < 50; i++) {
        stars.push({
          col: Math.floor(Math.random() * cols),
          row: Math.floor(Math.random() * skyH),
          speed: 0.3 + Math.random() * 2,
          phase: Math.random() * Math.PI * 2,
          bright: 0.15 + Math.random() * 0.5,
        })
      }
    }

    function resize() {
      const rect = parent!.getBoundingClientRect()
      canvas!.width = rect.width
      canvas!.height = rect.height
      cols = Math.ceil(canvas!.width / CELL)
      rows = Math.ceil(canvas!.height / CELL)
      ctx!.font = `${CELL}px "VT323", monospace`
      ctx!.textBaseline = 'top'
      generateStars()
    }

    function noise(x: number, y: number, t: number) {
      return Math.sin(x * 0.1 + t) + Math.cos(y * 0.1 - t) + Math.sin((x + y) * 0.05 + t * 0.5)
    }

    function draw() {
      ctx!.fillStyle = '#000000'
      ctx!.fillRect(0, 0, canvas!.width, canvas!.height)

      const now = Date.now()
      let progress = 0
      if (now > simStartTime) {
        progress = Math.min((now - simStartTime) / 12000, 1.0)
        if (phase === 'INIT' && progress > 0) {
          phase = 'RISING'
          setSimStatus(<span style={{ color: '#aaa' }}>ACTIVE // MOONRISE</span>)
        }
        if (phase === 'RISING' && progress > 0.3) {
          phase = 'HOWLING'
          setSimStatus(<span style={{ color: '#0f0' }}>ACTIVE // HOWLING</span>)
        }
        if (phase === 'HOWLING' && progress >= 1.0) {
          phase = 'NIGHT'
          setSimStatus(<span style={{ color: '#fff' }}>STABLE // NIGHT CYCLE</span>)
        }
      }

      if (phase !== 'INIT') {
        setSimPhase((progress * 99.99).toFixed(4))
      }

      const baseSoilHeight = Math.floor(rows * 0.65)
      const wolfBaseX = Math.floor(cols * 0.30)
      const wolfBaseY = baseSoilHeight
      const moonCX = Math.floor(cols * 0.68)
      const moonCY = Math.floor(rows * 0.18)

      if (progress > 0.05) {
        const starAlpha = Math.min((progress - 0.05) / 0.15, 1.0)
        for (const s of stars) {
          const flicker = Math.sin(time * 0.04 * s.speed + s.phase) * 0.3 + 0.7
          const a = s.bright * flicker * starAlpha
          ctx!.fillStyle = `rgba(255,255,255,${a})`
          ctx!.fillText('.', s.col * CELL, s.row * CELL)
        }
      }

      if (progress > 0) {
        for (const mb of moonBlocks) {
          if (progress >= mb.t) {
            const mx = (moonCX + mb.x) * CELL
            const my = (moonCY + mb.y) * CELL
            const alpha = Math.min(1, (progress - mb.t) / 0.08)
            const val = Math.floor(255 * mb.bright * alpha)
            ctx!.fillStyle = `rgb(${val},${val},${Math.floor(val * 0.92)})`
            ctx!.fillRect(mx + 1, my + 1, CELL - 2, CELL - 2)
          }
        }
      }

      for (let x = 0; x < cols; x++) {
        const surfaceOffset = Math.sin(x * 0.1 + time * 0.02) * 2 + Math.cos(x * 0.05) * 2
        const columnSurface = Math.floor(baseSoilHeight + surfaceOffset)

        for (let y = columnSurface; y < rows; y++) {
          const depth = y - columnSurface
          const flowVal = noise(x, y, time * 0.03)
          let ci = Math.floor(depth * 0.5 + flowVal * 3 + 2)
          ci = Math.max(0, Math.min(ci, densityChars.length - 2))

          let alpha = 1.0
          if (progress > 0.1) {
            const dw = Math.abs(x - wolfBaseX) + Math.abs(y - wolfBaseY) * 0.5
            if (dw < 4) { alpha = 0.15; ci = densityChars.length - 2 }
          }

          if (depth < 2) ctx!.fillStyle = `rgba(85,85,85,${alpha})`
          else if (depth < 6) ctx!.fillStyle = `rgba(51,51,51,${alpha})`
          else ctx!.fillStyle = `rgba(17,17,17,${alpha})`
          ctx!.fillText(densityChars[ci], x * CELL, y * CELL)
        }
      }

      if (progress > 0) {
        ctx!.fillStyle = '#FFFFFF'
        const surfAtWolf = Math.floor(baseSoilHeight +
          Math.sin(wolfBaseX * 0.1 + time * 0.02) * 2 +
          Math.cos(wolfBaseX * 0.05) * 2)

        for (const block of wolfBlocks) {
          if (progress >= block.t) {
            let swayX = 0
            if (block.y < -14) {
              swayX = Math.round(Math.sin(time * 0.04 + block.y * 0.08) * 0.6)
            }
            const dx = (wolfBaseX + block.x + swayX) * CELL
            const dy = (surfAtWolf + block.y) * CELL
            ctx!.fillRect(dx + 1, dy + 1, CELL - 2, CELL - 2)
          }
        }

        if (progress >= 1.0) {
          const eyePhase = (time % 200) / 200
          if (eyePhase < 0.15) {
            const eyeAlpha = Math.sin(eyePhase / 0.15 * Math.PI)
            const eyeX = wolfBaseX + (6 - wolfCenterCol)
            const eyeY = surfAtWolf + (7 - (wolfRows - 1))
            ctx!.fillStyle = `rgba(255, 200, 0, ${eyeAlpha})`
            ctx!.fillRect(eyeX * CELL + 1, eyeY * CELL + 1, CELL - 2, CELL - 2)
          }
        }
      }

      time++
      animId = requestAnimationFrame(draw)
    }

    window.addEventListener('resize', resize)
    resize()
    document.fonts.ready.then(() => {
      if (ctx) ctx.font = `${CELL}px "VT323", monospace`
    })
    animId = requestAnimationFrame(draw)

    return () => {
      window.removeEventListener('resize', resize)
      cancelAnimationFrame(animId)
    }
  }, [])

  return (
    <div className="w-screen h-screen bg-black text-white font-['VT323',monospace] overflow-hidden select-none antialiased">
      <main className="grid grid-cols-1 md:grid-cols-2 w-full h-full">
        <section className="flex items-center justify-center border-b md:border-b-0 md:border-r border-[#1a1a1a] relative z-10 py-10 md:py-0 px-5">
          <div className="absolute text-[12px] text-[#444] tracking-[2px] uppercase top-6 left-6">NIGHT.PROTOCOL // WOLFNET_01</div>
          
          <div className="flex flex-col items-center gap-7">
            <div className="transform scale-100 md:scale-150" dangerouslySetInnerHTML={buildBrandSVG()} />
            <div className="text-[24px] text-[#666] tracking-[6px] font-sans">AI 狼人杀</div>
            
            <div className="flex flex-col gap-2 w-[180px]">
              <button
                onClick={startGame}
                disabled={isCreating}
                aria-busy={isCreating}
                className="font-['VT323',monospace] text-[16px] px-4 py-2 bg-transparent border border-[#555] text-white cursor-pointer transition-colors text-left tracking-[2px] hover:bg-white hover:text-black disabled:cursor-wait disabled:opacity-70 disabled:hover:bg-transparent disabled:hover:text-white"
              >
                {isCreating ? (
                  <span className="inline-flex items-center gap-2">
                    <span className="inline-block w-2 h-2 bg-white animate-[pulse_1s_ease-in-out_infinite]" />
                    CREATING...
                  </span>
                ) : (
                  <>&gt; START_GAME</>
                )}
              </button>
              {hasSavedSession && (
                <button
                  onClick={continueGame}
                  disabled={isCreating}
                  className="font-['VT323',monospace] text-[16px] px-4 py-2 bg-transparent border border-[#2d5f3b] text-[#8de0a6] cursor-pointer transition-colors text-left tracking-[2px] hover:bg-[#8de0a6] hover:text-black disabled:opacity-50 disabled:hover:bg-transparent disabled:hover:text-[#8de0a6]"
                >
                  &gt; CONTINUE_GAME
                </button>
              )}
              <button
                onClick={() => setShowSettings(true)}
                disabled={isCreating}
                className="font-['VT323',monospace] text-[16px] px-4 py-2 bg-transparent border border-[#333] text-[#888] cursor-pointer transition-colors text-left tracking-[2px] hover:bg-[#111] hover:border-[#555] hover:text-white disabled:opacity-50"
              >&gt; CONFIG</button>
            </div>
            {startError ? (
              <div className="text-[13px] text-[#a00] tracking-[1px]">{startError}</div>
            ) : !apiKeySet && (
              <div className="text-[12px] text-[#664400] tracking-[1px]">[WARN] API_KEY NOT SET</div>
            )}
          </div>

          <div className="absolute text-[12px] text-[#444] tracking-[2px] uppercase left-6 bottom-6 text-left">
            V 1.0.0<br/>
            <span style={{color: '#222'}}>LYCANTHROPE PROTOCOL</span>
          </div>
        </section>

        <section className="relative bg-black bg-[linear-gradient(to_bottom,rgba(255,255,255,0),rgba(255,255,255,0)_50%,rgba(0,0,0,0.1)_50%,rgba(0,0,0,0.1))] bg-[length:100%_4px]">
          <canvas ref={canvasRef} className="block w-full h-full [image-rendering:pixelated]"></canvas>
          <div className="absolute text-[12px] text-[#444] tracking-[2px] uppercase bottom-6 right-6 text-right">
            SIMULATION: <span style={{color: '#fff'}}>{simStatus}</span><br/>
            YIELD: <span className="inline-block w-[80px]">{simPhase}</span>
          </div>
        </section>
      </main>

      <SettingsModal 
        isVisible={showSettings} 
        onClose={() => setShowSettings(false)} 
        onSaved={checkApiKey} 
      />
    </div>
  )
}
