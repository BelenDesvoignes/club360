<template>
  <div class="booking-container">
    <header class="booking-header">
      <div class="booking-header-main">
        <div class="booking-header-left">
          <h1>{{ selectedSportId ? 'Reservar Turno' : 'Reservar' }}</h1>
          <div class="booking-stepline">
            <span class="step-pill">Paso {{ selectedSportId ? '2' : '1' }}</span>
            <span class="step-text">{{ selectedSportId ? 'Elegí el tipo de reserva y horario' : 'Elegí el deporte' }}</span>
          </div>
        </div>

        <div v-if="selectedSportId" class="booking-stepper" aria-label="Progreso de reserva">
          <div class="stepper-node done">
            <span class="node-dot">1</span>
            <span class="node-label">Deporte</span>
          </div>
          <div class="stepper-line"></div>
          <div class="stepper-node current">
            <span class="node-dot">2</span>
            <span class="node-label">Horario</span>
          </div>
          <div class="stepper-line"></div>
          <div class="stepper-node">
            <span class="node-dot">3</span>
            <span class="node-label">Confirmar</span>
          </div>
        </div>
      </div>
    </header>

    <!-- Paso 1: elegir deporte -->
    <div v-if="!selectedSportId && !loading && !userSuspended" class="sports-step">
      <div class="sports-grid">
        <button
          v-for="sport in sports"
          :key="sport.activity_id"
          type="button"
          class="sport-tile"
          :style="sportHeroStyle(sport.activity_name)"
          @click="selectSport(sport.activity_id)"
        >
          <div class="sport-tile-overlay">
            <div class="sport-tile-copy">
              <div class="sport-tile-title">{{ sport.activity_name || `Deporte ${sport.activity_id}` }}</div>
              <div class="sport-tile-sub">Ver horarios disponibles y reservar turnos</div>
            </div>
            <div class="sport-tile-action">Ver horarios y reservar</div>
          </div>
        </button>
      </div>

      <div v-if="sports.length === 0" class="empty-state">
        Todavía no hay deportes cargados para mostrar.
      </div>
    </div>

    <!-- Paso 2: tipo de reserva + filtro por día (solo si ya eligió deporte) -->
    <div v-if="selectedSportId && !userSuspended" class="reservation-controls">
      <div class="reserve-type">
        <button type="button" :class="{active: reservationType === 'class'}" @click="reservationType = 'class'">Reserva Única</button>
        <button type="button" :class="{active: reservationType === 'subscription'}" @click="reservationType = 'subscription'">Reservar Abono</button>
      </div>

      <div class="day-filter">
        <label>Filtrar por día</label>
        <select v-model="selectedWeekday">
          <option value="all">Todos</option>
          <option v-for="(label, idx) in weekDays" :key="idx" :value="label">{{ label }}</option>
        </select>
      </div>

      <button type="button" class="change-sport" @click="clearSport">Cambiar deporte</button>
    </div>

    <!-- Advertencia si está suspendido -->
    <div v-if="userSuspended" class="suspension-warning">
      <div class="warning-icon">🚫</div>
      <div class="warning-content">
        <h3>Tu cuenta está suspendida</h3>
        <p>Debes solicitar reactivación para poder hacer nuevas reservas. Contacta al soporte para resolver esto.</p>
      </div>
    </div>

    <div v-if="loading" class="loading-spinner">Cargando clases disponibles...</div>

    <div v-else-if="isRefreshing" class="loading-refresh">Actualizando...</div>

    <div v-if="successMessage" :class="['booking-feedback', bookingStatus]">
      <div>
        <strong>{{ bookingStatus === 'confirmed' || bookingStatus === 'completed' ? '¡Reserva confirmada!' : bookingStatus === 'cancelled' ? 'Reserva cancelada' : 'Reserva pendiente de pago' }}</strong>
        <p>{{ successMessage }}</p>
      </div>
      <button type="button" class="booking-feedback-close" @click="successMessage = ''">Cerrar</button>
    </div>

    <div v-else-if="userSuspended" class="suspended-block">
      <p>No puedes hacer reservas mientras tu cuenta esté suspendida.</p>
    </div>

    <div v-else-if="selectedSportId" class="classes-grid">
      <div
        v-for="activity in visibleActivities"
        :key="`${activity.activity_id}`"
        class="activity-shell"
      >
        <div class="activity-hero" :style="sportHeroStyle(activity.activity_name)">
          <div class="activity-hero-overlay">
            <div class="activity-hero-title">{{ activity.activity_name || `Actividad ${activity.activity_id}` }}</div>
            <div class="activity-hero-sub">
              {{ reservationType === 'subscription' ? 'Horarios recurrentes disponibles' : (activity.instances.length === 1 ? '1 turno disponible' : `${activity.instances.length} turnos disponibles`) }}
            </div>
          </div>
          <div class="activity-hero-chip">
            {{ reservationType === 'subscription' ? `${activity.templates?.length || 0} horarios` : `${activity.instances.length} turnos` }}
          </div>
        </div>

        <div class="activity-body">
          <template v-if="reservationType === 'subscription'">
            <div v-if="activity.templates && activity.templates.length" class="turn-grid">
              <div v-for="tpl in activity.templates" :key="`tpl-${tpl.id}`" class="turn-card">
                <div class="turn-card-top">
                  <div class="turn-card-date">{{ tpl.day_of_week }} · {{ tpl.start_time }}hs</div>
                  <span class="turn-card-badge available">Recurrente</span>
                </div>
                <div class="turn-card-body">
                  <div class="turn-card-row">Horario fijo semanal</div>
                  <div class="turn-card-row spots">Precio por clase: ${{ tpl.price }}</div>
                </div>
                <button type="button" class="turn-card-btn" @click="selectTemplateForSubscription(tpl, activity.activity_name)">
                  Seleccionar Abono
                </button>
              </div>
            </div>
            <div v-else class="no-turnos card-empty-inline">No hay horarios recurrentes para este deporte</div>
          </template>

          <template v-else>
            <div v-if="activity.instances.length > 0" class="turn-grid">
              <div v-for="turno in activity.instances" :key="turno.id" class="turn-card" :class="{ full: isFullyBooked(turno) }">
                <div class="turn-card-top">
                  <div class="turn-card-date">{{ formatBookingDate(turno.date, turno.template.day_of_week) }}</div>
                  <span class="turn-card-badge" :class="isFullyBooked(turno) ? 'full' : 'available'">
                    {{ isFullyBooked(turno) ? 'Completo' : 'Disponible' }}
                  </span>
                </div>

                <div class="turn-card-body">
                  <div class="turn-card-row">⏰ {{ formatTurnLabel(turno) }}</div>
                  <div class="turn-card-row">📍 {{ turno.court || 'Sin cancha' }}</div>
                  <div class="turn-card-row spots">👥 Cupos: {{ turno.booked_count }}/{{ turno.template.capacity }}</div>
                  <div class="turn-card-price">${{ turno.template.price }}</div>
                </div>

                <button
                  type="button"
                  class="turn-card-btn"
                  :class="{ disabled: isFullyBooked(turno) }"
                  :disabled="isFullyBooked(turno) || bookingInProgress"
                  @click="selectInstanceForBooking(turno)"
                >
                  {{ bookingInProgress && selectedInstance?.id === turno.id ? 'Procesando...' : (isFullyBooked(turno) ? 'Sin Cupo' : 'Reservar') }}
                </button>
              </div>
            </div>

            <div v-else class="no-turnos card-empty-inline">No hay turnos disponibles para esta actividad</div>
          </template>
        </div>
      </div>

      <div v-if="groupedActivities.length === 0" class="empty-state">
        Todavía no hay clases cargadas para mostrar.
      </div>
    </div>

    <PaymentModal
      v-model="showGatewayModal"
      :amount="pendingPaymentAmount"
      :depositAmount="Number(selectedInstance?.template?.price || 0) * 0.5"
      :fullAmount="Number(selectedInstance?.template?.price || 0)"
      :payeeName="selectedInstance?.activity_name || 'Reserva'"
      :isAbono="paymentType === 'monthly'"
      :busy="finalizingPayment"
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
                <div class="turno-date">{{ formatBookingDate(turno.date, turno.template.day_of_week) }}</div>
                <div class="turno-badge" :class="isFullyBooked(turno) ? 'full' : 'available'">
                  {{ isFullyBooked(turno) ? 'Sin cupos' : 'Disponible' }}
                </div>
              </div>

              <div class="turno-details">
                <div class="detail-row">
                  <span class="detail-label">Horario:</span>
                  <span class="detail-value">{{ formatTurnLabel(turno) }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">Cancha:</span>
                  <span class="detail-value">{{ turno.court || 'Sin cancha' }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">Cupos:</span>
                  <span class="detail-value">{{ turno.booked_count }} / {{ turno.template.capacity }}</span>
                </div>
                <div class="detail-row price-row">
                  <span class="detail-label">Precio de la clase:</span>
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
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useAppClockStore } from '../stores/appClock'
import PaymentModal from '../components/PaymentModal.vue'

const auth = useAuthStore()
const clock = useAppClockStore()
const router = useRouter()
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
const bookingStatus = ref('')
const successMessage = ref('')
const errorMessage = ref('')
const isRefreshing = ref(false)
const userSuspended = ref(false)
const isUserAbonado = ref(false)

const myBookings = ref([])
const myBookingsLoaded = ref(false)

const isAuthError = (e) => {
  const status = e?.response?.status
  const detail = String(e?.response?.data?.detail || '')
  return status === 401 || detail.toLowerCase().includes('token')
}

const handleAuthError = (e) => {
  if (!isAuthError(e)) return false
  auth.logout()
  router.push('/login')
  errorMessage.value = 'Tu sesión expiró. Iniciá sesión nuevamente.'
  return true
}

const showTurnosModal = ref(false)
const selectedActivity = ref(null)
const selectedInstance = ref(null)
const paymentType = ref('seña')

const showGatewayModal = ref(false)
const pendingPaymentAmount = ref(0)
const finalizingPayment = ref(false)

// Subscription quote state (backend is source of truth)
const subscriptionQuoteAmount = ref(0)
const subscriptionPayNowRequired = ref(true)
const subscriptionQuoteReason = ref('')

// Reservation UI state
const reservationType = ref('class') // 'class' or 'subscription'
const selectedWeekday = ref('all')
const weekDays = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
const selectedSportId = ref(null)

const sports = computed(() => groupedActivities.value.map(a => ({ activity_id: a.activity_id, activity_name: a.activity_name })))

const sportHeroStyle = (name) => {
  const normalized = String(name || '').toLowerCase()

  const base = {
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    backgroundRepeat: 'no-repeat',
  }

  if (normalized.includes('fut')) {
    return { ...base, backgroundColor: '#2d658d', backgroundImage: "url('/sports/futbol.png')" }
  }

  if (normalized.includes('pad') || normalized.includes('pádel') || normalized.includes('paddle')) {
    return { ...base, backgroundColor: '#5a8849', backgroundImage: "url('/sports/padel.png')" }
  }

  if (normalized.includes('bas') || normalized.includes('basket')) {
    return { ...base, backgroundColor: '#ff6f00', backgroundImage: "url('/sports/basquet.png')" }
  }

  if (normalized.includes('vol') || normalized.includes('vóley') || normalized.includes('voley')) {
    return { ...base, backgroundColor: '#2d658d', backgroundImage: "url('/sports/voley.png')" }
  }

  return { ...base, backgroundColor: '#2d658d', backgroundImage: 'none' }
}

const selectSport = (sportId) => {
  selectedSportId.value = sportId
  reservationType.value = 'class'
  selectedWeekday.value = 'all'
}

const clearSport = () => {
  selectedSportId.value = null
  reservationType.value = 'class'
  selectedWeekday.value = 'all'
}

const visibleActivities = computed(() => {
  const dayFilter = selectedWeekday.value
  const base = selectedSportId.value
    ? groupedActivities.value.filter(a => a.activity_id === selectedSportId.value)
    : []

  return base.map((act) => {
    let templates = act.templates || []
    let instancesList = act.instances || []

    if (dayFilter !== 'all') {
      templates = templates.filter(t => t.day_of_week === dayFilter)
      instancesList = instancesList.filter(i => (i.template && i.template.day_of_week === dayFilter))
    }

    if (reservationType.value === 'subscription') {
      return { ...act, templates, instances: [] }
    }
    return { ...act, templates: act.templates || [], instances: instancesList }
  }).filter(a => (a.templates.length || a.instances.length))
})

const weekdayToJsIndex = {
  Domingo: 0,
  Lunes: 1,
  Martes: 2,
  'Miércoles': 3,
  Miercoles: 3,
  Jueves: 4,
  Viernes: 5,
  Sábado: 6,
  Sabado: 6,
}

const countRemainingMonthlyOccurrences = (dayOfWeek) => {
  if (!dayOfWeek) return 0

  const targetDay = weekdayToJsIndex[dayOfWeek]
  if (targetDay === undefined) return 0

  const today = clock.effectiveNow
  const endOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0)
  let count = 0

  for (const cursor = new Date(today); cursor <= endOfMonth; cursor.setDate(cursor.getDate() + 1)) {
    if (cursor.getDay() === targetDay) {
      count += 1
    }
  }

  return count
}

