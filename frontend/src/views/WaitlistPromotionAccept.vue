<template>
  <div class="waitlist-page">
    <div v-if="loading" class="state-panel compact">
      <img src="../assets/logo.png" alt="Club 360" class="brand-logo" />
      <div class="spinner"></div>
      <p>Cargando tu cupo disponible...</p>
    </div>

    <div v-else-if="error" class="state-panel">
      <img src="../assets/logo.png" alt="Club 360" class="brand-logo" />
      <div class="state-icon error">✕</div>
      <h2>Algo salió mal</h2>
      <p>{{ error }}</p>
      <button class="btn-primary" type="button" @click="goHome">Volver al inicio</button>
    </div>

    <div v-else-if="success" class="state-panel">
      <img src="../assets/logo.png" alt="Club 360" class="brand-logo" />
      <div class="state-icon success">✓</div>
      <h2>Reserva confirmada</h2>
      <p>{{ successMessage }}</p>
      <button class="btn-primary" type="button" @click="goToBookings">Ir a Mis Reservas</button>
    </div>

    <div v-else-if="rejected" class="state-panel">
      <img src="../assets/logo.png" alt="Club 360" class="brand-logo" />
      <div class="state-icon neutral">✓</div>
      <h2>Respuesta registrada</h2>
      <p>Pasaremos al siguiente socio en la lista de espera.</p>
      <button class="btn-primary" type="button" @click="goHome">Volver al inicio</button>
    </div>

    <main v-else class="offer-shell">
      <section class="brand-panel" aria-label="Club 360">
        <img src="../assets/logo.png" alt="Club 360" class="hero-logo" />
      </section>

      <div class="offer-modal" role="dialog" aria-modal="true">
        <div class="modal-card">
          <div v-if="ownerMismatch" class="owner-warning">
            <div class="state-icon error">✕</div>
            <h1>Este cupo pertenece a otro socio</h1>
            <p>Iniciá sesión con la cuenta anotada en la lista de espera para aceptar y pagar este lugar.</p>
            <button class="btn-primary" type="button" @click="goLoginForThisOffer">Cambiar de cuenta</button>
          </div>

          <template v-else>
            <header class="modal-head">
              <div class="status-badge">Lista de espera</div>
              <h1>Hay un cupo disponible</h1>
              <p>Confirmá si querés tomar este lugar. Al aceptar vas a completar el pago dentro de la app.</p>
            </header>

            <section class="class-summary">
              <div class="summary-row featured">
                <span>Actividad</span>
                <strong>{{ offer.activity_name }}</strong>
              </div>
              <div class="summary-row">
                <span>Fecha</span>
                <strong>{{ formattedDate }}</strong>
              </div>
              <div class="summary-row">
                <span>Horario</span>
                <strong>{{ offer.start_time || '-' }} hs</strong>
              </div>
              <div class="summary-row">
                <span>Valor</span>
                <strong>{{ formattedPrice }}</strong>
              </div>
            </section>

            <section class="decision-copy">
              <div class="decision-icon" aria-hidden="true">i</div>
              <p>
                Si rechazás, el cupo se ofrece automáticamente al siguiente socio de la lista.
              </p>
            </section>

            <p v-if="actionError" class="inline-error">{{ actionError }}</p>

            <footer>
              <button class="btn-secondary" type="button" :disabled="busy" @click="rejectOffer">
                Rechazar
              </button>
              <button class="btn-primary" type="button" :disabled="busy" @click="acceptOffer">
                {{ busy ? 'Procesando...' : 'Aceptar y pagar' }}
              </button>
            </footer>
          </template>
        </div>
      </div>
    </main>

    <PaymentModal
      v-model="showPaymentModal"
      :amount="depositAmount"
      :deposit-amount="depositAmount"
      :full-amount="fullAmount"
      :payee-name="offer?.activity_name || 'clase'"
      :busy="finalizingPayment"
      @result="onPaymentResult"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PaymentModal from '../components/PaymentModal.vue'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const loading = ref(true)
const busy = ref(false)
const finalizingPayment = ref(false)
const showPaymentModal = ref(false)
const error = ref('')
const actionError = ref('')
const success = ref(false)
const rejected = ref(false)
const successMessage = ref('')
const offer = ref(null)
const booking = ref(null)

const token = computed(() => route.params.token)
const fullAmount = computed(() => Number(offer.value?.price || 0))
const depositAmount = computed(() => roundMoney(fullAmount.value * 0.5))

const formattedDate = computed(() => {
  if (!offer.value?.date) return '-'
  const [year, month, day] = String(offer.value.date).split('-')
  if (!year || !month || !day) return offer.value.date
  return `${day}/${month}/${year}`
})

