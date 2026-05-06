<template>
  <div class="container">
    <div class="card">
      <h1>¡Hola de nuevo! 👋</h1>
      <p class="subtitle">Ingresa a CLUB360</p>

      <form @submit.prevent="handleLogin">
        <input
          v-model="credenciales.email"
          type="email"
          placeholder="Tu correo"
          required
        />
        <input
          v-model="credenciales.password"
          type="password"
          placeholder="Tu contraseña"
          required
        />

        <button type="submit" :disabled="cargando">
          {{ cargando ? 'Validando...' : 'Entrar' }}
        </button>
      </form>

      <div v-if="error" class="alert error">
        {{ error }}
      </div>

      <p class="back">
        ¿No tienes cuenta? <router-link to="/register">Regístrate</router-link>
      </p>
      <p class="back"><router-link to="/">← Volver al inicio</router-link></p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

const credenciales = ref({ email: '', password: '' })
const cargando = ref(false)
const error = ref('')

const handleLogin = async () => {
  cargando.value = true
  error.value = ''
  try {
    const exito = await auth.login(credenciales.value.email, credenciales.value.password)
    if (exito) {
      // Redirigir según el rol o a una página de inicio
      router.push('/')
    }
  } catch (err) {
    error.value = err
  } finally {
    cargando.value = false
  }
}
</script>

<style scoped>
/* Reutilizamos tus estilos del registro para mantener coherencia */
.container { display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #1a237e; font-family: 'Segoe UI', sans-serif; }
.card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); width: 100%; max-width: 350px; text-align: center; }
input { width: 100%; padding: 12px; margin-bottom: 1rem; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }
button { width: 100%; padding: 12px; background: #ff6f00; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; }
button:disabled { background: #ccc; }
.alert { margin-top: 1rem; padding: 10px; border-radius: 6px; font-size: 0.9rem; background: #fadbd8; color: #c0392b; }
.back { margin-top: 1rem; font-size: 0.9rem; }
.back a { color: #1a237e; font-weight: bold; text-decoration: none; }
</style>