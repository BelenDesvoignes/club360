<template>
  <div class="page">
    <div class="gestion-container">
      <header class="page-header">
        <h1>Gestión de Clientes</h1>
        <p>Panel de administración de clientes, estados de cuenta y reservas</p>
      </header>

      <div class="filters-card">
        <div class="filter-group search-group">
          <label>Buscar cliente</label>
          <input 
            type="text" 
            v-model="filterSearch" 
            placeholder="Ingresá nombre o DNI..." 
          />
        </div>
        
        <div class="filter-group">
          <label>Filtrar por Estado</label>
          <select v-model="filterStatus">
            <option value="">Todos los estados</option>
            <option value="Activo">Activo</option>
            <option value="Suspendido">Suspendido</option>
          </select>
        </div>

        <div class="actions-group">
          <button @click="resetFilters" class="btn-clear">Limpiar</button>
          <button @click="showCreateModal = true" class="btn-primary-action">+ Nuevo Cliente</button>
        </div>
      </div>

      <div class="table-container">
        <table class="shifts-table">
          <thead>
            <tr>
              <th>Nombre y Apellido</th>
              <th>DNI</th>
              <th>Estado</th>
              <th class="text-center">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="cliente in filteredClientes" :key="cliente.id">
              <tr :class="{ 'row-suspended': cliente.estado === 'Suspendido' }">
                <td>
                  <span class="client-name">{{ cliente.nombre }}</span>
                </td>
                <td>{{ cliente.dni }}</td>
                <td>
                  <span class="status-badge" :class="cliente.estado.toLowerCase()">
                    {{ cliente.estado }}
                  </span>
                </td>
                <td class="actions-cell justify-center">
                  <button 
                    @click="toggleSuspension(cliente)" 
                    class="icon-btn"
                    :disabled="loadingSuspension[cliente.id]"
                    :title="cliente.estado === 'Suspendido' ? 'Levantar suspensión' : 'Suspender cliente'"
                  >
                    <span v-if="loadingSuspension[cliente.id]" class="spinner-small"></span>
                    <span v-else>{{ cliente.estado === 'Suspendido' ? '✅' : '🚫' }}</span>
                  </button>

                  <button 
                    @click="toggleAccordion(cliente.id)" 
                    class="icon-btn" 
                    :class="{ 'rotate-arrow': activeAccordion === cliente.id }"
                    title="Ver operaciones"
                  >
                    {{ activeAccordion === cliente.id ? '▲' : '▼' }}
                  </button>

                  <div class="dropdown-wrapper">
                    <button 
                      @click.stop="toggleDropdown(cliente.id)" 
                      class="icon-btn" 
                      title="Más opciones"
                    >
                      ⋮
                    </button>
                    <div v-if="activeDropdown === cliente.id" class="dropdown-menu dropdown-right">
                      <button @click="editCliente(cliente)">✏️ Editar Datos</button>
                      <button @click="deleteCliente(cliente)" class="btn-delete-option">🗑️ Eliminar cliente</button>
                    </div>
                  </div>
                </td>
              </tr>

              <tr v-if="activeAccordion === cliente.id" class="accordion-row">
                <td colspan="4">
                  <div class="accordion-content">
                    <div class="accordion-header">
                      <h4>Operaciones asociadas a: <span>{{ cliente.nombre }}</span></h4>
                    </div>
                    <div class="accordion-actions">
                      <button @click="createReserva(cliente)" class="btn-nested">📅 Nueva Reserva</button>
                      <button @click="viewReservas(cliente)" class="btn-nested">🔍 Historial Reservas</button>
                      <button @click="viewPagos(cliente)" class="btn-nested">💳 Ver Pagos </button>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
        
        <div v-if="filteredClientes.length === 0" class="empty-state">
          No se encontraron clientes con los criterios de búsqueda.
        </div>
      </div>
    </div>

    <transition name="fade">
      <div v-if="showCreateModal" class="modal-overlay">
        <div class="modal-card form-modal-card">
          <header class="form-header">
            <h3>Registrar cliente</h3>
            <p>Crea una cuenta para un nuevo cliente desde el panel.</p>
          </header>

          <form @submit.prevent="handleSubmitForm" class="equipo-form">
            <div class="form-grid">
              <div class="input-group">
                <label>Nombre</label>
                <input v-model="form.first_name" type="text" required />
              </div>
              <div class="input-group">
                <label>Apellido</label>
                <input v-model="form.last_name" type="text" required />
              </div>
            </div>

            <div class="input-group">
              <label>DNI (sin puntos)</label>
              <input v-model="form.dni" type="text" required />
            </div>

            <div class="input-group">
              <label>Correo electrónico</label>
              <input v-model="form.email" type="email" required />
            </div>

            <div class="input-group">
              <label>Contraseña</label>
              <input v-model="form.password" type="password" required />
            </div>

            <div class="modal-actions-container">
              <button type="submit" class="btn-confirm" :disabled="loadingForm">
                <span v-if="loadingForm" class="spinner-inline"></span>
                <span v-else>Crear cliente</span>
              </button>
              <button type="button" @click="closeCreateModal" class="btn-cancel" :disabled="loadingForm">
                Cancelar
              </button>
            </div>
          </form>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div v-if="toastMessage" :class="['alert-toast', toastType]">{{ toastMessage }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

// Filtros reactivos
const filterSearch = ref('')
const filterStatus = ref('')

// Control de Modales y Loadings
const showCreateModal = ref(false)
const loadingForm = ref(false)
const loadingSuspension = ref({}) // Diccionario clave-valor para traquear loaders individuales por ID de cliente

// Estados de control de UI
const activeDropdown = ref(null)
const activeAccordion = ref(null)

// Sistema de Toasts estándar
const toastMessage = ref('')
const toastType = ref('')

// Formulario reactivo
const form = ref({
  first_name: '',
  last_name: '',
  dni: '',
  email: '',
  password: ''
})

// Lista de clientes conectada a la base de datos
const clientes = ref([])

const fetchClientes = async () => {
  try {
    const res = await axios.get('/admin/clientes')
    clientes.value = res.data.sort((a, b) => b.id - a.id)
  } catch (e) {
    showToast("Error al cargar el listado de clientes.", "error")
  }
}

const filteredClientes = computed(() => {
  return clientes.value.filter(c => {
    const searchLower = filterSearch.value.toLowerCase().trim()
    if (!searchLower) return !filterStatus.value || c.estado === filterStatus.value

    const matchNombre = c.nombre?.toLowerCase().includes(searchLower)
    const matchDni = c.dni?.startsWith(searchLower)
    const matchStatus = !filterStatus.value || c.estado === filterStatus.value
    
    return (matchNombre || matchDni) && matchStatus
  })
})

const resetFilters = () => {
  filterSearch.value = ''
  filterStatus.value = ''
}

const toggleDropdown = (clienteId) => {
  activeDropdown.value = activeDropdown.value === clienteId ? null : clienteId
}

const toggleAccordion = (clienteId) => {
  activeAccordion.value = activeAccordion.value === clienteId ? null : clienteId
}

const handleSubmitForm = async () => {
  loadingForm.value = true
  try {
    const res = await axios.post('/admin/crear-cliente', form.value)
    
    // 💡 SOLUCIÓN AL UNDEFINED: Forzamos la estructura exacta que la grilla requiere ('nombre' combinado)
    const nuevoCliente = {
      id: res.data?.id_user || res.data?.id || Date.now(),
      nombre: `${form.value.first_name.trim()} ${form.value.last_name.trim()}`, 
      dni: form.value.dni,
      estado: 'Activo'
    }

    clientes.value.unshift(nuevoCliente)
    showToast('Cliente creado con éxito en la base de datos.', 'success')
    closeCreateModal()
  } catch (error) {
    const errorMsg = error.response?.data?.detail || 'Error al guardar el cliente.'
    showToast(errorMsg, 'error')
  } finally {
    loadingForm.value = false
  }
}

const closeCreateModal = () => {
  showCreateModal.value = false
  form.value = { first_name: '', last_name: '', dni: '', email: '', password: '' }
}

const toggleSuspension = async (cliente) => {
  // Activamos el spinner únicamente para la id de este cliente
  loadingSuspension.value[cliente.id] = true
  try {
    const res = await axios.patch(`/admin/clientes/${cliente.id}/suspension`)
    
    const index = clientes.value.findIndex(c => c.id === cliente.id)
    if (index !== -1) {
      clientes.value[index].estado = res.data.nuevo_estado
    }
    
    if (res.data.nuevo_estado === 'Suspendido') {
      showToast(`Se ha suspendido al cliente ${cliente.nombre}`, 'error')
    } else {
      showToast(`Se levantó la suspensión para ${cliente.nombre}`, 'success')
    }
  } catch (error) {
    const errorMsg = error.response?.data?.detail || 'No se pudo alterar el estado del cliente'
    showToast(errorMsg, 'error')
  } finally {
    // Apagamos el spinner local
    loadingSuspension.value[cliente.id] = false
  }
}

const editCliente = (cliente) => alert(`Editar datos de: ${cliente.nombre}`)
const createReserva = (cliente) => alert(`Nueva reserva para: ${cliente.nombre}`)
const viewReservas = (cliente) => alert(`Historial de reservas de: ${cliente.nombre}`)
const viewPagos = (cliente) => alert(`Cuenta corriente de: ${cliente.nombre}`)

const deleteCliente = (cliente) => {
  if (confirm(`¿Estás seguro de que querés eliminar permanentemente a ${cliente.nombre}?`)) {
    alert(`Eliminando a: ${cliente.nombre}`)
  }
}

const showToast = (msg, type) => {
  toastMessage.value = msg
  toastType.value = type
  setTimeout(() => { toastMessage.value = '' }, 3000)
}

if (typeof window !== 'undefined') {
  window.addEventListener('click', () => {
    activeDropdown.value = null
  })
}

onMounted(fetchClientes)
</script>

<style scoped>
/* ==========================================
   ESTRUCTURA DE PÁGINA Y FONDO
   ========================================== */
.page {
  position: relative;
  min-height: 100vh;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
  background: #ffffff;
  font-family: 'Segoe UI', Roboto, sans-serif;
  box-sizing: border-box;
}

.page::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 300px;
  background: #2d658d;
  z-index: 0;
}

