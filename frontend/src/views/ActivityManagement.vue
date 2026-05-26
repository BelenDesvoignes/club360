<template>
  <div class="page">
    <div class="gestion-container">
      <div class="card">
        <div class="card-header">
        </div>
        <div class="card-body">
          <h1>{{ isEditing ? 'Editar turno' : 'Crear turno' }}</h1>
          <p class="subtitle">Configurá los horarios de los turnos </p>

          <form @submit.prevent="handleSubmit" class="gestion-form">
            <div class="field">
              <label class="label">Actividad</label>
              <div class="control">
                <select v-model="form.name" required :disabled="isEditing">
                  <option value="" disabled>Seleccioná actividad</option>
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
        <option v-for="day in days" :key="day" :value="day">{{ day }}</option>
      </select>
    </div>
  </div>
  <div class="field">
    <label class="label">Hora</label>
    <div class="control">
      <select v-model="form.shifts[0].start_time" required>
      <option v-for="h in hours" :key="h" :value="h">{{ h }}hs</option>
    </select>
    </div>
  </div>
  <div class="field">
    <label class="label">Cupo</label>
    <div class="control">
      <input type="number" v-model="form.shifts[0].capacity" min="1" required />
    </div>
  </div>
</div>

            <div class="form-actions">
              <button type="submit" class="primary" :disabled="loading">
                <span v-if="loading" class="spinner"></span>
                <span v-else>{{ isEditing ? 'ACTUALIZAR' : 'CREAR TURNO' }}</span>
              </button>

              <button v-if="isEditing" type="button" @click="cancelEdit" class="back-link">
                Cancelar edición
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- Precio de actividades -->
      <div class="list-section" style="max-width: 450px;">
        <h2 class="list-title">Precio de actividades</h2>
        <p class="subtitle" style="text-align:left; margin-bottom:16px;">
          El precio aplica a todos los turnos de cada actividad.
        </p>
        <div v-for="act in activitiesBase" :key="act.id" class="price-row">
          <span class="price-label">{{ act.name }}</span>
          <div class="control price-input-wrap">
            <span style="color:#6b7280; margin-right:4px;">$</span>
            <input type="number" v-model.number="act.editPrice" min="0" step="0.01" />
          </div>
          <button @click="savePrice(act)" class="price-btn">Guardar</button>
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
                  <button @click="editMode(item)" class="icon-btn" title="Editar">✏️</button>
                  <button @click="deleteActivity(item.templateId)" class="icon-btn" title="Eliminar">🗑️</button>
                </td>
              </tr>
              <tr v-if="flatActivities.length === 0">
                <td colspan="5" class="empty-text">No hay turnos registrados.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <transition name="fade">
      <div v-if="message" :class="['alert-toast', messageType]">{{ message }}</div>
    </transition>

    <transition name="fade">
      <div v-if="showConfirmModal" class="modal-overlay">
        <div class="modal-card">
          <template v-if="checkingBookings">
            <p style="color:#6b7280; font-size:14px;">Verificando reservas...</p>
          </template>
          <template v-else-if="hasConfirmedBookings">
            <h3>Este turno tiene reservas confirmadas</h3>
            <p>¿Qué querés hacer con las reservas existentes?</p>
            <div class="modal-actions" style="flex-direction: column;">
              <button @click="executeDelete(false)" class="btn-confirm">
                No cancelar reservas
              </button>
              <button @click="executeDelete(true)" class="btn-danger">
                Cancelar reservas y eliminar
              </button>
              <button @click="showConfirmModal = false" class="btn-cancel">
                Cancelar operación
              </button>
            </div>
          </template>
          <template v-else>
            <h3>¿Eliminar turno?</h3>
            <p>Este turno no tiene reservas confirmadas.</p>
            <div class="modal-actions">
              <button @click="executeDelete(false)" class="btn-confirm">Eliminar turno</button>
              <button @click="showConfirmModal = false" class="btn-cancel">Cancelar</button>
            </div>
          </template>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'

const hours = [
  '08:00','09:00','10:00','11:00','12:00','13:00',
  '14:00','15:00','16:00','17:00','18:00','19:00',
  '20:00','21:00'
]

