<template>
  <div class="page">
    <div class="gestion-container">
      <div class="card">
        <div class="card-header"></div>

        <div class="card-body">
          <h1>{{ isEditing ? 'Editar turno' : 'Crear turno' }}</h1>
          <p class="subtitle">Configurá los horarios de los turnos</p>

          <form @submit.prevent="handleSubmit" class="gestion-form">
            <div class="field">
              <label class="label">Actividad</label>
              <div class="control">
                <select v-model="form.name" required :disabled="isEditing">
                  <option v-for="(court, act) in activityMap" :key="act" :value="act">
                    {{ act }}
                  </option>
                </select>
              </div>
            </div>

            <div class="form-grid-row">
              <div class="field">
                <label class="label">Día</label>
                <div class="control">
                  <select v-model="form.shifts[0].day_of_week" required>
                    <option v-for="day in days" :key="day" :value="day">
                      {{ day }}
                    </option>
                  </select>
                </div>
              </div>

              <div class="field">
                <label class="label">Hora</label>
                <div class="control">
                  <select v-model="form.shifts[0].start_time" required>
                    <option v-for="h in hours" :key="h" :value="h">
                      {{ h }}hs
                    </option>
                  </select>
                </div>
              </div>

              <div class="field">
                <label class="label">Cupo</label>
                <div class="control">
                  <input
                    type="text"
                    inputmode="numeric"
                    pattern="[0-9]*"
                    min="1"
                    max="100"
                    maxlength="3"
                    autocomplete="off"
                    v-model="form.shifts[0].capacity"
                    @input="sanitizeCapacity(form.shifts[0])"
                    @blur="normalizeCapacity(form.shifts[0])"
                    required
                  />
                </div>
              </div>
            </div>

            <div class="form-actions">
              <button type="submit" class="primary" :disabled="loading">
                <span v-if="loading" class="spinner"></span>
                <span v-else>{{ isEditing ? 'ACTUALIZAR' : 'CREAR TURNO' }}</span>
              </button>

              <button
                v-if="isEditing"
                type="button"
                @click="cancelEdit"
                class="back-link"
              >
                Cancelar edición
              </button>
            </div>
          </form>
        </div>
      </div>

      <div class="list-section" style="max-width: 450px;">
        <h2 class="list-title">Precio de actividades</h2>
        <p class="subtitle" style="text-align:left; margin-bottom:16px;">
          El precio aplica a todos los turnos de cada actividad.
        </p>

        <div v-for="act in activitiesBase" :key="act.id" class="price-row">
          <span class="price-label">{{ act.name }}</span>

          <div class="control price-input-wrap">
            <span style="color:#6b7280; margin-right:4px;">$</span>
            <input 
            type="number" 
            v-model.number="act.editPrice" 
            min="1" 
            step="0.01" 
            required
            @input="sanitizePrice(act)"
          />
          </div>

          <button type="button" @click="savePrice(act)" class="price-btn">
            Guardar
          </button>
        </div>
      </div>

      <div class="list-section">
        <h2 class="list-title">Turnos existentes</h2>

        <div class="table-container">
          <table class="activities-table">
            <thead>
              <tr>
                <th>Actividad</th>
                <th>Día</th>
                <th>Hora</th>
                <th>Cupo</th>
                <th>Acciones</th>
              </tr>
            </thead>

            <tbody>
              <tr v-for="item in flatActivities" :key="item.templateId">
                <td><strong>{{ item.name }}</strong></td>
                <td>{{ item.day }}</td>
                <td>{{ item.time }}hs</td>
                <td>{{ item.capacity }}</td>
                <td class="actions-cell">
                  <button @click="editMode(item)" class="icon-btn" title="Editar" type="button">
                    ✏️
                  </button>
                  <button @click="deleteActivity(item.templateId)" class="icon-btn" title="Eliminar" type="button">
                    🗑️
                  </button>
                </td>
              </tr>

              <tr v-if="flatActivities.length === 0">
                <td colspan="5" class="empty-text">No hay turnos registrados.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Turnos eliminados -->
      <div
        v-if="hasInactiveTemplates"
        class="list-section deleted-section"
        :class="{ 'is-open': showDeletedTurns }"
      >
        <button
          type="button"
          class="collapse-trigger"
          @click="showDeletedTurns = !showDeletedTurns"
          :aria-expanded="showDeletedTurns"
        >
          <div class="collapse-text">
            <div class="collapse-title-row">
              <h2 class="list-title" style="margin:0;">Turnos eliminados</h2>
              <span class="count-badge">{{ inactiveTemplates.length }}</span>
            </div>

            <p class="subtitle" style="margin:4px 0 0; text-align:left;">
              Tocá para ver y rehabilitar los turnos eliminados
            </p>
          </div>

          <svg
            class="chevron"
            :class="{ open: showDeletedTurns }"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M6 9l6 6 6-6"
              stroke="currentColor"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </button>

        <transition name="collapse">
          <div v-show="showDeletedTurns" class="collapse-content">
            <div class="table-container">
              <table class="activities-table">
                <thead>
                  <tr>
                    <th>Actividad</th>
                    <th>Día</th>
                    <th>Hora</th>
                    <th>Cupo</th>
                    <th>Acciones</th>
                  </tr>
                </thead>

                <tbody>
                  <tr
                    v-for="item in inactiveTemplates"
                    :key="item.templateId"
                    class="inactive-row"
                  >
                    <td><strong>{{ item.name }}</strong></td>
                    <td>{{ item.day }}</td>
                    <td>{{ item.time }}hs</td>
                    <td>{{ item.capacity }}</td>
                    <td class="actions-cell">
                      <button
                        @click="reactivateTemplate(item.templateId)"
                        class="reactivate-btn"
                        title="Reactivar"
                        type="button"
                      >
                        Reactivar
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </transition>
      </div>
    </div>

    <transition name="fade">
      <div v-if="message" :class="['alert-toast', messageType]">{{ message }}</div>
    </transition>

    <transition name="fade">
      <div v-if="showConfirmModal" class="modal-overlay">
        <div class="modal-card">
          <template v-if="checkingBookings">
            <div class="modal-loading">
              <span class="spinner dark"></span>
              <p>Verificando reservas...</p>
            </div>
          </template>

          <template v-else-if="hasConfirmedBookings">
            <h3>Este turno tiene reservas activas</h3>
            <p>¿Qué querés hacer con las reservas existentes?</p>
            <div class="modal-actions" style="flex-direction: column;">
              <button @click="executeDelete(false)" class="btn-confirm" type="button">
                No cancelar reservas
              </button>
              <button @click="executeDelete(true)" class="btn-danger" type="button">
                Cancelar reservas y eliminar
              </button>
              <button @click="showConfirmModal = false" class="btn-cancel" type="button">
                Cancelar operación
              </button>
            </div>
          </template>

          <template v-else>
            <h3>¿Eliminar turno?</h3>
            <p>Este turno no tiene reservas activas.</p>
            <div class="modal-actions">
              <button @click="executeDelete(false)" class="btn-confirm" type="button">
                Eliminar turno
              </button>
              <button @click="showConfirmModal = false" class="btn-cancel" type="button">
                Cancelar
              </button>
            </div>
          </template>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div v-if="operationInProgress" class="operation-overlay" aria-live="polite">
        <div class="operation-card">
          <span class="spinner large"></span>
          <h3>{{ operationTitle }}</h3>
          <p>{{ operationMessage }}</p>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '../utils/api'