.gestion-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 40px;
  align-items: center;
}

.page-header {
  text-align: center;
  margin-bottom: 10px;
}
.page-header h1 {
  margin: 0 0 8px;
  font-size: 28px;
  color: #ffffff;
  font-weight: 800;
}
.page-header p {
  margin: 0;
  color: #e2e8f0;
  font-size: 15px;
}

/* ==========================================
   FILTROS (Estilo Card Flotante)
   ========================================== */
.filters-card { 
  width: 100%;
  background: white; 
  padding: 30px; 
  border-radius: 18px; 
  display: flex; 
  gap: 20px; 
  align-items: flex-end;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.15);
  box-sizing: border-box;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.search-group {
  flex: 2;
}

.filter-group label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}

input, select {
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px 12px;
  background: #ffffff;
  color: #111827;
  font-size: 15px;
  outline: none;
  box-sizing: border-box;
  height: 42px;
}

input:focus {
  border-color: #ff6f00;
}

.actions-group {
  display: flex;
  gap: 12px;
  align-items: center;
}

.btn-clear {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff8f5; 
  color: #ff6f00;     
  border: 1px solid #ffbc99;
  padding: 10px 20px;
  border-radius: 10px;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  height: 42px; 
  text-transform: uppercase;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.btn-clear:hover {
  background: #ff6f00;
  color: white;
  border-color: #ff6f00;
}

.btn-primary-action {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ff6f00;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 10px;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  height: 42px;
  text-transform: uppercase;
  transition: opacity 0.2s, transform 0.2s;
  white-space: nowrap;
  box-shadow: 0 4px 12px rgba(255, 111, 0, 0.2);
}

.btn-primary-action:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

/* ==========================================
   TABLA DE CLIENTES
   ========================================== */
.table-container { 
  width: 100%;
  background: white; 
  padding: 30px; 
  border-radius: 18px; 
  box-shadow: 0 10px 30px rgba(0,0,0,0.05);
  overflow-x: auto; 
  box-sizing: border-box;
}

.shifts-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.shifts-table th {
  padding: 12px;
  border-bottom: 2px solid #f3f4f6;
  color: #6b7280;
  font-size: 13px;
  text-transform: uppercase;
  font-weight: 800;
}

.shifts-table td {
  padding: 15px 12px;
  border-bottom: 1px solid #f9fafb;
  color: #374151;
  font-size: 14px;
  vertical-align: middle;
}

.client-name {
  font-weight: 700;
  color: #111827;
}

.row-suspended {
  background: #fffdfd;
}

.row-suspended .client-name {
  color: #9ca3af;
  text-decoration: line-through;
  opacity: 0.6;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 700;
  display: inline-block;
  text-transform: uppercase;
}

.status-badge.activo {
  background: #e6f4ea;
  color: #137333;
}

.status-badge.suspendido {
  background: #fce8e6;
  color: #c5221f;
}

.actions-cell {
  display: flex;
  gap: 20px;
  align-items: center;
}

.text-center { text-align: center; }
.justify-center { justify-content: center; }

/* 💡 BOTONES */
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  cursor: pointer;
  filter: grayscale(1);
  opacity: 0.4;
  font-size: 18px;
  transition: transform 0.2s, opacity 0.2s, filter 0.2s;
  padding: 0;
  min-width: 24px;
  min-height: 24px;
}

