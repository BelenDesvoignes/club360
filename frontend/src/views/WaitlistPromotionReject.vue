<template>
  <div class="waitlist-rejection-container">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Procesando tu rechazo...</p>
    </div>

    <!-- Success State -->
    <div v-else-if="success" class="success-state">
      <div class="icon-success">✓</div>
      <h2>Rechazo registrado</h2>
      <p>Tu rechazo ha sido procesado correctamente.</p>
      <p class="info-text">Pasaremos al siguiente en la lista de espera. ¡Suerte!</p>
      <button @click="goHome" class="btn-primary">
        Volver al inicio
      </button>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <div class="icon-error">✕</div>
      <h2>Algo salió mal</h2>
      <p>{{ error }}</p>
      <button @click="goHome" class="btn-primary">
        Volver al inicio
      </button>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '../utils/api'

export default {
  name: 'WaitlistPromotionReject',
  setup() {
    const router = useRouter()
    const route = useRoute()
    const loading = ref(true)
    const success = ref(false)
    const error = ref(null)

    onMounted(async () => {
      try {
        const token = route.params.token
        if (!token) {
          error.value = 'Token inválido'
          loading.value = false
          return
        }

        // Llamar al endpoint de rechazo
        const response = await api.post(`/waiting-lists/reject/${token}`)
        
        success.value = true
        loading.value = false

        // Redirigir automáticamente después de 5 segundos
        setTimeout(() => {
          goHome()
        }, 5000)
      } catch (err) {
        console.error('Error rechazando promoción:', err)
        error.value = err.response?.data?.detail || 'Error al procesar el rechazo'
        loading.value = false
      }
    })

    const goHome = () => {
      router.push('/')
    }

    return {
      loading,
      success,
      error,
      goHome
    }
  }
}
</script>

<style scoped>
.waitlist-rejection-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.loading-state,
.success-state,
.error-state {
  background: white;
  border-radius: 12px;
  padding: 40px;
  max-width: 500px;
  width: 100%;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #5a8849;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-state p {
  color: #666;
  font-size: 16px;
  margin: 0;
}

.icon-success {
  font-size: 60px;
  color: #5a8849;
  margin-bottom: 20px;
  font-weight: bold;
}

.icon-error {
  font-size: 60px;
  color: #dc3545;
  margin-bottom: 20px;
  font-weight: bold;
}

.success-state h2,
.error-state h2 {
  margin: 0 0 15px 0;
  font-size: 24px;
  color: #333;
}

.success-state p,
.error-state p {
  color: #666;
  font-size: 16px;
  margin: 10px 0;
}

.info-text {
  background: #f5f5f5;
  padding: 15px;
  border-radius: 8px;
  margin: 20px 0 !important;
  font-size: 14px;
}

.btn-primary {
  background-color: #5a8849;
  color: white;
  border: none;
  padding: 12px 30px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  margin-top: 20px;
  transition: background-color 0.3s;
}

.btn-primary:hover {
  background-color: #4a6b38;
}

.btn-primary:active {
  transform: scale(0.98);
}
</style>
