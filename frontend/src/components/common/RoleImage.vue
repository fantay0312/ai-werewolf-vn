<template>
  <div class="role-image-container" :class="containerClass">
    <img
      v-if="imageUrl"
      :src="imageUrl"
      :alt="altText"
      :class="imageClass"
      @error="handleImageError"
      @load="handleImageLoad"
    />
    <div v-else class="placeholder" :class="imageClass">
      <span class="placeholder-text">{{ placeholderText }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { getPortrait, getRoleCard, getRoleName, ROLE_CARD_BACK } from '@/config/assets'
import type { RoleType } from '@/config/assets'

interface Props {
  role: RoleType
  type?: 'portrait' | 'card'  // 立绘或身份牌
  showName?: boolean
  containerClass?: string
  imageClass?: string
  fallbackToBack?: boolean    // 是否在错误时显示反面牌
}

const props = withDefaults(defineProps<Props>(), {
  type: 'portrait',
  showName: false,
  containerClass: '',
  imageClass: '',
  fallbackToBack: true,
})

const imageError = ref(false)
const imageLoaded = ref(false)

const imageUrl = computed(() => {
  if (imageError.value && props.fallbackToBack && props.type === 'card') {
    return ROLE_CARD_BACK
  }

  return props.type === 'portrait'
    ? getPortrait(props.role)
    : getRoleCard(props.role)
})

const altText = computed(() => {
  const roleName = getRoleName(props.role)
  return props.type === 'portrait'
    ? `${roleName}立绘`
    : `${roleName}身份牌`
})

const placeholderText = computed(() => {
  return getRoleName(props.role)
})

function handleImageError() {
  console.warn(`Failed to load image for role: ${props.role}, type: ${props.type}`)
  imageError.value = true
}

function handleImageLoad() {
  imageLoaded.value = true
}
</script>

<style scoped>
.role-image-container {
  position: relative;
  display: inline-block;
}

.role-image-container img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-weight: bold;
}

.placeholder-text {
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}
</style>
