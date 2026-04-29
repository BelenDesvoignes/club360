import { createApp } from 'vue'
import App from './App.vue'
import axios from 'axios'

const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
axios.defaults.baseURL = apiBaseUrl

createApp(App).mount('#app')