function computeAmountToPay() {
  const price = Number(selectedInstance.value?.template?.price || 0)
  if (!Number.isFinite(price) || price <= 0) return 0
  if (paymentType.value === 'monthly') {
    if (Number.isFinite(subscriptionQuoteAmount.value) && subscriptionQuoteAmount.value > 0) {
      return subscriptionQuoteAmount.value
    }
    return price * countRemainingMonthlyOccurrences(selectedInstance.value?.template?.day_of_week)
  }
  return paymentType.value === 'full' ? price : price * 0.5
}

const isSubscriptionWindowOpen = computed(() => {
  const day = clock.effectiveNow.getDate()
  return day >= 1 && day <= 30
})

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
  const date = parseLocalDate(dateStr)
  if (!date) return 'Sin fecha'
  return date.toLocaleDateString('es-AR', { day: '2-digit', month: 'long', year: 'numeric' })
}

const formatBookingDate = (dateStr, fallbackDay) => {
  const date = parseLocalDate(dateStr)
  if (!date) return fallbackDay || 'Sin fecha'

  const formatted = date.toLocaleDateString('es-AR', {
    weekday: 'long',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })

  return formatted.replace(',', '').charAt(0).toUpperCase() + formatted.replace(',', '').slice(1)
}

const formatTurnLabel = (instance) => {
  if (!instance) return 'Sin horario'
  return `${instance.template?.start_time || '--:--'}hs`
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

const fetchInstances = async ({ showRefresh = false } = {}) => {
  if (showRefresh) isRefreshing.value = true
  try {
    // Add cache busting and timeout to prevent slow loads
    const res = await axios.get('/shifts/instances', {
      timeout: 5000
    })
    instances.value = res.data
  } catch (e) {
    console.error('Error al cargar clases:', e)
    instances.value = []
  } finally {
    if (showRefresh) isRefreshing.value = false
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
    
    const res = await axios.get('/subscriptions/me/status', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })

    userSuspended.value = Boolean(res.data?.suspended)
  } catch (e) {
    if (handleAuthError(e)) return
    console.error('Error al verificar estado:', e)
  }
}

