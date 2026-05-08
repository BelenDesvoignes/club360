<template>
  <div class="gestion-container">
    <div class="form-card">
      <header class="form-header">
        <h1>{{ isEditing ? 'Editar Actividad' : 'Nueva actividad' }}</h1>
        <p> </p>
      </header>

      <form @submit.prevent="handleSubmit" class="gestion-form">
        <div class="form-grid">
          <div class="input-group">
            <label>Nombre de la actividad</label>
            <input v-model="form.name" type="text" placeholder="Ej: Fútbol" required />
          </div>
          <div class="input-group">
            <label>Cancha</label>
            <input v-model="form.court" type="text" placeholder="Ej: Cancha 1" required />
          </div>
        </div>

        <div class="section-header">
          <h3>Horarios semanales</h3>
          <button type="button" @click="addShift" class="btn-add-inline">+ Agregar horario</button>
        </div>

        <div v-for="(shift, index) in form.shifts" :key="index" class="shift-row">
          <select v-model="shift.day_of_week">
            <option>Lunes</option><option>Martes</option><option>Miércoles</option>
            <option>Jueves</option><option>Viernes</option><option>Sábado</option>
            <option>Domingo</option>
          </select>
          <input type="time" v-model="shift.start_time" required />
          <div class="cupo-input">
            <input type="number" v-model="shift.capacity" placeholder="Cupo" required min="1" />
          </div>
          <button type="button" @click="removeShift(index)" class="btn-remove-mini" v-if="form.shifts.length > 1">✕</button>
        </div>

        <div class="form-actions">
          <button type="submit" class="btn-submit" :disabled="loading">
            {{ isEditing ? 'Actualizar cambios' : 'Crear actividad' }}
          </button>
          <button v-if="isEditing" type="button" @click="cancelEdit" class="btn-cancel">Cancelar</button>
        </div>
      </form>
    </div>

    <div class="list-section">
      <h2 class="list-title">Actividades existentes</h2>
      <div v-if="activities.length === 0" class="empty-state">No hay actividades cargadas.</div>

      <div class="activities-grid">
        <div v-for="act in activities" :key="act.id" class="activity-card">
          <div class="card-info">
            <h3>{{ act.name }}</h3>
            <span class="court-badge">{{ act.court }}</span>
            <div class="shifts-summary">
              <p v-for="s in act.templates" :key="s.id">
                • {{ s.day_of_week }} {{ s.start_time }}hs (Cupo: {{ s.capacity }})
              </p>
            </div>
          </div>
          <div class="card-actions">
            <button @click="editMode(act)" title="Editar">✏️</button>
            <button @click="deleteActivity(act.id)" title="Eliminar">🗑️</button>
          </div>
        </div>
      </div>
    </div>

    <transition name="fade">
      <div v-if="message" :class="['alert', messageType]">{{ message }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const activities = ref([])
const loading = ref(false)
const isEditing = ref(false)
const editingId = ref(null)
const message = ref('')
const messageType = ref('')

const form = ref({
  name: '',
  court: '',
  shifts: [{ day_of_week: 'Lunes', start_time: '18:00', capacity: 20 }]
})

const fetchActivities = async () => {
  try {
    const res = await axios.get('/activities/')
    activities.value = res.data
  } catch (e) {
    console.error("Error al cargar actividades", e)
  }
}

const addShift = () => form.value.shifts.push({ day_of_week: 'Lunes', start_time: '18:00', capacity: 20 })
const removeShift = (index) => form.value.shifts.splice(index, 1)

const handleSubmit = async () => {
  loading.value = true
  try {
    if (isEditing.value) {
      await axios.put(`/activities/${editingId.value}`, form.value)
      message.value = "Actividad actualizada correctamente"
    } else {
      await axios.post('/activities/', form.value)
      message.value = "Actividad creada con éxito"
    }
    messageType.value = "success"
    cancelEdit()
    fetchActivities()
  } catch (e) {
    messageType.value = "error"
    message.value = "Error al procesar la solicitud"
  } finally {
    loading.value = false
    setTimeout(() => { message.value = '' }, 3000) // Limpiar mensaje tras 3 seg
  }
}

const editMode = (act) => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
  isEditing.value = true
  editingId.value = act.id

  // Mapeamos 'templates' de la DB al array 'shifts' que usa nuestro formulario
  form.value = {
    name: act.name,
    court: act.court,
    shifts: act.templates ? JSON.parse(JSON.stringify(act.templates)) : []
  }
}

