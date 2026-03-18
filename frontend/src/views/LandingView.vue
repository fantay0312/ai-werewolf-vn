<template>
  <main class="oasis-main">
    <section class="panel-left">
      <div class="sys-label label-top-left">SYS.INIT // CORE_01</div>

      <div class="brand-container" @click="startGame">
        <svg
          id="logo-svg"
          :width="svgWidth"
          :height="svgHeight"
          :viewBox="`0 0 ${svgWidth} ${svgHeight}`"
          xmlns="http://www.w3.org/2000/svg"
          style="shape-rendering: crispEdges;"
        >
          <rect
            v-for="(rect, i) in svgRects"
            :key="i"
            :x="rect.x"
            :y="rect.y"
            :width="rect.w"
            :height="rect.h"
            fill="#FFF"
          />
        </svg>
      </div>

      <!-- Settings button -->
      <button
        class="settings-btn"
        @click="showSettings = true"
        title="AI设置"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="#555">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>

      <!-- API Key warning -->
      <div v-if="!apiKeySet" class="api-warning">
        <span>&#9888; API Key未设置</span>
        <button @click="showSettings = true" class="api-warning-btn">设置</button>
      </div>

      <!-- Start game button -->
      <button class="start-btn" @click="startGame">
        [ 开始游戏 ]
      </button>

      <div class="sys-label label-bottom-left">
        V 1.0.4<br>
        <span style="color: #222;">AESTHETIC PROTOCOL</span>
      </div>
    </section>

    <section class="panel-right">
      <canvas ref="canvasRef"></canvas>

      <div class="sys-label label-bottom-right">
        SIMULATION: <span :style="{ color: simStatusColor }">{{ simStatus }}</span><br>
        YIELD: <span class="data-stream">{{ simYield }}</span>
      </div>
    </section>

    <!-- Settings Modal -->
    <SettingsModal
      :is-visible="showSettings"
      @close="showSettings = false"
      @saved="onSettingsSaved"
    />
  </main>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/gameStore'
import { configApi } from '../api'
import SettingsModal from '../components/common/SettingsModal.vue'

const router = useRouter()
const gameStore = useGameStore()

const showSettings = ref(false)
const apiKeySet = ref(false)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const simStatus = ref('BOOTING...')
const simStatusColor = ref('#fff')
const simYield = ref('0.0000')

let animFrameId = 0

// --- SVG Brand ---
const pixelSize = 4
const iconMatrix = [
  [0,0,0,0,1,0,1,0,0,0,0],
  [0,0,0,1,1,1,1,1,0,0,0],
  [0,0,1,1,0,1,0,1,1,0,0],
  [0,1,1,0,0,0,0,0,1,1,0],
  [1,1,0,0,1,1,1,0,0,1,1],
  [0,1,1,0,1,0,1,0,1,1,0],
  [1,1,0,0,1,1,1,0,0,1,1],
  [0,1,1,0,0,0,0,0,1,1,0],
  [0,0,1,1,0,1,0,1,1,0,0],
  [0,0,0,1,1,1,1,1,0,0,0],
  [0,0,0,0,1,0,1,0,0,0,0],
]
const textMatrix = [
  [0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0],
  [0,1,1,0, 0,0,0,0, 0,1,1,0, 0,1,0,0, 0,1,1,0],
  [1,0,0,1, 0,1,1,1, 1,0,0,0, 0,0,0,0, 1,0,0,0],
  [1,0,0,1, 1,0,0,1, 0,1,1,0, 0,1,0,0, 0,1,1,0],
  [1,0,0,1, 1,0,0,1, 0,0,0,1, 0,1,0,0, 0,0,0,1],
  [0,1,1,0, 0,1,1,1, 1,1,1,0, 0,1,0,0, 1,1,1,0],
]

const iconWidth = iconMatrix[0].length * pixelSize
const iconHeight = iconMatrix.length * pixelSize
const textWidth = textMatrix[0].length * pixelSize
const textHeight = textMatrix.length * pixelSize
const svgWidth = iconWidth + textWidth + 16
const svgHeight = Math.max(iconHeight, textHeight)

const svgRects = computed(() => {
  const rects: { x: number; y: number; w: number; h: number }[] = []
  iconMatrix.forEach((row, y) => {
    row.forEach((val, x) => {
      if (val === 1) {
        rects.push({ x: x * pixelSize, y: y * pixelSize, w: pixelSize, h: pixelSize })
      }
    })
  })
  const textOffsetX = iconWidth + 16
  const textOffsetY = (iconHeight - textHeight) / 2 + 2
  textMatrix.forEach((row, y) => {
    row.forEach((val, x) => {
      if (val === 1) {
        rects.push({
          x: textOffsetX + x * pixelSize,
          y: textOffsetY + y * pixelSize,
          w: pixelSize,
          h: pixelSize,
        })
      }
    })
  })
  return rects
})

