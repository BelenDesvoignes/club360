import { defineStore } from 'pinia'
import axios from 'axios'
import api from '../utils/api'

const STORAGE_KEY = 'club360_simulated_today'
const HEADER_NAME = 'X-Club360-Today'

const isValidIsoDate = (value) => {
  if (!value) return false
  const v = String(value).trim()
  if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) return false
  const [y, m, d] = v.split('-').map(Number)
  if (!y || !m || !d) return false
  const probe = new Date(y, m - 1, d)
  return probe.getFullYear() === y && probe.getMonth() === m - 1 && probe.getDate() === d
}

const formatLocalYyyyMmDd = (dt) => {
  const y = dt.getFullYear()
  const m = String(dt.getMonth() + 1).padStart(2, '0')
  const d = String(dt.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const parseIsoDateAsLocalNoon = (dateStr) => {
  if (!isValidIsoDate(dateStr)) return null
  const [y, m, d] = String(dateStr).trim().split('-').map(Number)
  // Noon avoids DST edge cases when doing date math.
  return new Date(y, m - 1, d, 12, 0, 0, 0)
}

export const useAppClockStore = defineStore('appClock', {
  state: () => ({
    simulatedToday: localStorage.getItem(STORAGE_KEY) || '',
  }),
  getters: {
    hasOverride: (state) => isValidIsoDate(state.simulatedToday),
    effectiveTodayStr: (state) => (isValidIsoDate(state.simulatedToday) ? state.simulatedToday : formatLocalYyyyMmDd(new Date())),
    effectiveNow: (state) => {
      if (!isValidIsoDate(state.simulatedToday)) return new Date()
      return parseIsoDateAsLocalNoon(state.simulatedToday) || new Date()
    },
  },
  actions: {
    hydrateFromStorage() {
      const stored = localStorage.getItem(STORAGE_KEY) || ''
      this.simulatedToday = stored
      if (isValidIsoDate(stored)) {
        axios.defaults.headers.common[HEADER_NAME] = stored
      } else {
        delete axios.defaults.headers.common[HEADER_NAME]
      }
    },

    triggerPendingSubscriptionReminder(dateStr) {
      if (!isValidIsoDate(dateStr)) return

      const [, , day] = String(dateStr).split('-').map(Number)
      if (day !== 10) return

      api.get('/cron/send-pending-subscription-reminders')
        .catch(() => {
          // Silently ignore reminder errors; the date change must still work.
        })
    },

    setSimulatedToday(dateStr) {
      const next = String(dateStr || '').trim()
      if (!next) {
        this.clearSimulatedToday()
        return
      }
      if (!isValidIsoDate(next)) return

      this.simulatedToday = next
      localStorage.setItem(STORAGE_KEY, next)
      axios.defaults.headers.common[HEADER_NAME] = next
      this.triggerPendingSubscriptionReminder(next)
    },

    clearSimulatedToday() {
      this.simulatedToday = ''
      localStorage.removeItem(STORAGE_KEY)
      delete axios.defaults.headers.common[HEADER_NAME]
    },
  },
})
