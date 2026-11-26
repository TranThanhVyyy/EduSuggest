import api from '@/service/api'
import { authState, clearSession, setCurrentUser, setSession } from '@/service/authState'

export async function registerAccount(values) {
  const { data } = await api.post('/auth/register', {
    tenTaiKhoan: values.username.trim().toLowerCase(),
    hoTen: values.fullName.trim(),
    email: values.email.trim(),
    matKhau: values.password,
    soDienThoai: values.phone.trim() || null,
  })
  return data
}

export async function loginAccount(username, password) {
  const { data } = await api.post('/auth/login', {
    tenTaiKhoan: username.trim().toLowerCase(),
    matKhau: password,
  })
  setSession(data.access_token, null)
  return loadCurrentUser()
}

export async function loadCurrentUser() {
  if (!authState.accessToken) {
    setCurrentUser(null)
    return null
  }
  const { data } = await api.get('/auth/me')
  setCurrentUser(data)
  return data
}

export async function logoutAccount() {
  try {
    if (authState.accessToken) await api.post('/auth/logout')
  } finally {
    clearSession()
  }
}

export async function changePassword(currentPassword, newPassword) {
  const { data } = await api.put('/users/change-password', {
    matKhauHienTai: currentPassword,
    matKhauMoi: newPassword,
  })
  return data
}

export function getRoleName(user = authState.user) {
  return String(user?.tenVaiTro || '').trim().toUpperCase()
}

export function getRoleLandingRouteName(user = authState.user) {
  const destinations = {
    ADMIN: 'admin-dashboard',
    EXPERT: 'reviewer-dashboard',
    PROVIDER: 'provider-dashboard',
    USER: 'user-dashboard',
  }
  return destinations[getRoleName(user)] || 'access-denied'
}
