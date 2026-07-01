<template>
  <div class="payments-container">
    <header class="payments-header">
      <h1>Mis Pagos</h1>
      <p>Historial financiero y comprobantes de tu cuenta en el club.</p>
    </header>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Buscando movimientos financieros...</p>
    </div>

    <div v-else>
      <section class="payments-section suspensions-section">
        <div class="section-heading">
          <div>
            <h2>Mis suspensiones</h2>
            <p>Acá aparecen tus suspensiones activas para regularizarlas.</p>
          </div>
        </div>

        <div v-if="suspensionPayments.length" class="table-wrapper">
          <table class="custom-table">
            <thead>
              <tr>
                <th class="col-date">Fecha</th>
                <th class="col-concept">Suspensión</th>
                <th class="col-amount text-right">Monto</th>
                <th class="col-status text-center">Estado</th>
                <th class="col-actions text-center">Acción</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in suspensionPayments" :key="p.id" class="table-row suspension-row">
                <td class="cell-date font-medium text-nowrap">{{ formatDate(p.date) }}</td>
                <td class="cell-concept font-semibold">{{ formatConcept(p) }}</td>
                <td class="cell-amount text-right font-mono font-bold text-base price-clean">${{ p.amount }}</td>
                <td class="cell-status text-center">
                  <span :class="['status-badge', getStatusClass(p.status)]">
                    {{ formatStatusLabel(p.status) }}
                  </span>
                </td>
                <td class="cell-actions text-center">
                  <button
                    v-if="isPayableStatus(p.status)"
                    class="btn-primary-pay"
                    @click="openPaymentFlow(p)"
                    title="Hacé clic para pagar esta suspensión"
                  >
                    Pagar suspensión 💳
                  </button>
                  <span v-else class="text-disabled">-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="empty-state-card-unified compact-empty">
          <div class="empty-icon-large">✅</div>
          <h2>No tenés suspensiones activas</h2>
          <p>Cuando tengas una suspensión activa, va a aparecer acá para poder pagarla.</p>
        </div>
      </section>

      <section class="payments-section">
        <div class="section-heading">
          <div>
            <h2>Historial de pagos</h2>
            <p>Movimientos financieros y comprobantes registrados en tu cuenta.</p>
          </div>
        </div>

        <div v-if="filteredPayments.length" class="table-wrapper">
          <table class="custom-table">
            <thead>
              <tr>
                <th class="col-date">Fecha</th>
                <th class="col-concept">Concepto / Categoría</th>
                <th class="col-amount text-right">Monto</th>
                <th class="col-status text-center">Estado</th>
                <th class="col-actions text-center">Acción</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in paginatedPayments" :key="p.id" class="table-row">
                <td class="cell-date font-medium text-nowrap">{{ formatDate(p.date) }}</td>
                <td class="cell-concept capitalize font-semibold">{{ formatConcept(p) }}</td>
                <td class="cell-amount text-right font-mono font-bold text-base price-clean">${{ p.amount }}</td>
                <td class="cell-status text-center">
                  <span :class="['status-badge', getStatusClass(p.status)]">
                    {{ formatStatusLabel(p.status) }}
                  </span>
                </td>
                <td class="cell-actions text-center">
                  <button
                    v-if="isPayableStatus(p.status)"
                    class="btn-primary-pay"
                    :class="{ disabled: isMonthlyPaymentBlocked(p) }"
                    :disabled="isMonthlyPaymentBlocked(p)"
                    @click="openPaymentFlow(p)"
                    :title="isMonthlyPaymentBlocked(p) ? 'Tenés una suspensión activa para este deporte' : 'Hacé clic para liquidar este saldo pendiente'"
                  >
                    Pagar 💳
                  </button>
                  <span v-else class="text-disabled">-</span>
                </td>
              </tr>
            </tbody>
          </table>

          <div class="pagination-footer" v-if="totalPages !== 1">
            <button @click="prevPage" :disabled="currentPage === 1" class="page-btn">← Anterior</button>
            <span class="page-info">Página <strong>{{ currentPage }}</strong> de {{ totalPages }}</span>
            <button @click="nextPage" :disabled="currentPage === totalPages" class="page-btn">Siguiente →</button>
          </div>
        </div>

        <div v-else class="empty-state-card-unified">
          <div class="empty-icon-large">💳</div>
          <h2>No tienes pagos registrados aún</h2>
          <p>No encontramos ningún movimiento financiero asociado a tu cuenta actualmente.</p>
        </div>
      </section>
    </div>

    <PaymentModal
      v-model="isModalOpen"
      :amount="selectedPaymentAmount"
      :payeeName="selectedPaymentConcept"
      @result="handlePaymentResult"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'
