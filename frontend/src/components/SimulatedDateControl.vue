<template>
  <div v-if="auth.isAuthenticated" :class="['sim-date', { compact }]">
    <span v-if="!compact" class="sim-date-label">Día</span>

    <input
      class="sim-date-input"
      type="text"
      inputmode="numeric"
      placeholder="dd/mm/aaaa"
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

const formatDisplayDate = (isoDate) => {
  if (!isoDate) return ''
  const [year, month, day] = String(isoDate).split('-')
  if (!year || !month || !day) return ''
  return `${day}/${month}/${year}`
}

const parseDisplayDate = (value) => {
  const raw = String(value || '').trim()
  if (!raw) return ''

  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw

  const parts = raw.split(/[\/\-.]/).map(part => part.trim())
  if (parts.length !== 3) return ''

  const [day, month, year] = parts
  if (!/^\d{1,2}$/.test(day) || !/^\d{1,2}$/.test(month) || !/^\d{4}$/.test(year)) return ''

  const normalized = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`
  const probe = new Date(`${normalized}T12:00:00`)
  if (Number.isNaN(probe.getTime())) return ''
  if (probe.getFullYear() !== Number(year) || probe.getMonth() + 1 !== Number(month) || probe.getDate() !== Number(day)) return ''

  return normalized
}

const modelValue = computed(() => formatDisplayDate(clock.hasOverride ? clock.simulatedToday : ''))

const onInput = (e) => {
  const v = e?.target?.value
  if (!v) {
    clock.clearSimulatedToday()
    return
  }

  const iso = parseDisplayDate(v)
  if (!iso) return

  clock.setSimulatedToday(iso)
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