.icon-btn:hover:not(:disabled) {
  transform: scale(1.2);
  filter: grayscale(0);
  opacity: 1;
}

.icon-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

/* ==========================================
   NUEVA SUB-FILA EXPANDIBLE (ACORDEÓN ▼)
   ========================================== */
.accordion-row {
  background: #fdfefe;
  border-left: 4px solid #2d658d;
}

.accordion-row td {
  padding: 0px 24px 15px 24px !important;
  border-bottom: 1px solid #e5e7eb !important;
}

.accordion-content {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px 20px;
  animation: slideDown 0.2s ease-out;
}

.accordion-header h4 {
  margin: 0 0 12px 0;
  font-size: 12px;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.accordion-header h4 span {
  color: #1e293b;
  font-weight: 700;
}

.accordion-actions {
  display: flex;
  gap: 12px;
}

.btn-nested {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #334155;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.btn-nested:hover {
  background: #2d658d;
  color: white;
  border-color: #2d658d;
  transform: translateY(-1px);
}

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ==========================================
   MENÚ DESPLEGABLE CONTEXTUAL (OPCIONES ⋮)
   ========================================== */
.dropdown-wrapper {
  position: relative;
  display: inline-block;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 50;
  min-width: 160px;
  background-color: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.12);
  padding: 6px 0;
  margin-top: 6px;
  display: flex;
  flex-direction: column;
}

