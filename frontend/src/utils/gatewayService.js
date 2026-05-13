// Simulación de pasarela: tokeniza datos sensibles (no persiste PAN/CVV)

export const gatewayService = {
  async tokenize(data) {
    // data: { cardNumber, holderName, expiry, cvv }
    // Simulamos latencia de red
    await new Promise((resolve) => setTimeout(resolve, 350))

    const rand = Math.random().toString(36).slice(2)
    const ts = Date.now().toString(36)

    return {
      token: `tok_${ts}_${rand}`
    }
  },

  async charge({ token, amount, cardStatus }) {
    // Simulamos latencia de red
    await new Promise((resolve) => setTimeout(resolve, 450))

    if (!token) {
      return { status: 'declined', reason: 'invalid_token' }
    }

    const numericAmount = Number(amount)
    if (!Number.isFinite(numericAmount) || numericAmount <= 0) {
      return { status: 'declined', reason: 'invalid_amount' }
    }

    // Regla de negocio simulada por status (alineada al enum del backend):
    // - 'Activa' => aprobado
    // - 'Sin Fondos' => rechazado por fondos
    // - 'Bloqueada' => rechazado por tarjeta bloqueada
    const normalized = String(cardStatus || 'Activa').trim().toLowerCase()

    if (normalized === 'sin fondos') {
      return { status: 'declined', reason: 'insufficient_funds' }
    }
    if (normalized === 'bloqueada') {
      return { status: 'declined', reason: 'card_blocked' }
    }

    return { status: 'approved' }
  }
}
