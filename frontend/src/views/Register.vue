<template>
  <div class="page">
    <div class="card" aria-label="Registro">
      <div class="card-header" aria-hidden="true">
        <div class="brand">CLUB360</div>
      </div>

      <div class="card-body">
        <h1>Registrate</h1>
        <p class="subtitle">Completá tus datos para crear tu cuenta.</p>

        <form @submit.prevent="enviarRegistro" novalidate>
          <div class="two-col">
            <label class="field">
              <span class="label">Nombre</span>
              <div class="control">
                <span class="icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 12C14.2091 12 16 10.2091 16 8C16 5.79086 14.2091 4 12 4C9.79086 4 8 5.79086 8 8C8 10.2091 9.79086 12 12 12Z" stroke="currentColor" stroke-width="1.8" />
                    <path d="M4.5 20C5.6 17 8.5 15 12 15C15.5 15 18.4 17 19.5 20" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                  </svg>
                </span>
                <input v-model.trim="usuario.first_name" type="text" autocomplete="given-name" placeholder="Nombre" required />
              </div>
            </label>

            <label class="field">
              <span class="label">Apellido</span>
              <div class="control">
                <span class="icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 12C14.2091 12 16 10.2091 16 8C16 5.79086 14.2091 4 12 4C9.79086 4 8 5.79086 8 8C8 10.2091 9.79086 12 12 12Z" stroke="currentColor" stroke-width="1.8" />
                    <path d="M4.5 20C5.6 17 8.5 15 12 15C15.5 15 18.4 17 19.5 20" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                  </svg>
                </span>
                <input v-model.trim="usuario.last_name" type="text" autocomplete="family-name" placeholder="Apellido" required />
              </div>
            </label>
          </div>

          <label class="field">
            <span class="label">DNI</span>
            <div class="control">
              <span class="icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M7 4H17C18.1046 4 19 4.89543 19 6V18C19 19.1046 18.1046 20 17 20H7C5.89543 20 5 19.1046 5 18V6C5 4.89543 5.89543 4 7 4Z" stroke="currentColor" stroke-width="1.8" />
                  <path d="M8 8H16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                  <path d="M8 12H13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                </svg>
              </span>
              <input v-model.trim="usuario.dni" type="text" inputmode="numeric" autocomplete="off" placeholder="DNI (sin puntos)" required />
            </div>
          </label>

          <label class="field">
            <span class="label">Correo Electrónico</span>
            <div class="control">
              <span class="icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M4 6.5C4 5.67157 4.67157 5 5.5 5H18.5C19.3284 5 20 5.67157 20 6.5V17.5C20 18.3284 19.3284 19 18.5 19H5.5C4.67157 19 4 18.3284 4 17.5V6.5Z" stroke="currentColor" stroke-width="1.8" />
                  <path d="M5 7L12 12L19 7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              </span>
              <input v-model.trim="usuario.email" type="email" autocomplete="email" placeholder="email@club.com" required />
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
              <input v-model="usuario.password" type="password" autocomplete="new-password" placeholder="••••••••" required />
            </div>
          </label>

          <button class="primary" type="submit" :disabled="cargando">
            {{ cargando ? 'Procesando...' : 'Crear cuenta' }}
          </button>
        </form>

        <div v-if="mensaje" :class="['alert', esError ? 'error' : 'success']" role="alert">
          {{ mensaje }}
        </div>

        <div class="divider" aria-hidden="true"><span>o</span></div>

        <p class="back">¿Ya tenés cuenta? <router-link to="/login">Iniciar sesión</router-link></p>
        <p class="back"><router-link to="/">← Volver</router-link></p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const usuario = ref({ first_name: '', last_name: '', dni: '', email: '', password: '' })
const mensaje = ref('')
const esError = ref(false)
const cargando = ref(false)

const enviarRegistro = async () => {
  cargando.value = true
  mensaje.value = ''
  try {
    await axios.post('/auth/register', usuario.value)
    esError.value = false
    mensaje.value = 'Registro exitoso.'
    usuario.value = { first_name: '', last_name: '', dni: '', email: '', password: '' }
  } catch (error) {
    esError.value = true
    mensaje.value = error.response?.data?.detail || 'Error al conectar con el servidor'
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
  max-width: 420px;
  background: #ffffff;
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.28);
}

.card-header {
  position: relative;
  height: 105px;
  background: #ffffff;
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
  color: #2d658d;
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

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

@media (max-width: 460px) {
  .two-col {
    grid-template-columns: 1fr;
  }
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

.primary {
  width: 100%;
  padding: 12px;
  background: #2d658d;
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
}

.error {
  background: #fadbd8;
  color: #c0392b;
}

.success {
  background: #d4efdf;
  color: #27ae60;
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
  color: #2d658d;
  font-weight: 700;
  text-decoration: none;
  touch-action: manipulation;
}
</style>