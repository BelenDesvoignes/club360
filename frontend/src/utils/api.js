import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
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