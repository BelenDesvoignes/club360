<template>
  <div class="profile-page">
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Cuenta personal</p>
        <h1>Mi perfil</h1>
        <p class="hero-text">Revisá tus datos y actualizá tu información personal cuando quieras.</p>
      </div>
    </section>

    <section class="content-grid">
      <article class="panel">
        <div class="panel-header">
          <div>
            <p class="panel-kicker">Datos visibles</p>
            <h3>Tu información</h3>
          </div>
        </div>

        <form @submit.prevent="saveProfile" class="info-list" novalidate>
          <div class="editable-row">
            <dt>Nombre</dt>
            <dd>
              <input 
                v-model.trim="form.first_name" 
                type="text" 
                placeholder="Tu nombre" 
              />
            </dd>
          </div>
          
          <div class="editable-row">
            <dt>Apellido</dt>
            <dd>
              <input 
                v-model.trim="form.last_name" 
                type="text" 
                placeholder="Tu apellido" 
              />
            </dd>
          </div>
          
          <div>
            <dt>DNI (No editable)</dt>
            <dd class="static-value">{{ auth.user?.dni || 'Sin dato' }}</dd>
          </div>
          
          <div class="editable-row">
            <dt>Correo electrónico</dt>
            <dd>
              <input 
                v-model.trim="form.email" 
                type="email" 
                placeholder="usuario@correo.com" 
              />
            </dd>
          </div>

          <div class="save-section-inline">
            <button type="submit" class="primary save-button" :disabled="saving">
              {{ saving ? 'Guardando...' : 'Guardar cambios' }}
            </button>
          </div>
        </form>
      </article>
    </section>

    <div v-if="message" :class="['message', isError ? 'error' : 'success']">
      {{ message }}
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const saving = ref(false)
const message = ref('')
const isError = ref(false)

const form = ref({
  first_name: '',
  last_name: '',
  email: '',
})

// Sincroniza los campos de texto basándose estrictamente en el usuario logueado en el Store
const syncForm = () => {
  if (auth.user) {
    form.value.first_name = auth.user.first_name || ''
    form.value.last_name = auth.user.last_name || ''
    form.value.email = auth.user.email || ''
  }
}

// Escucha activa de cambios en la sesión: si cambia de usuario, se actualizan los inputs al instante
watch(
  () => auth.user,
  (newUser) => {
    if (newUser) {
      syncForm()
    }
  },
  { deep: true, immediate: true }
)

const getReadableErrorMessage = (error) => {
  const data = error?.response?.data
  if (typeof data?.detail === 'string') {
    if (data.detail.includes("already exists") || data.detail.includes("Ya existe")) {
      return 'El correo electrónico ya está registrado. Por favor, usá otro.'
    }
    return data.detail
  }
  return 'No fue posible guardar los cambios. Revisá los datos ingresados.'
}

const validateForm = () => {
  if (!form.value.first_name) {
    message.value = 'El campo Nombre es obligatorio.'
    isError.value = true
    return false
  }
  if (!form.value.last_name) {
    message.value = 'El campo Apellido es obligatorio.'
    isError.value = true
    return false
  }
  if (form.value.first_name.length < 2) {
    message.value = 'El nombre debe tener al menos 2 caracteres.'
    isError.value = true
    return false
  }
  if (form.value.last_name.length < 2) {
    message.value = 'El apellido debe tener al menos 2 caracteres.'
    isError.value = true
    return false
  }
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(form.value.email)) {
    message.value = 'El formato del correo electrónico no es válido.'
    isError.value = true
    return false
  }
  return true
}

const saveProfile = async () => {
  message.value = ''
  isError.value = false

  if (
    auth.user &&
    form.value.first_name === auth.user.first_name &&
    form.value.last_name === auth.user.last_name &&
    form.value.email === auth.user.email
  ) {
    return
  }

  if (!validateForm()) return

  saving.value = true
  try {
    await auth.updateProfile({
      first_name: form.value.first_name,
      last_name: form.value.last_name,
      email: form.value.email,
    })
    
    if (auth.refreshUser) {
      await auth.refreshUser()
    }

    message.value = '¡Modificación realizada de manera correcta!'
    isError.value = false
  } catch (error) {
    message.value = getReadableErrorMessage(error)
    isError.value = true
    console.error("Error al guardar perfil:", error)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  if (auth.refreshUser) {
    await auth.refreshUser()
  }
  syncForm()
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
  position: relative;
  overflow: hidden;
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
  max-width: 58ch;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
}

.panel {
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid rgba(45, 101, 141, 0.12);
  border-radius: 24px;
  box-shadow: 0 18px 45px rgba(13, 18, 74, 0.08);
  padding: 26px;
}

.panel-header {
  margin-bottom: 20px;
}

.info-list {
  margin: 0;
  display: grid;
  gap: 14px;
}

.info-list > div, 
.info-list .editable-row {
  padding: 16px 18px;
  background: rgba(255, 255, 255, 0.92);
  border-radius: 18px;
  border: 1px solid rgba(45, 101, 141, 0.1);
  box-shadow: 0 10px 24px rgba(13, 18, 74, 0.04);
}

.info-list dt {
  margin: 0 0 4px;
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: rgba(13, 18, 74, 0.52);
  font-weight: 800;
}

.info-list dd {
  margin: 0;
  color: #0d124a;
  font-weight: 700;
  font-size: 1rem;
}

.static-value {
  padding: 4px 0;
  color: #2d658d !important;
}

.editable-row {
  display: grid;
  gap: 8px;
}

.editable-row input {
  width: 100%;
  border: 1px solid rgba(45, 101, 141, 0.18);
  border-radius: 14px;
  padding: 14px 16px;
  font-size: 1rem;
  color: #0d124a;
  background: #ffffff;
  outline: none;
}

.editable-row input:focus {
  border-color: #2d658d;
  box-shadow: 0 0 0 3px rgba(45, 101, 141, 0.14);
}

.primary {
  border: none;
  border-radius: 14px;
  padding: 14px 18px;
  font-weight: 800;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  background: linear-gradient(135deg, #2d658d, #0d124a);
  color: white;
  box-shadow: 0 16px 30px rgba(13, 18, 74, 0.18);
}

.primary:hover {
  transform: translateY(-1px);
}

.primary:disabled {
  opacity: 0.7;
  cursor: progress;
}

.message {
  margin-top: 4px;
  padding: 14px 16px;
  border-radius: 16px;
  font-weight: 700;
  box-shadow: 0 10px 22px rgba(13, 18, 74, 0.06);
}

.message.success {
  background: rgba(16, 185, 129, 0.12);
  color: #065f46;
}

.message.error {
  background: rgba(239, 68, 68, 0.1);
  color: #991b1b;
}

.save-section-inline {
  display: flex;
  justify-content: center;
  margin-top: 10px;
}

.save-button {
  min-width: min(100%, 280px);
}
</style>