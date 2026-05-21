<template>
  <Teleport to="body">
    <div v-if="modelValue" class="modal-root" role="dialog" aria-modal="true">
      <div class="overlay" @click="close('dismiss')"></div>

      <div class="modal" tabindex="-1">
        <header class="modal-header">
          <div class="title-wrap">
            <h2 class="title">Pagar {{ payeeLabel }}</h2>
            <p class="subtitle">Usted está por pagar <strong>{{ formattedAmount }}</strong>.</p>
          </div>
          <button class="icon-btn" type="button" @click="close('dismiss')" aria-label="Cerrar">✕</button>
        </header>

        <section class="modal-body">
          <div class="summary">
            <div class="summary-row">
              <span class="k">Monto</span>
              <span class="v">{{ formattedAmount }}</span>
            </div>
            <div class="summary-row">
              <span class="k">Método</span>
              <span class="v">Tarjeta guardada</span>
            </div>
          </div>

          <div v-if="linkedCard" class="card-preview" :class="{ expired: isCardExpired }">
            <div class="card-top">
              <span class="pill">Guardada</span>
              <span class="exp" :class="{ bad: isCardExpired }">Vence {{ linkedCard.expiry }}</span>
            </div>
            <div class="card-number">**** **** **** {{ linkedCard.lastFour }}</div>
            <div class="card-meta">
              <div class="meta-col">
                <div class="meta-label">Titular</div>
                <div class="meta-value">{{ linkedCard.holderName }}</div>
              </div>
              
            </div>

            <p v-if="isCardExpired" class="inline-error">
              El pago fue rechazado porque su tarjeta está vencida.
            </p>
          </div>

          <div v-else class="no-card">
            <p class="no-card-title">No tenés una tarjeta vinculada.</p>
            <p class="no-card-sub">
              Para usar el pago virtual necesitás vincular una tarjeta, o podés abonar presencialmente en recepción.
            </p>

            <div class="no-card-actions">
              <button class="secondary" type="button" @click="goAddCard">Agregar tarjeta</button>
              <span class="hint">o abonar presencialmente en recepción</span>
            </div>
          </div>

          <p v-if="message" class="message" :class="messageType">{{ message }}</p>
        </section>

        <footer class="modal-footer">
          <button class="ghost" type="button" @click="close('cancel')" :disabled="isProcessing">Cancelar</button>
          <button
            class="primary"
            type="button"
            @click="pay"
            :disabled="!canPay"
          >
            {{ isProcessing ? 'Procesando…' : 'Pagar' }}
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import axios from 'axios'
import { gatewayService } from '../utils/gatewayService'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  amount: { type: Number, required: true },
  payeeName: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue', 'result'])

const router = useRouter()
const auth = useAuthStore()

const linkedCard = ref(null)
const isProcessing = ref(false)
const message = ref('')
const messageType = ref('') // success | error

const storageKey = computed(() => {
  const email = auth.userEmail || 'anonymous'
  return `club360:card:${email}`
})

function loadLinkedCard() {
  return axios
    .get('/cards/me')
    .then((res) => {
      const card = res.data
      if (!card) {
        linkedCard.value = null
        return
      }

      let token = ''
      try {
        const raw = localStorage.getItem(storageKey.value)
        const stored = raw ? JSON.parse(raw) : null
        token = stored?.token || ''
      } catch {
        token = ''
      }

      linkedCard.value = {
        token,
        lastFour: card.last_four,
        holderName: card.card_holder,
        expiry: card.expiry_date,
        status: card.status || 'Activa',
        linkedAt: card.created_at
      }
    })
    .catch((err) => {
      if (err?.response?.status === 401) {
        auth.logout()
        router.push('/login')
        linkedCard.value = null
        return
      }
      linkedCard.value = null
    })
}

function expiryIsValid(mmYY) {
  if (!mmYY || mmYY.length !== 5) return false
  const parts = mmYY.split('/')
  if (parts.length !== 2) return false

  const mm = Number(parts[0])
  const yy = Number(parts[1])
  if (!Number.isInteger(mm) || !Number.isInteger(yy)) return false
  if (mm < 1 || mm > 12) return false

  const year = 2000 + yy
  const now = new Date()
  const currentYear = now.getFullYear()
  const currentMonth = now.getMonth() + 1

  if (year < currentYear) return false
  if (year === currentYear && mm < currentMonth) return false

  return true
}

const isCardExpired = computed(() => {
  if (!linkedCard.value?.expiry) return true
  return !expiryIsValid(linkedCard.value.expiry)
})

const canPay = computed(() => {
  if (!props.modelValue) return false
  if (isProcessing.value) return false
  if (!linkedCard.value) return false
  if (isCardExpired.value) return false
  return Number.isFinite(props.amount) && props.amount > 0
})

const payeeLabel = computed(() => props.payeeName?.trim() || 'monto requerido')

const formattedAmount = computed(() => {
  try {
    return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(props.amount)
  } catch {
    return `$ ${props.amount}`
  }
})

const shortToken = computed(() => {
  const t = linkedCard.value?.token || ''
  if (!t) return '-'
  if (t.length <= 16) return t
  return `${t.slice(0, 8)}…${t.slice(-6)}`
})

function close(source) {
  message.value = ''
  messageType.value = ''
  emit('update:modelValue', false)

  emit('result', {
    status: 'Cancelado',
    source
  })
}

function goAddCard() {
  emit('update:modelValue', false)
  router.push('/agregar-tarjeta')
}