import PaymentModal from '../components/PaymentModal.vue' 

const auth = useAuthStore()
const payments = ref([])
const loading = ref(false)

const currentPage = ref(1)
const itemsPerPage = ref(5)

const isModalOpen = ref(false)
const selectedPaymentAmount = ref(0)
const selectedPaymentConcept = ref('')
const activePaymentObject = ref(null)
const SUSPENSION_PAYMENT_AMOUNT = 8000

const suspensionPayments = computed(() => {
  return payments.value
    .filter(p => p.is_suspension)
    .sort((a, b) => new Date(b.date) - new Date(a.date))
})

const paymentHistory = computed(() => payments.value.filter(p => !p.is_suspension))

// Ordenamos los pagos por fecha de emisión (del más reciente al más antiguo) antes de aplicar la paginación:
const filteredPayments = computed(() => {
  return [...paymentHistory.value].sort((a, b) => {
    return new Date(b.date) - new Date(a.date)
  })
})

// Paginación reactiva sobre la lista
const totalPages = computed(() => {
  return Math.ceil(filteredPayments.value.length / itemsPerPage.value)
})

const paginatedPayments = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  const end = start + itemsPerPage.value
  return filteredPayments.value.slice(start, end)
})

const nextPage = () => {
  if (currentPage.value < totalPages.value) currentPage.value++
}
const prevPage = () => {
  if (currentPage.value > 1) currentPage.value--
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return dateStr
  const d = date.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
  const t = date.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', hour12: false })
  return `${d} - ${t}`
}

const formatConcept = (payment) => {
  if (payment.is_suspension) {
    if (payment.reason === 'SUSPENSION_CLASE_LIBRE') return 'Suspensión de clase libre'
    if (payment.reason === 'SUSPENSION_ABONO') {
      return payment.sport_name ? `Suspensión de abono - ${payment.sport_name}` : 'Suspensión de abono'
    }
    return 'Suspensión activa'
  }

  if (payment.type === 'subscription' || payment.type === 'suscripcion') {
    return 'Abono Mensual'
  }

  if (payment.type === 'refund_partial') {
    return 'Devolución por cancelación: Seña 50% '
  }
  if (payment.type === 'refund_total') {
    return 'Devolución por cancelación: Pago total '
  }

  if (payment.type === 'booking') {
    const amount = Number(payment.amount)
    if (amount === 10000) return 'Reserva: clase 50%'
    if (amount > 10000) return 'Reserva: pago total'
    return 'Reserva: pago'
  }
  
  return payment.type
}

const formatStatusLabel = (status) => {
  const s = status ? status.toLowerCase() : ''
  if (s === 'completed' || s === 'approved' || s === 'pagado') {
    return 'Pagado'
  }
  if (s === 'partial') {
    return 'Pendiente parcial'
  }
  if (s === 'pending' || s === 'pendiente') {
    return 'Pendiente'
  }
  return status
}

const getStatusClass = (status) => {
  const s = status ? status.toLowerCase() : ''
  if (s.includes('pagado') || s.includes('approved') || s.includes('completed')) {
    return 'badge-success'
  }
  if (s.includes('pending') || s.includes('pendiente') || s.includes('partial')) {
    return 'badge-warning'
  }
  return 'badge-danger'
}

const isPayableStatus = (status) => {
  const s = String(status || '').toLowerCase()
  return s === 'pending' || s === 'pendiente' || s === 'partial'
}

const sameActivityId = (left, right) => String(left ?? '') === String(right ?? '')

const isSubscriptionPayment = (payment) => {
  return ['subscription', 'suscripcion', 'Subscription'].includes(payment?.type)
}

const isMonthlyPaymentBlocked = (payment) => {
  if (!isSubscriptionPayment(payment) || !payment?.activity_id) return false
  return suspensionPayments.value.some(s =>
    s.reason === 'SUSPENSION_ABONO' && sameActivityId(s.activity_id, payment.activity_id)
  )
}

