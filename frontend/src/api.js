import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL ?? ''

const client = axios.create({
  baseURL: BASE,
  timeout: 60_000,
  headers: { 'Content-Type': 'application/json' },
})

export async function planTrip(payload) {
  const response = await client.post('/api/plan-trip/', payload)
  return response.data
}
