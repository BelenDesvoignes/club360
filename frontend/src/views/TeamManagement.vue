<template>
  <div class="equipo-container">
    <div class="form-card">
      <header class="form-header">
        <h1>Registrar miembro del equipo</h1>
        <p>Añade un nuevo administrador o empleado al sistema.</p>
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

        <div class="input-group">
          <label>Rol</label>
          <select v-model="form.role">
            <option value="empleado">Empleado </option>
            <option value="admin">Administrador </option>
          </select>
        </div>

        <button type="submit" class="btn-submit" :disabled="loading">
          {{ loading ? 'Guardando...' : 'Crear usuario' }}
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
  password: '',
  role: 'empleado'
})

const loading = ref(false)
const message = ref('')
const messageType = ref('')

const handleSubmit = async () => {
  loading.value = true
  message.value = ''

  try {
    // 1. Obtenemos la URL de la variable de entorno
    // Si no existe (por ejemplo en local), usamos el localhost por defecto
    const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

   const response = await axios.post(`${apiBaseUrl}/admin/crear-equipo`, form.value)

    message.value = '¡Miembro del equipo creado con éxito!'
    messageType.value = 'success'

    // Limpiar formulario tras éxito
    form.value = {
      first_name: '',
      last_name: '',
      dni: '',
      email: '',
      password: '',
      role: 'employee'
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
.equipo-container {
  padding: 40px 20px;
  display: flex;
  justify-content: center;
  background-color: #f8f9fa;
  min-height: calc(100vh - 60px);
}

.form-card {
  background: white;
  padding: 40px;
  border-radius: 20px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
  width: 100%;
  max-width: 550px;
}

.form-header {
  text-align: center;
  margin-bottom: 30px;
}

.form-header h1 {
  color: #0d124a;
  font-size: 1.8rem;
  margin: 0;
  font-weight: 800;
}

.form-header p {
  color: #7f8c8d;
  font-size: 0.95rem;
  margin-top: 8px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.input-group {
  margin-bottom: 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

label {
  font-weight: 700;
  font-size: 0.85rem;
  color: #2c3e50;
  margin-left: 4px;
}

input, select {
  padding: 12px 15px;
  border: 2px solid #edf2f7;
  border-radius: 12px;
  font-size: 1rem;
  transition: all 0.3s ease;
  outline: none;
}

input:focus, select:focus {
  border-color: #ff6f00;
  background-color: #fff;
  box-shadow: 0 0 0 4px rgba(255, 111, 0, 0.1);
}

.btn-submit {
  width: 100%;
  padding: 15px;
  background: linear-gradient(135deg, #0d124a 0%, #1a237e 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-top: 15px;
}

.btn-submit:hover:not(:disabled) {
  background: #ff6f00;
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(255, 111, 0, 0.3);
}

.btn-submit:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.alert {
  margin-top: 20px;
  padding: 12px;
  border-radius: 10px;
  text-align: center;
  font-size: 0.9rem;
  font-weight: 600;
}

.success {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

/* Responsivo */
@media (max-width: 480px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  .form-card {
    padding: 25px;
  }
}
</style>