const fetchMyBookings = async ({ showRefresh = false } = {}) => {
  if (showRefresh) isRefreshing.value = true
  try {
    auth.hydrateFromToken()
    const token = auth.token || localStorage.getItem('token')
    if (!token) {
      myBookings.value = []
      myBookingsLoaded.value = true
      return
    }

    const res = await axios.get('/bookings/me', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })

    myBookings.value = Array.isArray(res.data) ? res.data : []
    myBookingsLoaded.value = true
  } catch (e) {
    if (handleAuthError(e)) return
    myBookings.value = []
    myBookingsLoaded.value = true
  } finally {
    if (showRefresh) isRefreshing.value = false
  }
}

const hasActiveBookingForInstance = (instanceId) => {
  if (!instanceId) return false
  return myBookings.value.some((b) => b?.instance_id === instanceId && b?.status !== 'Cancelled')
}

const selectInstanceForBooking = async (instance) => {
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

  if (!myBookingsLoaded.value) {
    await fetchMyBookings({ showRefresh: true })
  }

  if (hasActiveBookingForInstance(instance.id)) {
    errorMessage.value = 'Ya tenés una reserva para este turno.'
    selectedInstance.value = null
    return
  }

  // Flujo directo: abonado reserva, no abonado abre modal de pago.
  paymentType.value = 'seña'
  await checkAbonado(instance.template.id)
  await confirmBooking()
}

