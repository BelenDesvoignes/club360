<template>
  <div class="profile-page">
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Cuenta personal</p>
        <h1>Mi perfil</h1>
        <p class="hero-text">Revisá tus datos personales y editalos de forma individual si lo necesitás.</p>
      </div>
    </section>

    <section class="content-grid">
      <article class="panel">
        <div class="panel-header">
          <div>
            <p class="panel-kicker">Datos de usuario</p>
            <h3>Tu información</h3>
          </div>
        </div>

        <div class="info-list">
          
          <div class="profile-row">
            <div class="row-header">
              <dt>Nombre</dt>
              <button 
                v-if="!editing.first_name" 
                @click="startEdit('first_name')" 
                class="edit-icon-btn"
                title="Editar nombre"
              >
                ✏️
              </button>
            </div>
            <dd>
              <div v-if="editing.first_name" class="edit-input-group">
                <input v-model.trim="form.first_name" type="text" placeholder="Escribí tu nombre" />
                <button @click="saveField('first_name')" class="action-btn save-btn" :disabled="saving">✔️</button>
                <button @click="cancelEdit('first_name')" class="action-btn cancel-btn">❌</button>
              </div>
              <span v-else class="display-value">{{ userData.first_name || '—' }}</span>
            </dd>
          </div>
          
          <div class="profile-row">
            <div class="row-header">
              <dt>Apellido</dt>
              <button 
                v-if="!editing.last_name" 
                @click="startEdit('last_name')" 
                class="edit-icon-btn"
                title="Editar apellido"
              >
                ✏️
              </button>
            </div>
            <dd>
              <div v-if="editing.last_name" class="edit-input-group">
                <input v-model.trim="form.last_name" type="text" placeholder="Escribí tu apellido" />
                <button @click="saveField('last_name')" class="action-btn save-btn" :disabled="saving">✔️</button>
                <button @click="cancelEdit('last_name')" class="action-btn cancel-btn">❌</button>
              </div>
              <span v-else class="display-value">{{ userData.last_name || '—' }}</span>
            </dd>
          </div>
          
          <div class="profile-row static-row">
            <div class="row-header">
              <dt>DNI (No editable)</dt>
            </div>
            <dd>
              <span class="display-value static-text">{{ userData.dni || '—' }}</span>
            </dd>
          </div>
          
          <div class="profile-row">
            <div class="row-header">
              <dt>Correo electrónico</dt>
              <button 
                v-if="!editing.email" 
                @click="startEdit('email')" 
                class="edit-icon-btn"
                title="Editar correo"
              >
                ✏️
              </button>
            </div>
            <dd>
              <div v-if="editing.email" class="edit-input-group">
                <input v-model.trim="form.email" type="email" placeholder="ejemplo@gmail.com" />
                <button @click="saveField('email')" class="action-btn save-btn" :disabled="saving">✔️</button>
                <button @click="cancelEdit('email')" class="action-btn cancel-btn">❌</button>
              </div>
              <span v-else class="display-value">{{ userData.email || '—' }}</span>
            </dd>
          </div>
        </div>

      </article>
    </section>

    <div v-if="message" :class="['message', isError ? 'error' : 'success']">
      {{ message }}
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import axios from 'axios'

const auth = useAuthStore()
const saving = ref(false)
const message = ref('')
const isError = ref(false)

const userData = ref({
  first_name: '',
  last_name: '',
  dni: '',
  email: ''
})

const editing = ref({
  first_name: false,
  last_name: false,
  email: false
})

const form = ref({
  first_name: '',
  last_name: '',
  email: '',
})

