import { createApp } from 'vue'
import App from './App.vue'
import axios from 'axios'
import router from './router'

const apiBaseUrl = import.meta.env.VITE_API_URL || '/api'
axios.defaults.baseURL = apiBaseUrl

createApp(App).use(router).mount('#app')