.dropdown-menu.dropdown-right {
  left: auto;
  right: 0;
}

.dropdown-menu button {
  width: 100%;
  padding: 10px 16px;
  background: none;
  border: none;
  text-align: left;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
  transition: background 0.2s;
}

.dropdown-menu button:hover {
  background-color: #f3f4f6;
  color: #111827;
}

.dropdown-menu button.btn-delete-option {
  color: #dc2626;
  border-top: 1px solid #f3f4f6;
}

.dropdown-menu button.btn-delete-option:hover {
  background-color: #fef2f2;
}

/* ==========================================
   MODAL DE REGISTRO INTEGRADO
   ========================================== */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(45, 101, 141, 0.8); 
  backdrop-filter: blur(4px);
  display: flex; justify-content: center; align-items: center; z-index: 100;
}

.form-modal-card {
  background: white;
  padding: 35px;
  border-radius: 18px;
  width: 90%;
  max-width: 480px;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.2);
}

.form-header {
  text-align: center;
  margin-bottom: 25px;
}

.form-header h3 {
  font-size: 22px;
  color: #111827;
  font-weight: 800;
  margin: 0;
}

.form-header p {
  color: #6b7280;
  font-size: 13px;
  margin-top: 6px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.input-group {
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  text-align: left;
}

.input-group label {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 6px;
}

.modal-actions-container {
  display: flex;
  gap: 10px;
  margin-top: 25px;
}

.btn-confirm { 
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 1; 
  background: #ff6f00; 
  color: white; 
  border: none; 
  padding: 12px; 
  border-radius: 10px; 
  font-weight: 700; 
  cursor: pointer;
  text-transform: uppercase;
  font-size: 13px;
  letter-spacing: 0.5px;
  min-height: 43px;
}

.btn-confirm:disabled {
  background: #d1d5db;
  cursor: not-allowed;
}

.btn-cancel {
  flex: 1;
  background: #e5e7eb;
  color: #374151;
  border: none;
  padding: 12px;
  border-radius: 10px;
  font-weight: 700;
  cursor: pointer;
  text-transform: uppercase;
  font-size: 13px;
}

.btn-cancel:hover:not(:disabled) {
  background: #cbd5e1;
}

.btn-cancel:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

/* ==========================================
   SPINNERS DE CARGA (CSS puro y elegante)
   ========================================== */
.spinner-inline {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 0.8s linear infinite;
}

.spinner-small {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  border-top-color: #374151;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ==========================================
   ALERTAS TOAST Y AUXILIARES
   ========================================== */
.alert-toast {
  position: fixed;
  bottom: 20px;
  right: 20px;
  padding: 15px 25px;
  border-radius: 12px;
  color: white;
  font-weight: 600;
  box-shadow: 0 10px 20px rgba(0,0,0,0.1);
  z-index: 1000;
}

.success { background: #2d658d; }
.error { background: #c0392b; }

.empty-state {
  padding: 40px;
  text-align: center;
  color: #9ca3af;
  font-weight: 600;
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>