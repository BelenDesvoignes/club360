<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="modal">

      <!-- Paso 1: Email -->
      <div v-if="paso === 1">
        <div class="modal-icon">🔑</div>
        <h2>Recuperar contraseña</h2>
        <p>Ingresá tu email y te enviamos un código de 6 dígitos.</p>
        <div class="control">
          <input v-model="email" type="email" placeholder="email@club.com" @keyup.enter="solicitarCodigo" />
        </div>
        <div v-if="error" class="alert">{{ error }}</div>
        <button class="primary" @click="solicitarCodigo" :disabled="cargando || !email">
          {{ cargando ? 'Enviando...' : 'Enviar código' }}
        </button>
        <button class="link" @click="$emit('close')">Cancelar</button>
      </div>

      <!-- Paso 2: Código -->
      <div v-else-if="paso === 2">
        <div class="modal-icon">📩</div>
        <h2>Revisá tu email</h2>
        <p>Enviamos un código a <strong>{{ email }}</strong>. Ingresalo abajo.</p>
        <div class="codigo-inputs">
          <input
            v-for="(_, i) in digitos"
            :key="i"
            :ref="el => inputsRef[i] = el"
            v-model="digitos[i]"
            type="text"
            inputmode="numeric"
            maxlength="1"
            class="digito"
            @input="avanzar(i)"
            @keydown.backspace="retroceder(i)"
          />
        </div>
        <div v-if="error" class="alert">{{ error }}</div>
        <button class="primary" @click="verificarCodigo" :disabled="cargando || !codigoCompleto">
          {{ cargando ? 'Verificando...' : 'Verificar código' }}
        </button>
        <button class="link" @click="solicitarCodigo">¿No llegó? Reenviar</button>
      </div>

      <!-- Paso 3: Nueva contraseña -->
      <div v-else-if="paso === 3">
        <div class="modal-icon">🔒</div>
        <h2>Nueva contraseña</h2>
        <p>Elegí una contraseña de al menos 8 caracteres.</p>
        <div class="control">
          <input
            v-model="nuevaPassword"
            :type="verPass ? 'text' : 'password'"
            placeholder="Nueva contraseña"
          />
          <button class="icon-button" type="button" @click="verPass = !verPass">
            {{ verPass ? '👁' : '👁' }}
          </button>
        </div>
        <div class="control">
          <input
            v-model="confirmarPassword"
            :type="verPass ? 'text' : 'password'"
            placeholder="Confirmar contraseña"
            @keyup.enter="resetearPassword"
          />
        </div>
        <div v-if="error" class="alert">{{ error }}</div>
        <button class="primary" @click="resetearPassword" :disabled="cargando || !nuevaPassword || !confirmarPassword">
          {{ cargando ? 'Guardando...' : 'Guardar contraseña' }}
        </button>
      </div>

      <!-- Paso 4: Éxito -->
      <div v-else-if="paso === 4">
        <div class="modal-icon">✅</div>
        <h2>¡Listo!</h2>
        <p>Tu contraseña fue actualizada correctamente. Ya podés iniciar sesión.</p>
        <button class="primary" @click="$emit('close')">Volver al login</button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'

const emit = defineEmits(['close'])

const paso = ref(1)
const email = ref('')
const digitos = ref(['', '', '', '', '', ''])
const inputsRef = ref([])
const nuevaPassword = ref('')
const confirmarPassword = ref('')
const verPass = ref(false)
const cargando = ref(false)
const error = ref('')

const codigoCompleto = computed(() => digitos.value.every(d => d !== ''))
const codigoString = computed(() => digitos.value.join(''))

function avanzar(i) {
  // Permitir solo números
  digitos.value[i] = digitos.value[i].replace(/\D/g, '')
  if (digitos.value[i] && i < 5) {
    inputsRef.value[i + 1]?.focus()
  }
}

function retroceder(i) {
  if (!digitos.value[i] && i > 0) {
    digitos.value[i - 1] = ''
    inputsRef.value[i - 1]?.focus()
  }
}

async function solicitarCodigo() {
  error.value = ''
  cargando.value = true
  try {
    await axios.post('/api/auth/forgot-password', { email: email.value })
    digitos.value = ['', '', '', '', '', '']
    paso.value = 2
  } catch (e) {
    error.value = 'Error al enviar el código. Verificá el email.'
  } finally {
    cargando.value = false
  }
}

async function verificarCodigo() {
  error.value = ''
  cargando.value = true
  try {
    await axios.post('/api/auth/verify-reset-code', {
      email: email.value,
      code: codigoString.value
    })
    paso.value = 3
  } catch (e) {
    error.value = 'Código inválido o expirado.'
    digitos.value = ['', '', '', '', '', '']
    inputsRef.value[0]?.focus()
  } finally {
    cargando.value = false
  }
}

async function resetearPassword() {
  error.value = ''
  if (nuevaPassword.value !== confirmarPassword.value) {
    error.value = 'Las contraseñas no coinciden.'
    return
  }
  if (nuevaPassword.value.length < 8) {
    error.value = 'La contraseña debe tener al menos 8 caracteres.'
    return
  }
  cargando.value = true
  try {
    await axios.post('/api/auth/reset-password', {
      email: email.value,
      code: codigoString.value,
      new_password: nuevaPassword.value
    })
    paso.value = 4
  } catch (e) {
    error.value = 'Error al actualizar la contraseña. Intentá de nuevo.'
  } finally {
    cargando.value = false
  }
}
</script>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 16px;
}

.modal {
  background: white;
  border-radius: 18px;
  padding: 32px 24px 24px;
  width: 100%;
  max-width: 360px;
  text-align: center;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
}

.modal-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

h2 {
  margin: 0 0 8px;
  font-size: 22px;
  color: #111827;
}

p {
  color: #6b7280;
  font-size: 14px;
  margin: 0 0 20px;
}

.control {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 12px;
}

.control input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 16px;
  background: transparent;
  color: #111827;
}

.control input::placeholder {
  color: #9ca3af;
}

.codigo-inputs {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 16px;
}

.digito {
  width: 44px;
  height: 54px;
  text-align: center;
  font-size: 22px;
  font-weight: 700;
  border: 2px solid #e5e7eb;
  border-radius: 10px;
  outline: none;
  color: #111827;
  transition: border-color 0.2s;
}

.digito:focus {
  border-color: #ff6f00;
}

.primary {
  width: 100%;
  padding: 13px;
  background: #ff6f00;
  color: white;
  border: none;
  border-radius: 10px;
  font-weight: 800;
  font-size: 15px;
  cursor: pointer;
  touch-action: manipulation;
  transition: background 0.2s;
}

.primary:hover:not(:disabled) {
  background: #e65c00;
}

.primary:disabled {
  background: #d1d5db;
  cursor: not-allowed;
}

.link {
  background: none;
  border: none;
  color: #1a237e;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 12px;
  display: block;
  width: 100%;
  touch-action: manipulation;
}

.alert {
  background: #fadbd8;
  color: #c0392b;
  padding: 10px;
  border-radius: 8px;
  font-size: 13px;
  margin-bottom: 12px;
}

.icon-button {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  padding: 0;
}
</style>