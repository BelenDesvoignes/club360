<template>
  <div class="page">
    <div class="container">
      
      <header class="header">
        <h1>Mis créditos</h1>
        <p class="subtitle">
          Listado de tus créditos a favor por deporte. Usalos antes de su fecha de vencimiento.
        </p>
      </header>

      <section class="credits-section" aria-label="Créditos disponibles">
        
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <p>Cargando tus créditos...</p>
        </div>

        <div v-else>
          <div v-if="sortedCredits.length === 0" class="empty-state">
            No tenés créditos disponibles en este momento. 
          </div>

          <div v-else class="credits-list">
            <div 
              v-for="credit in sortedCredits" 
              :key="credit.id" 
              class="credit-row"
              :class="{ 'credit-row-used': isCreditUsed(credit.id) }"
            >
              <div class="sport-container">
                <span class="sport-name">{{ credit.activity_name || getSportName(credit.activity_id) }}</span>
              </div>

              <div class="expiry-container">
                <div class="expiry-info">
                  <span class="expiry-label">Vence el:</span>
                  <span class="expiry-date" v-if="!isCreditUsed(credit.id)">{{ formatDate(credit.expiry_date) }}</span>
                  <span class="used-label" v-else>Crédito usado en esta sesión</span>
                </div>
              </div>

              <div class="action-container">
                <button 
                  @click="handleReserveWithCredit(credit)" 
                  class="primary"
                  :disabled="isCreditUsed(credit.id)"
                >
                  {{ isCreditUsed(credit.id) ? 'Usado' : 'Solicitar clase con crédito' }}
                </button>
              </div>
            </div>
          </div>
        </div>

      </section>
    </div>

    <div v-if="isModalOpen" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        
        <div v-if="reservationSuccess" class="modal-success-state">
          <div class="success-icon">✓</div>
          <h2>¡Reserva Confirmada!</h2>
          <p>Tu clase fue reservada con éxito utilizando tu crédito.</p>
        </div>

        <div v-else>
          <header class="modal-header">
            <h2>Nueva reserva con crédito</h2>
            <p class="modal-subtitle">
              Seleccioná una clase de <strong>{{ selectedCredit?.activity_name || getSportName(selectedCredit?.activity_id) }}</strong>
            </p>
          </header>

          <div v-if="loadingInstances" class="modal-loading">
            <div class="spinner"></div>
            <p>Buscando clases disponibles...</p>
          </div>

          <div v-else class="modal-clases-scroll">
            <div v-if="filteredInstances.length === 0" class="modal-empty">
              No hay clases disponibles para esta actividad en este momento.
            </div>
            
            <div 
              v-for="instance in filteredInstances" 
              :key="instance.id" 
              class="clase-card"
              :class="{ 
                'selected': selectedInstanceId === instance.id,
                'already-booked': hasUserBooking(instance.id),
                'class-full-error': selectedInstanceId === instance.id && instance.booked_count >= instance.capacity
              }"
              @click="selectedInstanceId = instance.id"
            >
              <div class="clase-info">
                <h3>{{ getDayOfWeekName(instance.date) }}</h3>
                <p class="clase-datetime">
                  {{ formatDate(instance.date) }} — {{ instance.template?.start_time || 'Horario a confirmar' }}
                </p>
                <span class="cupos-texto">
                  Cupos: {{ instance.booked_count }}/{{ instance.capacity }}
                </span>
              </div>
            </div>
          </div>

          <div v-if="hasActiveBooking" class="error-notice-container">
            <span class="error-text-inline">⚠ Ya estás inscripto en esta clase</span>
          </div>
          <div v-else-if="isClassFull" class="error-notice-container">
            <span class="error-text-inline">⚠ No hay cupos disponibles</span>
          </div>

          <footer class="modal-actions">
            <button 
              @click="confirmReservation" 
              class="btn-confirmar" 
              :disabled="!selectedInstanceId || submittingReservation || hasActiveBooking || isClassFull"
              :class="{ 'btn-loading': submittingReservation }"
            >
              <span v-if="submittingReservation" class="btn-spinner"></span>
              <span v-else>CONFIRMAR RESERVA</span>
            </button>
            <button @click="closeModal" class="btn-cancelar" :disabled="submittingReservation">
              CANCELAR
            </button>
          </footer>
        </div>

      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const loading = ref(true)