const hours = [
  '08:00', '09:00', '10:00', '11:00', '12:00', '13:00',
  '14:00', '15:00', '16:00', '17:00', '18:00', '19:00',
  '20:00', '21:00'
]

const activityMap = {
  'Fútbol': 'Cancha 1',
  'Vóley': 'Cancha 2',
  'Pádel': 'Cancha 3',
  'Básquet': 'Cancha 4'
}

const days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']

// ── refs ──────────────────────────────────────────────────────────────────────
const activities = ref([])
const activitiesBase = ref([])
const inactiveTemplates = ref([])
const loading = ref(false)
const isEditing = ref(false)
const editingId = ref(null)
const message = ref('')
const messageType = ref('')
const showDeletedTurns = ref(false)
const hasInactiveTemplates = computed(() => inactiveTemplates.value.length > 0)

let messageTimer = null
const defaultActivity = Object.keys(activityMap)[0]  // primera actividad del mapa
const form = ref({
  name: defaultActivity,
  court: activityMap[defaultActivity],
  shifts: [{
    day_of_week: 'Lunes',
    start_time: '18:00',
    capacity: 20,
    price: null
  }]
})

// ── helpers ───────────────────────────────────────────────────────────────────
const sanitizeCapacity = (shift) => {
  let value = String(shift.capacity ?? '')

  // deja solo números
  value = value.replace(/\D/g, '')

  if (value === '') {
    shift.capacity = ''
    return
  }

  const capacity = parseInt(value, 10)
  shift.capacity = Math.min(Math.max(capacity, 1), 100)
}