const selectTemplateForSubscription = async (template, activity_name) => {
  if (!isSubscriptionWindowOpen.value) {
    errorMessage.value = '⚠️ El abono mensual solo puede pagarse entre el día 1 y el 30.'
    return
  }

  // prepare selectedInstance shape similar to instance for reuse in modal
  selectedInstance.value = {
    template: template,
    activity_name: activity_name,
    id: null,
    date: null,
  }

  // Compra de abono: se paga al 100% (sin "reserva" previa).
  paymentType.value = 'monthly'
  await checkAbonado(template.id)
  if (isUserAbonado.value) {
    errorMessage.value = 'Ya tenés un abono activo para este horario.'
    closePaymentModal()
    return
  }

  // Ask backend for the quote (discount + remaining classes + pay-now rule)
  try {
    auth.hydrateFromToken()
    const token = auth.token || localStorage.getItem('token')
    if (!token) {
      errorMessage.value = 'Tu sesión expiró. Iniciá sesión nuevamente.'
      closePaymentModal()
      return
    }

    const quoteRes = await axios.get('/subscriptions/quote', {
      params: { template_id: template.id },
      headers: { Authorization: `Bearer ${token}` }
    })

    subscriptionQuoteAmount.value = Number(quoteRes.data?.amount || 0)
    subscriptionPayNowRequired.value = Boolean(quoteRes.data?.pay_now_required)
    subscriptionQuoteReason.value = String(quoteRes.data?.discount_reason || '')
  } catch (e) {
    if (handleAuthError(e)) return
    const detail = e.response?.data?.detail || 'No se pudo calcular el abono.'
    errorMessage.value = detail
    closePaymentModal()
    return
  }

  pendingPaymentAmount.value = computeAmountToPay()
  if (!pendingPaymentAmount.value) {
    errorMessage.value = 'No se pudo determinar el monto a pagar.'
    closePaymentModal()
    return
  }

  showGatewayModal.value = true
}

