<template>
  <div class="container">
    <div class="card">
      <h1>Socio Nuevo 🤝</h1>
      <p class="subtitle">Registrate en CLUB360</p>

      <form @submit.prevent="enviarRegistro">
        <div class="form-row">
          <input v-model="usuario.first_name" type="text" placeholder="Nombre" required />
          <input v-model="usuario.last_name" type="text" placeholder="Apellido" required />
        </div>

        <input v-model="usuario.dni" type="text" placeholder="DNI (sin puntos)" required />
        <input v-model="usuario.email" type="email" placeholder="Correo Electrónico" required />
        <input v-model="usuario.password" type="password" placeholder="Contraseña segura" required />

        <button type="submit" :disabled="cargando">
          {{ cargando ? 'Procesando...' : 'Crear Cuenta' }}
        </button>
      </form>

      <div v-if="mensaje" :class="['alert', esError ? 'error' : 'success']">
        {{ mensaje }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

// Variables reactivas (necesarias para que Vue "escuche" los cambios)
const usuario = ref({
  first_name: '',
  last_name: '',
  dni: '',
  email: '',
  password: ''
})

const mensaje = ref('')
const esError = ref(false)
const cargando = ref(false)

const enviarRegistro = async () => {
  cargando.value = true
  mensaje.value = ''

  try {
    // Como definimos la baseURL en main.js, aquí solo ponemos la ruta relativa
    const res = await axios.post('/auth/register', usuario.value)

    esError.value = false
    mensaje.value = `¡Bienvenido ${res.data.first_name}! Registro exitoso.`

    // Limpiamos el formulario tras el éxito
    usuario.value = { first_name: '', last_name: '', dni: '', email: '', password: '' }

  } catch (error) {
    esError.value = true
    // Captura el mensaje de error que definimos en el backend (ej: "DNI already exists")
    mensaje.value = error.response?.data?.detail || "Error al conectar con el servidor"
  } finally {
    cargando.value = false
  }
}
</script>

<style>
/* Tus estilos actuales */
.container { display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #f4f7f6; font-family: 'Segoe UI', sans-serif; }
.card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }
h1 { color: #2c3e50; margin-bottom: 0.5rem; text-align: center; }
.subtitle { text-align: center; color: #7f8c8d; margin-bottom: 1.5rem; }
.form-row { display: flex; gap: 10px; }
input { width: 100%; padding: 12px; margin-bottom: 1rem; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }
button { width: 100%; padding: 12px; background: #42b983; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; transition: background 0.3s; }
button:hover { background: #3aa876; }
button:disabled { background: #95a5a6; }
.alert { margin-top: 1rem; padding: 10px; border-radius: 6px; text-align: center; font-size: 0.9rem; }
.error { background: #fadbd8; color: #c0392b; }
.success { background: #d4efdf; color: #27ae60; }
</style>