const normalizeCapacity = (shift) => {
  sanitizeCapacity(shift)

  const capacity = Number(shift.capacity)

  if (!Number.isFinite(capacity) || capacity < 1) {
    shift.capacity = 1
    return
  }

  if (capacity > 100) {
    shift.capacity = 100
  }
}

// ── fetch ─────────────────────────────────────────────────────────────────────
const fetchActivities = async () => {
  try {
    const res = await api.get('/activities/')
    activities.value = res.data
    activitiesBase.value = res.data.map(act => ({
      ...act,
      editPrice: act.templates?.[0]?.price ?? 100
    }))
  } catch (e) {
    console.error('Error al cargar actividades', e)
  }
}

const fetchInactiveTemplates = async () => {
  try {
    const res = await api.get('/shifts/templates/inactive')
    inactiveTemplates.value = Array.isArray(res.data) ? res.data : []

    if (inactiveTemplates.value.length === 0) {
      showDeletedTurns.value = false
    }
  } catch (e) {
    console.error('Error al cargar turnos eliminados', e)
    inactiveTemplates.value = []
    showDeletedTurns.value = false
  }
}

const showMessage = (text, type = 'success', duration = 5000) => {
  message.value = text
  messageType.value = type

  if (messageTimer) {
    clearTimeout(messageTimer)
  }

  messageTimer = setTimeout(() => {
    message.value = ''
    messageTimer = null
  }, duration)
}

// ── computed ──────────────────────────────────────────────────────────────────
const flatActivities = computed(() => {
  const list = []

  activities.value.forEach(act => {
    ;(act.templates || []).forEach(temp => {
      list.push({
        activityId: act.id,
        templateId: temp.id,
        name: act.name,
        court: act.court,
        day: temp.day_of_week,
        time: temp.start_time,
        capacity: temp.capacity
      })
    })
  })

  return list
})

// ── turnos: crear / editar ────────────────────────────────────────────────────
const handleSubmit = async () => {
  const currentShift = form.value.shifts[0]
  normalizeCapacity(currentShift)

  const capacity = Number(currentShift.capacity)

  if (
    !Number.isFinite(capacity) ||
    !Number.isInteger(capacity) ||
    capacity < 1 ||
    capacity > 100
  ) {
    showMessage('El cupo debe ser un número válido entre 1 y 100.', 'error')
    return
  }

  loading.value = true

  try {
    const currentCourt = typeof activityMap[form.value.name] === 'object'
      ? activityMap[form.value.name].court
      : activityMap[form.value.name]

    const payload = {
      name: form.value.name,
      court: currentCourt,
      shifts: [{
        ...form.value.shifts[0],
        capacity
      }]
    }

    if (isEditing.value) {
      await api.put(`/shifts/templates/${editingId.value}`, {
        activity_id: payload.shifts[0].activity_id,
        day_of_week: payload.shifts[0].day_of_week,
        start_time: payload.shifts[0].start_time,
        capacity
      })
      showMessage('Turno actualizado', 'success')
    } else {
      await api.post('/activities/', payload)
      showMessage('Turno creado con éxito', 'success')
    }

    cancelEdit()
    await Promise.all([fetchActivities(), fetchInactiveTemplates()])
  } catch (e) {
    console.error(e)
    showMessage(
      e.response?.data?.detail || e.response?.data?.message || 'Error al procesar la solicitud.',
      'error'
    )
  } finally {
    loading.value = false
  }
}