const formattedPrice = computed(() => formatCurrency(fullAmount.value))
const ownerMismatch = computed(() => Boolean(offer.value?.owner_mismatch))

function roundMoney(value) {
  return Math.round(Number(value || 0) * 100) / 100
}

function formatCurrency(value) {
  try {
    return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
  } catch {
    return `$ ${value}`
  }
}

async function loadOffer() {
  if (!token.value) {
    error.value = 'Token inválido'
    loading.value = false
    return
  }

  rememberPostLoginRedirect()

  try {
    const response = await api.get(`/waiting-lists/offer/${token.value}`)
    offer.value = response.data
  } catch (err) {
    error.value = err.response?.data?.detail || 'No se pudo cargar la oferta'
  } finally {
    loading.value = false
  }
}

async function acceptOffer() {
  if (busy.value) return
  actionError.value = ''

  if (booking.value) {
    showPaymentModal.value = true
    return
  }

  busy.value = true

  try {
    const response = await api.post(`/waiting-lists/accept/${token.value}`)
    booking.value = response.data
    showPaymentModal.value = true
  } catch (err) {
    if (err.response?.status === 401) {
      rememberPostLoginRedirect()
      router.push({
        path: '/login',
        query: { redirect: route.fullPath }
      })
      return
    }

    actionError.value = err.response?.data?.detail || 'No se pudo aceptar el cupo'
  } finally {
    busy.value = false
  }
}

function goLoginForThisOffer() {
  rememberPostLoginRedirect({ force: true })
  router.push({
    path: '/login',
    query: { redirect: route.fullPath }
  })
}

function rememberPostLoginRedirect({ force = false } = {}) {
  if (auth.isAuthenticated && !force) return
  sessionStorage.setItem('club360_post_login_redirect', route.fullPath)
  localStorage.setItem('club360_post_login_redirect', route.fullPath)
}

async function rejectOffer() {
  if (busy.value) return
  actionError.value = ''
  busy.value = true

  try {
    await api.post(`/waiting-lists/reject/${token.value}`)
    rejected.value = true
  } catch (err) {
    actionError.value = err.response?.data?.detail || 'No se pudo rechazar el cupo'
  } finally {
    busy.value = false
  }
}

async function onPaymentResult(result) {
  if (!result) return

  if (result.status !== 'Aprobado') {
    if (result.source === 'dismiss' || result.source === 'cancel') {
      actionError.value = 'La reserva quedó pendiente. Para confirmar el cupo necesitás completar el pago.'
    }
    return
  }

  finalizingPayment.value = true
  actionError.value = ''

  try {
    await api.post('/payments/me/complete-booking', {
      amount: result.amount,
      booking_id: booking.value.id
    })

    showPaymentModal.value = false
    success.value = true
    const amountText = formatCurrency(result.amount)
    successMessage.value = `Tu pago fue aprobado. Podés ver los detalles en Mis Reservas.`
  } catch (err) {
    actionError.value = err.response?.data?.detail || 'El pago fue aprobado, pero no pudimos confirmar la reserva. Iniciá sesión con el usuario de la lista de espera e intentá nuevamente.'
  } finally {
    finalizingPayment.value = false
  }
}

function goToBookings() {
  router.push('/reservas')
}

function goHome() {
  router.push('/')
}

onMounted(loadOffer)
</script>

<style scoped>
.waitlist-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px;
  background:
    linear-gradient(180deg, rgba(45, 101, 141, 0.08), rgba(255, 255, 255, 0) 44%),
    #f8f9fa;
}

.state-panel,
.modal-card {
  width: min(560px, 100%);
  background: #ffffff;
  border: 1px solid rgba(13, 18, 74, 0.08);
  border-radius: 8px;
  box-shadow: 0 18px 55px rgba(13, 18, 74, 0.16);
}

.state-panel {
  padding: 34px 28px 28px;
  text-align: center;
}

.state-panel.compact {
  width: min(420px, 100%);
}

.brand-logo {
  display: block;
  width: 160px;
  height: auto;
  margin: 0 auto 18px;
}

.state-panel h2,
.modal-card h1 {
  margin: 0;
  color: #0d124a;
}

.modal-card h1 {
  font-size: 1.45rem;
  line-height: 1.15;
}

.state-panel p,
.modal-head p,
.decision-copy p {
  color: #5f6b76;
  line-height: 1.5;
}

.modal-head p {
  margin: 8px 0 0;
}

