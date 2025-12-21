<template>
  <div class="h-screen flex flex-col items-center justify-center bg-gray-900 text-gray-100 relative">
    <!-- 设置按钮 -->
    <button
      @click="showSettings = true"
      class="absolute top-4 right-4 p-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
      title="AI设置"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    </button>

    <!-- API状态提示 -->
    <div
      v-if="!apiKeySet"
      class="absolute top-4 left-4 px-4 py-2 bg-yellow-500/20 border border-yellow-500/30 rounded-lg text-yellow-400 text-sm flex items-center space-x-2"
    >
      <span>&#9888;</span>
      <span>未配置API Key，AI将使用fallback模式</span>
      <button
        @click="showSettings = true"
        class="underline hover:text-yellow-300"
      >
        去设置
      </button>
    </div>

    <h1 class="text-6xl font-title mb-8 text-purple-500 animate-pulse">AI 狼人杀</h1>
    <button
      @click="startGame"
      class="px-8 py-4 bg-purple-600 hover:bg-opacity-80 rounded-lg text-2xl font-bold transition-all transform hover:scale-105"
    >
      开始游戏
    </button>

    <!-- 设置模态框 -->
    <SettingsModal
      :is-visible="showSettings"
      @close="showSettings = false"
      @saved="onSettingsSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/gameStore'
import { configApi } from '../api'
import SettingsModal from '../components/common/SettingsModal.vue'

const router = useRouter()
const gameStore = useGameStore()

const showSettings = ref(false)
const apiKeySet = ref(false)

async function checkApiKey() {
  try {
    const config = await configApi.getLLMConfig()
    apiKeySet.value = config.api_key_set
  } catch (error) {
    console.error('检查API配置失败:', error)
  }
}

function onSettingsSaved() {
  checkApiKey()
}

async function startGame() {
  await gameStore.createGame()
  router.push('/game')
}

onMounted(() => {
  checkApiKey()
})
</script>