const editMode = (item) => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
  isEditing.value = true
  editingId.value = item.templateId

  form.value = {
    name: item.name,
    court: item.court,
    shifts: [{
      id: item.templateId,
      activity_id: item.activityId,
      day_of_week: item.day,
      start_time: item.time,
      capacity: item.capacity
    }]
  }
}

const cancelEdit = () => {
  isEditing.value = false
  editingId.value = null
  form.value = {
    name: defaultActivity,
    court: activityMap[defaultActivity],
    shifts: [{ day_of_week: 'Lunes', start_time: '18:00', capacity: 20 }]
  }
}

// ── turnos: eliminar ──────────────────────────────────────────────────────────
const showConfirmModal = ref(false)
const idToDelete = ref(null)
const hasConfirmedBookings = ref(false)
const checkingBookings = ref(false)
const operationInProgress = ref(false)
const operationTitle = ref('')
const operationMessage = ref('')

const startOperationFeedback = (title, message) => {
  operationTitle.value = title
  operationMessage.value = message
  operationInProgress.value = true
}

const stopOperationFeedback = () => {
  operationInProgress.value = false
  operationTitle.value = ''
  operationMessage.value = ''
}

const deleteActivity = async (id) => {
  idToDelete.value = id
  showConfirmModal.value = true
  checkingBookings.value = true
  hasConfirmedBookings.value = false

  try {
    const res = await api.get(`/shifts/templates/${id}/check-bookings`)
    hasConfirmedBookings.value = res.data.has_active_bookings
  } catch (e) {
    showMessage('Error al verificar reservas.', 'error')
    showConfirmModal.value = false
  } finally {
    checkingBookings.value = false
  }
}

const executeDelete = async (cancelBookings) => {
  showConfirmModal.value = false
  loading.value = true

  let url = `/shifts/templates/${idToDelete.value}`
  let feedbackTitle = 'Eliminando turno'
  let feedbackMessage = 'Estamos procesando la eliminación del turno.'

  if (!hasConfirmedBookings.value) {
    url += '/safe-clean'
    feedbackMessage = 'Estamos eliminando el turno y sus clases.'
  } else {
    if (cancelBookings === false) {
      url += '/keep-active-classes'
      feedbackMessage = 'Estamos desactivando el turno y conservando las clases con reservas activas.'
    } else if (cancelBookings === true) {
      url += '/cancel-everything'
      feedbackTitle = 'Eliminando turno'
      feedbackMessage = 'Estamos procesando reembolsos y enviando las notificaciones por mail.'
    }
  }

  try {
    startOperationFeedback(feedbackTitle, feedbackMessage)
    const res = await api.delete(url)
    await Promise.all([fetchActivities(), fetchInactiveTemplates()])
    showMessage(res.data.message || 'Operación realizada correctamente', 'success')
  } catch (e) {
    console.error(e)
    showMessage(e.response?.data?.detail || 'No se pudo eliminar el turno.', 'error')
  } finally {
    loading.value = false
    idToDelete.value = null
    stopOperationFeedback()
  }
}

const reactivateTemplate = async (templateId) => {
  // Buscar el turno eliminado que se quiere reactivar
  const template = inactiveTemplates.value.find(t => t.id === templateId)

  // Validar si ya existe un turno activo con misma actividad/día/hora
  const existsActive = flatActivities.value.some(
    act => act.name === template.name &&
           act.day === template.day_of_week &&
           act.time === template.start_time
  )

  if (existsActive) {
    showMessage('Ya existe un turno activo con esos datos. No se puede reactivar.', 'error')
    return
  }

  loading.value = true
  try {
    startOperationFeedback(
      'Reactivando turno',
      'Estamos reactivando el turno y creando las clases'
    )
    const res = await api.patch(`/shifts/templates/${templateId}/reactivate`)
    await Promise.all([fetchActivities(), fetchInactiveTemplates()])
    showMessage(res.data.message || 'Turno reactivado correctamente', 'success')
  } catch (e) {
    console.error(e)
    showMessage(e.response?.data?.detail || 'No se pudo reactivar el turno.', 'error')
  } finally {
    loading.value = false
    stopOperationFeedback()
  }
}


