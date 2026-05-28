<template >
  <button
   :disabled="!canShow"
    v-if="canShow"
    type="button"
    :class="buttonClass"
    aria-label="Volver a la página anterior"
    @click="goBack"
  >
    <span class="back-icon">←</span>
    <span v-if="variant !== 'icon'" class="back-text">Atrás</span>
  </button>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { previousRoutePath } from '../router'

const props = defineProps({
  variant: {
    type: String,
    default: 'pill',
  },
})

const router = useRouter()
const route = useRoute()

const canShow = computed(() => {
  return Boolean(previousRoutePath.value) && previousRoutePath.value !== route.fullPath
})

const buttonClass = computed(() => {
  return props.variant === 'icon' ? 'back-btn back-btn--icon' : 'back-btn back-btn--pill'
})

const goBack = async () => {
  const target = previousRoutePath.value
  if (target) {
    try {
      await router.push(target)
      return
    } catch {
      // ignore and fall back
    }
  }

  // fallback: avoid leaving the SPA if there is no previous route
  if (route.fullPath !== '/') {
    router.push('/')
  }
}
</script>

<style scoped>
.back-btn {
  display: inline-flex;
  align-items: center;
  color: #0d124a;
  font-weight: 900;
  cursor: pointer;
}

.back-btn:hover {
  filter: brightness(0.98);
}

.back-btn--pill {
  gap: 10px;
  border: 1px solid rgba(45, 101, 141, 0.18);
  background: rgba(255, 255, 255, 0.9);
  padding: 10px 14px;
  border-radius: 999px;
}

.back-btn--icon {
  gap: 0;
  border: none;
  background: transparent;
  padding: 8px;
  border-radius: 12px;
}

.back-icon {
  font-size: 1.1rem;
  line-height: 1;
}

.back-text {
  font-size: 0.95rem;
  line-height: 1;
}
</style>
