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
  }
}