// ── precios ───────────────────────────────────────────────────────────────────
const sanitizePrice = (act) => {
  let value = String(act.editPrice ?? '')

  // deja solo números y punto decimal
  value = value.replace(/[^0-9.]/g, '')

  // convertir a número
  let num = parseFloat(value)

  // si está vacío, NaN o menor a 1 → forzar a 1
  if (!Number.isFinite(num) || num < 1) {
    act.editPrice = 1
    return
  }

  act.editPrice = num
}


// ── init ──────────────────────────────────────────────────────────────────────
onMounted(() => {
  Promise.all([fetchActivities(), fetchInactiveTemplates()])
})
</script>

<style scoped>
.page {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
  background: #ffffff;
  font-family: 'Segoe UI', Roboto, sans-serif;
}

.page::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 300px;
  background: #2d658d;
  z-index: 0;
}

.gestion-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 1000px;
  display: flex;
  flex-direction: column;
  gap: 40px;
  align-items: center;
}

.card {
  width: 100%;
  max-width: 600px;
  background: #ffffff;
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.15);
}

.card-header {
  height: 80px;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-body {
  padding: 0 30px 30px;
  text-align: center;
}

h1 {
  margin: 0 0 8px;
  font-size: 24px;
  color: #111827;
}

.subtitle {
  margin: 0 0 20px;
  color: #6b7280;
  font-size: 14px;
}

.field {
  display: block;
  text-align: left;
  margin-bottom: 15px;
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
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px 12px;
  background: #ffffff;
}

select,
input {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  color: #111827;
  font-size: 15px;
}

select:disabled {
  color: #9ca3af;
  cursor: not-allowed;
}

.form-grid-row {
  display: grid;
  grid-template-columns: 2fr 1.5fr 1fr;
  gap: 12px;
}

.form-actions {
  margin-top: 8px;
}

.primary {
  width: 100%;
  padding: 14px;
  background: #2d658d;
  color: white;
  border: none;
  border-radius: 10px;
  font-weight: 800;
  cursor: pointer;
  margin-top: 10px;
  transition: transform 0.2s;
}

.primary:hover {
  transform: translateY(-2px);
  opacity: 0.9;
}

.spinner {
  display: inline-block;
  width: 18px;
  height: 18px;
  border: 3px solid rgba(255, 255, 255, 0.45);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  vertical-align: middle;
}

.spinner.dark {
  border-color: rgba(45, 101, 141, 0.25);
  border-top-color: #2d658d;
}

.spinner.large {
  width: 34px;
  height: 34px;
  border-width: 4px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.back-link {
  display: block;
  width: 100%;
  margin-top: 12px;
  padding: 12px;
  font-size: 14px;
  font-weight: 700;
  color: #4b5563;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  cursor: pointer;
  text-transform: uppercase;
  transition: all 0.2s ease;
}

.back-link:hover {
  background: #e5e7eb;
  color: #1f2937;
  border-color: #9ca3af;
}

/* precio */
.price-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.price-label {
  width: 80px;
  font-weight: 600;
  color: #374151;
  font-size: 14px;
}

.price-input-wrap {
  flex: 1;
  padding: 8px 12px;
}

.price-btn {
  background: #2d658d;
  color: white;
  border: none;
  border-radius: 10px;
  padding: 9px 16px;
  font-weight: 700;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
}

.price-btn:hover {
  opacity: 0.85;
}

/* tabla */
.list-section {
  width: 100%;
  background: white;
  padding: 30px;
  border-radius: 18px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
}

.list-title {
  color: #111827;
  margin-bottom: 20px;
  font-size: 20px;
  font-weight: 800;
}

.table-container {
  overflow-x: auto;
}

.activities-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.activities-table th {
  padding: 12px;
  border-bottom: 2px solid #f3f4f6;
  color: #6b7280;
  font-size: 13px;
  text-transform: uppercase;
}

.activities-table td {
  padding: 15px 12px;
  border-bottom: 1px solid #f9fafb;
  color: #374151;
  font-size: 14px;
}

.inactive-row td {
  color: #6b7280;
}

.empty-text {
  text-align: center;
  padding: 20px 12px;
  color: #6b7280;
}

.icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  filter: grayscale(1);
  opacity: 0.4;
  font-size: 18px;
  transition: transform 0.2s;
}

.icon-btn:hover {
  transform: scale(1.1);
}

.reactivate-btn {
  background: #2d658d;
  color: white;
  border: none;
  border-radius: 10px;
  padding: 9px 14px;
  font-weight: 700;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
}

.reactivate-btn:hover {
  opacity: 0.85;
}

/* desplegable turnos eliminados */
.deleted-section {
  padding: 0;
  overflow: hidden;
  border: 1px solid rgba(45, 101, 141, 0.10);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.25s ease, transform 0.25s ease, border-color 0.25s ease;
}

.deleted-section.is-open {
  border-color: rgba(45, 101, 141, 0.22);
  box-shadow: 0 16px 35px rgba(45, 101, 141, 0.10);
}

.collapse-trigger {
  width: 100%;
  border: none;
  background: transparent;
  padding: 22px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  text-align: left;
  transition: background 0.2s ease, transform 0.2s ease;
}

.collapse-trigger:hover {
  background: rgba(45, 101, 141, 0.03);
}

.collapse-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.collapse-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 30px;
  height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  background: rgba(45, 101, 141, 0.12);
  color: #2d658d;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.02em;
}

