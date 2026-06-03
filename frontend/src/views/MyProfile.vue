<template>
  <div class="profile-page">
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Cuenta personal</p>
        <h1>Mi perfil</h1>
        <p class="hero-text">Revisá tus datos, actualizá tu correo y cambiá tu foto de perfil cuando quieras.</p>
      </div>

      <div class="hero-card">
        <button class="avatar-button" type="button" @click="triggerFilePicker">
          <img v-if="avatarSrc" :src="avatarSrc" alt="Foto de perfil" class="avatar-image" />
          <div v-else class="avatar-fallback">{{ avatarInitials }}</div>
        </button>
        <input ref="fileInput" type="file" accept="image/*" class="hidden-input" @change="handleFileChange" />

        <div class="identity-block">
          <h2>{{ fullName }}</h2>
          <p>Perfil personal</p>
        </div>
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

        <dl class="info-list">
          <div>
            <dt>Nombre</dt>
            <dd>{{ profile.first_name || 'Sin dato' }}</dd>
          </div>
          <div>
            <dt>Apellido</dt>
            <dd>{{ profile.last_name || 'Sin dato' }}</dd>
          </div>
          <div>
            <dt>DNI</dt>
            <dd>{{ profile.dni || 'Sin dato' }}</dd>
          </div>
          <div class="editable-row">
            <dt>Correo electrónico</dt>
            <dd>
              <input v-model.trim="form.email" type="email" autocomplete="email" required />
            </dd>
          </div>
          <div>
            <dt>Rol</dt>
            <dd>{{ profile.role || 'cliente' }}</dd>
          </div>
        </dl>
      </article>
    </section>

    <div v-if="message" :class="['message', isError ? 'error' : 'success']">{{ message }}</div>

    <section class="save-section">
      <p class="save-hint">Los cambios se guardan sobre todo tu perfil</p>
      <button type="button" class="primary save-button" :disabled="saving" @click="saveProfile">
        {{ saving ? 'Guardando...' : 'Guardar cambios' }}
      </button>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const fileInput = ref(null)
const saving = ref(false)
const message = ref('')
const isError = ref(false)
const avatarPreview = ref('')

const profile = computed(() => auth.user || {})

const form = ref({
  email: '',
  profile_photo_url: null,
})

const fullName = computed(() => {
  const first = profile.value.first_name || ''
  const last = profile.value.last_name || ''
  return `${first} ${last}`.trim() || 'Mi perfil'
})

const avatarInitials = computed(() => {
  const firstInitial = profile.value.first_name?.trim()?.charAt(0) || ''
  const lastInitial = profile.value.last_name?.trim()?.charAt(0) || ''
  return `${firstInitial}${lastInitial}`.toUpperCase() || 'U'
})

const avatarSrc = computed(() => avatarPreview.value || profile.value.profile_photo_url || '')

const getReadableErrorMessage = (error) => {
  const data = error?.response?.data

  if (typeof data?.detail === 'string') return data.detail

  if (Array.isArray(data?.detail)) {
    const emailError = data.detail.find((item) => item?.loc?.includes('email'))
    if (emailError) return 'El correo electrónico no es válido. Revisá que no termine en punto o tenga espacios de más.'
    return 'Revisá los datos ingresados porque hay campos que no son válidos.'
  }

  if (typeof data?.message === 'string') return data.message

  return 'No se pudo guardar el perfil.'
}

const syncForm = () => {
  form.value.email = profile.value.email || ''
  form.value.profile_photo_url = profile.value.profile_photo_url || null
  avatarPreview.value = profile.value.profile_photo_url || ''
}

const triggerFilePicker = () => {
  fileInput.value?.click()
}

const handleFileChange = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = () => {
    const result = typeof reader.result === 'string' ? reader.result : ''
    avatarPreview.value = result
    form.value.profile_photo_url = result
  }
  reader.readAsDataURL(file)
}

