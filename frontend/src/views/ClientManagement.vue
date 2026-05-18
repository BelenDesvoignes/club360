<template>
  <div class="equipo-container">
    <div class="form-card">
      <header class="form-header">
        <h1>Registrar cliente</h1>
        <p>Crea una cuenta para un cliente (puede hacerlo un administrador o empleado).</p>
      </header>

      <form @submit.prevent="handleSubmit" class="equipo-form">
        <div class="form-grid">
          <div class="input-group">
            <label>Nombre</label>
            <input v-model="form.first_name" type="text" placeholder="" required />
          </div>
          <div class="input-group">
            <label>Apellido</label>
            <input v-model="form.last_name" type="text" placeholder="" required />
          </div>
        </div>

        <div class="input-group">
          <label>DNI (sin puntos)</label>
          <input v-model="form.dni" type="text" placeholder="" required />
        </div>

        <div class="input-group">
          <label>Correo electrónico</label>
          <input v-model="form.email" type="email" placeholder="" required />
        </div>

        <div class="input-group">
          <label>Contraseña</label>
          <input v-model="form.password" type="password" placeholder="" required />
        </div>

        <button type="submit" class="btn-submit" :disabled="loading">
          {{ loading ? 'Guardando...' : 'Crear cliente' }}
        </button>

        <div v-if="message" :class="['alert', messageType]">
          {{ message }}
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const form = ref({
  first_name: '',
  last_name: '',
  dni: '',
  email: '',
  password: ''
})

const loading = ref(false)
const message = ref('')
const messageType = ref('')

const handleSubmit = async () => {
  loading.value = true
  message.value = ''

  try {
    const response = await axios.post('/admin/crear-cliente', form.value)

    message.value = 'Cliente creado con éxito.'
    messageType.value = 'success'

    form.value = {
      first_name: '',
      last_name: '',
      dni: '',
      email: '',
      password: ''
    }
  } catch (error) {
    messageType.value = 'error'
    message.value = error.response?.data?.detail || 'Error al conectar con el servidor'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* Reuso de estilos de TeamManagement */
.equipo-container {
  position: relative;
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 60px 20px;
  background: #ffffff;
  font-family: 'Segoe UI', Roboto, sans-serif;
}

.equipo-container::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 300px;
  background: #2d658d;
  z-index: 0;
}

.form-card {
  position: relative;
  z-index: 1;
  background: white;
  padding: 40px;
  border-radius: 18px;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.15);
  width: 100%;
  max-width: 500px;
}

.form-header { text-align: center; margin-bottom: 30px }
.form-header h1 { color: #111827; font-size: 24px; margin: 0; font-weight: 800 }
.form-header p { color: #6b7280; font-size: 14px; margin-top: 8px }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px }
.input-group { margin-bottom: 18px; display: flex; flex-direction: column; text-align: left }
label { display: block; font-size: 12px; font-weight: 600; color: #374151; margin-bottom: 6px; margin-left: 2px }
input { padding: 12px 15px; border: 1px solid #e5e7eb; border-radius: 10px; font-size: 15px; transition: all 0.3s ease; outline: none; background: #ffffff; color: #111827 }
input:focus { border-color: #ff6f00; box-shadow: 0 0 0 3px rgba(255, 111, 0, 0.1) }
.btn-submit { width: 100%; padding: 14px; background: #ff6f00; color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 800; cursor: pointer; transition: all 0.2s; margin-top: 10px; text-transform: uppercase; letter-spacing: 1px }
.btn-submit:disabled { background: #d1d5db; cursor: not-allowed }
.alert { margin-top: 20px; padding: 15px; border-radius: 12px; text-align: center }
.alert.success { background: #ecfdf5; color: #065f46 }
.alert.error { background: #fff1f2; color: #9f1239 }

</style>
