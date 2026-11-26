import axios from 'axios'
import { authState, clearSession } from '@/service/authState'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'
const API_ORIGIN = API_BASE_URL.replace(/\/api\/?$/, '')

export function resolveMediaUrl(url) {
  if (!url) return ''
  const value = String(url).trim()
  if (!value) return ''
  if (/^https?:\/\//i.test(value) || value.startsWith('data:') || value.startsWith('blob:')) {
    return value
  }
  return `${API_ORIGIN}${value.startsWith('/') ? value : `/${value}`}`
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  if (authState.accessToken) {
    config.headers.Authorization = `Bearer ${authState.accessToken}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && authState.accessToken) {
      clearSession()
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event('edusuggest:auth-expired'))
      }
    }
    return Promise.reject(error)
  },
)

export default api