.chevron {
  width: 26px;
  height: 26px;
  color: #2d658d;
  transition: transform 0.25s ease;
  flex-shrink: 0;
}

.chevron.open {
  transform: rotate(180deg);
}

.collapse-content {
  padding: 0 24px 24px;
}

.collapse-enter-active,
.collapse-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease, max-height 0.25s ease;
  overflow: hidden;
}

.collapse-enter-from,
.collapse-leave-to {
  opacity: 0;
  transform: translateY(-8px);
  max-height: 0;
}

.collapse-enter-to,
.collapse-leave-from {
  opacity: 1;
  transform: translateY(0);
  max-height: 1000px;
}

/* modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(45, 101, 141, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 100;
}

.modal-card {
  background: white;
  padding: 30px;
  border-radius: 18px;
  width: 90%;
  max-width: 350px;
  text-align: center;
}

.modal-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.modal-loading p {
  margin: 0;
  color: #6b7280;
  font-size: 14px;
}

.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.btn-confirm {
  flex: 1;
  background: #ff6f00;
  color: white;
  border: none;
  padding: 12px;
  border-radius: 10px;
  font-weight: 700;
  cursor: pointer;
}

.btn-cancel {
  flex: 1;
  background: #e5e7eb;
  color: #374151;
  border: none;
  padding: 12px;
  border-radius: 10px;
  font-weight: 700;
  cursor: pointer;
}

.btn-danger {
  flex: 1;
  background: #c0392b;
  color: white;
  border: none;
  padding: 12px;
  border-radius: 10px;
  font-weight: 700;
  cursor: pointer;
  margin-top: 8px;
}

/* overlay operación */
.operation-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(17, 24, 39, 0.58);
  backdrop-filter: blur(4px);
}

.operation-card {
  width: min(92vw, 380px);
  background: #ffffff;
  border-radius: 18px;
  padding: 28px;
  text-align: center;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.2);
}

.operation-card h3 {
  margin: 16px 0 8px;
  color: #111827;
  font-size: 20px;
}

.operation-card p {
  margin: 0;
  color: #6b7280;
  font-size: 14px;
  line-height: 1.45;
}

.operation-card .spinner {
  border-color: rgba(45, 101, 141, 0.25);
  border-top-color: #2d658d;
}

/* toast */
.alert-toast {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  width: min(92vw, 560px);
  padding: 16px 22px;
  border-radius: 12px;
  color: white;
  font-weight: 600;
  text-align: center;
  line-height: 1.4;
  white-space: normal;
  word-break: break-word;
  z-index: 9999;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}

.success {
  background: #2d658d;
}

.error {
  background: #c0392b;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 540px) {
  .form-grid-row {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