const fetchUserData = async () => {
  try {
    if (auth.refreshUser) {
      await auth.refreshUser()
    }
    
    if (auth.user && auth.user.first_name) {
      userData.value = auth.user
    } else {
      const token = localStorage.getItem('token') || auth.token
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      
      const response = await axios.get(`${apiUrl}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      if (response.data) {
        userData.value = response.data
        auth.user = response.data
      }
    }
  } catch (e) {
    console.error("Error al traer datos reales del backend:", e)
    message.value = "No se pudieron cargar tus datos de usuario."
    isError.value = true
  }
}

const startEdit = (field) => {
  message.value = ''
  isError.value = false
  
  Object.keys(editing.value).forEach(k => editing.value[k] = false)
  
  form.value.first_name = userData.value.first_name || ''
  form.value.last_name = userData.value.last_name || ''
  form.value.email = userData.value.email || ''
  
  editing.value[field] = true
}

const cancelEdit = (field) => {
  editing.value[field] = false
  message.value = ''
  isError.value = false
}

const saveField = async (field) => {
  message.value = ''
  isError.value = false

  const valueAEditar = form.value[field];

  // 1. VALIDACIÓN: Campo Vacío
  if (!valueAEditar || valueAEditar.length === 0) {
    message.value = 'Debe completar el campo.'
    isError.value = true
    return
  }

  // 2. VALIDACIÓN: Formato de Email Estricto
  if (field === 'email') {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(valueAEditar) || valueAEditar.includes(' ')) {
      message.value = 'El formato del correo electrónico no es válido.'
      isError.value = true
      return
    }
  }

  // Si el valor no cambió en absoluto, cerramos la edición sin hacer request
  if (valueAEditar === userData.value[field]) {
    editing.value[field] = false
    return
  }

  saving.value = true
  try {
    const payload = {
      first_name: field === 'first_name' ? form.value.first_name : userData.value.first_name,
      last_name: field === 'last_name' ? form.value.last_name : userData.value.last_name,
      email: field === 'email' ? form.value.email : userData.value.email,
    }

    await auth.updateProfile(payload)
    await fetchUserData()

    message.value = '¡Modificación realizada correctamente!'
    isError.value = false
    editing.value[field] = false
  } catch (error) {
    // CAPTURA EL COMENTARIO PRECISO DEL BACKEND (Ej: "Ya existe una cuenta con ese correo electrónico.")
    const errorDetail = error?.response?.data?.detail
    message.value = typeof errorDetail === 'string' ? errorDetail : 'Error al intentar actualizar.'
    isError.value = true
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchUserData()
})
</script>

<style scoped>
/* (Se mantiene el mismo estilo prolijo anterior) */
.profile-page { max-width: 800px; margin: 0 auto; padding: 28px 24px 36px; display: grid; gap: 22px; }
.hero { background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%); border: 1px solid rgba(45, 101, 141, 0.12); border-radius: 24px; box-shadow: 0 18px 45px rgba(13, 18, 74, 0.08); padding: 32px; }
.eyebrow, .panel-kicker { margin: 0 0 10px; text-transform: uppercase; letter-spacing: 0.16em; font-size: 0.72rem; font-weight: 800; color: #2d658d; }
.hero h1, .panel-header h3 { margin: 0; color: #0d124a; }
.hero h1 { font-size: clamp(2rem, 4vw, 2.8rem); line-height: 1.1; }
.hero-text { margin: 14px 0 0; color: rgba(13, 18, 74, 0.72); font-size: 1rem; }
.panel { background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%); border: 1px solid rgba(45, 101, 141, 0.12); border-radius: 24px; box-shadow: 0 18px 45px rgba(13, 18, 74, 0.08); padding: 26px; }
.panel-header { margin-bottom: 24px; }
.info-list { display: grid; gap: 16px; }
.profile-row { padding: 16px 20px; background: rgba(255, 255, 255, 0.92); border-radius: 18px; border: 1px solid rgba(45, 101, 141, 0.1); box-shadow: 0 10px 24px rgba(13, 18, 74, 0.04); display: grid; gap: 6px; }
.static-row { background: rgba(240, 244, 248, 0.6); }
.row-header { display: flex; justify-content: space-between; align-items: center; }
.info-list dt { margin: 0; font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.14em; color: rgba(13, 18, 74, 0.52); font-weight: 800; }
.info-list dd { margin: 0; }
.display-value { color: #0d124a; font-weight: 700; font-size: 1.1rem; }
.static-text { color: #2d658d; }
.edit-icon-btn { background: none; border: none; cursor: pointer; font-size: 1.1rem; padding: 4px; transition: transform 0.2s ease; }
.edit-icon-btn:hover { transform: scale(1.2); }
.edit-input-group { display: flex; gap: 8px; align-items: center; width: 100%; }
.edit-input-group input { flex: 1; border: 1px solid #2d658d; border-radius: 10px; padding: 8px 12px; font-size: 1rem; color: #0d124a; font-weight: 700; outline: none; }
.action-btn { border: none; border-radius: 10px; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 1rem; }
.save-btn { background-color: rgba(16, 185, 129, 0.15); }
.cancel-btn { background-color: rgba(239, 68, 68, 0.15); }
.message { margin-top: 12px; padding: 14px 16px; border-radius: 16px; font-weight: 700; }
.message.success { background: rgba(16, 185, 129, 0.12); color: #065f46; }
.message.error { background: rgba(239, 68, 68, 0.1); color: #991b1b; }
</style>