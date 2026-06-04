import axios from 'axios'

const resolveApiBaseUrl = () => {
  const explicitBaseUrl = import.meta.env.VITE_API_URL
  if (explicitBaseUrl) return explicitBaseUrl

  const hostname = window.location.hostname
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://127.0.0.1:8000'
  }

  return `${window.location.origin}/api`
}

const api = axios.create({
  baseURL: resolveApiBaseUrl(),
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }

  const simulatedToday = localStorage.getItem('club360_simulated_today')
  if (simulatedToday) {
    config.headers = config.headers || {}
    config.headers['X-Club360-Today'] = simulatedToday
  }

  return config
})

export default api