.spinner {
  width: 44px;
  height: 44px;
  border: 4px solid #e5e9ef;
  border-top-color: #2d658d;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 18px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.state-icon {
  width: 56px;
  height: 56px;
  display: grid;
  place-items: center;
  margin: 0 auto 18px;
  border-radius: 50%;
  font-size: 28px;
  font-weight: 900;
}

.state-icon.success,
.state-icon.neutral {
  color: #2f7d32;
  background: #e8f5e9;
}

.state-icon.error {
  color: #b42318;
  background: #fff0ed;
}

.offer-shell {
  width: min(980px, 100%);
  display: grid;
  grid-template-columns: 0.82fr 1fr;
  align-items: stretch;
  gap: 0;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 22px 65px rgba(13, 18, 74, 0.16);
  background: #ffffff;
  border: 1px solid rgba(13, 18, 74, 0.08);
}

.brand-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 46px 34px;
  background:
    linear-gradient(145deg, rgba(13, 18, 74, 0.92), rgba(45, 101, 141, 0.96)),
    #2d658d;
}

.hero-logo {
  width: min(280px, 82%);
  height: auto;
  padding: 18px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 16px 34px rgba(0, 0, 0, 0.18);
}

.offer-modal {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px;
}

.modal-card {
  width: 100%;
  padding: 0;
  border: 0;
  box-shadow: none;
}

.modal-head {
  padding: 2px 0 18px;
}

.owner-warning {
  text-align: center;
  padding: 8px 4px 2px;
}

.owner-warning p {
  margin: 10px auto 18px;
  max-width: 390px;
  color: #5f6b76;
  line-height: 1.5;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 5px 10px;
  border-radius: 8px;
  background: rgba(45, 101, 141, 0.08);
  color: #2d658d;
  font-weight: 900;
  text-transform: uppercase;
  font-size: 0.75rem;
  margin-bottom: 10px;
}

.class-summary {
  border: 1px solid rgba(13, 18, 74, 0.08);
  border-radius: 8px;
  background: #fbfdff;
  overflow: hidden;
}

.summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 48px;
  padding: 11px 14px;
  border-bottom: 1px solid rgba(13, 18, 74, 0.08);
}

.summary-row:last-child {
  border-bottom: 0;
}

.summary-row.featured {
  min-height: 58px;
  background: rgba(45, 101, 141, 0.05);
}

.class-summary span {
  color: #5f6b76;
  font-weight: 700;
  font-size: 0.88rem;
}

.class-summary strong {
  color: #0d124a;
  text-align: right;
  font-weight: 900;
}

.decision-copy {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 16px;
  padding: 12px 14px;
  border-radius: 8px;
  background: rgba(255, 111, 0, 0.08);
}

.decision-copy p {
  margin: 0;
  font-weight: 700;
  font-size: 0.92rem;
}

.decision-icon {
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 50%;
  background: #ff6f00;
  color: #ffffff;
  font-weight: 900;
  font-size: 0.85rem;
}

.inline-error {
  margin: 14px 0 0;
  padding: 12px 14px;
  border-radius: 8px;
  background: #fff0ed;
  color: #b42318;
  font-weight: 700;
}

.modal-card footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

.btn-primary,
.btn-secondary {
  border: 0;
  border-radius: 8px;
  padding: 12px 18px;
  font-weight: 800;
  cursor: pointer;
  min-height: 44px;
  transition: transform 0.12s ease, filter 0.12s ease, background-color 0.12s ease;
}

.btn-primary {
  background: #2d658d;
  color: white;
}

.btn-secondary {
  background: #edf1f5;
  color: #0d124a;
}

.btn-primary:hover,
.btn-secondary:hover {
  filter: brightness(0.98);
}

.btn-primary:active,
.btn-secondary:active {
  transform: translateY(1px);
}

.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.btn-primary:disabled:active,
.btn-secondary:disabled:active {
  transform: none;
}

@media (max-width: 820px) {
  .offer-shell {
    display: block;
    width: min(560px, 100%);
  }

  .brand-panel {
    padding: 22px 18px;
  }

  .hero-logo {
    width: 180px;
    padding: 12px;
  }

  .offer-modal {
    padding: 22px;
  }
}

@media (max-width: 560px) {
  .waitlist-page {
    padding: 14px;
    align-items: center;
  }

  .brand-panel {
    padding: 18px;
  }

  .hero-logo {
    width: 150px;
  }

  .offer-modal {
    padding: 18px;
  }

  .modal-card footer {
    flex-direction: column-reverse;
  }

  .btn-primary,
  .btn-secondary {
    width: 100%;
  }

  .summary-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }

  .class-summary strong {
    text-align: left;
  }
}
</style>
