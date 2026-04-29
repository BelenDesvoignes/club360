<template>
  <div class="container">
    <div class="card">
      <h1>Socio nuevo 🤝</h1>
      <p class="subtitle">Registrate en CLUB360</p>

      <form @submit.prevent="enviarRegistro">
        <div class="form-row">
          <input v-model="usuario.first_name" type="text" placeholder="Nombre" required />
          <input v-model="usuario.last_name" type="text" placeholder="Apellido" required />
        </div>
        <input v-model="usuario.dni" type="text" placeholder="DNI (sin puntos)" required />
        <input v-model="usuario.email" type="email" placeholder="Correo electrónico" required />
        <input v-model="usuario.password" type="password" placeholder="Contraseña" required />
        <button type="submit" :disabled="cargando">
          {{ cargando ? 'Procesando...' : 'Crear cuenta' }}
        </button>
      </form>

      <div v-if="mensaje" :class="['alert', esError ? 'error' : 'success']">
        {{ mensaje }}
      </div>

      <p class="back"><router-link to="/">← Volver</router-link></p>
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
    const res = await axios.post('/auth/register', usuario.value)
    esError.value = false
    mensaje.value = ` Registro exitoso.`
    usuario.value = { first_name: '', last_name: '', dni: '', email: '', password: '' }
  } catch (error) {
    esError.value = true
    mensaje.value = error.response?.data?.detail || "Error al conectar con el servidor"
  } finally {
    cargando.value = false
  }
}
</script>

<style scoped>
.container { display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #08116d; font-family: 'Segoe UI', sans-serif; }
.card { background: rgb(239, 239, 239); padding: 2rem; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 100%; max-width: 400px; margin: 1rem; }
h1 { color: #2c3e50; margin-bottom: 0.5rem; text-align: center; }
.subtitle { text-align: center; color: #7f8c8d; margin-bottom: 1.5rem; }
.form-row { display: flex; gap: 10px; }
input { width: 100%; padding: 12px; margin-bottom: 1rem; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }
button { width: 100%; padding: 12px; background: #ff6f00; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; transition: background 0.3s; }
button:hover { background: #e65100; }
button:disabled { background: #95a5a6; }
.alert { margin-top: 1rem; padding: 10px; border-radius: 6px; text-align: center; font-size: 0.9rem; }
.error { background: #fadbd8; color: #c0392b; }
.success { background: #d4efdf; color: #27ae60; }
.back { text-align: center; margin-top: 1rem; }
.back a { color: #1a237e; text-decoration: none; }
</style>