const saveProfile = async () => {
  saving.value = true
  message.value = ''
  try {
    const updated = await auth.updateProfile({
      email: form.value.email,
      profile_photo_url: form.value.profile_photo_url,
    })
    avatarPreview.value = updated.profile_photo_url || ''
    message.value = 'Perfil actualizado correctamente.'
    isError.value = false
  } catch (error) {
    message.value = getReadableErrorMessage(error)
    isError.value = true
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  if (!auth.user && auth.isAuthenticated) {
    await auth.refreshUser()
  }
  syncForm()
})

watch(
  () => auth.user,
  () => {
    syncForm()
  },
  { deep: true }
)
</script>

<style scoped>
.profile-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 28px 24px 36px;
  display: grid;
  gap: 22px;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
  gap: 22px;
  align-items: stretch;
}

.hero-copy,
.hero-card,
.panel {
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid rgba(45, 101, 141, 0.12);
  border-radius: 24px;
  box-shadow: 0 18px 45px rgba(13, 18, 74, 0.08);
}

.hero-copy {
  padding: 32px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.hero-copy::after {
  content: '';
  position: absolute;
  right: -40px;
  top: -40px;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(45, 101, 141, 0.16) 0%, rgba(45, 101, 141, 0) 70%);
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

.hero-copy h1,
.panel-header h3 {
  margin: 0;
  color: #0d124a;
}

.hero-copy h1 {
  font-size: clamp(2.1rem, 5vw, 3.4rem);
  line-height: 1.02;
}

.hero-text {
  margin: 14px 0 0;
  color: rgba(13, 18, 74, 0.72);
  font-size: 1rem;
  max-width: 58ch;
}

.hero-card {
  padding: 28px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  text-align: center;
  position: relative;
}

.hero-card::before {
  content: '';
  position: absolute;
  inset: 16px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(45, 101, 141, 0.04), rgba(13, 18, 74, 0));
  pointer-events: none;
}

.avatar-button {
  position: relative;
  width: 186px;
  height: 186px;
  border-radius: 50%;
  border: none;
  padding: 0;
  overflow: hidden;
  cursor: pointer;
  background: linear-gradient(135deg, #2d658d, #0d124a);
  box-shadow: 0 20px 40px rgba(13, 18, 74, 0.2);
  z-index: 1;
}

.avatar-image,
.avatar-fallback {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-fallback {
  color: #ffffff;
  font-size: 3rem;
  font-weight: 900;
  letter-spacing: 0.08em;
}

.hidden-input {
  display: none;
}

.identity-block h2 {
  margin: 0;
  color: #0d124a;
  font-size: 1.5rem;
}

.identity-block p {
  margin: 6px 0 0;
  color: rgba(13, 18, 74, 0.68);
  font-weight: 600;
  letter-spacing: 0.04em;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 20px;
}

.panel {
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

.info-list div {
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

.editable-row {
  display: grid;
  gap: 8px;
}

.editable-row dt,
.photo-note span {
  font-size: 0.82rem;
  font-weight: 800;
  color: rgba(13, 18, 74, 0.7);
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

.editable-row input::placeholder {
  color: rgba(13, 18, 74, 0.38);
}

.editable-row input:focus {
  border-color: #2d658d;
  box-shadow: 0 0 0 3px rgba(45, 101, 141, 0.14);
}

.primary,
.secondary {
  border: none;
  border-radius: 14px;
  padding: 14px 18px;
  font-weight: 800;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.primary {
  background: linear-gradient(135deg, #2d658d, #0d124a);
  color: white;
  box-shadow: 0 16px 30px rgba(13, 18, 74, 0.18);
}

.secondary {
  background: rgba(45, 101, 141, 0.08);
  color: #0d124a;
}

.primary:hover,
.secondary:hover,
.avatar-button:hover {
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

.save-section {
  display: grid;
  gap: 14px;
  justify-items: center;
  padding: 10px 0 14px;
}

.save-hint {
  margin: 0;
  color: rgba(13, 18, 74, 0.68);
  font-weight: 600;
  text-align: center;
  max-width: 42ch;
}

.save-button {
  min-width: min(100%, 280px);
}

@media (max-width: 900px) {
  .hero,
  .content-grid {
    grid-template-columns: 1fr;
  }

  .avatar-button {
    width: 156px;
    height: 156px;
  }

  .avatar-actions {
    flex-direction: column;
  }
}
</style>