// --- Canvas Animation ---
const CELL_SIZE = 14
const densityChars = ['@', '#', '&', '%', '*', '+', '=', '-', ':', '.', ' ']

const sproutData = [
  { x: 0, y: 0, t: 0.05 },
  { x: 0, y: -1, t: 0.10 },
  { x: 0, y: -2, t: 0.15 },
  { x: 0, y: -3, t: 0.20 },
  { x: 0, y: -4, t: 0.25 },
  { x: 0, y: -5, t: 0.30 },
  { x: 0, y: -6, t: 0.35 },
  { x: 0, y: -7, t: 0.40 },
  { x: -1, y: -4, t: 0.50 },
  { x: -2, y: -5, t: 0.55 },
  { x: -3, y: -5, t: 0.60 },
  { x: -2, y: -4, t: 0.62 },
  { x: 1, y: -5, t: 0.52 },
  { x: 2, y: -6, t: 0.57 },
  { x: 3, y: -6, t: 0.62 },
  { x: 2, y: -5, t: 0.64 },
  { x: -1, y: -8, t: 0.75 },
  { x: 1, y: -8, t: 0.75 },
  { x: 0, y: -9, t: 0.80 },
  { x: -1, y: -10, t: 0.85 },
  { x: 1, y: -10, t: 0.85 },
  { x: 0, y: -11, t: 0.90 },
  { x: 0, y: -13, t: 0.98 },
]

function noise(x: number, y: number, t: number) {
  return Math.sin(x * 0.1 + t) + Math.cos(y * 0.1 - t) + Math.sin((x + y) * 0.05 + t * 0.5)
}

function initCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return

  const ctx = canvas.getContext('2d', { alpha: false })
  if (!ctx) return

  let time = 0
  let phase: 'INIT' | 'GROWING' | 'MATURE' = 'INIT'
  const simStartTime = Date.now() + 1500

  function resize() {
    if (!canvas) return
    const rect = canvas.parentElement!.getBoundingClientRect()
    canvas.width = rect.width
    canvas.height = rect.height
    ctx!.font = `${CELL_SIZE}px "VT323", monospace`
    ctx!.textBaseline = 'top'
  }

  const onResize = () => resize()
  window.addEventListener('resize', onResize)
  resize()

  function draw() {
    if (!canvas || !ctx) return

    ctx.fillStyle = '#000000'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    const cols = Math.ceil(canvas.width / CELL_SIZE)
    const rows = Math.ceil(canvas.height / CELL_SIZE)

    const now = Date.now()
    let progress = 0

    if (now > simStartTime) {
      const duration = 12000
      progress = Math.min((now - simStartTime) / duration, 1.0)

      if (phase === 'INIT' && progress > 0) {
        phase = 'GROWING'
        simStatus.value = 'ACTIVE // BIOGENESIS'
        simStatusColor.value = '#0f0'
      } else if (phase === 'GROWING' && progress === 1.0) {
        phase = 'MATURE'
        simStatus.value = 'STABLE // CYCLE RUNNING'
        simStatusColor.value = '#fff'
      }
    }

    if (phase !== 'INIT') {
      simYield.value = (progress * 99.99).toFixed(4)
    }

    const baseSoilHeight = Math.floor(rows * 0.65)
    const rootX = Math.floor(cols / 2)

    for (let x = 0; x < cols; x++) {
      const surfaceOffset = Math.sin(x * 0.1 + time * 0.02) * 2 + Math.cos(x * 0.05) * 2
      const columnSurface = Math.floor(baseSoilHeight + surfaceOffset)

      let rootY = baseSoilHeight
      if (x === rootX) {
        rootY = columnSurface
      }

      for (let y = columnSurface; y < rows; y++) {
        const depth = y - columnSurface
        const flowVal = noise(x, y, time * 0.03)
        let charIndex = Math.floor(depth * 0.5 + flowVal * 3 + 2)
        charIndex = Math.max(0, Math.min(charIndex, densityChars.length - 2))

        let alpha = 1.0
        if (progress > 0) {
          const distToRoot = Math.sqrt(Math.pow(x - rootX, 2) + Math.pow(y - rootY, 2))
          if (distToRoot < 3 && progress > 0.1) {
            alpha = 0.2
            charIndex = densityChars.length - 2
          }
        }

        if (depth < 2) ctx.fillStyle = `rgba(85, 85, 85, ${alpha})`
        else if (depth < 6) ctx.fillStyle = `rgba(51, 51, 51, ${alpha})`
        else ctx.fillStyle = `rgba(17, 17, 17, ${alpha})`

        ctx.fillText(densityChars[charIndex], x * CELL_SIZE, y * CELL_SIZE)
      }
    }

    // Draw sprout
    if (progress > 0) {
      ctx.fillStyle = '#FFFFFF'
      const currentSurfaceAtRoot = Math.floor(
        baseSoilHeight +
          (Math.sin(rootX * 0.1 + time * 0.02) * 2 + Math.cos(rootX * 0.05) * 2)
      )

      sproutData.forEach((block) => {
        if (progress >= block.t) {
          let swayX = 0
          if (block.y < -4) {
            swayX = Math.round(Math.sin(time * 0.05 + block.y * 0.1) * 0.6)
          }
          const drawX = (rootX + block.x + swayX) * CELL_SIZE
          const drawY = (currentSurfaceAtRoot + block.y) * CELL_SIZE
          ctx.fillRect(drawX + 1, drawY + 1, CELL_SIZE - 2, CELL_SIZE - 2)
        }
      })
    }

    time++
    animFrameId = requestAnimationFrame(draw)
  }

  animFrameId = requestAnimationFrame(draw)

  // Return cleanup
  return () => {
    window.removeEventListener('resize', onResize)
    cancelAnimationFrame(animFrameId)
  }
}

