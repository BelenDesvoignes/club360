<template>
  <div class="page">
    <div class="card" aria-label="Inicio de sesión">
      <div class="card-header" aria-hidden="true">
        <div class="brand">CLUB360</div>
      </div>

      <div class="card-body">
        <h1>¡Bienvenido!</h1>
        <p class="subtitle">Por favor, ingresa tus datos para iniciar sesión.</p>

        <form @submit.prevent="handleLogin" novalidate>
          <label class="field">
            <span class="label">Correo Electrónico</span>
            <div class="control">
              <span class="icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M4 6.5C4 5.67157 4.67157 5 5.5 5H18.5C19.3284 5 20 5.67157 20 6.5V17.5C20 18.3284 19.3284 19 18.5 19H5.5C4.67157 19 4 18.3284 4 17.5V6.5Z" stroke="currentColor" stroke-width="1.8" />
                  <path d="M5 7L12 12L19 7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              </span>
              <input
                v-model.trim="credenciales.email"
                type="email"
                autocomplete="email"
                placeholder="email@club.com"
                required
              />
            </div>
          </label>

          <label class="field">
            <span class="label">Contraseña</span>
            <div class="control">
              <span class="icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M7 11V8.8C7 6.14903 9.23858 4 12 4C14.7614 4 17 6.14903 17 8.8V11" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                  <path d="M6.5 11H17.5C18.6046 11 19.5 11.8954 19.5 13V19C19.5 20.1046 18.6046 21 17.5 21H6.5C5.39543 21 4.5 20.1046 4.5 19V13C4.5 11.8954 5.39543 11 6.5 11Z" stroke="currentColor" stroke-width="1.8" />
                </svg>
              </span>

              <input
                v-model="credenciales.password"
                :type="verPassword ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="••••••••"
                required
              />

              <button
                class="icon-button"
                type="button"
                @click="verPassword = !verPassword"
                :aria-label="verPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'"
              >
                <svg v-if="!verPassword" viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M2 12C4.4 7.5 8 5 12 5C16 5 19.6 7.5 22 12C19.6 16.5 16 19 12 19C8 19 4.4 16.5 2 12Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
                  <path d="M12 15C13.6569 15 15 13.6569 15 12C15 10.3431 13.6569 9 12 9C10.3431 9 9 10.3431 9 12C9 13.6569 10.3431 15 12 15Z" stroke="currentColor" stroke-width="1.8" />
                </svg>
                <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M3 3L21 21" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                  <path d="M10.5 10.7C10.2 11.1 10 11.5 10 12C10 13.1 10.9 14 12 14C12.5 14 12.9 13.8 13.3 13.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                  <path d="M6.2 6.7C4.5 7.9 3.1 9.7 2 12C4.4 16.5 8 19 12 19C13.7 19 15.3 18.5 16.8 17.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                  <path d="M9.8 5.3C10.5 5.1 11.2 5 12 5C16 5 19.6 7.5 22 12C21.2 13.6 20.2 15 19 16.1" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              </button>
            </div>
          </label>

          <a class="forgot" href="#" @click.prevent="mostrarRecupero = true">
              ¿Olvidaste tu contraseña?
          </a>
          <button class="primary" type="submit" :disabled="cargando">
            {{ cargando ? 'Validando...' : 'Iniciar Sesión' }}
          </button>
        </form>
        <ForgotPassword v-if="mostrarRecupero" @close="mostrarRecupero = false" />

        <div v-if="error" class="alert error" role="alert">{{ error }}</div>

        <div class="divider" aria-hidden="true"><span>o</span></div>

        <p class="back">
          ¿Sos nuevo en CLUB360? <router-link to="/register">Registrate</router-link>
        </p>
        <p class="back"><router-link to="/">← Volver al inicio</router-link></p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'
import ForgotPassword from '../components/ForgotPassword.vue'

const mostrarRecupero = ref(false)

const auth = useAuthStore()
const router = useRouter()

const credenciales = ref({ email: '', password: '' })
const cargando = ref(false)
const error = ref('')
const verPassword = ref(false)

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
    error.value = err?.response?.data?.detail || err?.message || 'Error al iniciar sesión'
  } finally {
    cargando.value = false
  }
}
</script>

<style scoped>
.page {
  position: relative;
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  background: #ffffff;
  font-family: 'Segoe UI', sans-serif;
}

.page::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: clamp(220px, 32vh, 360px);
  background: #2d658d;
  z-index: 0;
}

.card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 380px;
  background: #ffffff;
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.28);
}

.card-header {
  position: relative;
  height: 105px;
  background: #ffffff ;
}

.brand {
  position: absolute;
  left: 0;
  right: 0;
  top: 38px;
  text-align: center;
  font-weight: 800;
  letter-spacing: 4px;
  font-size: 28px;
  color: #5a8849;
  user-select: none;
}

.card-body {
  padding: 18px 18px 20px;
  text-align: center;
}

h1 {
  margin: 0px 0 8px;
  font-size: 31px;
  color: #111827;
}

.subtitle {
  margin: 0 0 16px;
  color: #6b7280;
  font-size: 14px;
}

.field {
  display: block;
  text-align: left;
  margin-bottom: 12px;
}

.label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 6px;
}

.control {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px 12px;
  background: #ffffff;
}

.icon {
  color: #9ca3af;
  display: inline-flex;
}

input {
  width: 100%;
  border: none;
  outline: none;
  padding: 0;
  margin: 0;
  background: transparent;
  color: #111827;
  font-size: 16px; /* evita zoom/doble tap en iOS */
}

input::placeholder {
  color: #9ca3af;
}

.icon-button {
  border: none;
  background: transparent;
  color: #9ca3af;
  padding: 6px;
  margin: -6px;
  cursor: pointer;
  touch-action: manipulation;
}

.forgot {
  display: inline-block;
  margin: 4px 0 12px;
  font-size: 12px;
  color: #1a237e;
  text-decoration: none;
  font-weight: 600;
  touch-action: manipulation;
}

.primary {
  width: 100%;
  padding: 12px;
  background: #ff6f00;
  color: white;
  border: none;
  border-radius: 10px;
  font-weight: 800;
  cursor: pointer;
  touch-action: manipulation;
}

.primary:disabled {
  background: #c7c7c7;
  cursor: not-allowed;
}

.alert {
  margin-top: 12px;
  padding: 10px;
  border-radius: 10px;
  font-size: 0.9rem;
  background: #fadbd8;
  color: #c0392b;
}

.divider {
  position: relative;
  margin: 16px 0 12px;
  height: 1px;
  background: #e5e7eb;
}

.divider span {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  background: #ffffff;
  padding: 0 10px;
  font-size: 12px;
  color: #9ca3af;
}

.back {
  margin: 10px 0 0;
  font-size: 12px;
  color: #374151;
}

.back a {
  color: #1a237e;
  font-weight: 700;
  text-decoration: none;
  touch-action: manipulation;
}
</style>