const rawCredits = ref([])
const myBookings = ref([]) 
const usedCreditIds = ref([]) 

// Estados reactivos del Modal
const isModalOpen = ref(false)
const selectedCredit = ref(null)
const instances = ref([])
const loadingInstances = ref(false)
const selectedInstanceId = ref(null)
const submittingReservation = ref(false)
const reservationSuccess = ref(false)

const sortedCredits = computed(() => {
  return [...rawCredits.value].sort((a, b) => {
    if (!a.expiry_date) return 1
    if (!b.expiry_date) return -1
    return new Date(a.expiry_date) - new Date(b.expiry_date)
  })
})

const filteredInstances = computed(() => {
  if (!selectedCredit.value) return []
  
  return instances.value.filter(instance => {
    const instanceActivityId = instance.template?.activity_id
    if (!instanceActivityId) return false
    return Number(instanceActivityId) === Number(selectedCredit.value.activity_id)
  })
})

const hasActiveBooking = computed(() => {
  if (!selectedInstanceId.value) return false
  return hasUserBooking(selectedInstanceId.value)
})

const isClassFull = computed(() => {
  if (!selectedInstanceId.value) return false
  const target = instances.value.find(i => i.id === selectedInstanceId.value)
  if (!target) return false
  return target.booked_count >= target.capacity
})

const hasUserBooking = (instanceId) => {
  return myBookings.value.some(b => b.instance_id === instanceId && b.status !== 'Cancelled')
}

const isCreditUsed = (creditId) => {
  return usedCreditIds.value.includes(creditId)
}

const getDayOfWeekName = (dateStr) => {
  if (!dateStr) return 'Día a confirmar'
  const [year, month, day] = dateStr.split('-').map(Number)
  const dateObj = new Date(year, month - 1, day)
  
  const days = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
  return days[dateObj.getDay()]
}

const fetchMyCredits = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    const res = await axios.get('/credits/me', {
      headers: { Authorization: `Bearer ${token}` }
    })
    rawCredits.value = res.data || []
  } catch (error) {
    console.error("Error al obtener los créditos del backend:", error)
  } finally {
    loading.value = false
  }
}

const fetchMyBookings = async () => {
  try {
    const token = localStorage.getItem('token')
    const res = await axios.get('/bookings/me', {
      headers: { Authorization: `Bearer ${token}` }
    })
    myBookings.value = res.data || []
  } catch (error) {
    console.error("Error al obtener las reservas del usuario:", error)
  }
}

const fetchShiftInstances = async () => {
  loadingInstances.value = true
  try {
    const token = localStorage.getItem('token')
    const res = await axios.get('/shifts/instances', {
      headers: { Authorization: `Bearer ${token}` }
    })
    instances.value = res.data || []
  } catch (error) {
    console.error("Error al traer las instancias de turnos desde el servidor:", error)
  } finally {
    loadingInstances.value = false
  }
}

const getSportName = (activityId) => {
  const sports = {
    1: 'Fútbol',
    2: 'Vóley',
    3: 'Pádel',
    4: 'Básquet'
  }
  return sports[activityId] || 'Deporte General'
}

const formatDate = (dateStr) => {
  if (!dateStr) return 'Fin de mes'
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'UTC' })
}

const handleReserveWithCredit = async (credit) => {
  if (isCreditUsed(credit.id)) return
  selectedCredit.value = credit
  selectedInstanceId.value = null
  isModalOpen.value = true
  
  await Promise.all([fetchShiftInstances(), fetchMyBookings()])
}

