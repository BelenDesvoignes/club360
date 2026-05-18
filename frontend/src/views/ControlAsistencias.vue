<template>
  <div class="control-asistencias-container">
    <div class="header-box">
      <h2>🔒 Cierre Masivo de Asistencias</h2>
      <p class="subtitle">Módulo Administrativo - Procesamiento de Socios Ausentes</p>
    </div>

    <div class="management-card">
      <h3>Cierre de Turno por Evento</h3>
      <p class="info-text">
        Al ejecutar esta acción, el sistema buscará todas las reservas de la clase que hayan quedado en estado 
        <span class="badge pending">Pending</span> y las cambiará automáticamente a 
        <span class="badge absent">Absent</span>. También se incrementará el contador de penalizaciones de cada socio afectado.
      </p>

      <form @submit.prevent="handleCloseInstance" class="control-form">
        <div class="form-group">
          <label for="instance-id">ID de la Instancia de Clase (Turno):</label>
          <input 
            type="number" 
            id="instance-id" 
            v-model.number="instanceId" 
            placeholder="Ej: 14" 
            required
            :disabled="loading"
          />
        </div>

        <button type="submit" class="btn-submit" :disabled="loading || !instanceId">
          <span v-if="loading">⏳ Procesando Cierre...</span>
          <span v-else>🔒 Confirmar y Cerrar Planilla</span>
        </button>
      </form>
    </div>

    <div v-if="notification" :class="['notification-box', notification.type]">
      <div class="noti-icon">
        {{ notification.type === 'success' ? '🚀' : '⚠️' }}
      </div>
      <div class="noti-content">
        <h4>{{ notification.title }}</h4>
        <p>{{ notification.message }}</p>
        <div v-if="notification.type === 'success' && notification.count !== null" class="summary-box">
          <p><strong>Clase ID:</strong> #{{ notification.instanceId }}</p>
          <p><strong>Socios penalizados (Ausentes):</strong> {{ notification.count }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useAuthStore } from '../stores/auth';
import axios from 'axios';

const auth = useAuthStore();
const instanceId = ref(null);
const loading = ref(false);
const notification = ref(null);

const handleCloseInstance = async () => {
  if (!instanceId.value) return;
  
  loading.value = true;
  notification.value = null;

  try {
    
    const response = await axios.put(
      `http://127.0.0.1:8000/bookings/instances/${instanceId.value}/close`,
      {},
      {
        headers: {
          Authorization: `Bearer ${auth.token}` // Pasamos la credencial del empleado
        }
      }
    );

    // Se realizo el barrido con exito: 
    notification.value = {
      type: 'success',
      title: '¡Clase Cerrada Exitosamente!',
      message: response.data.message,
      instanceId: response.data.instance_id,
      count: response.data.absentees_processed
    };

    // Limpiamos el formulario tras el éxito: 
    instanceId.value = null;

  } catch (error) {
    // Capturamos los rebotes del backend (403 No autorizado, 404 No existe, etc.)
    const apiError = error.response?.data?.detail || 'Error de comunicación con el servidor del club.';
    
    notification.value = {
      type: 'error',
      title: 'No se pudo completar el cierre',
      message: apiError,
      count: null
    };
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.control-asistencias-container {
  max-width: 600px;
  margin: 30px auto;
  padding: 0 20px;
  font-family: sans-serif;
}

.header-box {
  text-align: center;
  margin-bottom: 25px;
}

.subtitle {
  color: #6b7280;
  font-size: 0.95rem;
  margin-top: 5px;
}

.management-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  padding: 25px;
  border-radius: 14px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

.management-card h3 {
  margin: 0 0 10px 0;
  color: #1f2937;
  font-size: 1.25rem;
}

.info-text {
  color: #4b5563;
  font-size: 0.9rem;
  line-height: 1.5;
  margin-bottom: 20px;
}


.badge {
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 0.8rem;
}
.pending { background: #fef3c7; color: #d97706; }
.absent { background: #fee2e2; color: #dc2626; }

.control-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 0.9rem;
  font-weight: 600;
  color: #374151;
}

.form-group input {
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 1rem;
  outline: none;
  transition: border-color 0.2s;
}

.form-group input:focus {
  border-color: #ff6f00; 
}

.btn-submit {
  background: #ff6f00;
  color: white;
  border: none;
  padding: 12px;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.2s, opacity 0.2s;
}

.btn-submit:hover:not(:disabled) {
  background: #e66400;
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* PANELS DE NOTIFICACIÓN */
.notification-box {
  display: flex;
  align-items: flex-start;
  margin-top: 25px;
  padding: 20px;
  border-radius: 12px;
  animation: slideUp 0.3s ease-out;
}

.success {
  background-color: #ecfdf5;
  border: 1px solid #10b981;
  color: #065f46;
}

.error {
  background-color: #fff5f5;
  border: 1px solid #ef4444;
  color: #991b1b;
}

.noti-icon {
  font-size: 1.8rem;
  margin-right: 15px;
}

.noti-content h4 {
  margin: 0 0 5px 0;
  font-size: 1.1rem;
  font-weight: 700;
}

.noti-content p {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.4;
}

.summary-box {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #10b981;
  font-size: 0.85rem;
}

.summary-box p {
  margin: 4px 0;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(15px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>