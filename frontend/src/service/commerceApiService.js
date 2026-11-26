import api from '@/service/api'

export function formatVnd(amount) {
  if (amount === null || amount === undefined || amount === '') {
    return 'Chưa cập nhật học phí'
  }
  const num = Number(amount)
  if (Number.isNaN(num)) return 'Chưa cập nhật học phí'
  if (num === 0) return 'Miễn phí'
  return `${new Intl.NumberFormat('vi-VN').format(num)} ₫`
}

export function generateIdempotencyKey(prefix = 'es') {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}-${crypto.randomUUID()}`
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export function commerceErrorMessage(error, fallback = 'Không thể xử lý yêu cầu. Vui lòng thử lại.') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
  return fallback
}

// Capabilities (zero-DB-query safe on Production)
export async function fetchCommerceCapabilities() {
  const { data } = await api.get('/commerce/capabilities')
  return data
}

// Wishlist
export async function fetchWishlist({ page = 1, pageSize = 12 } = {}) {
  const { data } = await api.get('/wishlist', {
    params: { page, page_size: pageSize },
  })
  return data
}

export async function fetchWishlistCount() {
  const { data } = await api.get('/wishlist/count')
  return data
}

export async function fetchWishlistStatus(courseId) {
  const { data } = await api.get(`/wishlist/${courseId}/status`)
  return data
}

export async function addToWishlist(courseId) {
  const { data } = await api.post(`/wishlist/${courseId}`)
  return data
}

export async function removeFromWishlist(courseId) {
  const { data } = await api.delete(`/wishlist/${courseId}`)
  return data
}

export async function moveWishlistToCart(courseId) {
  const { data } = await api.post(`/wishlist/${courseId}/move-to-cart`)
  return data
}

// Shopping Cart
export async function fetchCart() {
  const { data } = await api.get('/cart')
  return data
}

export async function fetchCartCount() {
  const { data } = await api.get('/cart/count')
  return data
}

export async function addToCart(courseId) {
  const { data } = await api.post('/cart/items', { maKhoaHoc: Number(courseId) })
  return data
}

export async function removeFromCart(courseId) {
  const { data } = await api.delete(`/cart/items/${courseId}`)
  return data
}

export async function clearCart() {
  const { data } = await api.delete('/cart')
  return data
}

// Buy Now validation
export async function validateBuyNow(courseId) {
  const { data } = await api.get(`/commerce/buy-now/validate/${courseId}`)
  return data
}

// Orders & Checkout
export async function previewOrder(payload) {
  const { data } = await api.post('/orders/preview', payload)
  return data
}

export async function createOrder(payload, idempotencyKey) {
  const { data } = await api.post('/orders', payload, {
    headers: { 'Idempotency-Key': idempotencyKey },
  })
  return data
}

export async function fetchOrders({ page = 1, pageSize = 10, trangThai = '' } = {}) {
  const params = { page, page_size: pageSize }
  if (trangThai) params.trang_thai = trangThai
  const { data } = await api.get('/orders', { params })
  return data
}

export async function fetchOrderDetail(orderId) {
  const { data } = await api.get(`/orders/${orderId}`)
  return data
}

export async function fetchOrderStatus(orderId) {
  const { data } = await api.get(`/orders/${orderId}/status`)
  return data
}

export async function cancelOrder(orderId, lyDo = '') {
  const { data } = await api.post(`/orders/${orderId}/cancel`, lyDo ? { lyDo } : {})
  return data
}

export async function initiatePayment(orderId, congThanhToan, idempotencyKey) {
  const { data } = await api.post(
    `/orders/${orderId}/payments`,
    { congThanhToan },
    { headers: { 'Idempotency-Key': idempotencyKey } },
  )
  return data
}

// Mock Payment Sandbox Simulator (test staging only)
export async function fetchMockPaymentSession(txnRef) {
  const { data } = await api.get(`/payments/mock/${encodeURIComponent(txnRef)}`)
  return data
}

export async function simulateMockPayment(txnRef, ketQua) {
  const { data } = await api.post(
    `/payments/mock/${encodeURIComponent(txnRef)}/simulate`,
    { ketQua },
  )
  return data
}

// VNPay Sandbox Return URL read-only verification (never grants enrollment)
export async function verifyVnpayReturn(queryParams) {
  const { data } = await api.get('/payments/vnpay/return', {
    params: queryParams,
  })
  return data
}

// USER Payment Incident Report (never asks for card/OTP/password)
export async function reportPaymentIncident(orderId, payload) {
  const { data } = await api.post(`/orders/${orderId}/incidents`, payload)
  return data
}

export async function fetchMyOrderIncidents(orderId) {
  const { data } = await api.get(`/orders/${orderId}/incidents`)
  return data
}

// ADMIN Commerce Management, Reconciliation & Exception Refunds
export async function fetchAdminCommerceOverview() {
  const { data } = await api.get('/admin/commerce/overview')
  return data
}

export async function fetchAdminRevenueDashboard() {
  const { data } = await api.get('/admin/commerce/revenue')
  return data
}

export async function fetchAdminOrders({ page = 1, pageSize = 20, trangThai = '', q = '' } = {}) {
  const params = { page, page_size: pageSize }
  if (trangThai) params.trang_thai = trangThai
  if (q) params.q = q
  const { data } = await api.get('/admin/commerce/orders', { params })
  return data
}

export async function fetchAdminTransactions() {
  const { data } = await api.get('/admin/commerce/transactions')
  return data
}

export async function fetchAdminReconciliationQueue() {
  const { data } = await api.get('/admin/commerce/reconciliation')
  return data
}

export async function fetchAdminIncidents() {
  const { data } = await api.get('/admin/commerce/incidents')
  return data
}

export async function adminActivateReconciliation(paymentId, lyDo) {
  const { data } = await api.post(`/admin/commerce/reconciliation/${paymentId}/activate`, { lyDo })
  return data
}

export async function adminCreateExceptionRefund(payload, idempotencyKey) {
  const { data } = await api.post('/admin/commerce/refunds', payload, {
    headers: { 'Idempotency-Key': idempotencyKey },
  })
  return data
}

export async function adminVerifyExceptionRefund(paymentId, ghiChuXacMinh) {
  const { data } = await api.post(`/admin/commerce/refunds/${paymentId}/verify`, { ghiChuXacMinh })
  return data
}

export async function adminExecuteExceptionRefund(paymentId, mockOutcome = 'REFUNDED') {
  const { data } = await api.post(`/admin/commerce/refunds/${paymentId}/execute`, { mockOutcome })
  return data
}

export async function adminReconcileUnknownRefund(paymentId, payload) {
  const { data } = await api.post(`/admin/commerce/refunds/${paymentId}/reconcile-unknown`, payload)
  return data
}

// PROVIDER Sales Dashboard (owner-scoped)
export async function fetchProviderSalesSummary() {
  const { data } = await api.get('/provider/sales/summary')
  return data
}

export async function fetchProviderSalesItems() {
  const { data } = await api.get('/provider/sales/items')
  return data
}