const closeModal = () => {
  if (submittingReservation.value) return
  isModalOpen.value = false
  selectedCredit.value = null
  selectedInstanceId.value = null
  reservationSuccess.value = false
}

const confirmReservation = async () => {
  if (!selectedInstanceId.value || !selectedCredit.value || hasActiveBooking.value) return
  
  submittingReservation.value = true
  const creditIdTarget = selectedCredit.value.id
  
  try {
    const token = localStorage.getItem('token')
    
    await axios.post(
      `/bookings/reserve-with-credit?instance_id=${selectedInstanceId.value}&credit_id=${creditIdTarget}`,
      {}, 
      { headers: { Authorization: `Bearer ${token}` } }
    )
    
    if (!usedCreditIds.value.includes(creditIdTarget)) {
      usedCreditIds.value.push(creditIdTarget)
    }
    localStorage.setItem('used_credits_session', JSON.stringify(usedCreditIds.value))
    
    reservationSuccess.value = true
    
    setTimeout(async () => {
      closeModal()
      await fetchMyCredits()
    }, 2200)

  } catch (error) {
    const errorDetail = error.response?.data?.detail || "No se pudo procesar la reserva con crédito"
    alert(`Error: ${errorDetail}`)
    console.error("Error en reserva por crédito:", error.response)
  } finally {
    submittingReservation.value = false
  }
}

onMounted(() => {
  fetchMyCredits()
})
</script>

<style scoped>
.page {
  width: 100%;
  padding: 28px 40px 40px;
  max-width: 1200px;
  margin: 0 auto;
  min-height: 100vh;
  background: transparent;
}

.container {
  max-width: none;
  margin: 0;
}

.header {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-bottom: 18px;
}

.header h1 {
  font-size: 2.5rem;
  color: #2d658d;
  font-weight: 900;
  margin: 0 0 10px;
}

.subtitle {
  margin: 0;
  color: #5a8849;
  font-weight: 400;
  font-size: 1.1rem;
}

.credits-section {
  background: white;
  border-radius: 14px;
  padding: 18px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
}

.empty-state {
  padding: 14px;
  border-radius: 12px;
  border: 1px dashed rgba(45, 101, 141, 0.35);
  color: #2d658d;
  background: rgba(45, 101, 141, 0.06);
  font-size: 1rem;
}

.credits-list {
  display: flex;
  flex-direction: column;
}

.credit-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 8px;
  border-bottom: 1px solid rgba(13, 18, 74, 0.08);
  gap: 20px;
  transition: background-color 0.2s ease, opacity 0.2s ease;
}

.credit-row:last-child {
  border-bottom: none;
}

.credit-row-used {
  background-color: #f9fafb;
  opacity: 0.65;
}

.sport-container {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 180px;
}

.sport-name {
  font-size: 1.1rem;
  font-weight: 700;
  color: #0d124a;
}

.expiry-container {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 160px;
}

.expiry-info {
  display: flex;
  flex-direction: column;
}

.expiry-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  font-weight: 700;
  color: #9ca3af;
  letter-spacing: 0.5px;
}

.expiry-date {
  font-size: 0.95rem;
  font-weight: 700;
  color: #b43b3b;
}

.used-label {
  font-size: 0.9rem;
  font-weight: 700;
  color: #6b7280;
}

.primary {
  border: none;
  border-radius: 12px;
  padding: 12px 20px;
  font-size: 1rem;
  font-weight: 800;
  color: white;
  background: #5a8849;
  cursor: pointer;
  transition: all 0.12s ease;
  white-space: nowrap;
}

.primary:hover:not(:disabled) {
  filter: brightness(0.98);
}

.primary:active:not(:disabled) {
  transform: translateY(1px);
}

.primary:disabled {
  background: #d1d5db !important;
  color: #9ca3af !important;
  cursor: not-allowed;
}

