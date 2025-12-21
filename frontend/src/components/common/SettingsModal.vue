<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="isVisible"
        class="fixed inset-0 z-50 flex items-center justify-center"
      >
        <!-- 背景遮罩 -->
        <div
          class="absolute inset-0 bg-black/80 backdrop-blur-sm"
          @click="handleClose"
        ></div>

        <!-- 弹窗主体 -->
        <div class="settings-modal relative w-full max-w-lg mx-4 animate-scale-in">
          <!-- 标题栏 -->
          <div class="modal-header">
            <div class="flex items-center space-x-3">
              <div class="header-icon">
                <span>&#9881;</span>
              </div>
              <div>
                <h2 class="text-xl font-bold text-white">AI设置</h2>
                <p class="text-sm text-gray-400">配置LLM API连接参数</p>
              </div>
            </div>

            <button
              class="close-btn"
              @click="handleClose"
            >
              <span>&times;</span>
            </button>
          </div>

          <!-- 主体内容 -->
          <div class="modal-body">
            <!-- API Base URL -->
            <div class="form-group">
              <label class="form-label">API Base URL</label>
              <input
                v-model="formData.api_base"
                type="text"
                class="form-input"
                placeholder="https://api.openai.com/v1"
              />
              <p class="form-hint">留空使用默认OpenAI地址，或填写第三方API地址</p>
            </div>

            <!-- API Key -->
            <div class="form-group">
              <label class="form-label">API Key</label>
              <div class="input-with-status">
                <input
                  v-model="formData.api_key"
                  :type="showApiKey ? 'text' : 'password'"
                  class="form-input"
                  :placeholder="config.api_key_set ? '******** (已设置)' : '请输入API Key'"
                />
                <button
                  type="button"
                  class="toggle-visibility-btn"
                  @click="showApiKey = !showApiKey"
                >
                  {{ showApiKey ? '隐藏' : '显示' }}
                </button>
              </div>
              <p class="form-hint">
                <span v-if="config.api_key_set" class="text-green-400">API Key已配置</span>
                <span v-else class="text-yellow-400">未配置API Key，AI将使用fallback模式</span>
              </p>
            </div>

            <!-- Model -->
            <div class="form-group">
              <label class="form-label">模型</label>
              <select v-model="formData.model" class="form-input">
                <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
                <option value="gpt-4">gpt-4</option>
                <option value="gpt-4-turbo">gpt-4-turbo</option>
                <option value="gpt-4o">gpt-4o</option>
                <option value="gpt-4o-mini">gpt-4o-mini</option>
                <option value="claude-3-opus">claude-3-opus</option>
                <option value="claude-3-sonnet">claude-3-sonnet</option>
                <option value="claude-3-haiku">claude-3-haiku</option>
                <option value="deepseek-chat">deepseek-chat</option>
                <option value="custom">自定义...</option>
              </select>
              <input
                v-if="formData.model === 'custom'"
                v-model="customModel"
                type="text"
                class="form-input mt-2"
                placeholder="输入自定义模型名称"
              />
            </div>

            <!-- Temperature -->
            <div class="form-group">
              <label class="form-label">Temperature: {{ formData.temperature }}</label>
              <input
                v-model.number="formData.temperature"
                type="range"
                min="0"
                max="2"
                step="0.1"
                class="form-range"
              />
              <p class="form-hint">较低值使输出更确定，较高值使输出更随机</p>
            </div>

            <!-- Max Tokens -->
            <div class="form-group">
              <label class="form-label">Max Tokens</label>
              <input
                v-model.number="formData.max_tokens"
                type="number"
                min="100"
                max="8000"
                class="form-input"
              />
            </div>

            <!-- 测试结果 -->
            <div v-if="testResult" class="test-result" :class="testResult.success ? 'success' : 'error'">
              <div class="flex items-center space-x-2">
                <span>{{ testResult.success ? '&#10003;' : '&#10007;' }}</span>
                <span>{{ testResult.message }}</span>
              </div>
              <p v-if="testResult.response" class="text-sm mt-1 opacity-80">
                响应: {{ testResult.response }}
              </p>
            </div>
          </div>

          <!-- 底部按钮 -->
          <div class="modal-footer">
            <button
              class="btn btn-secondary"
              @click="handleTest"
              :disabled="testing"
            >
              {{ testing ? '测试中...' : '测试连接' }}
            </button>
            <div class="flex space-x-3">
              <button
                class="btn btn-outline"
                @click="handleClose"
              >
                取消
              </button>
              <button
                class="btn btn-primary"
                @click="handleSave"
                :disabled="saving"
              >
                {{ saving ? '保存中...' : '保存配置' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { configApi, type LLMConfigResponse, type LLMTestResponse } from '@/api'

interface Props {
  isVisible: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  saved: []
}>()

const config = ref<LLMConfigResponse>({
  api_key_set: false,
  api_base: null,
  model: 'gpt-3.5-turbo',
  max_tokens: 1000,
  temperature: 0.7
})

const formData = reactive({
  api_key: '',
  api_base: '',
  model: 'gpt-3.5-turbo',
  max_tokens: 1000,
  temperature: 0.7
})

const customModel = ref('')
const showApiKey = ref(false)
const saving = ref(false)
const testing = ref(false)
const testResult = ref<LLMTestResponse | null>(null)

async function loadConfig() {
  try {
    const data = await configApi.getLLMConfig()
    config.value = data
    formData.api_base = data.api_base || ''
    formData.model = data.model
    formData.max_tokens = data.max_tokens
    formData.temperature = data.temperature
  } catch (error) {
    console.error('加载配置失败:', error)
  }
}

async function handleSave() {
  saving.value = true
  testResult.value = null

  try {
    const updateData: Record<string, unknown> = {
      api_base: formData.api_base || null,
      model: formData.model === 'custom' ? customModel.value : formData.model,
      max_tokens: formData.max_tokens,
      temperature: formData.temperature
    }

    if (formData.api_key) {
      updateData.api_key = formData.api_key
    }

    const result = await configApi.setLLMConfig(updateData)
    config.value = result
    formData.api_key = ''

    emit('saved')
    emit('close')
  } catch (error) {
    console.error('保存配置失败:', error)
    testResult.value = {
      success: false,
      message: '保存配置失败'
    }
  } finally {
    saving.value = false
  }
}

async function handleTest() {
  testing.value = true
  testResult.value = null

  try {
    // 先保存当前配置
    const updateData: Record<string, unknown> = {
      api_base: formData.api_base || null,
      model: formData.model === 'custom' ? customModel.value : formData.model
    }

    if (formData.api_key) {
      updateData.api_key = formData.api_key
    }

    await configApi.setLLMConfig(updateData)

    // 然后测试连接
    testResult.value = await configApi.testLLMConnection()
  } catch (error) {
    testResult.value = {
      success: false,
      message: '测试失败: ' + (error as Error).message
    }
  } finally {
    testing.value = false
  }
}

function handleClose() {
  emit('close')
}

watch(() => props.isVisible, (visible) => {
  if (visible) {
    loadConfig()
    testResult.value = null
  }
})

onMounted(() => {
  if (props.isVisible) {
    loadConfig()
  }
})
</script>

<style scoped>
.settings-modal {
  @apply bg-gray-900 rounded-xl border border-gray-700 shadow-2xl overflow-hidden;
}

.modal-header {
  @apply flex items-center justify-between px-6 py-4 border-b border-gray-700 bg-gray-800/50;
}

.header-icon {
  @apply w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center text-xl;
}

.close-btn {
  @apply w-8 h-8 rounded-lg bg-gray-700 hover:bg-gray-600 flex items-center justify-center text-gray-400 hover:text-white transition-colors text-xl;
}

.modal-body {
  @apply px-6 py-4 space-y-4 max-h-96 overflow-y-auto;
}

.form-group {
  @apply space-y-1;
}

.form-label {
  @apply block text-sm font-medium text-gray-300;
}

.form-input {
  @apply w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500;
}

.form-hint {
  @apply text-xs text-gray-500;
}

.form-range {
  @apply w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer;
}

.input-with-status {
  @apply flex space-x-2;
}

.input-with-status .form-input {
  @apply flex-1;
}

.toggle-visibility-btn {
  @apply px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm text-gray-300 transition-colors;
}

.test-result {
  @apply p-3 rounded-lg;
}

.test-result.success {
  @apply bg-green-500/20 border border-green-500/30 text-green-400;
}

.test-result.error {
  @apply bg-red-500/20 border border-red-500/30 text-red-400;
}

.modal-footer {
  @apply flex items-center justify-between px-6 py-4 border-t border-gray-700 bg-gray-800/30;
}

.btn {
  @apply px-4 py-2 rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed;
}

.btn-primary {
  @apply bg-blue-600 hover:bg-blue-500 text-white;
}

.btn-secondary {
  @apply bg-gray-700 hover:bg-gray-600 text-gray-300;
}

.btn-outline {
  @apply border border-gray-600 hover:bg-gray-700 text-gray-300;
}

/* 动画 */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.animate-scale-in {
  animation: scale-in 0.2s ease-out;
}

@keyframes scale-in {
  from {
    transform: scale(0.95);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
