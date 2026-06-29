<template>
  <div class="profile-page">
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Cuenta personal</p>
        <h1>Mi perfil</h1>
        <p class="hero-text">
          Revisá tus datos personales y editarlos de forma general si lo necesitás.
        </p>
      </div>
    </section>

    <section class="content-grid">
      <article class="panel">
        <div class="panel-header">
          <div>
            <p class="panel-kicker">Datos de usuario</p>
            <h3>Tu información</h3>
          </div>

          <div class="header-actions">
            <button
              v-if="!isEditing"
              @click="startEdit"
              class="header-btn edit-btn"
            >
              Editar
            </button>

            <template v-else>
              <button
                @click="saveProfile"
                class="header-btn save-profile-btn"
                :disabled="saving"
              >
                Guardar
              </button>
              <button
                @click="cancelEdit"
                class="header-btn cancel-profile-btn"
                :disabled="saving"
              >
                Cancelar
              </button>
            </template>
          </div>
        </div>

        <div class="info-list">
          <div class="profile-row">
            <div class="row-header">
              <dt>Nombre</dt>
            </div>
            <dd>
              <input
                v-if="isEditing"
                v-model.trim="form.first_name"
                type="text"
                placeholder="Escribí tu nombre"
              />
              <span v-else class="display-value">{{ userData.first_name || '—' }}</span>
            </dd>
          </div>

          <div class="profile-row">
            <div class="row-header">
              <dt>Apellido</dt>
            </div>
            <dd>
              <input
                v-if="isEditing"
                v-model.trim="form.last_name"
                type="text"
                placeholder="Escribí tu apellido"
              />
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
            </div>
            <dd>
              <input
                v-if="isEditing"
                v-model.trim="form.email"
                type="email"
                placeholder="ejemplo@gmail.com"
              />
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
const isEditing = ref(false)

const userData = ref({
  first_name: '',
  last_name: '',
  dni: '',
  email: ''
})

const form = ref({
  first_name: '',
  last_name: '',
  email: ''
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
    console.error('Error al traer datos reales del backend:', e)
    message.value = 'No se pudieron cargar tus datos de usuario.'
    isError.value = true
  }
}

const startEdit = () => {
  message.value = ''
  isError.value = false

  form.value.first_name = userData.value.first_name || ''
  form.value.last_name = userData.value.last_name || ''
  form.value.email = userData.value.email || ''

  isEditing.value = true
}

const cancelEdit = () => {
  isEditing.value = false
  message.value = ''
  isError.value = false
}

const saveProfile = async () => {
  message.value = ''
  isError.value = false

  const { first_name, last_name, email } = form.value

  // Validaciones
  if (!first_name || !last_name || !email) {
    message.value = 'Debe completar todos los campos.'
    isError.value = true
    return
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(email) || email.includes(' ')) {
    message.value = 'El formato del correo electrónico no es válido.'
    isError.value = true
    return
  }

  // Si no hubo cambios, cerramos edición
  if (
    first_name === userData.value.first_name &&
    last_name === userData.value.last_name &&
    email === userData.value.email
  ) {
    isEditing.value = false
    return
  }

  saving.value = true
  try {
    const payload = {
      first_name,
      last_name,
      email
    }

    await auth.updateProfile(payload)
    await fetchUserData()

    message.value = '¡Modificación realizada correctamente!'
    isError.value = false
    isEditing.value = false
  } catch (error) {
    const errorDetail = error?.response?.data?.detail
    message.value =
      typeof errorDetail === 'string'
        ? errorDetail
        : 'Error al intentar actualizar.'
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
.profile-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 28px 24px 36px;
  display: grid;
  gap: 22px;
}

.hero {
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid rgba(45, 101, 141, 0.12);
  border-radius: 24px;
  box-shadow: 0 18px 45px rgba(13, 18, 74, 0.08);
  padding: 32px;
}

.eyebrow,
.panel-kicker {
  margin: 0 0 10px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  font-size: 0.72rem;
  font-weight: 800;
  color: #2d658d;
}

.hero h1,
.panel-header h3 {
  margin: 0;
  color: #0d124a;
}

.hero h1 {
  font-size: clamp(2rem, 4vw, 2.8rem);
  line-height: 1.1;
}

.hero-text {
  margin: 14px 0 0;
  color: rgba(13, 18, 74, 0.72);
  font-size: 1rem;
}

.panel {
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid rgba(45, 101, 141, 0.12);
  border-radius: 24px;
  box-shadow: 0 18px 45px rgba(13, 18, 74, 0.08);
  padding: 26px;
}

.panel-header {
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.header-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.header-btn {
  border: none;
  border-radius: 10px;
  padding: 10px 16px;
  font-weight: 700;
  cursor: pointer;
}

.edit-btn {
  background: rgba(45, 101, 141, 0.12);
  color: #0d124a;
}

.save-profile-btn {
  background: rgba(16, 185, 129, 0.16);
  color: #065f46;
}

.cancel-profile-btn {
  background: rgba(239, 68, 68, 0.15);
  color: #991b1b;
}

.info-list {
  display: grid;
  gap: 16px;
}

.profile-row {
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.92);
  border-radius: 18px;
  border: 1px solid rgba(45, 101, 141, 0.1);
  box-shadow: 0 10px 24px rgba(13, 18, 74, 0.04);
  display: grid;
  gap: 6px;
}

.static-row {
  background: rgba(240, 244, 248, 0.6);
}

.row-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-list dt {
  margin: 0;
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: rgba(13, 18, 74, 0.52);
  font-weight: 800;
}

.info-list dd {
  margin: 0;
}

.display-value {
  color: #0d124a;
  font-weight: 700;
  font-size: 1.1rem;
}

.static-text {
  color: #2d658d;
}

.profile-row input {
  width: 100%;
  border: 1px solid #2d658d;
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 1rem;
  color: #0d124a;
  font-weight: 700;
  outline: none;
}

.message {
  margin-top: 12px;
  padding: 14px 16px;
  border-radius: 16px;
  font-weight: 700;
}

.message.success {
  background: rgba(16, 185, 129, 0.12);
  color: #065f46;
}

.message.error {
  background: rgba(239, 68, 68, 0.1);
  color: #991b1b;
}
</style>