// --- Game Logic ---
async function checkApiKey() {
  try {
    const config = await configApi.getLLMConfig()
    apiKeySet.value = config.api_key_set
  } catch {
    // ignore
  }
}

function onSettingsSaved() {
  checkApiKey()
}

async function startGame() {
  await gameStore.createGame()
  router.push('/game')
}

let cleanup: (() => void) | undefined

onMounted(() => {
  checkApiKey()
  cleanup = initCanvas()
})

onUnmounted(() => {
  cleanup?.()
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=VT323&display=swap');

.oasis-main {
  display: grid;
  grid-template-columns: 1fr 1fr;
  width: 100vw;
  height: 100vh;
  background: #000;
  font-family: 'VT323', monospace;
  color: #fff;
  user-select: none;
  -webkit-font-smoothing: none;
  overflow: hidden;
}

.panel-left {
  display: flex;
  align-items: center;
  justify-content: center;
  border-right: 1px solid #1a1a1a;
  position: relative;
  z-index: 10;
  flex-direction: column;
  gap: 32px;
}

.panel-right {
  position: relative;
  background: #000;
  background-image: linear-gradient(
    to bottom,
    rgba(255, 255, 255, 0),
    rgba(255, 255, 255, 0) 50%,
    rgba(0, 0, 0, 0.1) 50%,
    rgba(0, 0, 0, 0.1)
  );
  background-size: 100% 4px;
}

.brand-container {
  display: flex;
  align-items: center;
  gap: 24px;
  transform: scale(1.5);
  cursor: pointer;
  transition: opacity 0.2s;
}
.brand-container:hover {
  opacity: 0.8;
}

canvas {
  display: block;
  width: 100%;
  height: 100%;
  image-rendering: -moz-crisp-edges;
  image-rendering: -webkit-optimize-contrast;
  image-rendering: crisp-edges;
  image-rendering: pixelated;
}

.sys-label {
  position: absolute;
  font-size: 12px;
  color: #444;
  letter-spacing: 2px;
  text-transform: uppercase;
}

.label-top-left {
  top: 24px;
  left: 24px;
}

.label-bottom-right {
  bottom: 24px;
  right: 24px;
  text-align: right;
}

.label-bottom-left {
  left: 24px;
  bottom: 24px;
  text-align: left;
}

.data-stream {
  display: inline-block;
  width: 80px;
}

.settings-btn {
  position: absolute;
  top: 24px;
  right: 24px;
  background: transparent;
  border: 1px solid #222;
  border-radius: 4px;
  padding: 8px;
  cursor: pointer;
  transition: border-color 0.2s;
}
.settings-btn:hover {
  border-color: #555;
}
.settings-btn:hover svg {
  stroke: #999;
}

.api-warning {
  position: absolute;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 12px;
  color: #666;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #222;
  padding: 6px 12px;
}

.api-warning-btn {
  background: none;
  border: none;
  color: #888;
  font-family: 'VT323', monospace;
  font-size: 12px;
  cursor: pointer;
  text-decoration: underline;
}
.api-warning-btn:hover {
  color: #fff;
}

.start-btn {
  background: none;
  border: 1px solid #333;
  color: #888;
  font-family: 'VT323', monospace;
  font-size: 20px;
  padding: 12px 32px;
  cursor: pointer;
  letter-spacing: 4px;
  transition: all 0.2s;
}
.start-btn:hover {
  border-color: #fff;
  color: #fff;
  box-shadow: 0 0 20px rgba(255, 255, 255, 0.05);
}
</style>