const activityMap = {
  'Fútbol': 'Cancha 1',
  'Vóley': 'Cancha 2',
  'Pádel': 'Cancha 3',
  'Básquet': 'Cancha 4'
}

const days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']

// ── refs ──────────────────────────────────────────────────────────────────────
const activities     = ref([])
const activitiesBase = ref([])   // ← declarado acá arriba, antes de fetchActivities
const loading        = ref(false)
const isEditing      = ref(false)
const editingId      = ref(null)
const message        = ref('')
const messageType    = ref('')

const form = ref({
  name: '',
  court: '',
  shifts: [{ day_of_week: 'Lunes', start_time: '18:00', capacity: 20, price: null }]
})

// ── fetch ─────────────────────────────────────────────────────────────────────
const fetchActivities = async () => {
  try {
    const res = await axios.get('/activities/')
    activities.value = res.data
    activitiesBase.value = res.data.map(act => ({
      ...act,
      editPrice: act.templates?.[0]?.price ?? 100
    }))
  } catch (e) {
    console.error('Error al cargar', e)
  }
}

// ── computed ──────────────────────────────────────────────────────────────────
const flatActivities = computed(() => {
  const list = []
  activities.value.forEach(act => {
    act.templates.forEach(temp => {
      list.push({
        id:         act.id,
        templateId: temp.id,
        name:       act.name,
        court:      act.court,
        day:        temp.day_of_week,
        time:       temp.start_time,
        capacity:   temp.capacity
      })
    })
  })
  return list
})

// ── turnos: crear / editar ────────────────────────────────────────────────────
const handleSubmit = async () => {
  loading.value = true
  try {
    const currentCourt = typeof activityMap[form.value.name] === 'object'
      ? activityMap[form.value.name].court
      : activityMap[form.value.name]

    const payload = {
      name:   form.value.name,
      court:  currentCourt,
      shifts: form.value.shifts
    }

    if (isEditing.value) {
      await axios.put(`/activities/${editingId.value}`, payload)
      message.value = 'Turno actualizado'
    } else {
      await axios.post('/activities/', payload)
      message.value = 'Turno creado con éxito'
    }

    messageType.value = 'success'
    cancelEdit()
    await fetchActivities()
  } catch (e) {
    console.error(e)
    messageType.value = 'error'
    message.value = e.response?.data?.detail || 'Error al procesar la solicitud.'
  } finally {
    loading.value = false
    setTimeout(() => { message.value = '' }, 3000)
  }
}

const editMode = (item) => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
  isEditing.value  = true
  editingId.value  = item.id

  form.value = {
    name:  item.name,
    court: item.court,
    shifts: [{
      id:           item.templateId,
      day_of_week:  item.day,
      start_time:   item.time,
      capacity:     item.capacity
    }]
  }
}

const cancelEdit = () => {
  isEditing.value = false
  editingId.value = null
  form.value = {
    name:  '',
    court: '',
    shifts: [{ day_of_week: 'Lunes', start_time: '18:00', capacity: 20 }]
  }
}

// ── turnos: eliminar ──────────────────────────────────────────────────────────
const showConfirmModal    = ref(false)
const idToDelete          = ref(null)
const hasConfirmedBookings = ref(false)
const checkingBookings    = ref(false)

const deleteActivity = async (id) => {
  idToDelete.value          = id
  showConfirmModal.value    = true
  checkingBookings.value    = true
  hasConfirmedBookings.value = false

  try {
    const res = await axios.get(`/activities/templates/${id}/check-bookings`)
    hasConfirmedBookings.value = res.data.has_confirmed_bookings
  } catch (e) {
    message.value         = 'Error al verificar reservas.'
    messageType.value     = 'error'
    showConfirmModal.value = false
  } finally {
    checkingBookings.value = false
  }
}

const executeDelete = async (cancelBookings) => {
  showConfirmModal.value = false
  try {
    await axios.delete(`/activities/templates/${idToDelete.value}`, {
      params: { cancel_bookings: cancelBookings }
    })
    await fetchActivities()
    message.value     = 'Eliminado correctamente'
    messageType.value = 'success'
  } catch (e) {
    messageType.value = 'error'
    message.value     = e.response?.data?.detail || 'No se pudo eliminar el turno.'
  } finally {
    setTimeout(() => { message.value = '' }, 3000)
  }
}

