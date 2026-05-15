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
          <div class="activity-info">
            <h3 class="activity-name">{{ activity.activity_name || `Actividad ${activity.activity_id}` }}</h3>
            <p class="day-time">{{ activity.instances.length }} turno(s) disponibles</p>
          </div>
          <button type="button" class="toggle-details-btn" @click="toggleActivity(activity.activity_id)">
            {{ expandedActivityId === activity.activity_id ? 'Ocultar turnos' : 'Ver turnos' }}
          </button>
        </div>

        <div class="card-body">
          <div class="info-row">
            <span class="label">Actividad:</span>
            <span class="value">{{ activity.activity_name || `Actividad ${activity.activity_id}` }}</span>
          </div>
          <div class="info-row">
            <span class="label">Turnos con cupo:</span>
            <span class="value">{{ availableSlotsCount(activity) }}</span>
          </div>
          <div class="capacity-bar">
            <div
              class="capacity-fill"
              :style="{ width: activityFill(activity) + '%' }"
            ></div>
          </div>
          <p v-if="activityHasNoSlots(activity)" class="fully-booked-msg">Sin cupos disponibles</p>
          <p v-else class="available-slots">Elegí el turno que quieras reservar</p>

          <transition name="fade">
            <div v-if="expandedActivityId === activity.activity_id" class="turns-list">
              <div
                v-for="turno in activity.instances"
                :key="turno.id"
                class="turn-row"
                :class="{ full: isFullyBooked(turno) }"
              >
                <div class="turn-info">
                  <strong>{{ formatDate(turno.date) }}</strong>
                  <span>{{ turno.template.day_of_week }} - {{ turno.template.start_time }}hs</span>
                  <small>{{ turno.booked_count }} / {{ turno.template.capacity }} cupos</small>
                  <small class="price" v-if="turno.template.price">Precio: ${{ turno.template.price }}</small>
                </div>

                <div class="turn-actions">
                  <button
                    @click="selectInstanceForBooking(turno)"
                    :disabled="bookingInProgress"
                    class="btn-book"
                    :class="{ disabled: isFullyBooked(turno) }"
                  >
                    {{ bookingInProgress && selectedInstance?.id === turno.id ? 'Procesando...' : (isFullyBooked(turno) ? 'Sin cupos' : 'Reservar') }}
                  </button>
                  <button
                    v-if="isFullyBooked(turno)"
                    @click="joinWaitlist(turno)"
                    class="btn-waitlist"
                  >
                    Lista de espera
                  </button>
                </div>
              </div>
            </div>
          </transition>
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
            {{ bookingStatus === 'completed' || bookingStatus === 'confirmed' ? '✓' : '⏳' }}
          </div>
          <h2>{{ bookingStatus === 'completed' || bookingStatus === 'confirmed' ? '¡Reserva confirmada!' : 'Reserva pendiente de pago' }}</h2>
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
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import PaymentModal from '../components/PaymentModal.vue'

const auth = useAuthStore()
const instances = ref([])
const expandedActivityId = ref(null)
const loading = ref(false)
const bookingInProgress = ref(false)
const successMessage = ref('')
const errorMessage = ref('')
const userSuspended = ref(false)
const isUserAbonado = ref(false)

const showPaymentModal = ref(false)
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

  for (const instance of instances.value) {
    const activityId = instance.template.activity_id
    if (!groups.has(activityId)) {
      groups.set(activityId, {
        activity_id: activityId,
        activity_name: instance.activity_name,
        instances: []
      })
    }

    groups.get(activityId).instances.push(instance)
  }

  return Array.from(groups.values()).map((activity) => {
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
  return availableSlotsCount(activity) === 0
}

const activityFill = (activity) => {
  if (!activity.instances.length) return 0
  const booked = activity.instances.filter((instance) => isFullyBooked(instance)).length
  return Math.round((booked / activity.instances.length) * 100)
}

const toggleActivity = (activityId) => {
  if (expandedActivityId.value === activityId) {
    expandedActivityId.value = null
  } else {
    expandedActivityId.value = activityId
  }
}

const fetchInstances = async () => {
  loading.value = true
  try {
    const res = await axios.get('/shifts/instances')
    instances.value = res.data
  } catch (e) {
    console.error('Error al cargar clases:', e)
    instances.value = []
  } finally {
    loading.value = false
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
      { amount: pendingPaymentAmount.value },
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

  // Si el usuario cancela o se rechaza, volvemos al modal de confirmación.
  showPaymentModal.value = true
  confirmReady.value = true

  if (result.status === 'Cancelado') {
    errorMessage.value = 'Pago cancelado.'
    return
  }

  errorMessage.value = 'Pago rechazado.'
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
  fetchInstances()
  checkUserStatus()
})
</script>

<style scoped>
.booking-container {
  padding: 40px 20px;
  max-width: 1200px;
  margin: 0 auto;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  min-height: 100vh;
}

.booking-header {
  text-align: center;
  margin-bottom: 30px;
}

.booking-header h1 {
  font-size: 2.5rem;
  color: #0d124a;
  font-weight: 800;
  margin: 0 0 10px;
}

.booking-header p {
  font-size: 1.1rem;
  color: #6c757d;
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

.classes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 25px;
}

.class-card {
  background: white;
  border-radius: 15px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  border-left: 5px solid #ff6f00;
}

.class-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
}

.card-header {
  background: linear-gradient(135deg, #ff6f00 0%, #ff8c00 100%);
  color: white;
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.activity-info h3 {
  font-size: 1.3rem;
  margin: 0 0 5px;
  font-weight: 800;
}

.day-time {
  font-size: 0.9rem;
  margin: 0;
  opacity: 0.9;
}

.toggle-details-btn {
  border: 1px solid rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.12);
  color: white;
  border-radius: 999px;
  padding: 8px 14px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}

.card-body {
  padding: 20px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.info-row .label {
  font-weight: 600;
  color: #6c757d;
}

.info-row .value {
  font-weight: 700;
  color: #0d124a;
}

.capacity-bar {
  height: 8px;
  background: #e9ecef;
  border-radius: 999px;
  overflow: hidden;
  margin: 15px 0;
}

.capacity-fill {
  height: 100%;
  background: #ff6f00;
  transition: width 0.3s ease;
}

.fully-booked-msg {
  color: #dc3545;
  font-weight: 600;
  margin: 10px 0;
}

.available-slots {
  color: #28a745;
  font-weight: 600;
  margin: 10px 0;
}

.turns-list {
  margin-top: 15px;
  display: flex;
  flex-direction: column;
  gap: 12px;
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
  background: #28a745;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-book:hover:not(:disabled) {
  background: #1e7e34;
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
  background: #fff3cd;
  color: #856404;
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
  color: #28a745;
}

.modal-icon.pending {
  color: #ffc107;
}

.modal-icon.error {
  color: #dc3545;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
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
