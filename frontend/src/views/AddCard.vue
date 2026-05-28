<template>
  <div class="page">
    <div class="container">
      <header class="header">
        <h1>Vincular tarjeta</h1>
        <p class="subtitle">
          Guardamos solo un token y los últimos 4 dígitos. No almacenamos CVV.
        </p>
      </header>

      <section class="card-list" aria-label="Tarjeta vinculada">
        <div class="section-title">
          <h2>Mi tarjeta</h2>
        </div>

        <div v-if="linkedCard" class="linked-card">
          <div class="linked-card-top">
            <div class="linked-card-brand">Tarjeta</div>
            <div class="linked-card-status">Vinculada</div>
          </div>

          <div class="linked-card-number">**** **** **** {{ linkedCard.lastFour }}</div>
          <div class="linked-card-meta">
            <div>
              <div class="meta-label">Titular</div>
              <div class="meta-value">{{ linkedCard.holderName }}</div>
            </div>
            <div class="meta-right">
              <div class="meta-label">Vence</div>
              <div class="meta-value">{{ linkedCard.expiry }}</div>
            </div>
          </div>
        </div>

        <div v-else class="empty-state">
          No hay tarjeta vinculada.
        </div>
      </section>

      <section class="form-section" aria-label="Formulario de tarjeta">
        <div class="section-title">
          <h2>Datos de la tarjeta</h2>
        </div>

        <form class="form" @submit.prevent="onSubmit">
          <div class="grid">
            <div class="field">
              <label for="cardNumber">Número de tarjeta</label>
              <input
                id="cardNumber"
                v-model="form.cardNumber"
                inputmode="numeric"
                autocomplete="cc-number"
                placeholder="1234 5678 9012 3456"
                maxlength="19"
                :class="{ invalid: showError('cardNumber') }"
                @input="handleCardNumberInput"
                @blur="touched.cardNumber = true"
              />
              <p v-if="showError('cardNumber')" class="error">{{ errors.cardNumber }}</p>
            </div>

            <div class="field">
              <label for="holderName">Nombre del titular</label>
              <input
                id="holderName"
                v-model.trim="form.holderName"
                autocomplete="cc-name"
                placeholder="Nombre Apellido"
                :class="{ invalid: showError('holderName') }"
                @input="touched.holderName = true"
                @blur="touched.holderName = true"
              />
              <p v-if="showError('holderName')" class="error">{{ errors.holderName }}</p>
            </div>

            <div class="field">
              <label for="expiry">Fecha de vencimiento (MM/AA)</label>
              <input
                id="expiry"
                v-model="form.expiry"
                inputmode="numeric"
                autocomplete="cc-exp"
                placeholder="MM/AA"
                maxlength="5"
                :class="{ invalid: showError('expiry') }"
                @input="handleExpiryInput"
                @blur="touched.expiry = true"
              />
              <p v-if="showError('expiry')" class="error">{{ errors.expiry }}</p>
            </div>

            <div class="field">
              <label for="cvv">CVV</label>
              <input
                id="cvv"
                v-model="form.cvv"
                inputmode="numeric"
                autocomplete="cc-csc"
                placeholder="123"
                maxlength="4"
                :class="{ invalid: showError('cvv') }"
                @input="handleCvvInput"
                @blur="touched.cvv = true"
              />
              <p v-if="showError('cvv')" class="error">{{ errors.cvv }}</p>
            </div>
          </div>

          <div class="actions">
            <button class="primary" type="submit" :disabled="isSubmitting || !isFormValid">
              {{ linkedCard ? 'Reemplazar tarjeta' : 'Vincular tarjeta' }}
            </button>
            <p v-if="submitError" class="submit-error">{{ submitError }}</p>
            <p v-if="submitOk" class="submit-ok">Tarjeta vinculada correctamente.</p>
          </div>
        </form>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import { gatewayService } from '../utils/gatewayService'

const auth = useAuthStore()
const router = useRouter()

const isSubmitting = ref(false)
const submitError = ref('')
const submitOk = ref(false)

const form = reactive({
  cardNumber: '',
  holderName: '',
  expiry: '',
  cvv: ''
})

const touched = reactive({
  cardNumber: false,
  holderName: false,
  expiry: false,
  cvv: false
})

const storageKey = computed(() => {
  const email = auth.userEmail || 'anonymous'
  return `club360:card:${email}`
})

const linkedCard = ref(null)

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
        submitError.value = 'Tu sesión expiró. Volvé a iniciar sesión.'
        auth.logout()
        router.push('/login')
        return
      }
      linkedCard.value = null
    })
}

function saveLinkedCard(card) {
  localStorage.setItem(storageKey.value, JSON.stringify(card))
  linkedCard.value = card
}

