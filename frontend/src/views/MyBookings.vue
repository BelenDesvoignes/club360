<template>
  <div class="my-bookings-container">
    <header class="bookings-header">
      <h1>Mis Reservas</h1>
      <p>Aquí puedes ver todas tus reservas y gestionarlas</p>
    </header>

    <div v-if="loading" class="loading-spinner">Cargando reservas...</div>

    <div v-else-if="bookings.length === 0" class="empty-state">
      <div class="empty-icon">📋</div>
      <h2>No tienes reservas aún</h2>
      <p>¡Comienza a reservar actividades para poder verlas aquí!</p>
      <router-link to="/reservar" class="btn btn-primary">Ir a reservar</router-link>
    </div>

    <div v-else class="bookings-grid">
      <div v-for="booking in bookings" :key="booking.id" class="booking-card" :class="getCardClass(booking)">
        <div class="booking-header-card">
          <div class="booking-status" :class="getCardClass(booking)">
            {{ getStatusLabel(booking.status, booking) }}
          </div>
          <span class="booking-id">#{{ booking.id }}</span>
        </div>

        <div class="booking-content">
          <div class="activity-section">
            <h3 class="activity-name">{{ booking.activity_name || `Actividad ${booking.instance_id}` }}</h3>
            <p class="activity-date">{{ formatDate(booking.date) }}</p>
          </div>

          <div class="schedule-section">
            <div class="schedule-row">
              <span class="label">Día:</span>
              <span class="value">{{ booking.day_of_week }}</span>
            </div>
            <div class="schedule-row">
              <span class="label">Horario:</span>
              <span class="value">{{ booking.start_time }}hs</span>
            </div>
          </div>

          <div class="booking-meta">
            <span class="created-at">Reservada el {{ formatDateTime(booking.created_at) }}</span>
          </div>

          <div class="booking-actions">
            <div v-if="isBookingExpired(booking)" class="expired-notice">
              <span class="expired-icon">🕐</span>
              <span>Esta reserva ha expirado. Pasó la fecha y hora.</span>
            </div>

            <template v-else-if="booking.status === 'Confirmed'">
              <button @click="activeQrId = activeQrId === booking.id ? null : booking.id" class="btn btn-secondary btn-sm">
                {{ activeQrId === booking.id ? 'Ocultar QR' : 'Ver QR' }}
              </button>
              <button @click="cancelBooking(booking.id)" class="btn btn-danger btn-sm">
                Cancelar Reserva
              </button>
            </template>

            <template v-else-if="booking.status === 'Pending'">
              <p class="pending-notice">Pendiente de pago de seña (50%)</p>
              <button @click="paySeña(booking.id)" class="btn btn-success btn-sm">
                Pagar Seña
              </button>
              <button @click="cancelBooking(booking.id)" class="btn btn-danger btn-sm">
                Cancelar
              </button>
            </template>
          </div>

          <div v-if="activeQrId === booking.id" class="qr-container">
            <p class="qr-text">Presentá este código en recepción para ingresar:</p>
            <div class="qr-frame">
              <qrcode-vue :value="String(booking.id)" :size="130" level="H" render-as="svg" />
              <p class="qr-id-display">ID de Reserva: #{{ booking.id }}</p>
              <p style="font-size: 0.85rem; color: #6b7280; margin-top: 5px; font-weight: 600;">
                (Para Cierre Masivo - ID de Clase: #{{ booking.instance_id }})
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <PaymentModal
      v-model="showGatewayModal"
      :amount="pendingPaymentAmount"
      :payeeName="pendingPayeeName"
      @result="onGatewayResult"
    />

    <transition name="fade">
      <div v-if="showCancelModal" class="modal-overlay" @click="showCancelModal = false">
        <div class="modal-content" @click.stop>
          <div class="modal-icon warning">⚠️</div>
          <h2>¿Cancelar reserva?</h2>
          <p>Esta acción no se puede deshacer. ¿Estás seguro de que deseas cancelar esta reserva?</p>
          <div class="modal-actions">
            <button @click="showCancelModal = false" class="btn btn-secondary">No, mantenerla</button>
            <button @click="confirmCancel" class="btn btn-danger">Sí, cancelar</button>
          </div>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div v-if="successMessage" class="modal-overlay" @click="successMessage = ''">
        <div class="modal-content" @click.stop>
          <div class="modal-icon success">✓</div>
          <h2>Operación exitosa</h2>
          <p>{{ successMessage }}</p>
          <button @click="successMessage = ''" class="btn btn-primary">Cerrar</button>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div v-if="errorMessage" class="modal-overlay error" @click="errorMessage = ''">
        <div class="modal-content" @click.stop>
          <div class="modal-icon error">✕</div>
          <h2>Error</h2>
          <p>{{ errorMessage }}</p>
          <button @click="errorMessage = ''" class="btn btn-primary">Cerrar</button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import PaymentModal from '../components/PaymentModal.vue'
import QrcodeVue from 'qrcode.vue'

const auth = useAuthStore()
const bookings = ref([])
const loading = ref(false)
const successMessage = ref('')
const errorMessage = ref('')
const showCancelModal = ref(false)
const bookingToCancel = ref(null)

const showGatewayModal = ref(false)
const pendingPaymentAmount = ref(0)
const pendingBookingId = ref(null)
const pendingPayeeName = ref('Reserva')
const activeQrId = ref(null)

const formatDate = (dateStr) => {
  if (!dateStr) return 'Sin fecha'
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-AR', { day: '2-digit', month: 'long', year: 'numeric' })
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return 'Sin fecha'
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

const parseLocalDate = (dateStr) => {
  if (!dateStr) return null
  const rawDate = String(dateStr).split('T')[0]
  const [year, month, day] = rawDate.split('-').map(Number)

  if (!year || !month || !day) {
    const fallbackDate = new Date(dateStr)
    return Number.isNaN(fallbackDate.getTime()) ? null : fallbackDate
  }

  const localDate = new Date(year, month - 1, day)
  return Number.isNaN(localDate.getTime()) ? null : localDate
}

const isBookingExpired = (booking) => {
  if (!booking.date || !booking.start_time) return false
  const bookingDate = parseLocalDate(booking.date)
  if (!bookingDate) return false

  const [hours, minutes] = String(booking.start_time).split(':').map(Number)
  if (!Number.isFinite(hours) || !Number.isFinite(minutes)) return false

  bookingDate.setHours(hours, minutes, 0, 0)
  const now = new Date()
  return now > bookingDate
}

const getStatusLabel = (status, booking) => {
  if (booking && isBookingExpired(booking)) {
    return 'Fecha pasada'
  }
  const labels = {
    'Confirmed': 'Confirmada',
    'Pending': 'Pendiente de Pago',
    'Cancelled': 'Cancelada',
    'Attended': 'Asistida',
    'Concreted': 'Asistida', 
    'Absent': 'Ausente'      
  }
  return labels[status] || status
}

const getCardClass = (booking) => {
  const classes = {
    'Confirmed': 'status-confirmed',
    'Pending': 'status-pending',
    'Cancelled': 'status-cancelled',
    'Attended': 'status-attended',
    'Concreted': 'status-attended',
    'Absent': 'status-absent'       
  }
  return classes[booking.status] || ''
}

const fetchBookings = async () => {
  loading.value = true
  try {
    auth.hydrateFromToken()
    const token = auth.token || localStorage.getItem('token')

    if (!token) return

    const res = await axios.get('/bookings/me', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    bookings.value = res.data
  } catch (e) {
    console.error('Error al cargar reservas:', e)
    bookings.value = []
  } finally {
    loading.value = false
  }
}

const cancelBooking = (bookingId) => {
  bookingToCancel.value = bookingId
  showCancelModal.value = true
}

const confirmCancel = async () => {
  showCancelModal.value = false
  try {
    auth.hydrateFromToken()
    const token = auth.token || localStorage.getItem('token')

    const res = await axios.post(`/bookings/${bookingToCancel.value}/cancel`, {}, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    successMessage.value = res.data.message || 'Reserva cancelada exitosamente'
    setTimeout(() => { fetchBookings() }, 1500)
  } catch (e) {
    errorMessage.value = e.response?.data?.detail || 'Error al cancelar la reserva'
    console.error('Error al cancelar:', e)
  }
}

const paySeña = async (bookingId) => {
  const booking = bookings.value.find((b) => b.id === bookingId)
  if (!booking) return

  const price = Number(booking.price || 0)
  if (!Number.isFinite(price) || price <= 0) {
    errorMessage.value = 'No se pudo determinar el precio de la reserva.'
    return
  }

  pendingBookingId.value = bookingId
  pendingPaymentAmount.value = price * 0.5
  pendingPayeeName.value = booking.activity_name || 'Reserva'
  showGatewayModal.value = true
}

async function onGatewayResult(result) {
  if (!result) return
  if (result.status !== 'Aprobado') {
    errorMessage.value = result.status === 'Cancelado' ? 'Pago cancelado.' : 'Pago rechazado.'
    return
  }

  try {
    auth.hydrateFromToken()
    const token = auth.token || localStorage.getItem('token')
    if (!token) {
      errorMessage.value = 'Tu sesión expiró. Iniciá sesión nuevamente.'
      return
    }

    await axios.post(
      '/payments/me/complete-booking',
      { amount: pendingPaymentAmount.value, booking_id: pendingBookingId.value },
      { headers: { Authorization: `Bearer ${token}` } }
    )

    successMessage.value = 'Pago exitoso. Tu reserva quedó confirmada.'
    pendingBookingId.value = null
    pendingPaymentAmount.value = 0
    setTimeout(() => { fetchBookings() }, 800)
  } catch (e) {
    errorMessage.value = e.response?.data?.detail || 'Error al confirmar el pago'
  }
}

onMounted(() => {
  if (auth.isAuthenticated) fetchBookings()
})
</script>

<style scoped>
.my-bookings-container {
  padding: 40px 20px;
  max-width: 1200px;
  margin: 0 auto;
  background: rgba(45, 101, 141, 0.06);
  min-height: 100vh;
}
.bookings-header { text-align: center; margin-bottom: 40px; }
.bookings-header h1 { font-size: 2.5rem; color: #2d658d; font-weight: 800; margin: 0 0 10px; }
.bookings-header p { color: #5a8849; margin: 0; font-size: 1.1rem; }
.loading-spinner { text-align: center; font-size: 1.2rem; color: #6c757d; padding: 60px 20px; }
.empty-state {
  text-align: center; padding: 60px 20px; background: white; border-radius: 15px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}
.empty-icon { font-size: 4rem; margin-bottom: 20px; }
.empty-state h2 { font-size: 1.8rem; color: #0d124a; margin: 0 0 10px; }
.empty-state p { color: #6c757d; margin: 0 0 25px; font-size: 1.1rem; }
.bookings-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 25px; }

.booking-card {
  background: white; border-radius: 15px; overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08); transition: all 0.3s ease;
  display: flex; flex-direction: column; border-left: 5px solid #2d658d;
}
.booking-card:hover { transform: translateY(-5px); box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12); }
.booking-card.status-confirmed { border-left-color: #5a8849; }
.booking-card.status-pending { border-left-color: #ff6f00; }
.booking-card.status-cancelled { border-left-color: #2d658d; opacity: 0.7; }
.booking-card.status-attended { border-left-color: #5a8849; }
.booking-card.status-expired { border-left-color: #9ca3af; opacity: 0.6; }
.booking-card.status-absent { border-left-color: #dc3545; }

.booking-header-card {
  background: #2d658d; color: white; padding: 15px 20px;
  display: flex; justify-content: space-between; align-items: center;
}
.booking-card.status-confirmed .booking-header-card { background: #5a8849; }
.booking-card.status-pending .booking-header-card { background: #ff6f00; }
.booking-card.status-cancelled .booking-header-card { background: #2d658d; }
.booking-card.status-expired .booking-header-card { background: #9ca3af; }
.booking-status { font-weight: 700; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; }
.booking-id { font-size: 0.85rem; opacity: 0.9; }

.booking-content { padding: 20px; flex-grow: 1; display: flex; flex-direction: column; gap: 15px; }
.activity-section h3 { margin: 0 0 5px; color: #0d124a; font-size: 1.3rem; font-weight: 800; }
.activity-date { margin: 0; color: #6c757d; font-size: 1rem; }
.schedule-section { background: #f8f9fa; padding: 12px; border-radius: 8px; }
.schedule-row { display: flex; justify-content: space-between; align-items: center; margin: 5px 0; }
.schedule-row .label { color: #6c757d; font-weight: 600; font-size: 0.9rem; }
.schedule-row .value { color: #0d124a; font-weight: 700; }
.booking-meta { font-size: 0.85rem; color: #999; }
.pending-notice { background: #fff7ed; color: #b45309; padding: 10px; border-radius: 6px; margin: 0; font-size: 0.9rem; font-weight: 600; }

.booking-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.booking-actions .btn-danger { background: #ff6f00; color: white; border: none; }
.booking-actions .btn-danger:hover { background: #ff6f00; box-shadow: 0 8px 18px rgba(255, 111, 0, 0.22); }
.booking-actions .btn-success { background: #5a8849; color: white; border: none; }
.booking-actions .btn-success:hover { background: #5a8849; box-shadow: 0 8px 18px rgba(90, 136, 73, 0.22); }

.expired-notice {
  display: flex; align-items: center; gap: 10px; padding: 12px 15px; background: #f3f4f6;
  border-radius: 8px; color: #6b7280; font-weight: 600; font-size: 0.9rem; width: 100%;
}

.modal-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5); display: flex; justify-content: center; align-items: center; z-index: 1000; }
.modal-content { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3); max-width: 400px; text-align: center; }
.modal-icon { font-size: 3rem; margin-bottom: 15px; }
.modal-icon.success { color: #5a8849; }
.modal-icon.error { color: #dc3545; }
.modal-icon.warning { color: #ff6f00; }
.modal-content h2 { margin: 0 0 10px; color: #0d124a; }
.modal-content p { color: #6c757d; margin: 0 0 20px; line-height: 1.5; }
.modal-actions { display: flex; gap: 10px; justify-content: center; }

.btn { padding: 10px 16px; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.95rem; transition: all 0.3s ease; text-decoration: none; display: inline-block; }
.btn-primary { background: #007bff; color: white; }
.btn-primary:hover { background: #0056b3; }
.btn-secondary { background: #6c757d; color: white; }
.btn-secondary:hover { background: #5a6268; }
.btn-success { background: #28a745; color: white; }
.btn-success:hover { background: #1e7e34; }
.btn-danger { background: #dc3545; color: white; }
.btn-danger:hover { background: #a71d2a; }
.btn-sm { padding: 8px 12px; font-size: 0.85rem; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.qr-container { margin-top: 15px; padding: 12px; background: #f8f9fa; border-radius: 8px; border: 1px dashed #ced4da; text-align: center; }
.qr-text { font-size: 0.85rem; color: #6c757d; margin: 0 0 8px 0; font-weight: 600; }
.qr-frame { display: inline-block; background: white; padding: 8px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
.qr-id-display { font-size: 0.95rem; font-weight: 700; color: #0d124a; margin-top: 8px; margin-bottom: 0; }
</style>