import { defineStore } from 'pinia'
import axios from 'axios'
import api from '../utils/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null,
    role: localStorage.getItem('role') || null,
    userEmail: localStorage.getItem('email') || null,
    user: JSON.parse(localStorage.getItem('user') || 'null'),
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
    isAdmin: (state) => state.role === 'admin',
    isEmployee: (state) => state.role === 'empleado' || state.role === 'admin'
  },
  actions: {
    hydrateFromToken() {
      const token = localStorage.getItem('token')
      const role = localStorage.getItem('role')
      const userEmail = localStorage.getItem('email')

      this.token = token
      this.role = role
      this.userEmail = userEmail

      if (token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      } else {
        delete axios.defaults.headers.common['Authorization']
      }
    },

    async refreshUser() {
      if (!this.token) return null

      try {
        const meRes = await api.get('/auth/me')
        this.user = meRes.data
        localStorage.setItem('user', JSON.stringify(meRes.data))
        return meRes.data
      } catch (error) {
        return null
      }
    },

    async updateProfile(payload) {
      const res = await api.patch('/auth/me', payload)
      this.user = res.data
      localStorage.setItem('user', JSON.stringify(res.data))
      return res.data
    },

    async login(email, password) {
  try {
    const res = await axios.post('/auth/login', { email, password })

    this.token = res.data.access_token
    this.role = res.data.role
    this.userEmail = email

    localStorage.setItem('token', this.token)
    localStorage.setItem('role', this.role)
    localStorage.setItem('email', email)

    // ✅ Primero configurar el header
    axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`

    // ✅ Después llamar a /auth/me
    await this.refreshUser()

    return true
  } catch (error) {
    throw error.response?.data?.detail || 'Error al iniciar sesión'
  }
},
    logout() {
      this.token = null
      this.role = null
      this.userEmail = null
      localStorage.clear()
      delete axios.defaults.headers.common['Authorization']
    }
  }
})