const openPaymentFlow = (payment) => {
  if (isMonthlyPaymentBlocked(payment)) return
  activePaymentObject.value = payment
  selectedPaymentAmount.value = Number(payment.amount)
  selectedPaymentConcept.value = formatConcept(payment)
  isModalOpen.value = true
}

// Manejador de pago unificado y corregido sintácticamente
const handlePaymentResult = async (result) => {
  if (result && result.status === 'Aprobado') {
    const paymentId = activePaymentObject.value?.id
    const isSuspension = Boolean(activePaymentObject.value?.is_suspension)
    const isAbono = isSubscriptionPayment(activePaymentObject.value)

    // Mutación visual rápida para optimizar la respuesta en la interfaz
    const target = payments.value.find(p => p.id === paymentId)
    if (target) {
      target.status = 'completed' 
    }

    try {
      loading.value = true

      if (isSuspension) {
        await api.post('/payments/pagar-suspension', {
          suspension_id: activePaymentObject.value.suspension_id,
          amount: Number(selectedPaymentAmount.value)
        })
        console.log('¡Suspensión pagada y levantada con éxito!')
      } else if (isAbono) {
        await api.post(`/payments/me/complete-subscription/${paymentId}`)
        console.log('¡Suscripción y todas sus reservas mutadas con éxito!')
      } else {
        const bookingId = activePaymentObject.value?.booking_id || paymentId
        await api.post('/payments/me/complete-booking', {
          amount: Number(selectedPaymentAmount.value),
          booking_id: Number(bookingId)
        })
        console.log('¡Reserva de clase única actualizada correctamente!')
      }

      isModalOpen.value = false

    } catch (err) {
      console.error("Error al persistir la transacción en el servidor:", err)
      if (target) {
        target.status = 'pending' 
      }
      alert("Hubo un error al registrar el pago en el servidor.")
    } finally {
      await fetchPayments() 
      loading.value = false
    }
  }
}

const getUserIdFromExistingToken = () => {
  try {
    const token = auth.token || localStorage.getItem('token')
    if (token) {
      const base64Url = token.split('.')[1]
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
      const payload = JSON.parse(window.atob(base64))
      if (payload && payload.id) return payload.id
    }
  } catch (error) {
    console.error("No se pudo extraer el ID del token:", error)
  }
  return 1
}

const isKnownSuspensionReason = (reason) => {
  return reason === 'SUSPENSION_CLASE_LIBRE' || reason === 'SUSPENSION_ABONO'
}

const mapSuspensionToPaymentRow = (suspension) => ({
  id: `suspension-${suspension.id}`,
  suspension_id: suspension.id,
  payment_id: suspension.payment_id,
  amount: Number(suspension.amount || SUSPENSION_PAYMENT_AMOUNT),
  status: isKnownSuspensionReason(suspension.reason) ? 'pending' : 'active',
  type: 'suspension',
  date: suspension.start_date,
  reason: suspension.reason,
  activity_id: suspension.activity_id,
  sport_name: suspension.sport_name,
  is_suspension: true,
})

