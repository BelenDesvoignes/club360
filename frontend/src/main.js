import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import axios from 'axios'
import router from './router'

const apiBaseUrl = import.meta.env.VITE_API_URL || '/api'
axios.defaults.baseURL = apiBaseUrl

// Si hay un token guardado, lo ponemos en axios por defecto
const token = localStorage.getItem('token')
if (token) {
  axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
}

const app = createApp(App)
app.use(createPinia()) // <--- Agregar
app.use(router)
app.mount('#app')