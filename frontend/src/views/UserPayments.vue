<template>
  <div class="payments-container">
    <div class="header-section">
      <h1 class="main-title">Mis Pagos</h1>
      <p class="subtitle">Historial financiero y comprobantes de tu cuenta en el club.</p>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Buscando movimientos financieros...</p>
    </div>

    <div v-else-if="payments.length" class="table-wrapper">
      <table class="custom-table">
        <thead>
          <tr>
            <th class="col-date">Fecha de Emisión</th>
            <th class="col-concept">Concepto / Categoría</th>
            <th class="col-amount text-right">Monto Total</th>
            <th class="col-status text-center">Estado del Pago</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in paginatedPayments" :key="p.id" class="table-row">
            <td class="cell-date font-medium text-nowrap">
              {{ formatDate(p.date) }}
            </td>
            <td class="cell-concept capitalize font-semibold">
              {{ p.type === 'booking' ? 'Reserva de Clase' : p.type }}
            </td>
            <td class="cell-amount text-right font-mono font-bold text-base">
              ${{ p.amount }}
            </td>
            <td class="cell-status text-center">
              <span :class="['status-badge', getStatusClass(p.status)]">
                {{ p.status === 'pending' ? 'Pendiente' : p.status }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="pagination-footer" v-if="totalPages !== 1">
        <button 
          @click="prevPage" 
          :disabled="currentPage === 1" 
          class="page-btn"
        >
          ← Anterior
        </button>
        
        <span class="page-info">
          Página <strong>{{ currentPage }}</strong> de {{ totalPages }}
        </span>
        
        <button 
          @click="nextPage" 
          :disabled="currentPage === totalPages" 
          class="page-btn"
        >
          Siguiente →
        </button>
      </div>
    </div>

    <div v-else class="empty-state-card">
      <div class="empty-icon-circle">
        <span role="img" aria-label="tarjeta">💳</span>
      </div>
      <h3>Sin pagos registrados</h3>
      <p>No encontramos ningún movimiento financiero asociado a tu cuenta actualmente.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const payments = ref([])
const loading = ref(false)

const currentPage = ref(1)
const itemsPerPage = ref(5)

const totalPages = computed(() => {
  return Math.ceil(payments.value.length / itemsPerPage.value)
})

const paginatedPayments = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  const end = start + itemsPerPage.value
  return payments.value.slice(start, end)
})

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
  }
}

const prevPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return dateStr 
  const d = date.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
  const t = date.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', hour12: false })
  return `${d} - ${t}`
}

const getStatusClass = (status) => {
  const s = status ? status.toLowerCase() : ''
  if (s.includes('pagado') || s.includes('approved') || s.includes('exitoso')) {
    return 'badge-success'
  }
  if (s.includes('pending') || s.includes('pendiente')) {
    return 'badge-warning'
  }
  return 'badge-danger'
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

const fetchPayments = async () => {
  loading.value = true
  try {
    currentPage.value = 1
    const userId = getUserIdFromExistingToken()
    const response = await api.get(`/payments/user/${userId}`)
    payments.value = response.data
  } catch (e) {
    console.error("Error cargando pagos:", e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchPayments)
</script>

<style scoped>
.payments-container {
  padding: 32px;
  max-width: 1100px;
  margin: 0 auto;
  padding-top: 100px;
  padding-left: 90px;
  font-family: system-ui, -apple-system, sans-serif;
}
.header-section { margin-bottom: 28px; }
.main-title { font-size: 1.85rem; font-weight: 800; color: #0d124a; margin: 0; letter-spacing: -0.5px; }
.subtitle { color: #64748b; font-size: 0.9rem; margin-top: 4px; }
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
.empty-state-card h3 { margin: 0; font-size: 1.2rem; color: #1e293b; font-weight: 700; }
.empty-state-card p { color: #94a3b8; font-size: 0.85rem; margin-top: 6px; }
.empty-icon-circle { width: 56px; height: 56px; background-color: #f1f5f9; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 1.5rem; margin: 0 auto 16px auto; }
.spinner { border: 3px solid #f3f4f6; border-top: 3px solid #0d124a; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 12px auto; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
</style>

