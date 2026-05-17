<template>
  <div class="page">
    <div class="gestion-container">
      <header class="page-header">
        <h1>Gestión de Clases</h1>
      </header>

      <!-- Filtros -->
      <div class="filters-card">
        <div class="filter-group">
          <label>Filtrar por Actividad</label>
          <select v-model="filterActivity">
            <option value="">Todas las actividades</option>
            <option v-for="name in uniqueActivities" :key="name" :value="name">
              {{ name }}
            </option>
          </select>
        </div>
        <div class="filter-group">
          <label>Buscar por fecha</label>
          <input type="date" v-model="filterDate" />
        </div>
        <button @click="resetFilters" class="btn-clear">Limpiar</button>
      </div>

      <!-- Tabla de Instancias -->
      <div class="table-container">
        <div v-if="loading" class="loading-state">Cargando clases...</div>
        
        <table v-else class="shifts-table">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Actividad</th>
              <th>Horario</th>
              <th>Ocupación</th>
              <th>Capacidad</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="shift in filteredShifts" :key="shift.id" :class="{ 'row-cancelled': shift.is_cancelled }">
              <td>{{ formatDate(shift.date) }}</td>
              <td>
                <span class="activity-name">{{ shift.activity_name }}</span>
              </td>
              <td>{{ shift.template.start_time }}hs</td>
              <td>
                <div class="occupancy-bar">
                  <span :style="{ width: (shift.booked_count / shift.template.capacity * 100) + '%' }"></span>
                  <small>{{ shift.booked_count }} / {{ shift.template.capacity }}</small>
                </div>
              </td>
              <td>
                <input 
                  type="number" 
                  v-model.number="shift.capacity"
                  class="inline-input"
                  :min="shift.booked_count"
                />
              </td>
              <td class="actions-cell">
                <!-- CORREGIDO: Ahora usan .icon-btn como tu estándar -->
                <button @click="updateShift(shift)" class="icon-btn" title="Guardar cambios">💾</button>
                <button @click="confirmCancel(shift)" class="icon-btn" title="Cancelar clase">🚫</button>
              </td>
            </tr>
          </tbody>
        </table>
        
        <div v-if="filteredShifts.length === 0 && !loading" class="empty-state">
          No se encontraron clases con los filtros seleccionados.
        </div>
      </div>

      <!-- Alertas -->
      <transition name="fade">
        <div v-if="message" :class="['alert-toast', messageType]">{{ message }}</div>
      </transition>

      <!-- MODAL ESTÁNDAR -->
      <transition name="fade">
        <div v-if="showConfirmModal" class="modal-overlay">
          <div class="modal-card">
            <h3>Cancelar clase</h3>
            <p v-if="instanceToDelete">
              Estás por cancelar la clase de <strong>{{ instanceToDelete.activity_name }}</strong> <br>
              del día <strong>{{ instanceToDelete.date }}</strong>.
            </p>
            <div class="modal-actions">
              <button @click="executeCancel" class="btn-danger">
                Confirmar
              </button>
              <button @click="showConfirmModal = false" class="btn-cancel">
                Volver
              </button>
            </div>
          </div>
        </div>
      </transition>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'

const shifts = ref([])
const loading = ref(false)
const message = ref('')
const messageType = ref('')

// Filtros
const filterActivity = ref('')
const filterDate = ref('')

const fetchShifts = async () => {
  loading.value = true
  try {
    const res = await axios.get('/shifts/instances')
    shifts.value = res.data.sort((a, b) => new Date(a.date) - new Date(b.date))
  } catch (e) {
    showMsg("Error al cargar las clases", "error")
  } finally {
    loading.value = false
  }
}

const uniqueActivities = computed(() => {
  const names = shifts.value.map(s => s.activity_name)
  return [...new Set(names)]
})

const filteredShifts = computed(() => {
  return shifts.value.filter(s => {
    const matchAct = !filterActivity.value || s.activity_name === filterActivity.value
    const matchDate = !filterDate.value || s.date === filterDate.value
    return matchAct && matchDate
  })
})

const updateShift = async (shift) => {
  try {
    await axios.patch(`/shifts/instances/${shift.id}?capacity=${shift.capacity}`)
    showMsg("Cupo actualizado correctamente", "success")
    fetchShifts() 
  } catch (e) {
    const errorMsg = e.response?.data?.detail || "Error al actualizar"
    showMsg(errorMsg, "error")
  }
}

// Estado del Modal
const showConfirmModal = ref(false)
const instanceToDelete = ref(null)

const confirmCancel = (shift) => {
  instanceToDelete.value = shift
  showConfirmModal.value = true
}

const executeCancel = async () => {
  if (!instanceToDelete.value) return
  
  const id = instanceToDelete.value.id
  try {
    await axios.patch(`/shifts/instances/${id}/cancel`)
    showMsg("Clase cancelada con éxito", "success")
    showConfirmModal.value = false
    await fetchShifts()
  } catch (e) {
    const errorMsg = e.response?.data?.detail || "No se pudo cancelar la clase."
    showMsg(errorMsg, "error")
  } finally {
    instanceToDelete.value = null
  }
}

const resetFilters = () => {
  filterActivity.value = ''
  filterDate.value = ''
}