const fetchPayments = async () => {
  loading.value = true
  try {
    currentPage.value = 1
    const userId = getUserIdFromExistingToken()
    const [paymentsResponse, suspensionsResponse] = await Promise.all([
      api.get(`/payments/user/${userId}`),
      api.get('/payments/me/suspensions')
    ])

    const suspensionRows = Array.isArray(suspensionsResponse.data)
      ? suspensionsResponse.data.map(mapSuspensionToPaymentRow)
      : []
    const normalPayments = Array.isArray(paymentsResponse.data)
      ? paymentsResponse.data
      : []

    payments.value = [...suspensionRows, ...normalPayments]
  } catch (e) {
    console.error("Error cargando pagos:", e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchPayments)
</script>

<style scoped>
.payments-container { padding: 28px 40px 40px; max-width: 1200px; margin: 0 auto; background: transparent; min-height: 100vh; font-family: system-ui, -apple-system, sans-serif; }
.payments-header { display: flex; flex-direction: column; align-items: flex-start; margin-bottom: 18px; }
.payments-header h1 { font-size: 2.5rem; color: #2d658d; font-weight: 900; margin: 0 0 10px; }
.payments-header p { font-size: 1.1rem; color: #5a8849; margin: 0; }
.payments-section { margin-top: 26px; }
.suspensions-section { margin-top: 0; }
.section-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-bottom: 12px; }
.section-heading h2 { color: #0d124a; font-size: 1.35rem; font-weight: 900; margin: 0 0 4px; }
.section-heading p { color: #64748b; font-size: 0.95rem; margin: 0; }
.suspension-row { background: #fffaf0; }
.compact-empty { padding: 28px 24px; margin: 0; max-width: none; }
.compact-empty .empty-icon-large { font-size: 2.4rem; margin-bottom: 10px; }
.compact-empty h2 { font-size: 1.2rem; }
.table-wrapper { background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); overflow: hidden; }
.custom-table { width: 100%; border-collapse: collapse; text-align: left; margin: 0; }
.custom-table th { background-color: #0d124a; color: #ffffff; padding: 16px 20px; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
.custom-table td { padding: 18px 20px; font-size: 0.9rem; color: #334155; border-bottom: 1px solid #f1f5f9; }
.table-row:hover { background-color: #f8fafc; transition: background-color 0.2s ease; }
.pagination-footer { display: flex; align-items: center; justify-content: space-between; padding: 14px 20px; background-color: #ffffff; border-top: 1px solid #e2e8f0; }
.page-btn { background-color: #ffffff; color: #0d124a; border: 1px solid #e2e8f0; padding: 6px 14px; border-radius: 8px; font-size: 0.85rem; font-weight: 600; cursor: pointer; transition: all 0.2s ease; }
.page-btn:hover:not(:disabled) { background-color: #f1f5f9; border-color: #cbd5e1; }
.page-btn:disabled { color: #94a3b8; background-color: #f8fafc; cursor: not-allowed; border-color: #f1f5f9; }
.page-info { font-size: 0.85rem; color: #475569; }
.text-right { text-align: right; }
.text-center { text-align: center; }
.text-nowrap { white-space: nowrap; }
.font-mono { font-family: monospace; }
.font-bold { font-weight: 700; }
.font-semibold { font-weight: 600; }
.font-medium { font-weight: 500; }
.capitalize { text-transform: capitalize; }
.text-base { font-size: 1rem; }
.status-badge { padding: 6px 14px; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; display: inline-block; border: 1px solid transparent; }
.badge-success { background-color: #f0fdf4; color: #166534; border-color: #bbf7d0; }
.badge-warning { background-color: #fffbeb; color: #92400e; border-color: #fde68a; }
.badge-danger { background-color: #fef2f2; color: #991b1b; border-color: #fca5a5; }
.loading-state, .empty-state-card { text-align: center; padding: 60px 20px; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }
.spinner { border: 3px solid #f3f4f6; border-top: 3px solid #0d124a; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 12px auto; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
.price-clean { text-decoration: none !important; color: #0d124a !important; }

.btn-primary-pay {
  background-color: #f59e0b;
  color: #ffffff;
  border: none;
  padding: 8px 18px;
  border-radius: 8px; 
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease-in-out;
  box-shadow: 0 2px 4px rgba(245, 158, 11, 0.2);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.btn-primary-pay:hover {
  background-color: #d97706;
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(217, 119, 6, 0.3);
}
.btn-primary-pay.disabled,
.btn-primary-pay:disabled {
  background-color: #9ca3af;
  color: #f8fafc;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}
.btn-primary-pay:active {
  transform: translateY(1px);
  box-shadow: 0 1px 2px rgba(217, 119, 6, 0.2);
}
.text-disabled { color: #94a3b8; font-size: 0.9rem; font-weight: 500; }
.col-actions { width: 140px; }
.cell-actions { padding: 12px 20px; }

.empty-state-card-unified {
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  padding: 60px 40px;
  max-width: 1120px;
  margin: 30px auto 0 auto;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}
.empty-icon-large { font-size: 4rem; margin-bottom: 16px; line-height: 1; }
.empty-state-card-unified h2 { font-size: 1.8rem; color: #0d124a; font-weight: 800; margin: 0 0 12px 0; }
.empty-state-card-unified p { font-size: 1.05rem; color: #64748b; margin: 0; max-width: 600px; }
</style>