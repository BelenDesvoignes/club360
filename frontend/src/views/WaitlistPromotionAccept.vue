<template>
  <div class="waitlist-promotion-container">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Procesando tu aceptación...</p>
    </div>

    <!-- Success State -->
    <div v-else-if="success" class="success-state">
      <div class="icon-success">✓</div>
      <h2>¡Cupo confirmado!</h2>
      <p>Tu reserva ha sido confirmada exitosamente.</p>
      <p class="class-details" v-if="booking">
        <strong>{{ booking.activity_name }}</strong><br>
        {{ booking.date }} - {{ booking.time }} hs
      </p>
      <button @click="goToDashboard" class="btn-primary">
        Ir a mis reservas
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
  name: 'WaitlistPromotionAccept',
  setup() {
    const router = useRouter()
    const route = useRoute()
    const loading = ref(true)
    const success = ref(false)
    const error = ref(null)
    const booking = ref(null)

    onMounted(async () => {
      try {
        const token = route.params.token
        if (!token) {
          error.value = 'Token inválido'
          loading.value = false
          return
        }

        // Llamar al endpoint de aceptación
        const response = await api.post(`/waiting-lists/accept/${token}`)
        
        booking.value = response.data
        success.value = true
        loading.value = false

        // Redirigir automáticamente después de 5 segundos
        setTimeout(() => {
          goToDashboard()
        }, 5000)
      } catch (err) {
        console.error('Error aceptando promoción:', err)
        error.value = err.response?.data?.detail || 'Error al procesar la aceptación'
        loading.value = false
      }
    })

    const goToDashboard = () => {
      router.push('/reservas')
    }

    const goHome = () => {
      router.push('/')
    }

    return {
      loading,
      success,
      error,
      booking,
      goToDashboard,
      goHome
    }
  }
}
</script>

<style scoped>
.waitlist-promotion-container {
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

.class-details {
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
