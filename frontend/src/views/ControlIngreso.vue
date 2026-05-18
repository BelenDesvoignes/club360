<template>
  <div class="control-ingreso-container">
    <div class="header-box">
      <h2>📷 Control de Ingreso por QR</h2>
      <p class="subtitle">Stand de Recepción - Pase el código por el lector</p>
    </div>

    <div class="scanner-wrapper">
      <div id="qr-reader-canvas"></div>
    </div>

    <div v-if="feedback" :class="['feedback-card', feedback.type]">
      <div class="feedback-icon">
        {{ feedback.type === 'success' ? '✅' : '❌' }}
      </div>
      <div class="feedback-content">
        <h3>{{ feedback.title }}</h3>
        <p class="main-msg">{{ feedback.message }}</p>
        
        <div v-if="feedback.type === 'success' && feedback.data" class="socio-details">
          <p><strong>Socio:</strong> {{ feedback.data.client_name }}</p>
          <p><strong>Actividad:</strong> {{ feedback.data.activity_name }}</p>
          <p class="status-badge">Estado: Concreted</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue';
import { Html5Qrcode } from 'html5-qrcode';
import { useAuthStore } from '../stores/auth';
import axios from 'axios';

const auth = useAuthStore();
const feedback = ref(null);
let html5Qrcode = null;

const onScanSuccess = async (decodedText) => {
  if (html5Qrcode) await html5Qrcode.pause(true);

  try {
    const bookingId = parseInt(decodedText.trim ? decodedText.trim() : decodedText);
    
    if (isNaN(bookingId)) {
      throw new Error("El código QR escaneado no tiene un formato de reserva válido.");
    }

    const response = await axios.post(
      `http://127.0.0.1:8000/bookings/verify-qr?booking_id=${bookingId}`,
      {},
      {
        headers: {
          Authorization: `Bearer ${auth.token}`
        }
      }
    );

    feedback.value = {
      type: 'success',
      title: '¡Acceso Autorizado!',
      message: response.data.message,
      data: response.data
    };

  } catch (error) {
    const apiError = error.response?.data?.detail || error.message || 'Error de conexión con el servidor.';
    
    feedback.value = {
      type: 'error',
      title: 'Acceso Denegado',
      message: apiError
    };
  } finally {
    setTimeout(async () => {
      feedback.value = null;
      if (html5Qrcode) {
        try { html5Qrcode.resume(); } catch (e) { console.log(e); }
      }
    }, 3500);
  }
};

const onScanFailure = (error) => {};

onMounted(() => {
  html5Qrcode = new Html5Qrcode("qr-reader-canvas");
  
  html5Qrcode.start(
    { facingMode: "environment" },
    {
      fps: 10,
      qrbox: { width: 260, height: 260 }
    },
    onScanSuccess,
    onScanFailure
  ).catch(err => {
    console.error("Error de hardware en la cámara:", err);
    feedback.value = {
      type: 'error',
      title: 'Fallo de Hardware',
      message: 'No se detectó ninguna cámara activa o se denegaron los permisos del navegador.'
    };
  });
});

onBeforeUnmount(async () => {
  if (html5Qrcode) {
    try {
      if (html5Qrcode.isScanning) {
        await html5Qrcode.stop();
      }
    } catch (err) {
      console.error("Error al apagar la cámara:", err);
    }
  }
});
</script>

<style scoped>
.control-ingreso-container {
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

.scanner-wrapper {
  background: #1e293b;
  padding: 15px;
  border-radius: 16px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

#qr-reader-canvas {
  width: 100% !important;
  border: none !important;
  border-radius: 10px;
  overflow: hidden;
}

#qr-reader-canvas video {
  border-radius: 10px;
  object-fit: cover;
}

.feedback-card {
  display: flex;
  align-items: flex-start;
  margin-top: 25px;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
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

.feedback-icon {
  font-size: 2rem;
  margin-right: 15px;
}

.feedback-content h3 {
  margin: 0 0 5px 0;
  font-size: 1.2rem;
  font-weight: 700;
}

.main-msg {
  margin: 0;
  font-size: 0.95rem;
  line-height: 1.4;
}

.socio-details {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #10b981;
  font-size: 0.9rem;
}

.socio-details p {
  margin: 4px 0;
}

.status-badge {
  display: inline-block;
  margin-top: 5px !important;
  background: #10b981;
  color: white;
  padding: 2px 8px;
  border-radius: 6px;
  font-weight: bold;
  font-size: 0.8rem;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(15px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>