import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import axios from 'axios'
import router from './router'

const resolveApiBaseUrl = () => {
  const explicitBaseUrl = import.meta.env.VITE_API_URL
  if (explicitBaseUrl) return explicitBaseUrl

  const hostname = window.location.hostname
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://127.0.0.1:8000/api'
  }

  return `${window.location.origin}/api`
}

const apiBaseUrl = resolveApiBaseUrl()
axios.defaults.baseURL = apiBaseUrl

// Si hay un token guardado, lo ponemos en axios por defecto
const token = localStorage.getItem('token')
if (token) {
  axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
}

// Día corrido (simulación): si existe, lo enviamos en cada request
const simulatedToday = localStorage.getItem('club360_simulated_today')
if (simulatedToday) {
  axios.defaults.headers.common['X-Club360-Today'] = simulatedToday
}

const app = createApp(App)
app.use(createPinia()) // <--- Agregar
app.use(router)
app.mount('#app')