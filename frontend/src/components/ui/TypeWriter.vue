<template>
  <span>{{ displayedText }}<span v-if="isTyping" class="animate-pulse">|</span></span>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

const props = defineProps({
  text: {
    type: String,
    required: true
  },
  speed: {
    type: Number,
    default: 30
  }
})

const emit = defineEmits(['finished'])

const displayedText = ref('')
const isTyping = ref(false)

function typeText() {
  displayedText.value = ''
  isTyping.value = true
  let i = 0
  
  function type() {
    if (i < props.text.length) {
      displayedText.value += props.text.charAt(i)
      i++
      setTimeout(type, props.speed)
    } else {
      isTyping.value = false
      emit('finished')
    }
  }
  
  type()
}

watch(() => props.text, () => {
  typeText()
})

onMounted(() => {
  if (props.text) {
    typeText()
  }
})
</script>