const cancelEdit = () => {
  isEditing.value = false
  editingId.value = null
  form.value = {
    name: '',
    court: '',
    shifts: [{ day_of_week: 'Lunes', start_time: '18:00', capacity: 20 }]
  }
}

const deleteActivity = async (id) => {
  if (confirm('¿Estás seguro de eliminar esta actividad?')) {
    try {
      await axios.delete(`/activities/${id}`)
      fetchActivities()
      message.value = "Actividad eliminada"
      messageType.value = "success"
    } catch (e) {
      message.value = "Error al eliminar"
      messageType.value = "error"
    }
    setTimeout(() => { message.value = '' }, 3000)
  }
}

onMounted(fetchActivities)
</script>

<style scoped>
.gestion-container { padding: 20px; background-color: #f8f9fa; min-height: 100vh; display: flex; flex-direction: column; align-items: center; gap: 40px; }

/* Estilo Formulario */
.form-card { background: white; padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); width: 100%; max-width: 600px; }
.form-header { text-align: center; margin-bottom: 20px; }
.form-header h1 { color: #0d124a; font-size: 1.6rem; font-weight: 800; margin: 0; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }
.input-group { display: flex; flex-direction: column; gap: 5px; }
label { font-weight: 700; font-size: 0.85rem; color: #2c3e50; }
input, select { padding: 12px; border: 2px solid #edf2f7; border-radius: 10px; outline: none; transition: 0.3s; }
input:focus { border-color: #ff6f00; }

.section-header { display: flex; justify-content: space-between; align-items: center; margin: 20px 0 10px; }
.btn-add-inline { background: #ff6f00; color: white; border: none; padding: 6px 12px; border-radius: 8px; cursor: pointer; font-size: 0.8rem; font-weight: 600; }

.shift-row { display: grid; grid-template-columns: 2fr 1.5fr 1fr 0.5fr; gap: 10px; margin-bottom: 10px; align-items: center; }
.btn-remove-mini { background: #fee2e2; color: #dc2626; border: none; border-radius: 8px; padding: 10px; cursor: pointer; font-weight: bold; }

/* Estilo Listado de Cards */
.list-section { width: 100%; max-width: 900px; }
.list-title { color: #0d124a; font-size: 1.4rem; margin-bottom: 20px; font-weight: 800; text-align: center; }
.activities-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
.activity-card { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); display: flex; justify-content: space-between; border-left: 5px solid #ff6f00; transition: transform 0.2s; }
.activity-card:hover { transform: translateY(-3px); }

.court-badge { background: #edf2f7; color: #4a5568; padding: 3px 10px; border-radius: 6px; font-size: 0.7rem; font-weight: 800; text-transform: uppercase; display: inline-block; margin-top: 5px; }
.shifts-summary { margin-top: 15px; font-size: 0.85rem; color: #718096; line-height: 1.4; }
.card-actions button {
  background: white;
  border: 1px solid #edf2f7;
  padding: 8px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease; /* Transición suave */
  box-shadow: 0 2px 5px rgba(0,0,0,0.02);

  /* ESTO ES LO NUEVO: Vuelve gris el emoji */
  filter: grayscale(1);
  opacity: 0.7; /* Lo hace un poquito más sutil */
}

/* Y esto para cuando pasás el mouse por arriba */
.card-actions button:hover {
  background: #f8f9fa;
  transform: scale(1.1);

}
.form-actions { display: flex; gap: 10px; margin-top: 25px; }
.btn-submit { flex: 2; padding: 14px; background: #0d124a; color: white; border: none; border-radius: 12px; font-weight: 700; cursor: pointer; transition: 0.3s; }
.btn-submit:hover { background: #ff6f00; box-shadow: 0 4px 15px rgba(255, 111, 0, 0.3); }
.btn-cancel { flex: 1; background: #e2e8f0; border: none; border-radius: 12px; cursor: pointer; font-weight: 600; }

.empty-state { text-align: center; color: #a0aec0; padding: 40px; font-style: italic; }

/* Alertas */
.alert { position: fixed; bottom: 30px; right: 30px; padding: 15px 30px; border-radius: 12px; z-index: 1000; font-weight: 600; box-shadow: 0 10px 20px rgba(0,0,0,0.1); }
.success { background: #def7ec; color: #03543f; border-bottom: 4px solid #31c48d; }
.error { background: #fde8e8; color: #9b1c1c; border-bottom: 4px solid #f98080; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.5s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>