const checkAbonado = async (template_id) => {
  try {
    auth.hydrateFromToken()
    const token = auth.token || localStorage.getItem('token')
    
    if (!token) {
      isUserAbonado.value = false
      return false
    }
    
    if (!token) {
      isUserAbonado.value = false
      return false
    }

    const res = await axios.get('/subscriptions/me/active', {
      params: { template_id },
      headers: {
        Authorization: `Bearer ${token}`
      }
    })

    isUserAbonado.value = Boolean(res.data?.active)
    return isUserAbonado.value
  } catch (e) {
    if (handleAuthError(e)) return false
    isUserAbonado.value = false
    return false
  }
}

async function finalizeSubscriptionPurchase() {
  auth.hydrateFromToken()
  const token = auth.token || localStorage.getItem('token')

  if (!token) {
    errorMessage.value = 'Tu sesión expiró. Iniciá sesión nuevamente.'
    return
  }

  const templateId = selectedInstance.value?.template?.id
  if (!templateId) {
    errorMessage.value = 'No se pudo determinar el horario (template) para el abono.'
    return
  }

  let res
  try {
    res = await axios.post(
      '/subscriptions/purchase',
      { template_id: templateId },
      { headers: { Authorization: `Bearer ${token}` } }
    )
  } catch (e) {
    if (handleAuthError(e)) return
    throw e
  }

  bookingStatus.value = 'completed'
  errorMessage.value = ''
  const pagoTxt = subscriptionPayNowRequired.value
    ? 'Pago registrado.'
    : `Pago pendiente: $${pendingPaymentAmount.value}.`
  const reglaTxt = subscriptionQuoteReason.value ? ` ${subscriptionQuoteReason.value}` : ''

  successMessage.value = `¡Abono mensual registrado! ${pagoTxt}${reglaTxt} ` +
    `Reservas creadas: ${res.data.bookings_created}. ` +
    `Saltadas (sin cupo): ${res.data.skipped_full}. Ya existentes: ${res.data.skipped_existing}. ` +
    `Vigencia hasta: ${res.data.valid_to}.`

  closePaymentModal()
  showGatewayModal.value = false

  setTimeout(() => {
    fetchInstances({ showRefresh: true })
    fetchMyBookings({ showRefresh: true })
  }, 800)
}

const closePaymentModal = () => {
  selectedInstance.value = null
  paymentType.value = 'seña'
  isUserAbonado.value = false
  subscriptionQuoteAmount.value = 0
  subscriptionPayNowRequired.value = true
  subscriptionQuoteReason.value = ''
}