const formatDate = (dateStr) => {
  if (!dateStr) return 'Sin fecha'
  const date = new Date(dateStr + 'T12:00:00') 
  return date.toLocaleDateString('es-AR', { 
    day: '2-digit', 
    month: '2-digit', 
    year: 'numeric' 
  })
}

const showMsg = (txt, type) => {
  message.value = txt
  messageType.value = type
  setTimeout(() => message.value = '', 3000)
}

onMounted(fetchShifts)
</script>

<style scoped>
/* ==========================================
   ESTRUCTURA DE PÁGINA Y FONDO
   ========================================== */
.page {
  position: relative;
  min-height: 100vh;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
  background: #ffffff;
  font-family: 'Segoe UI', Roboto, sans-serif;
  box-sizing: border-box;
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
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 40px;
  align-items: center;
}

/* Encabezado Principal */
.page-header {
  text-align: center;
  margin-bottom: 10px;
}
.page-header h1 {
  margin: 0 0 8px;
  font-size: 28px;
  color: #ffffff;
  font-weight: 800;
}
.page-header p {
  margin: 0;
  color: #e2e8f0;
  font-size: 15px;
}

/* ==========================================
   FILTROS (Estilo Card Flotante)
   ========================================== */
.filters-card { 
  width: 100%;
  background: white; 
  padding: 30px; 
  border-radius: 18px; 
  display: flex; 
  gap: 20px; 
  align-items: flex-end;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.15);
  box-sizing: border-box;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.filter-group label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}

input, select {
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px 12px;
  background: #ffffff;
  color: #111827;
  font-size: 15px;
  outline: none;
  box-sizing: border-box;
}

select:disabled {
  color: #9ca3af;
  cursor: not-allowed;
}

.btn-clear {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ff6f00; 
  color: #ffffff;    
  border: 1px solid #d1d5db;
  padding: 10px 16px;
  border-radius: 10px;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  height: 42px; 
  text-transform: uppercase;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.btn-clear:hover {
  background: #e5e7eb;
  color: #1f2937;
  border-color: #9ca3af;
}

/* ==========================================
   TABLA DE CLASES (List Section Style)
   ========================================== */
.table-container { 
  width: 100%;
  background: white; 
  padding: 30px; 
  border-radius: 18px; 
  box-shadow: 0 10px 30px rgba(0,0,0,0.05);
  overflow-x: auto; 
  box-sizing: border-box;
}

.shifts-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.shifts-table th {
  padding: 12px;
  border-bottom: 2px solid #f3f4f6;
  color: #6b7280;
  font-size: 13px;
  text-transform: uppercase;
  font-weight: 800;
}

.shifts-table td {
  padding: 15px 12px;
  border-bottom: 1px solid #f9fafb;
  color: #374151;
  font-size: 14px;
}

.activity-name {
  font-weight: 700;
  color: #111827;
}

.inline-input {
  width: 60px;
  padding: 6px;
  text-align: center;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: transparent;
}

.row-cancelled {
  opacity: 0.4;
  text-decoration: line-through;
  background: #fff5f5;
}

/* Barra de Ocupación */
.occupancy-bar { 
  width: 110px; 
  height: 10px; 
  background: #e5e7eb; 
  border-radius: 10px; 
  position: relative;
  overflow: visible; 
  margin-bottom: 14px;
}

.occupancy-bar span { 
  position: absolute; 
  height: 100%; 
  background: #ff6f00; 
  border-radius: 10px;
  left: 0; 
}

.occupancy-bar small {
  position: absolute;
  top: 12px;
  left: 0;
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  width: 100%;
}

/* Acciones de la Tabla (Estilo Unificado) */
.actions-cell {
  display: flex;
  gap: 10px;
}

/* CORREGIDO: Estilo exacto tomado de tu ActivityManagement estándar */
.icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  filter: grayscale(1);
  opacity: 0.4;
  font-size: 18px;
  transition: transform 0.2s;
  padding: 0;
}

.icon-btn:hover {
  transform: scale(1.1);
  filter: grayscale(0); /* Permite ver el color real del emoji al hacer hover */
  opacity: 1;           /* Destaca el botón activo */
}

/* ==========================================
   MODALES
   ========================================== */
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
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.15);
}

.modal-card h3 {
  margin: 0 0 12px;
  font-size: 22px;
  color: #111827;
  font-weight: 800;
}

.modal-card p {
  margin: 0 0 20px;
  color: #6b7280;
  font-size: 14px;
  line-height: 1.5;
}

.modal-actions { 
  display: flex; 
  gap: 10px; 
  margin-top: 20px; 
}

.btn-danger {
  flex: 1;
  background: #ff6f00;
  color: white;
  border: none;
  padding: 12px;
  border-radius: 10px;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-danger:hover {
  opacity: 0.9;
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
  transition: background 0.2s;
}

.btn-cancel:hover {
  background: #cbd5e1;
}

/* ==========================================
   ALERTAS / TOASTS (Clase unificada con el estándar)
   ========================================== */
.alert-toast {
  position: fixed;
  bottom: 20px;
  right: 20px;
  padding: 15px 25px;
  border-radius: 12px;
  color: white;
  font-weight: 600;
  box-shadow: 0 10px 20px rgba(0,0,0,0.1);
  z-index: 1000;
}

.success { background: #2d658d; }
.error { background: #c0392b; }

.empty-state, .loading-state {
  padding: 40px;
  text-align: center;
  color: #9ca3af;
  font-weight: 600;
}

/* Animaciones */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>