async function pay() {
  message.value = ''
  messageType.value = ''

  if (!linkedCard.value) {
    message.value = 'Para pagar virtualmente necesitás una tarjeta vinculada.'
    messageType.value = 'error'
    emit('result', { status: 'Rechazado', reason: 'no_card' })
    return
  }

  if (isCardExpired.value) {
    message.value = 'El pago fue rechazado porque su tarjeta está vencida.'
    messageType.value = 'error'
    emit('result', { status: 'Rechazado', reason: 'expired_card' })
    return
  }

  isProcessing.value = true
  try {
    const res = await gatewayService.charge({
      token: linkedCard.value.token,
      amount: props.amount,
      cardStatus: linkedCard.value.status
    })

    if (res.status === 'approved') {
      message.value = 'Pago exitoso.'
      messageType.value = 'success'
      emit('result', { status: 'Aprobado' })
      // autocierre suave
      setTimeout(() => emit('update:modelValue', false), 650)
      return
    }

    if (res.reason === 'insufficient_funds') {
      message.value = 'El pago fue rechazado por fondos insuficientes.'
      messageType.value = 'error'
      emit('result', { status: 'Rechazado', reason: 'insufficient_funds' })
      return
    }

    if (res.reason === 'card_blocked') {
      message.value = 'El pago fue rechazado porque su tarjeta está bloqueada.'
      messageType.value = 'error'
      emit('result', { status: 'Rechazado', reason: 'card_blocked' })
      return
    }

    message.value = 'El pago fue rechazado.'
    messageType.value = 'error'
    emit('result', { status: 'Rechazado', reason: res.reason || 'declined' })
  } catch {
    message.value = 'No se pudo procesar el pago. Intentá nuevamente.'
    messageType.value = 'error'
    emit('result', { status: 'Rechazado', reason: 'gateway_error' })
  } finally {
    isProcessing.value = false
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      loadLinkedCard()
      message.value = ''
      messageType.value = ''
    }
  }
)

onMounted(() => {
  loadLinkedCard()
})
</script>

<style scoped>
.modal-root {
  position: fixed;
  inset: 0;
  z-index: 3000;
}

.overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
}

.modal {
  position: relative;
  width: min(680px, calc(100% - 24px));
  margin: 60px auto;
  background: #ffffff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.25);
}

.modal-header {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
  padding: 18px 18px 12px;
  border-bottom: 1px solid rgba(13, 18, 74, 0.08);
}

.title {
  margin: 0;
  font-size: 1.2rem;
  color: #2d658d;
}

.subtitle {
  margin: 6px 0 0;
  color: #5f6b76;
}

.icon-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  color: #0d124a;
  font-size: 1.1rem;
  padding: 6px 10px;
  border-radius: 10px;
}

.icon-btn:hover {
  background: rgba(45, 101, 141, 0.08);
}

.modal-body {
  padding: 14px 18px;
}

.summary {
  border: 1px solid rgba(13, 18, 74, 0.08);
  border-radius: 14px;
  padding: 12px;
  background: rgba(45, 101, 141, 0.04);
}

.summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
}

.k {
  color: #0d124a;
  font-weight: 800;
  font-size: 0.9rem;
}

.v {
  color: #0d124a;
  font-weight: 800;
}

.card-preview {
  margin-top: 14px;
  border-radius: 14px;
  padding: 14px;
  color: white;
  background: #2d658d;
}

.card-preview.expired {
  filter: grayscale(0.1);
  opacity: 0.92;
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  font-weight: 800;
  font-size: 0.8rem;
}

.exp {
  font-size: 0.85rem;
  opacity: 0.95;
}

.exp.bad {
  font-weight: 900;
}

.card-number {
  font-size: 1.25rem;
  letter-spacing: 2px;
  font-weight: 900;
}

.card-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
}

.meta-label {
  font-size: 0.72rem;
  opacity: 0.85;
}

.meta-value {
  font-weight: 800;
}

.meta-col.right {
  text-align: right;
}

.meta-value.token {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.inline-error {
  margin: 10px 0 0;
  font-weight: 900;
  background: rgba(180, 59, 59, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.22);
  padding: 10px 12px;
  border-radius: 12px;
}

.no-card {
  margin-top: 14px;
  border-radius: 14px;
  padding: 14px;
  border: 1px dashed rgba(45, 101, 141, 0.35);
  background: rgba(45, 101, 141, 0.06);
}

.no-card-title {
  margin: 0;
  color: #2d658d;
  font-weight: 900;
}

.no-card-sub {
  margin: 8px 0 0;
  color: #5f6b76;
}

.no-card-actions {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.hint {
  color: #0d124a;
  opacity: 0.75;
  font-weight: 700;
}

.message {
  margin: 14px 0 0;
  font-weight: 900;
  padding: 10px 12px;
  border-radius: 12px;
}

.message.success {
  background: rgba(90, 136, 73, 0.12);
  border: 1px solid rgba(90, 136, 73, 0.35);
  color: #5a8849;
}

.message.error {
  background: rgba(180, 59, 59, 0.08);
  border: 1px solid rgba(180, 59, 59, 0.25);
  color: #b43b3b;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 18px 18px;
  border-top: 1px solid rgba(13, 18, 74, 0.08);
}

.ghost {
  border-radius: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(13, 18, 74, 0.18);
  background: white;
  color: #0d124a;
  font-weight: 900;
  cursor: pointer;
}

.primary {
  border-radius: 12px;
  padding: 12px 14px;
  border: none;
  background: #2d658d;
  color: white;
  font-weight: 900;
  cursor: pointer;
}

.secondary {
  border-radius: 12px;
  padding: 10px 12px;
  border: 1px solid rgba(45, 101, 141, 0.35);
  background: white;
  color: #2d658d;
  font-weight: 900;
  cursor: pointer;
}

.primary:disabled,
.ghost:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 520px) {
  .modal {
    margin: 18px auto;
  }
}
</style>