async function finalizeBookingWithPayment() {
  auth.hydrateFromToken()
  const token = auth.token || localStorage.getItem('token')

  if (!token) {
    errorMessage.value = 'Tu sesión expiró. Iniciá sesión nuevamente.'
    return
  }

  let res
  try {
    res = await axios.post('/bookings/', {
      instance_id: selectedInstance.value.id
    }, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
  } catch (e) {
    if (handleAuthError(e)) return
    throw e
  }

  if (pendingPaymentAmount.value > 0) {
    try {
      await axios.post(
        '/payments/me/complete-booking',
        { amount: pendingPaymentAmount.value, booking_id: res.data.id },
        { headers: { Authorization: `Bearer ${token}` } }
      )
    } catch (e) {
      if (handleAuthError(e)) return
      throw e
    }
  }

  bookingStatus.value = 'completed'
  errorMessage.value = ''
  successMessage.value = `¡Tu reserva fue confirmada y el pago fue exitoso! Número de reserva: ${res.data.id}`
  closePaymentModal()

  setTimeout(() => {
    fetchInstances({ showRefresh: true })
    fetchMyBookings({ showRefresh: true })
  }, 1500)
}

function onGatewayResult(result) {
  if (!result) return
  const isSubscription = paymentType.value === 'monthly'

  if (result.status === 'Aprobado') {
    if (Number.isFinite(result.amount) && result.amount > 0) {
      pendingPaymentAmount.value = result.amount
    }

    if (result.paymentType === 'full') {
      paymentType.value = 'full'
    } else if (result.paymentType === 'deposit') {
      paymentType.value = 'seña'
    }

    const afterApproved = paymentType.value === 'monthly'
      ? finalizeSubscriptionPurchase
      : finalizeBookingWithPayment

    finalizingPayment.value = true
    afterApproved()
      .then(() => {
        showGatewayModal.value = false
      })
      .catch((e) => {
        if (handleAuthError(e)) return
        const detail = e.response?.data?.detail || 'Error al procesar la operación'
        errorMessage.value = detail
      })
      .finally(() => {
        finalizingPayment.value = false
      })
    return
  }

  // Days 1-10: allow subscription purchase even if payment isn't effective (pending payment).
  if (isSubscription && subscriptionPayNowRequired.value === false) {
    showGatewayModal.value = false
    finalizeSubscriptionPurchase().catch((e) => {
      if (handleAuthError(e)) return
      const detail = e.response?.data?.detail || 'Error al procesar la operación'
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
      errorMessage.value = ''
      successMessage.value =
        bookingStatus.value === 'completed'
          ? `¡Tu reserva ha sido confirmada! Número de reserva: ${res.data.id}`
          : `Tu reserva está pendiente. Número de reserva: ${res.data.id}.`

      closePaymentModal()
      setTimeout(() => {
        fetchInstances({ showRefresh: true })
        fetchMyBookings({ showRefresh: true })
      }, 1500)
      return
    }

    // No abonado: abrir PaymentModal.
    pendingPaymentAmount.value = computeAmountToPay()
    if (!pendingPaymentAmount.value) {
      errorMessage.value = 'No se pudo determinar el monto a pagar.'
      return
    }
    showGatewayModal.value = true
  } catch (e) {
    const detail = e.response?.data?.detail || 'Error al procesar la reserva'
    successMessage.value = ''
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
  fetchMyBookings({ showRefresh: true })
})
</script>

<style scoped>
.booking-container {
  padding: 28px 26px 40px;
  max-width: none;
  margin: 0;
  background: transparent;
  min-height: 100vh;
}

.booking-header {
  margin-bottom: 18px;
}

.booking-header-main {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.booking-header-left {
  min-width: 0;
}

.booking-header h1 {
  font-size: 2rem;
  color: #0d124a;
  font-weight: 900;
  margin: 0;
}

.booking-stepline {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}

.step-pill {
  font-weight: 800;
  font-size: 0.78rem;
  color: #155724;
  background: rgba(90, 136, 73, 0.18);
  border: 1px solid rgba(90, 136, 73, 0.28);
  padding: 6px 10px;
  border-radius: 999px;
  white-space: nowrap;
}

.step-text {
  color: rgba(13, 18, 74, 0.7);
  font-weight: 700;
  font-size: 0.95rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.booking-stepper {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(13, 18, 74, 0.1);
  box-shadow: 0 10px 22px rgba(17, 24, 39, 0.08);
}

.stepper-node {
  display: flex;
  align-items: center;
  gap: 8px;
}

.node-dot {
  width: 26px;
  height: 26px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  font-size: 0.78rem;
  background: rgba(13, 18, 74, 0.08);
  color: rgba(13, 18, 74, 0.7);
  border: 1px solid rgba(13, 18, 74, 0.12);
}

.stepper-node.done .node-dot {
  background: rgba(45, 101, 141, 0.14);
  color: #2d658d;
}

.stepper-node.current .node-dot {
  background: rgba(45, 101, 141, 0.18);
  color: #2d658d;
  border-color: rgba(45, 101, 141, 0.28);
}

.node-label {
  font-weight: 800;
  color: rgba(13, 18, 74, 0.8);
  font-size: 0.85rem;
}

.stepper-line {
  width: 26px;
  height: 2px;
  background: rgba(13, 18, 74, 0.12);
}

.reservation-controls {
  max-width: none;
  margin: 0 0 22px;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(45, 101, 141, 0.12);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  flex-wrap: wrap;
}

.reserve-type {
  display: flex;
  gap: 10px;
}

.reserve-type button {
  border: 1px solid rgba(45, 101, 141, 0.18);
  background: rgba(255, 255, 255, 0.8);
  color: #0d124a;
  padding: 10px 14px;
  border-radius: 999px;
  font-weight: 800;
  cursor: pointer;
}

.reserve-type button.active {
  background: #2d658d;
  color: white;
  border-color: transparent;
}

.day-filter {
  display: flex;
  align-items: center;
  gap: 10px;
}

.day-filter label {
  font-weight: 800;
  color: #0d124a;
  font-size: 0.9rem;
}

.day-filter select {
  border: 1px solid rgba(13, 18, 74, 0.18);
  background: white;
  border-radius: 12px;
  padding: 10px 12px;
  font-weight: 700;
  color: #0d124a;
}

.change-sport {
  border: none;
  background: rgba(45, 101, 141, 0.08);
  color: #2d658d;
  padding: 10px 12px;
  border-radius: 12px;
  font-weight: 800;
  cursor: pointer;
}

.change-sport:hover {
  background: rgba(45, 101, 141, 0.12);
}

.sports-step {
  max-width: none;
  margin: 0;
}

.sports-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;

  margin: 0;
}

.sport-tile {
  position: relative;
  border: 1px solid rgba(13, 18, 74, 0.12);
  border-radius: 18px;
  overflow: hidden;
  cursor: pointer;
  text-align: left;
  padding: 0;
  min-height: 168px;
  height: 100%;
  box-shadow: 0 18px 45px rgba(17, 24, 39, 0.12);
  background-size: cover;
  background-position: center;
}

.sport-tile::before {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.38);
}

.sport-tile-overlay {
  position: relative;
  z-index: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 18px;
  gap: 14px;
}

.sport-tile-copy {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sport-tile-title {
  color: #ffffff;
  font-weight: 900;
  font-size: 1.15rem;
}

.sport-tile-sub {
  color: rgba(255, 255, 255, 0.86);
  font-weight: 600;
  font-size: 0.85rem;
  max-width: 54ch;
}

.sport-tile-action {
  align-self: flex-end;
  background: #ff6f00;
  color: #ffffff;
  font-weight: 900;
  border-radius: 12px;
  padding: 10px 14px;
  font-size: 0.85rem;
  box-shadow: 0 10px 24px rgba(255, 111, 0, 0.25);
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

.loading-refresh {
  margin: 0 0 18px;
  padding: 10px 14px;
  border-radius: 14px;
  background: rgba(45, 101, 141, 0.08);
  border: 1px solid rgba(45, 101, 141, 0.18);
  color: #2d658d;
  font-weight: 900;
}

.booking-feedback {
  max-width: none;
  margin: 0 0 24px;
  padding: 18px 20px;
  border-radius: 16px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
}

.booking-feedback.confirmed {
  background: #eff6ff;
  border: 1px solid rgba(45, 101, 141, 0.22);
  color: #2d658d;
}

.booking-feedback.pending {
  background: #fff7f0;
  border: 1px solid rgba(255, 111, 0, 0.22);
  color: #ff6f00;
}

.booking-feedback.cancelled {
  background: #fff7ed;
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
  grid-template-columns: 1fr;
  gap: 18px;
}

.activity-shell {
  border-radius: 18px;
  overflow: hidden;
  border: 1px solid rgba(13, 18, 74, 0.12);
  background: rgba(255, 255, 255, 0.85);
  box-shadow: 0 16px 40px rgba(17, 24, 39, 0.12);
}

.activity-hero {
  position: relative;
  min-height: 90px;
  background-size: cover;
  background-position: center;
}

.activity-hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
}

.activity-hero-overlay {
  position: relative;
  z-index: 1;
  padding: 16px 18px;
}

.activity-hero-title {
  color: #ffffff;
  font-weight: 900;
  font-size: 1.05rem;
}

.activity-hero-sub {
  margin-top: 2px;
  color: rgba(255, 255, 255, 0.88);
  font-weight: 700;
  font-size: 0.82rem;
}

.activity-hero-chip {
  position: absolute;
  z-index: 1;
  top: 14px;
  right: 14px;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.22);
  color: rgba(255, 255, 255, 0.92);
  border-radius: 999px;
  padding: 6px 10px;
  font-weight: 900;
  font-size: 0.75rem;
}

.activity-body {
  padding: 16px 16px 18px;
}

.turn-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.turn-card {
  border-radius: 14px;
  border: 1px solid rgba(13, 18, 74, 0.1);
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 10px 24px rgba(17, 24, 39, 0.08);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.turn-card.full {
  opacity: 0.7;
}

.turn-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.turn-card-date {
  font-weight: 900;
  color: #0d124a;
  font-size: 0.86rem;
}

.turn-card-badge {
  font-weight: 900;
  font-size: 0.72rem;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid transparent;
  white-space: nowrap;
}

.turn-card-badge.available {
  background: rgba(90, 136, 73, 0.16);
  color: #155724;
  border-color: rgba(90, 136, 73, 0.25);
}

.turn-card-badge.full {
  background: rgba(220, 53, 69, 0.14);
  color: #721c24;
  border-color: rgba(220, 53, 69, 0.22);
}

.turn-card-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.turn-card-row {
  color: rgba(13, 18, 74, 0.78);
  font-weight: 700;
  font-size: 0.82rem;
}

.turn-card-row.spots {
  color: rgba(13, 18, 74, 0.62);
  font-weight: 800;
}

.turn-card-price {
  margin-top: 2px;
  color: #ff6f00;
  font-weight: 900;
  font-size: 0.92rem;
}

.turn-card-btn {
  width: 100%;
  border: none;
  border-radius: 10px;
  padding: 10px 12px;
  background: #ff6f00;
  color: #ffffff;
  font-weight: 900;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.turn-card-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 10px 22px rgba(255, 111, 0, 0.26);
}

.turn-card-btn:disabled,
.turn-card-btn.disabled {
  background: rgba(13, 18, 74, 0.14);
  color: rgba(13, 18, 74, 0.55);
  cursor: not-allowed;
  box-shadow: none;
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
  background: #ff6f00;
  border: none;
}

.reserve-direct-btn:hover {
  background: #ff6f00;
  box-shadow: 0 8px 22px rgba(255, 111, 0, 0.28);
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

@media (min-width: 1025px) {
  .booking-container {
    padding: 28px 40px 44px;
  }

  .booking-header {
    text-align: left;
  }

  .booking-header h1 {
    font-size: 2.2rem;
  }

  .sports-step {
    min-height: calc(100vh - 190px);
  }

  .sports-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    grid-auto-rows: minmax(190px, 1fr);
    min-height: calc(100vh - 190px);
  }

  .sport-tile {
    min-height: 190px;
    grid-column: auto;
  }
}

@media (max-width: 640px) {
  .booking-container {
    padding: 22px 14px;
  }

  .booking-header-main {
    flex-direction: column;
    align-items: flex-start;
  }

  .booking-stepper {
    display: none;
  }

  .sports-grid {
    grid-template-columns: 1fr;
  }

  .turn-grid {
    grid-template-columns: 1fr;
  }
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
  background: rgba(45, 101, 141, 0.08);
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
  font-size: 0.88rem;
  line-height: 1.15;
  margin-bottom: 3px;
  font-weight: 800;
}

.turn-info div {
  display: block;
  color: #6c757d;
  font-size: 0.82rem;
  line-height: 1.25;
  margin-top: 2px;
}

.turn-schedule {
  color: #0d124a !important;
}

.turn-spots {
  color: #4a4f5a !important;
}

.turn-price {
  color: #ff6f00 !important;
  font-weight: 700 !important;
}

.turn-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.btn-book {
  padding: 10px 16px;
  background: #2d658d;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-book:hover:not(:disabled) {
  background: #2d658d;
  transform: scale(1.02);
  box-shadow: 0 8px 18px rgba(45, 101, 141, 0.22);
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
  margin: 0 0 16px;
  color: #0d124a;
  font-weight: 800;
}

.payment-info {
  background: #fbfdff;
  border: 1px solid rgba(13, 18, 74, 0.08);
  padding: 16px 18px;
  border-radius: 16px;
  margin-bottom: 20px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
}

.payment-info .info-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
  align-items: center;
}

.payment-info .info-row:last-child {
  margin-bottom: 0;
}

.payment-info .label {
  font-weight: 700;
  color: #000000;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  flex-shrink: 0;
}

.payment-info .value {
  font-weight: 400;
  color: #0d124a;
  text-align: right;
  line-height: 1.2;
}

.price-amount {
  color: #ff6f00;
  font-size: 0.95rem;
  font-weight: 400;
  letter-spacing: -0.02em;
}

.payment-info .info-row.highlight {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(13, 18, 74, 0.08);
}

.payment-info .info-row.highlight .label,
.payment-info .info-row.highlight .value {
  color: #0d124a;
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
  background: #2d658d;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-turno-reserve:hover:not(:disabled):not(.disabled) {
  background: #2d658d;
  transform: translateY(-2px);
  box-shadow: 0 8px 18px rgba(45, 101, 141, 0.22);
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