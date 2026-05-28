<template>
  <div v-if="auth.isAuthenticated" :class="['sim-date', { compact }]">
    <span v-if="!compact" class="sim-date-label">Día</span>

    <input
      class="sim-date-input"
      type="date"
      :value="modelValue"
      @input="onInput"
    />

    <button
      v-if="clock.hasOverride"
      class="sim-date-btn"
      type="button"
      @click="clock.clearSimulatedToday()"
    >
      Hoy
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useAppClockStore } from '../stores/appClock'

const props = defineProps({
  compact: { type: Boolean, default: false },
})

const auth = useAuthStore()
const clock = useAppClockStore()

const modelValue = computed(() => (clock.hasOverride ? clock.simulatedToday : ''))

const onInput = (e) => {
  const v = e?.target?.value
  if (!v) {
    clock.clearSimulatedToday()
    return
  }
  clock.setSimulatedToday(v)
}
</script>

<style scoped>
.sim-date {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sim-date.compact {
  gap: 8px;
}

.sim-date-label {
  font-weight: 800;
  font-size: 0.85rem;
  color: rgba(13, 18, 74, 0.7);
}

.sim-date-input {
  border: 1px solid rgba(13, 18, 74, 0.18);
  background: #ffffff;
  border-radius: 10px;
  padding: 8px 10px;
  font-weight: 700;
  color: #0d124a;
}

.sim-date.compact .sim-date-input {
  padding: 6px 8px;
  font-weight: 800;
}

.sim-date-btn {
  border: 1px solid rgba(13, 18, 74, 0.18);
  background: #ffffff;
  border-radius: 10px;
  padding: 8px 10px;
  font-weight: 800;
  color: #0d124a;
  cursor: pointer;
}

.sim-date.compact .sim-date-btn {
  padding: 6px 8px;
}
</style>