function detectBrand(cardDigits) {
  const d = String(cardDigits || '')
  if (d.startsWith('4')) return 'Visa'
  if (/^5[1-5]/.test(d)) return 'Mastercard'
  if (/^3[47]/.test(d)) return 'Amex'
  return null
}

function digitsOnly(value) {
  return (value || '').replace(/\D/g, '')
}

function formatCardNumber(value) {
  // Mock/demo: requerimos 16 dígitos (4x4)
  const digits = digitsOnly(value).slice(0, 16)
  return digits.replace(/(\d{4})(?=\d)/g, '$1 ').trim()
}

function luhnIsValid(cardDigits) {
  if (!cardDigits) return false
  let sum = 0
  let shouldDouble = false

  for (let i = cardDigits.length - 1; i >= 0; i--) {
    let digit = Number(cardDigits[i])
    if (Number.isNaN(digit)) return false

    if (shouldDouble) {
      digit *= 2
      if (digit > 9) digit -= 9
    }

    sum += digit
    shouldDouble = !shouldDouble
  }

  return sum % 10 === 0
}

function parseExpiry(value) {
  const cleaned = (value || '').replace(/[^0-9/]/g, '')
  const digits = cleaned.replace(/\D/g, '').slice(0, 4)

  let mm = digits.slice(0, 2)
  let yy = digits.slice(2, 4)

  if (digits.length >= 3) {
    return `${mm}/${yy}`
  }
  return mm
}

function expiryIsValid(mmYY) {
  if (!mmYY || mmYY.length !== 5) return false
  const [mmStr, yyStr] = mmYY.split('/')
  if (!mmStr || !yyStr || mmStr.length !== 2 || yyStr.length !== 2) return false

  const mm = Number(mmStr)
  const yy = Number(yyStr)
  if (!Number.isInteger(mm) || !Number.isInteger(yy)) return false
  if (mm < 1 || mm > 12) return false

  // Interpretamos AA como 20AA (suficiente para tarjetas modernas)
  const year = 2000 + yy
  const now = new Date()
  const currentYear = now.getFullYear()
  const currentMonth = now.getMonth() + 1

  if (year < currentYear) return false
  if (year === currentYear && mm < currentMonth) return false

  return true
}

const errors = computed(() => {
  const next = {
    cardNumber: '',
    holderName: '',
    expiry: '',
    cvv: ''
  }

  const numberDigits = digitsOnly(form.cardNumber)
  if (!numberDigits) {
    next.cardNumber = 'Ingresá el número de tarjeta.'
  } else if (numberDigits.length !== 16) {
    next.cardNumber = 'El número debe tener 16 dígitos.'
  }

  if (!form.holderName) {
    next.holderName = 'Ingresá el nombre del titular.'
  } else if (form.holderName.length < 3) {
    next.holderName = 'El nombre del titular es muy corto.'
  }

  if (!form.expiry) {
    next.expiry = 'Ingresá la fecha de vencimiento.'
  } else if (!/^\d{2}\/\d{2}$/.test(form.expiry)) {
    next.expiry = 'Usá el formato MM/AA.'
  } else if (!expiryIsValid(form.expiry)) {
    next.expiry = 'La tarjeta está vencida o la fecha no es válida.'
  }

  const cvvDigits = digitsOnly(form.cvv)
  if (!cvvDigits) {
    next.cvv = 'Ingresá el CVV.'
  } else if (!/^\d{3,4}$/.test(cvvDigits)) {
    next.cvv = 'El CVV debe tener 3 o 4 dígitos.'
  }

  return next
})

const isFormValid = computed(() => Object.values(errors.value).every((msg) => !msg))

function hasError(field) {
  return Boolean(errors.value[field])
}

function showError(field) {
  return touched[field] && hasError(field)
}

function handleCardNumberInput() {
  touched.cardNumber = true
  form.cardNumber = formatCardNumber(form.cardNumber)
}

function handleExpiryInput() {
  touched.expiry = true
  form.expiry = parseExpiry(form.expiry)
}

function handleCvvInput() {
  touched.cvv = true
  form.cvv = digitsOnly(form.cvv).slice(0, 4)
}

function markAllTouched() {
  touched.cardNumber = true
  touched.holderName = true
  touched.expiry = true
  touched.cvv = true
}

