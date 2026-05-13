<template>
  <div class="gestion-container">
    <header class="page-header">
      <h1>Gestión de Clases Próximas</h1>
      <p>Administra instancias específicas y cupos por fecha</p>
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
              <button @click="updateShift(shift)" class="btn-save" title="Guardar cambios">💾</button>
              <button @click="confirmCancel(shift)" class="btn-cancel-shift" title="Cancelar clase">🚫</button>
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
      <div v-if="message" :class="['alert', messageType]">{{ message }}</div>
    </transition>

    <!-- Modal de Confirmación de Cancelación -->
    <transition name="fade">
    <div v-if="showConfirmModal" class="modal-overlay">
        <div class="modal-content">
        <div class="modal-icon">🚫</div>
        <h3>¿Cancelar esta clase?</h3>
        <p v-if="instanceToDelete">
            Estás por cancelar la clase de <strong>{{ instanceToDelete.activity_name }}</strong> <br>
            del día <strong>{{ instanceToDelete.date }}</strong>.
        </p>
        <div class="modal-actions">
            <button @click="executeCancel" class="btn-confirm-delete">
            Confirmar Cancelación
            </button>
            <button @click="showConfirmModal = false" class="btn-cancel-modal">
            Volver
            </button>
        </div>
        </div>
    </div>
    </transition>

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
const showConfirmModal = ref(false);
const instanceToDelete = ref(null);

// 1. Abre el modal y guarda la referencia de qué clase queremos cancelar
const confirmCancel = (shift) => {
  instanceToDelete.value = shift;
  showConfirmModal.value = true;
};

// 2. Ejecuta la cancelación real tras la confirmación
const executeCancel = async () => {
  if (!instanceToDelete.value) return;
  
  const id = instanceToDelete.value.id;
  
  try {
    // Llamada al endpoint específico de cancelación
    await axios.patch(`/shifts/instances/${id}/cancel`);
    
    showMsg("Clase cancelada con éxito", "success");
    showConfirmModal.value = false; // Cerramos el modal
    await fetchShifts(); // Recargamos la lista para que desaparezca la clase
  } catch (e) {
    const errorMsg = e.response?.data?.detail || "No se pudo cancelar la clase.";
    showMsg(errorMsg, "error");
  } finally {
    instanceToDelete.value = null;
  }
};

const resetFilters = () => {
  filterActivity.value = ''
  filterDate.value = ''
}

const formatDate = (dateStr) => {
  if (!dateStr) return 'Sin fecha';
  // Forzamos que la fecha sea al mediodía antes de formatear
  const date = new Date(dateStr + 'T12:00:00'); 
  return date.toLocaleDateString('es-AR', { 
    day: '2-digit', 
    month: '2-digit', 
    year: 'numeric' 
  });
};

const showMsg = (txt, type) => {
  message.value = txt
  messageType.value = type
  setTimeout(() => message.value = '', 3000)
}


onMounted(fetchShifts)
</script>

<style scoped>
.gestion-container { padding: 20px; max-width: 1000px; margin: 0 auto; font-family: sans-serif; }
.page-header { text-align: center; margin-bottom: 30px; }
.page-header h1 { color: #0d124a; margin-bottom: 5px; }
.page-header p { color: #666; }

/* Filtros */
.filters-card { 
  background: white; 
  padding: 20px; 
  border-radius: 15px; 
  display: flex; 
  gap: 20px; 
  align-items: flex-end;
  box-shadow: 0 4px 15px rgba(0,0,0,0.05);
  margin-bottom: 30px;
}
.filter-group { display: flex; flex-direction: column; gap: 5px; flex: 1; }
.filter-group label { font-size: 0.8rem; font-weight: bold; color: #4a5568; }
input, select { padding: 10px; border: 1px solid #e2e8f0; border-radius: 8px; }

/* Tabla */
.table-container { background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
.shifts-table { width: 100%; border-collapse: collapse; text-align: left; }
.shifts-table th { background: #f8fafc; padding: 15px; color: #64748b; font-size: 0.85rem; text-transform: uppercase; }
.shifts-table td { padding: 15px; border-top: 1px solid #f1f5f9; }

.activity-name { font-weight: bold; color: #0d124a; }

.occupancy-bar { 
  width: 100px; 
  height: 8px; 
  background: #edf2f7; 
  border-radius: 10px; 
  position: relative;
  overflow: hidden;
}
.occupancy-bar span { 
  position: absolute; 
  height: 100%; 
  background: #ff6f00; 
  left: 0; 
}
.occupancy-bar small { position: absolute; top: 10px; font-size: 0.7rem; width: 100%; }

.inline-input { width: 60px; padding: 5px; text-align: center; }

.actions-cell { display: flex; gap: 10px; }
.btn-save, .btn-cancel-shift { 
  background: none; 
  border: 1px solid #e2e8f0; 
  padding: 5px 8px; 
  border-radius: 5px; 
  cursor: pointer;
}
.btn-save:hover { background: #f0fff4; border-color: #48bb78; }
.btn-cancel-shift:hover { background: #fff5f5; border-color: #f56565; }

.row-cancelled { opacity: 0.5; text-decoration: line-through; background: #fef2f2; }

/* Alertas similares a tu ActivityManagement */
.alert { position: fixed; bottom: 30px; right: 30px; padding: 15px 30px; border-radius: 12px; z-index: 1000; font-weight: 600; }
.success { background: #def7ec; color: #03543f; border-bottom: 4px solid #31c48d; }
.error { background: #fde8e8; color: #9b1c1c; border-bottom: 4px solid #f98080; }

.empty-state, .loading-state { padding: 40px; text-align: center; color: #a0aec0; }

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.btn-clear {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: #f8fafc; /* Fondo casi blanco */
  color: #64748b;    /* Gris suave */
  border: 1px solid #e2e8f0;
  padding: 10px 16px;
  border-radius: 12px;
  font-weight: 600;
  cursor: pointer;
  height: 42px; /* Para que coincida con la altura de tus selects */
  transition: all 0.2s ease;
  white-space: nowrap;
}

.btn-clear:hover {
  background: #f1f5f9;
  color: #0d124a;
  border-color: #cbd5e1;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.btn-clear:active {
  transform: scale(0.97);
}

/* Overlay y Fondo */
.modal-overlay {
  position: fixed;
  top: 0; left: 0;
  width: 100%; height: 100%;
  background: rgba(13, 18, 74, 0.8); /* Azul oscuro traslúcido */
  backdrop-filter: blur(6px);       /* Efecto de desenfoque */
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 9999;
}

/* Caja del Diálogo */
.modal-content {
  background: white;
  padding: 40px;
  border-radius: 24px;
  text-align: center;
  max-width: 420px;
  width: 90%;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.modal-icon {
  font-size: 3rem;
  margin-bottom: 20px;
}

.modal-content h3 {
  color: #0d124a;
  font-size: 1.5rem;
  margin-bottom: 12px;
}

.modal-content p {
  color: #64748b;
  line-height: 1.6;
  margin-bottom: 30px;
}

/* Botones del Modal */
.modal-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.btn-confirm-delete {
  background: #ef4444; /* Rojo vibrante */
  color: white;
  border: none;
  padding: 14px;
  border-radius: 12px;
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-confirm-delete:hover {
  background: #dc2626;
}

.btn-cancel-modal {
  background: #f1f5f9;
  color: #475569;
  border: none;
  padding: 14px;
  border-radius: 12px;
  font-weight: 600;
  cursor: pointer;
}

.btn-cancel-modal:hover {
  background: #e2e8f0;
}

/* Animación de entrada/salida */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>