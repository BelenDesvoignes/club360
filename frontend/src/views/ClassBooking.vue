<template>
  <div class="booking-container">
    <header class="booking-header">
      <h1>Reservar Clase</h1>
      <p>Selecciona una clase y confirma tu reserva</p>
    </header>

    <!-- Advertencia si está suspendido -->
    <div v-if="userSuspended" class="suspension-warning">
      <div class="warning-icon">🚫</div>
      <div class="warning-content">
        <h3>Tu cuenta está suspendida</h3>
        <p>Debes solicitar reactivación para poder hacer nuevas reservas. Contacta al soporte para resolver esto.</p>
      </div>
    </div>

    <div v-if="loading" class="loading-spinner">Cargando clases disponibles...</div>

      <div v-if="successMessage" :class="['booking-feedback', bookingStatus]">
      <div>
        <strong>{{ bookingStatus === 'confirmed' ? '¡Reserva confirmada!' : bookingStatus === 'cancelled' ? 'Reserva cancelada' : 'Reserva pendiente de pago' }}</strong>
        <p>{{ successMessage }}</p>
      </div>
      <button type="button" class="booking-feedback-close" @click="successMessage = ''">Cerrar</button>
    </div>

    <div v-else-if="userSuspended" class="suspended-block">
      <p>No puedes hacer reservas mientras tu cuenta esté suspendida.</p>
    </div>

    <div v-else class="classes-grid">
      <div
        v-for="activity in groupedActivities"
        :key="`${activity.activity_id}`"
        class="class-card"
      >
        <div class="card-header">
          <h3 class="activity-name">{{ activity.activity_name || `Actividad ${activity.activity_id}` }}</h3>
          <span v-if="activity.instances.length > 0" class="activity-meta">
            {{ activity.instances.length === 1 ? '1 turno' : `${activity.instances.length} turnos` }}
          </span>
          <span v-else class="activity-meta disabled">Sin turnos</span>
        </div>

        <div class="card-modal-body">
          <div v-if="activity.instances.length > 0" class="turns-inline">
            <div
              v-for="turno in activity.instances"
              :key="turno.id"
              class="turn-row turn-row-inline"
            >
              <div class="turn-info">
                <strong>{{ turno.template.start_time }}hs · {{ turno.template.day_of_week }}</strong>
                <span>{{ turno.court || 'Sin cancha' }}</span>
                <small>Cupos: {{ turno.booked_count }}/{{ turno.template.capacity }}</small>
                <small class="price">${{ turno.template.price }}</small>
              </div>
              <div class="turn-actions">
                <button
                  @click="selectInstanceForBooking(turno)"
                  :disabled="isFullyBooked(turno) || bookingInProgress"
                  class="btn-book"
                  :class="{ disabled: isFullyBooked(turno) }"
                >
                  {{ bookingInProgress && selectedInstance?.id === turno.id ? 'Procesando...' : (isFullyBooked(turno) ? 'Sin cupos' : 'Reservar') }}
                </button>
              </div>
            </div>
          </div>

          <div v-else class="no-turnos card-empty-inline">
            No hay turnos disponibles para esta actividad
          </div>
        </div>
      </div>

      <div v-if="groupedActivities.length === 0" class="empty-state">
        Todavía no hay clases cargadas para mostrar.
      </div>
    </div>

    <!-- Modal para confirmar reserva y pago -->
    <transition name="fade">
      <div v-if="showPaymentModal" class="modal-overlay" @click.self="closePaymentModal">
        <div class="modal-content payment-modal" @click.stop>
          <button class="modal-close" @click="closePaymentModal">✕</button>
          
          <h2>Confirmar Reserva</h2>
          
          <div class="payment-info">
            <div class="info-row">
              <span class="label">Clase:</span>
              <span class="value">{{ selectedInstance?.activity_name || 'Clase seleccionada' }}</span>
            </div>
            <div class="info-row">
              <span class="label">Fecha:</span>
              <span class="value">{{ formatDate(selectedInstance?.date) }}</span>
            </div>
            <div class="info-row">
              <span class="label">Horario:</span>
              <span class="value">{{ selectedInstance?.template.start_time }}hs</span>
            </div>
            <div class="info-row highlight">
              <span class="label">Precio:</span>
              <span class="value price-amount">${{ selectedInstance?.template.price }}</span>
            </div>
          </div>

          <div v-if="!isUserAbonado" class="payment-options">
            <h3>Opciones de Pago</h3>
            <p class="payment-note">Como cliente no abonado, debes abonar al menos el 50% (seña)</p>
            
            <div class="option">
              <input
                type="radio"
                id="payment-seña"
                v-model="paymentType"
                value="seña"
              />
              <label for="payment-seña">
                <strong>Pagar 50% (Seña)</strong>
                <span>${{ (selectedInstance?.template.price * 0.5).toFixed(2) }}</span>
              </label>
            </div>

            <div class="option">
              <input
                type="radio"
                id="payment-full"
                v-model="paymentType"
                value="full"
              />
              <label for="payment-full">
                <strong>Pagar 100% (Completo)</strong>
                <span>${{ selectedInstance?.template.price }}</span>
              </label>
            </div>

            <p class="payment-warning">⚠️ Sin pagar ahora, la reserva quedará pendiente de pago y podrá cancelarse.</p>
          </div>

          <div v-else class="abonado-info">
            <p class="success-text">✓ Como cliente abonado, tu reserva será confirmada automáticamente.</p>
          </div>

          <div class="modal-actions">
            <button @click="closePaymentModal" class="btn btn-secondary">Cancelar</button>
            <button @click="confirmBooking" :disabled="bookingInProgress || !confirmReady" class="btn btn-primary">
              {{ bookingInProgress ? 'Procesando...' : 'Confirmar Reserva' }}
            </button>
          </div>
        </div>
      </div>
    </transition>

    <PaymentModal
      v-model="showGatewayModal"
      :amount="pendingPaymentAmount"
      :payeeName="selectedInstance?.activity_name || 'Reserva'"
      @result="onGatewayResult"
    />

    <!-- Modal de éxito -->
    <transition name="fade">
      <div v-if="successMessage" class="modal-overlay" @click="successMessage = ''">
        <div class="modal-content" @click.stop>
          <div :class="['modal-icon', bookingStatus]">
            {{ bookingStatus === 'completed' || bookingStatus === 'confirmed' ? '✓' : bookingStatus === 'cancelled' ? '⨯' : '⏳' }}
          </div>
          <h2>{{ bookingStatus === 'completed' || bookingStatus === 'confirmed' ? '¡Reserva confirmada!' : bookingStatus === 'cancelled' ? 'Reserva cancelada' : 'Reserva pendiente de pago' }}</h2>
          <p>{{ successMessage }}</p>
          <button @click="successMessage = ''" class="btn btn-primary">Cerrar</button>
        </div>
      </div>
    </transition>

    <!-- Modal de error -->
    <transition name="fade">
      <div v-if="errorMessage" class="modal-overlay error" @click="errorMessage = ''">
        <div class="modal-content" @click.stop>
          <div class="modal-icon error">✕</div>
          <h2>Error en la reserva</h2>
          <p>{{ errorMessage }}</p>
          <button @click="errorMessage = ''" class="btn btn-primary">Cerrar</button>
        </div>
      </div>
    </transition>

    <!-- Modal para seleccionar turno por actividad -->
    <transition name="fade">
      <div v-if="showTurnosModal" class="modal-overlay" @click="closeTurnosModal">
        <div class="modal-content turnos-modal" @click.stop>
          <button class="modal-close" @click="closeTurnosModal">✕</button>
          
          <h2>{{ selectedActivity?.activity_name }} - Turnos disponibles</h2>
          
          <div v-if="selectedActivity && selectedActivity.instances.length > 0" class="turnos-container">
            <div
              v-for="turno in selectedActivity.instances"
              :key="turno.id"
              class="turno-card"
              :class="{ 'full': isFullyBooked(turno) }"
            >
              <div class="turno-header">
                <div class="turno-date">{{ formatDate(turno.date) }}</div>
                <div class="turno-badge" :class="isFullyBooked(turno) ? 'full' : 'available'">
                  {{ isFullyBooked(turno) ? 'Sin cupos' : 'Disponible' }}
                </div>
              </div>

              <div class="turno-details">
                <div class="detail-row">
                  <span class="detail-label">Horario:</span>
                  <span class="detail-value">{{ turno.template.start_time }}hs</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">Día:</span>
                  <span class="detail-value">{{ turno.template.day_of_week }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">Cupos:</span>
                  <span class="detail-value">{{ turno.booked_count }} / {{ turno.template.capacity }}</span>
                </div>
                <div class="detail-row price-row">
                  <span class="detail-label">Precio:</span>
                  <span class="detail-value price">${{ turno.template.price }}</span>
                </div>
              </div>

              <button
                @click="selectInstanceForBooking(turno)"
                :disabled="isFullyBooked(turno) || bookingInProgress"
                class="btn-turno-reserve"
                :class="{ disabled: isFullyBooked(turno) }"
              >
                {{ bookingInProgress && selectedInstance?.id === turno.id ? 'Procesando...' : (isFullyBooked(turno) ? 'Sin cupos' : 'Reservar') }}
              </button>
            </div>
          </div>

          <div v-else class="no-turnos">
            No hay turnos disponibles para esta actividad
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import PaymentModal from '../components/PaymentModal.vue'

const auth = useAuthStore()
const dayOrder = {
  Lunes: 1,
  Martes: 2,
  'Miércoles': 3,
  Jueves: 4,
  Viernes: 5,
  Sábado: 6,
  Domingo: 7
}

const sortShifts = (shiftsArray) => {
  if (!shiftsArray) return []

  return shiftsArray.slice().sort((a, b) => {
    const orderA = dayOrder[a.day_of_week] || 99
    const orderB = dayOrder[b.day_of_week] || 99

    if (orderA !== orderB) return orderA - orderB
    return (a.start_time || '').localeCompare(b.start_time || '')
  })
}

const activities = ref([])
const instances = ref([])
const loading = ref(false)
const bookingInProgress = ref(false)
const successMessage = ref('')
const errorMessage = ref('')
const userSuspended = ref(false)
const isUserAbonado = ref(false)

const showPaymentModal = ref(false)
const showTurnosModal = ref(false)
const selectedActivity = ref(null)
const selectedInstance = ref(null)
const paymentType = ref('seña')
const bookingStatus = ref('pending')

const confirmReady = ref(false)
const showGatewayModal = ref(false)
const pendingPaymentAmount = ref(0)

function computeAmountToPay() {
  const price = Number(selectedInstance.value?.template?.price || 0)
  if (!Number.isFinite(price) || price <= 0) return 0
  return paymentType.value === 'full' ? price : price * 0.5
}

const groupedActivities = computed(() => {
  const groups = new Map()
  const activityIdToKey = new Map()
  const normalizeStr = (str) => str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim()

  for (const activity of activities.value) {
    const groupKey = normalizeStr(activity.name || `actividad-${activity.id}`)

    if (!groups.has(groupKey)) {
      activityIdToKey.set(activity.id, groupKey)
      groups.set(groupKey, {
        activity_id: activity.id,
        activity_name: activity.name,
        court: activity.court,
        templates: activity.templates ? sortShifts(JSON.parse(JSON.stringify(activity.templates))) : [],
        instances: []
      })
      continue
    }

    const existing = groups.get(groupKey)
    if ((!existing.templates || existing.templates.length === 0) && activity.templates && activity.templates.length > 0) {
      existing.activity_id = activity.id
      existing.activity_name = activity.name
      existing.court = activity.court
      existing.templates = sortShifts(JSON.parse(JSON.stringify(activity.templates)))
    }
  }

  for (const instance of instances.value) {
    const activityKey = activityIdToKey.get(instance.template.activity_id) || normalizeStr(instance.activity_name || `actividad-${instance.template.activity_id}`)
    if (!groups.has(activityKey)) {
      groups.set(activityKey, {
        activity_id: instance.template.activity_id,
        activity_name: instance.activity_name,
        court: instance.court || '',
        templates: [instance.template],
        instances: []
      })
    }

    const activityGroup = groups.get(activityKey)
    // Add all instances (not just first one per activity)
    activityGroup.instances.push(instance)
  }

  return Array.from(groups.values()).map((activity) => {
    activity.templates = sortShifts(activity.templates || [])
    activity.instances.sort((a, b) => new Date(a.date) - new Date(b.date))
    return activity
  })
})

const formatDate = (dateStr) => {
  if (!dateStr) return 'Sin fecha'
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-AR', { day: '2-digit', month: 'long', year: 'numeric' })
}

const isFullyBooked = (instance) => {
  return instance.booked_count >= instance.template.capacity
}

const availableSlotsCount = (activity) => {
  return activity.instances.filter((instance) => !isFullyBooked(instance)).length
}

const activityHasNoSlots = (activity) => {
  return activity.instances.length > 0 && availableSlotsCount(activity) === 0
}

const activityHasNoFutureInstances = (activity) => {
  return activity.instances.length === 0
}

const activityFill = (activity) => {
  if (!activity.instances.length) return 0
  const booked = activity.instances.filter((instance) => isFullyBooked(instance)).length
  return Math.round((booked / activity.instances.length) * 100)
}

const fetchInstances = async () => {
  try {
    // Add cache busting and timeout to prevent slow loads
    const res = await axios.get('/shifts/instances', {
      timeout: 5000
    })
    instances.value = res.data
  } catch (e) {
    console.error('Error al cargar clases:', e)
    instances.value = []
  }
}

const fetchActivities = async () => {
  try {
    const res = await axios.get('/activities/')
    // Deduplicar actividades por nombre normalizado, priorizando las que tengan templates
    const normalizeStr = (str) => str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim()
    const seenNames = new Map()
    res.data.forEach(activity => {
      const key = normalizeStr(activity.name)
      if (!seenNames.has(key) || (activity.templates && activity.templates.length > 0)) {
        seenNames.set(key, activity)
      }
    })
    activities.value = Array.from(seenNames.values())
  } catch (e) {
    console.error('Error al cargar actividades:', e)
    activities.value = []
  }
}

const checkUserStatus = async () => {
  try {
    auth.hydrateFromToken()
    const token = auth.token || localStorage.getItem('token')
    
    if (!token) return
    
    // Get user info via debug endpoint (TODO: crear endpoint público de /me)
    const res = await axios.get('/bookings/debug/auth', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    
    // For now, assume not suspended (TODO: verificar con endpoint de usuario)
    userSuspended.value = false
  } catch (e) {
    console.error('Error al verificar estado:', e)
  }
}

const selectInstanceForBooking = (instance) => {
  if (isFullyBooked(instance)) {
    joinWaitlist(instance)
    return
  }
  
  selectedInstance.value = {
    ...instance,
    activity_name: groupedActivities.value
      .find(a => a.activity_id === instance.template.activity_id)
      ?.activity_name
  }
  
  // Check if user is abonado for this activity
  checkAbonado(instance.template.activity_id)

  confirmReady.value = false
  showPaymentModal.value = true
  setTimeout(() => {
    confirmReady.value = true
  }, 300)
}

const checkAbonado = async (activity_id) => {
  try {
    auth.hydrateFromToken()
    const token = auth.token || localStorage.getItem('token')
    
    if (!token) {
      isUserAbonado.value = false
      return
    }
    
    // TODO: crear endpoint para verificar si es abonado
    isUserAbonado.value = false
  } catch (e) {
    isUserAbonado.value = false
  }
}

const closePaymentModal = () => {
  showPaymentModal.value = false
  selectedInstance.value = null
  paymentType.value = 'seña'
  confirmReady.value = false
}

async function finalizeBookingWithPayment() {
  auth.hydrateFromToken()
  const token = auth.token || localStorage.getItem('token')

  if (!token) {
    errorMessage.value = 'Tu sesión expiró. Iniciá sesión nuevamente.'
    return
  }

  const res = await axios.post('/bookings/', {
    instance_id: selectedInstance.value.id
  }, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  })

  if (pendingPaymentAmount.value > 0) {
    await axios.post(
      '/payments/me/complete-booking',
      { amount: pendingPaymentAmount.value, booking_id: res.data.id },
      { headers: { Authorization: `Bearer ${token}` } }
    )
  }

  bookingStatus.value = 'completed'
  successMessage.value = `¡Tu reserva fue confirmada y el pago fue exitoso! Número de reserva: ${res.data.id}`
  closePaymentModal()

  setTimeout(() => {
    fetchInstances()
  }, 1500)
}

function onGatewayResult(result) {
  if (!result) return
  if (result.status === 'Aprobado') {
    finalizeBookingWithPayment().catch((e) => {
      const detail = e.response?.data?.detail || 'Error al procesar la reserva'
      errorMessage.value = detail
    })
    return
  }

  if (result.status === 'Cancelado') {
    showGatewayModal.value = false
    closePaymentModal()
    return
  }

  errorMessage.value = 'Pago rechazado.'
}

const openTurnosModal = (activity) => {
  selectedActivity.value = activity
  showTurnosModal.value = true
}

const closeTurnosModal = () => {
  showTurnosModal.value = false
  selectedActivity.value = null
}

const confirmBooking = async () => {
  if (!selectedInstance.value) return

  bookingInProgress.value = true

  try {
    auth.hydrateFromToken()
    const token = auth.token || localStorage.getItem('token')

    if (!token) {
      errorMessage.value = 'Tu sesión expiró. Iniciá sesión nuevamente.'
      return
    }

    const price = Number(selectedInstance.value?.template?.price || 0)
    if (!Number.isFinite(price) || price <= 0) {
      errorMessage.value = 'No se pudo determinar el precio de la clase.'
      return
    }

    // Abonado: reserva directa.
    if (isUserAbonado.value) {
      const res = await axios.post('/bookings/', {
        instance_id: selectedInstance.value.id
      }, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      bookingStatus.value = res.data.status === 'Confirmed' ? 'completed' : 'pending'
      successMessage.value =
        bookingStatus.value === 'completed'
          ? `¡Tu reserva ha sido confirmada! Número de reserva: ${res.data.id}`
          : `Tu reserva está pendiente. Número de reserva: ${res.data.id}.`

      closePaymentModal()
      setTimeout(() => {
        fetchInstances()
      }, 1500)
      return
    }

    // No abonado: abrir PaymentModal (requiere apretar "Pagar").
    pendingPaymentAmount.value = computeAmountToPay()
    if (!pendingPaymentAmount.value) {
      errorMessage.value = 'No se pudo determinar el monto a pagar.'
      return
    }

    showPaymentModal.value = false
    showGatewayModal.value = true
  } catch (e) {
    const detail = e.response?.data?.detail || 'Error al procesar la reserva'
    errorMessage.value = detail
    console.error('Error al crear reserva:', e)
  } finally {
    bookingInProgress.value = false
  }
}

const joinWaitlist = async (instance) => {
  try {
    auth.hydrateFromToken()
    const token = auth.token || localStorage.getItem('token')

    if (!token) {
      errorMessage.value = 'Tu sesión expiró. Iniciá sesión nuevamente.'
      return
    }

    // TODO: implementar endpoint de waitlist
    errorMessage.value = 'Sistema de lista de espera en desarrollo. Intenta más tarde.'
  } catch (e) {
    errorMessage.value = 'Error al unirse a la lista de espera'
  }
}

onMounted(() => {
  loading.value = true
  Promise.all([fetchActivities(), fetchInstances()])
    .finally(() => {
      loading.value = false
    })
  checkUserStatus()
})
</script>

<style scoped>
.booking-container {
  padding: 40px 20px;
  max-width: 1200px;
  margin: 0 auto;
  background: linear-gradient(135deg, rgba(45, 101, 141, 0.08) 0%, rgba(90, 136, 73, 0.08) 52%, rgba(255, 111, 0, 0.08) 100%);
  min-height: 100vh;
}

.booking-header {
  text-align: center;
  margin-bottom: 30px;
}

.booking-header h1 {
  font-size: 2.5rem;
  color: #2d658d;
  font-weight: 800;
  margin: 0 0 10px;
}

.booking-header p {
  font-size: 1.1rem;
  color: #5a8849;
  margin: 0;
}

.suspension-warning {
  background: #f8d7da;
  border-left: 5px solid #dc3545;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 30px;
  display: flex;
  gap: 15px;
  align-items: flex-start;
}

.warning-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.warning-content h3 {
  margin: 0 0 5px;
  color: #721c24;
}

.warning-content p {
  margin: 0;
  color: #721c24;
}

.suspended-block {
  background: white;
  padding: 40px;
  border-radius: 15px;
  text-align: center;
  color: #6c757d;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.loading-spinner {
  text-align: center;
  font-size: 1.2rem;
  color: #6c757d;
  padding: 60px 20px;
}

.booking-feedback {
  max-width: 1100px;
  margin: 0 auto 24px;
  padding: 18px 20px;
  border-radius: 16px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
}

.booking-feedback.confirmed {
  background: linear-gradient(135deg, #eff6ff, #e8f3ec);
  border: 1px solid rgba(45, 101, 141, 0.22);
  color: #2d658d;
}

.booking-feedback.pending {
  background: linear-gradient(135deg, #fff7f0, #fff0e0);
  border: 1px solid rgba(255, 111, 0, 0.22);
  color: #ff6f00;
}

.booking-feedback.cancelled {
  background: linear-gradient(135deg, #fff7ed, #fef3c7);
  border: 1px solid rgba(255, 111, 0, 0.28);
  color: #b45309;
}

.booking-feedback p {
  margin: 6px 0 0;
  line-height: 1.5;
}

.booking-feedback-close {
  border: none;
  background: rgba(255, 255, 255, 0.65);
  color: inherit;
  border-radius: 999px;
  padding: 10px 16px;
  font-weight: 600;
  cursor: pointer;
  flex-shrink: 0;
}

.booking-feedback-close:hover {
  background: rgba(255, 255, 255, 0.9);
}

.classes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.class-card {
  background: linear-gradient(180deg, #ffffff 0%, #fff9f4 100%);
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 18px 45px rgba(17, 24, 39, 0.12);
  transition: all 0.3s ease;
  border: 1px solid rgba(45, 101, 141, 0.12);
  display: flex;
  flex-direction: column;
}

.class-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 24px 55px rgba(17, 24, 39, 0.16);
}

.card-header {
  background: linear-gradient(135deg, #2d658d 0%, #5a8849 60%, #ff6f00 100%);
  color: white;
  padding: 18px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.activity-name {
  font-size: 1.1rem;
  margin: 0;
  font-weight: 800;
  flex: 1;
}

.activity-meta {
  font-size: 0.8rem;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.95);
  background: rgba(255, 255, 255, 0.16);
  border: 1px solid rgba(255, 255, 255, 0.18);
  padding: 6px 10px;
  border-radius: 999px;
  white-space: nowrap;
}

.activity-meta.disabled {
  background: rgba(255, 255, 255, 0.1);
  opacity: 0.8;
}

.activity-info h3 {
  font-size: 1.2rem;
  margin: 0 0 4px;
  font-weight: 800;
}

.day-time {
  font-size: 0.8rem;
  margin: 0;
  opacity: 0.85;
}

.reserve-direct-btn {
  background: linear-gradient(135deg, #2d658d, #5a8849, #ff6f00);
  border: none;
}

.reserve-direct-btn:hover {
  background: linear-gradient(135deg, #24506f, #4d733d, #e65f00);
  box-shadow: 0 6px 20px rgba(45, 101, 141, 0.35);
}

.card-body {
  display: none;
}

.card-footer-actions {
  display: none;
}

.card-modal-body {
  padding: 18px;
}

.turns-inline {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.turn-row-inline {
  margin: 0;
  padding: 16px;
  background: #ffffff;
  border: 1px solid rgba(90, 136, 73, 0.18);
  box-shadow: 0 10px 24px rgba(17, 24, 39, 0.08);
}

.no-turnos.card-empty-inline {
  margin: 0;
  padding: 16px;
  border-radius: 14px;
  background: linear-gradient(135deg, #eff6ff, #fff7f0);
  border: 1px dashed rgba(45, 101, 141, 0.35);
  color: #2d658d;
  font-weight: 600;
  text-align: center;
}

.turn-row {
  border: 1px solid #edf2f7;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fbfdff;
  gap: 12px;
}

.turn-info {
  flex: 1;
}

.turn-info strong {
  display: block;
  color: #0d124a;
  font-size: 1.1rem;
  margin-bottom: 4px;
}

.turn-info span {
  display: block;
  color: #6c757d;
  font-size: 0.9rem;
}

.turn-info small {
  display: block;
  color: #999;
  font-size: 0.8rem;
  margin-top: 4px;
}

.price {
  color: #ff6f00 !important;
  font-weight: 600 !important;
}

.turn-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.btn-book {
  padding: 10px 16px;
  background: linear-gradient(135deg, #5a8849, #2d658d);
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-book:hover:not(:disabled) {
  background: linear-gradient(135deg, #4c763e, #24506f);
  transform: scale(1.05);
}

.btn-book:disabled,
.btn-book.disabled {
  background: #ccc;
  cursor: not-allowed;
  opacity: 0.6;
}

.btn-waitlist {
  padding: 10px 16px;
  background: #ffc107;
  color: #000;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.3s ease;
}

.btn-waitlist:hover {
  background: #e0a800;
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 30px;
  border-radius: 15px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
}

.payment-modal {
  text-align: left;
}

.modal-close {
  position: absolute;
  top: 15px;
  right: 15px;
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6c757d;
}

.modal-content h2 {
  margin: 0 0 20px;
  color: #0d124a;
  font-weight: 800;
}

.payment-info {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.payment-info .info-row {
  margin-bottom: 8px;
  align-items: center;
}

.payment-info .label {
  font-weight: 600;
  color: #6c757d;
}

.payment-info .value {
  font-weight: 700;
  color: #0d124a;
}

.price-amount {
  color: #ff6f00;
  font-size: 1.2rem;
}

.payment-options {
  margin-bottom: 20px;
}

.payment-options h3 {
  margin: 0 0 10px;
  color: #0d124a;
  font-size: 1rem;
}

.payment-note {
  font-size: 0.9rem;
  color: #6c757d;
  margin-bottom: 15px;
}

.option {
  display: flex;
  align-items: center;
  padding: 12px;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.option:hover {
  border-color: #ff6f00;
  background: #fff8f0;
}

.option input[type="radio"] {
  margin-right: 12px;
  cursor: pointer;
}

.option label {
  flex: 1;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.option label strong {
  color: #0d124a;
}

.option label span {
  color: #ff6f00;
  font-weight: 700;
  font-size: 1.1rem;
}

.payment-warning {
  background: #fff7ed;
  color: #b45309;
  padding: 10px;
  border-radius: 6px;
  font-size: 0.9rem;
  margin-bottom: 0;
}

.abonado-info {
  background: #d4edda;
  border: 1px solid #c3e6cb;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 20px;
}

.abonado-info .success-text {
  color: #155724;
  margin: 0;
  font-weight: 600;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 20px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-primary {
  background: #ff6f00;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #ff5500;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
}

.modal-icon {
  font-size: 3rem;
  margin-bottom: 15px;
  text-align: center;
}

.modal-icon.confirmed {
  color: #5a8849;
}

.modal-icon.pending {
  color: #ff6f00;
}

.modal-icon.error {
  color: #dc3545;
}

.modal-icon.cancelled {
  color: #ff6f00;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
}

/* Turnos Modal Styles */
.turnos-modal {
  max-width: 600px;
  max-height: 90vh;
}

.turnos-modal h2 {
  margin: 0 0 25px;
  color: #0d124a;
  font-weight: 800;
  font-size: 1.4rem;
}

.turnos-container {
  display: flex;
  flex-direction: column;
  gap: 15px;
  max-height: calc(90vh - 200px);
  overflow-y: auto;
  padding-right: 8px;
}

.turno-card {
  border: 2px solid #e9ecef;
  border-radius: 12px;
  padding: 16px;
  background: #fbfdff;
  transition: all 0.3s ease;
}

.turno-card:hover:not(.full) {
  border-color: #ff6f00;
  box-shadow: 0 4px 12px rgba(255, 111, 0, 0.1);
}

.turno-card.full {
  opacity: 0.7;
  background: #f8f9fa;
}

.turno-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.turno-date {
  font-size: 1.1rem;
  font-weight: 700;
  color: #0d124a;
}

.turno-badge {
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.turno-badge.available {
  background: #d4edda;
  color: #155724;
}

.turno-badge.full {
  background: #f8d7da;
  color: #721c24;
}

.turno-details {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 14px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9rem;
}

.detail-label {
  color: #6c757d;
  font-weight: 600;
}

.detail-value {
  color: #0d124a;
  font-weight: 700;
}

.detail-value.price {
  color: #ff6f00;
  font-size: 1rem;
}

.price-row {
  grid-column: 1 / -1;
  justify-content: space-between;
}

.btn-turno-reserve {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #5a8849, #2d658d);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-turno-reserve:hover:not(:disabled):not(.disabled) {
  background: linear-gradient(135deg, #4c763e, #24506f);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(45, 101, 141, 0.28);
}

.btn-turno-reserve:disabled,
.btn-turno-reserve.disabled {
  background: #ccc;
  cursor: not-allowed;
  opacity: 0.6;
}

.no-turnos {
  text-align: center;
  padding: 40px 20px;
  color: #6c757d;
  font-size: 1rem;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>