.loading-state {
  padding: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #0d124a;
  font-weight: 700;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid rgba(45, 101, 141, 0.15);
  border-radius: 50%;
  border-top-color: #2d658d;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(13, 18, 74, 0.45);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.modal-content {
  background: white;
  width: 100%;
  max-width: 550px;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  animation: modalScale 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes modalScale {
  from { transform: scale(0.95); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.modal-header h2 {
  font-size: 1.5rem;
  color: #2d658d;
  font-weight: 900;
  margin: 0 0 6px;
}

.modal-subtitle {
  margin: 0 0 18px;
  color: #666;
  font-size: 0.95rem;
}

.modal-clases-scroll {
  max-height: 340px;
  overflow-y: auto;
  padding-right: 6px;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.modal-clases-scroll::-webkit-scrollbar {
  width: 6px;
}
.modal-clases-scroll::-webkit-scrollbar-thumb {
  background: rgba(13, 18, 74, 0.15);
  border-radius: 4px;
}

.modal-empty {
  padding: 20px;
  text-align: center;
  color: #6b7280;
  border: 1px dashed rgba(0,0,0,0.1);
  border-radius: 12px;
}

.modal-loading {
  padding: 40px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: #0d124a;
}

.clase-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: #fff5ee;
  border: 2px solid #ffe4d1;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.clase-card:hover {
  background: #ffede0;
  border-color: #ff9e59;
}

.clase-card.selected {
  background: #ffebd9;
  border-color: #ff7300; 
  box-shadow: 0 4px 12px rgba(255, 115, 0, 0.15);
}

/* Estilos refinados para el aviso dinámico de validación previa */
.clase-card.already-booked {
  border-color: #fca5a5 !important;
  background: #fef2f2 !important;
}

.error-notice-container {
  padding: 0 4px 12px;
  text-align: left;
}

.error-text-inline {
  color: #dc2626;
  font-weight: 400; 
  font-size: 0.85rem; 
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.clase-info {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.clase-info h3 {
  margin: 0 0 4px;
  font-size: 1.05rem;
  color: #0d124a;
  font-weight: 800;
}

.clase-datetime {
  margin: 0 0 6px;
  font-size: 0.88rem;
  color: #4b5563;
}

.cupos-texto {
  font-size: 0.85rem;
  color: #0d124a;
  font-weight: 700;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  border-top: 1px solid rgba(0,0,0,0.06);
  padding-top: 16px;
}

.btn-confirmar {
  background: #2d658d;
  color: white;
  border: none;
  border-radius: 12px;
  padding: 12px 24px;
  font-weight: 800;
  cursor: pointer;
  font-size: 0.95rem;
  transition: opacity 0.15s;
}

.btn-confirmar:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.btn-confirmar:not(:disabled):hover {
  opacity: 0.9;
}

.btn-confirmar.btn-loading {
  background: #9ca3af !important;
  cursor: not-allowed;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.btn-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 0.6s linear infinite;
}

.btn-cancelar {
  background: #f3f4f6;
  color: #4b5563;
  border: none;
  border-radius: 12px;
  padding: 12px 20px;
  font-weight: 700;
  cursor: pointer;
  font-size: 0.95rem;
}

.btn-cancelar:hover {
  background: #e5e7eb;
}

.modal-success-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

.success-icon {
  width: 60px;
  height: 60px;
  background: #5a8849;
  color: white;
  font-size: 2rem;
  font-weight: bold;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  animation: scaleIn 0.3s ease;
}

@keyframes scaleIn {
  from { transform: scale(0); }
  to { transform: scale(1); }
}

@media (max-width: 768px) {
  .credit-row {
    flex-direction: column;
    align-items: flex-start;
    padding: 16px 4px;
    gap: 14px;
  }
  .sport-container, 
  .expiry-container,
  .action-container {
    width: 100%;
  }
  .primary {
    width: 100%;
    text-align: center;
  }
  .modal-content {
    width: 92%;
    padding: 16px;
  }
}
</style>