// ── precios ───────────────────────────────────────────────────────────────────
const savePrice = async (act) => {
  try {
    await axios.patch(`/activities/${act.id}/price`, null, {
      params: { price: act.editPrice }
    })
    message.value     = `Precio de ${act.name} actualizado`
    messageType.value = 'success'
    await fetchActivities()
  } catch (e) {
    message.value     = 'Error al actualizar precio'
    messageType.value = 'error'
  } finally {
    setTimeout(() => { message.value = '' }, 3000)
  }
}

// ── init ──────────────────────────────────────────────────────────────────────
onMounted(fetchActivities)
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
  top: 0; left: 0; right: 0;
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

.card-header { height: 80px; background: #ffffff; display: flex; align-items: center; justify-content: center; }
.card-body { padding: 0 30px 30px; text-align: center; }

h1 { margin: 0 0 8px; font-size: 24px; color: #111827; }
.subtitle { margin: 0 0 20px; color: #6b7280; font-size: 14px; }

.field { display: block; text-align: left; margin-bottom: 15px; }
.label { display: block; font-size: 12px; font-weight: 600; color: #374151; margin-bottom: 6px; }
.control {
  display: flex;
  align-items: center;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px 12px;
  background: #ffffff;
}

select, input {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  color: #111827;
  font-size: 15px;
}

select:disabled { color: #9ca3af; cursor: not-allowed; }

.form-grid-row {
  grid-template-columns: 2fr 1.5fr 1fr;
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
.primary:hover { transform: translateY(-2px); opacity: 0.9; }

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
.back-link:hover { background: #e5e7eb; color: #1f2937; border-color: #9ca3af; }

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
.price-input-wrap { flex: 1; padding: 8px 12px; }
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
.price-btn:hover { opacity: 0.85; }

/* tabla */
.list-section { width: 100%; background: white; padding: 30px; border-radius: 18px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }
.list-title { color: #111827; margin-bottom: 20px; font-size: 20px; font-weight: 800; }

.table-container { overflow-x: auto; }
.activities-table { width: 100%; border-collapse: collapse; text-align: left; }
.activities-table th {
  padding: 12px;
  border-bottom: 2px solid #f3f4f6;
  color: #6b7280;
  font-size: 13px;
  text-transform: uppercase;
}
.activities-table td { padding: 15px 12px; border-bottom: 1px solid #f9fafb; color: #374151; font-size: 14px; }

.icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  filter: grayscale(1);
  opacity: 0.4;
  font-size: 18px;
  transition: transform 0.2s;
}
.icon-btn:hover { transform: scale(1.1); }

/* modal */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(45, 101, 141, 0.8);
  backdrop-filter: blur(4px);
  display: flex; justify-content: center; align-items: center; z-index: 100;
}
.modal-card {
  background: white;
  padding: 30px;
  border-radius: 18px;
  width: 90%;
  max-width: 350px;
  text-align: center;
}
.modal-actions { display: flex; gap: 10px; margin-top: 20px; }
.btn-confirm { flex: 1; background: #ff6f00; color: white; border: none; padding: 12px; border-radius: 10px; font-weight: 700; cursor: pointer; }
.btn-cancel  { flex: 1; background: #e5e7eb; color: #374151; border: none; padding: 12px; border-radius: 10px; font-weight: 700; cursor: pointer; }
.btn-danger  { flex: 1; background: #c0392b; color: white; border: none; padding: 12px; border-radius: 10px; font-weight: 700; cursor: pointer; margin-top: 8px; }

/* toast */
.alert-toast {
  position: fixed;
  bottom: 20px; right: 20px;
  padding: 15px 25px;
  border-radius: 12px;
  color: white;
  font-weight: 600;
  box-shadow: 0 10px 20px rgba(0,0,0,0.1);
}
.success { background: #2d658d; }
.error   { background: #c0392b; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
@media (max-width: 540px) {
  .form-grid-row {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