async function onSubmit() {
  submitError.value = ''
  submitOk.value = false

  markAllTouched()

  if (hasError('cardNumber') || hasError('holderName') || hasError('expiry') || hasError('cvv')) {
    submitError.value = 'Revisá los campos marcados en rojo.'
    return
  }

  isSubmitting.value = true
  try {
    const data = {
      cardNumber: digitsOnly(form.cardNumber),
      holderName: form.holderName,
      expiry: form.expiry,
      cvv: digitsOnly(form.cvv)
    }

    const res = await gatewayService.tokenize(data)

    const lastFour = data.cardNumber.slice(-4)
    const apiRes = await axios.put('/cards/me', {
      card_holder: data.holderName,
      last_four: lastFour,
      expiry_date: data.expiry,
      brand: detectBrand(data.cardNumber)
    })

    // Guardamos token simulado local (en un gateway real, el token vendría del backend).
    saveLinkedCard({
      token: res.token,
      lastFour: apiRes.data.last_four,
      holderName: apiRes.data.card_holder,
      expiry: apiRes.data.expiry_date,
      status: apiRes.data.status || 'Activa',
      linkedAt: apiRes.data.created_at
    })

    // Limpieza visual: nunca persistimos CVV/PAN completos en estado
    form.cardNumber = ''
    form.cvv = ''

    submitOk.value = true
  } catch (e) {
    if (e?.response?.status === 401) {
      submitError.value = 'Tu sesión expiró. Volvé a iniciar sesión.'
      auth.logout()
      router.push('/login')
      return
    }
    submitError.value = 'No se pudo vincular la tarjeta. Intentá nuevamente.'
  } finally {
    isSubmitting.value = false
  }
}

async function onDelete() {
  submitError.value = ''
  submitOk.value = false
  isSubmitting.value = true
  try {
    await axios.delete('/cards/me')
    localStorage.removeItem(storageKey.value)
    linkedCard.value = null
    submitOk.value = true
  } catch {
    submitError.value = 'No se pudo eliminar la tarjeta. Intentá nuevamente.'
  } finally {
    isSubmitting.value = false
  }
}

onMounted(() => {
  loadLinkedCard()
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

.section-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin: 22px 0 10px;
}

.section-title h2 {
  margin: 0;
  font-size: 1rem;
  color: #0d124a;
}

.card-list,
.form-section {
  background: white;
  border-radius: 14px;
  padding: 18px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
}

.linked-card {
  border-radius: 14px;
  padding: 16px;
  background: #2d658d;
  color: white;
}

.linked-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.linked-card-brand {
  font-weight: 700;
}

.linked-card-status {
  font-size: 0.85rem;
  opacity: 0.9;
}

.linked-card-number {
  font-size: 1.25rem;
  letter-spacing: 2px;
  font-weight: 700;
}

.linked-card-meta {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-top: 14px;
}

.meta-label {
  font-size: 0.72rem;
  opacity: 0.85;
}

.meta-value {
  font-weight: 700;
}

.meta-right {
  text-align: right;
}

.empty-state {
  padding: 14px;
  border-radius: 12px;
  border: 1px dashed rgba(45, 101, 141, 0.35);
  color: #2d658d;
  background: rgba(45, 101, 141, 0.06);
}

.form {
  margin-top: 8px;
}

.grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
}

.field label {
  display: block;
  font-size: 0.85rem;
  font-weight: 700;
  color: #0d124a;
  margin-bottom: 6px;
}

.field input {
  width: 100%;
  border: 1px solid rgba(13, 18, 74, 0.2);
  border-radius: 10px;
  padding: 12px 12px;
  font-size: 1rem;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.field input:focus {
  border-color: #2d658d;
  box-shadow: 0 0 0 4px rgba(45, 101, 141, 0.15);
}

.field input.invalid {
  border-color: #b43b3b;
  box-shadow: 0 0 0 4px rgba(180, 59, 59, 0.12);
}

.error {
  margin: 6px 0 0;
  font-size: 0.85rem;
  color: #b43b3b;
}

.actions {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.primary {
  border: none;
  border-radius: 12px;
  padding: 12px 14px;
  font-size: 1rem;
  font-weight: 800;
  color: white;
  background: #5a8849;
  cursor: pointer;
  transition: transform 0.12s ease, filter 0.12s ease;
}

.secondary {
  border: 1px solid rgba(13, 18, 74, 0.22);
  border-radius: 12px;
  padding: 12px 14px;
  font-size: 1rem;
  font-weight: 800;
  color: #0d124a;
  background: white;
  cursor: pointer;
}

.secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.primary:hover {
  filter: brightness(0.98);
}

.primary:active {
  transform: translateY(1px);
}

.primary:disabled {
  opacity: 1;
  cursor: not-allowed;
  background: #9ca3af;
}

.submit-error {
  margin: 0;
  color: #b43b3b;
  font-weight: 700;
}

.submit-ok {
  margin: 0;
  background: #5a8849;
  color: #ffffff;
  font-weight: 900;
  padding: 12px 14px;
  border-radius: 12px;
  text-align: center;
}

@media (min-width: 900px) {
  .grid {
    grid-template-columns: 1.4fr 1fr;
  }
}
</style>
