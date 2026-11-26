import { reactive, watch } from 'vue'
import { authState } from '@/service/authState'
import { getRoleName } from '@/service/authService'
import { fetchMyEnrollments } from '@/service/userApiService'
import {
  addToCart,
  addToWishlist,
  fetchCart,
  fetchCommerceCapabilities,
  fetchWishlist,
  moveWishlistToCart,
  removeFromCart,
  removeFromWishlist,
} from '@/service/commerceApiService'

export const commerceState = reactive({
  capabilitiesLoaded: false,
  marketplaceEnabled: false,
  enrollmentGateEnabled: false,
  mockPaymentEnabled: false,
  vnpaySandboxEnabled: false,
  orderTtlMinutes: 15,

  loadedForUserId: null,
  loading: false,
  wishlistIds: new Set(),
  wishlistCount: 0,
  cartIds: new Set(),
  cartCount: 0,
  cartValidCount: 0,
  enrolledIds: new Set(),

  toastMessage: '',
  toastVariant: 'info',
})

let toastTimer = null
let capabilitiesPromise = null

export function showCommerceToast(message, variant = 'info') {
  if (toastTimer) {
    clearTimeout(toastTimer)
    toastTimer = null
  }
  commerceState.toastMessage = message
  commerceState.toastVariant = variant
  toastTimer = setTimeout(() => {
    commerceState.toastMessage = ''
    toastTimer = null
  }, 3600)
}

export function dismissCommerceToast() {
  if (toastTimer) {
    clearTimeout(toastTimer)
    toastTimer = null
  }
  commerceState.toastMessage = ''
}

export function resetCommerceState() {
  commerceState.loadedForUserId = null
  commerceState.loading = false
  commerceState.wishlistIds = new Set()
  commerceState.wishlistCount = 0
  commerceState.cartIds = new Set()
  commerceState.cartCount = 0
  commerceState.cartValidCount = 0
  commerceState.enrolledIds = new Set()
}

export async function loadCommerceCapabilities(force = false) {
  if (commerceState.capabilitiesLoaded && !force) {
    return commerceState
  }
  if (!capabilitiesPromise || force) {
    capabilitiesPromise = fetchCommerceCapabilities()
      .then((caps) => {
        commerceState.marketplaceEnabled = Boolean(caps?.marketplaceEnabled)
        commerceState.enrollmentGateEnabled = Boolean(caps?.enrollmentGateEnabled)
        commerceState.mockPaymentEnabled = Boolean(caps?.mockPaymentEnabled)
        commerceState.vnpaySandboxEnabled = Boolean(caps?.vnpaySandboxEnabled)
        commerceState.orderTtlMinutes = Number(caps?.orderTtlMinutes) || 15
        commerceState.capabilitiesLoaded = true
        return commerceState
      })
      .catch(() => {
        // Fail-closed: never break Production EduSuggest (24 tables)
        commerceState.marketplaceEnabled = false
        commerceState.enrollmentGateEnabled = false
        commerceState.mockPaymentEnabled = false
        commerceState.vnpaySandboxEnabled = false
        commerceState.capabilitiesLoaded = true
        return commerceState
      })
      .finally(() => {
        capabilitiesPromise = null
      })
  }
  return capabilitiesPromise
}

export async function syncLearnerCommerceState({ force = false } = {}) {
  await loadCommerceCapabilities()
  const isAuthed = Boolean(authState.accessToken && authState.user)
  const isLearner = isAuthed && getRoleName() === 'USER'
  const userId = authState.user?.maNguoiDung ?? null

  if (!isLearner || !userId) {
    resetCommerceState()
    return
  }

  if (!commerceState.marketplaceEnabled) {
    // Still sync enrollments safely if needed, never call Marketplace APIs on Production
    commerceState.wishlistIds = new Set()
    commerceState.wishlistCount = 0
    commerceState.cartIds = new Set()
    commerceState.cartCount = 0
    commerceState.cartValidCount = 0
    return
  }

  if (!force && commerceState.loadedForUserId === userId) {
    return
  }

  commerceState.loading = true
  try {
    const [wlRes, cartRes, enrRes] = await Promise.allSettled([
      fetchWishlist({ page: 1, pageSize: 100 }),
      fetchCart(),
      fetchMyEnrollments(),
    ])
    if (authState.user?.maNguoiDung !== userId) return

    if (wlRes.status === 'fulfilled' && wlRes.value) {
      const ids = new Set((wlRes.value.items || []).map((i) => Number(i.maKhoaHoc)))
      commerceState.wishlistIds = ids
      commerceState.wishlistCount = Number(wlRes.value.total ?? ids.size)
    }
    if (cartRes.status === 'fulfilled' && cartRes.value) {
      const ids = new Set((cartRes.value.items || []).map((i) => Number(i.maKhoaHoc)))
      commerceState.cartIds = ids
      commerceState.cartCount = Number(cartRes.value.tongSoLuong ?? ids.size)
      commerceState.cartValidCount = Number(cartRes.value.soLuongHopLe ?? ids.size)
    }
    if (enrRes.status === 'fulfilled' && Array.isArray(enrRes.value)) {
      commerceState.enrolledIds = new Set(
        enrRes.value.map((e) => Number(e.course?.id ?? e.maKhoaHoc)).filter((n) => !Number.isNaN(n)),
      )
    }
    commerceState.loadedForUserId = userId
  } finally {
    commerceState.loading = false
  }
}

export function isCourseWishlisted(courseId) {
  return commerceState.wishlistIds.has(Number(courseId))
}

export function isCourseInCart(courseId) {
  return commerceState.cartIds.has(Number(courseId))
}

export function isCourseEnrolled(courseId) {
  return commerceState.enrolledIds.has(Number(courseId))
}

export async function toggleWishlistCourse(courseId) {
  const id = Number(courseId)
  const wasWishlisted = commerceState.wishlistIds.has(id)
  const prevSet = new Set(commerceState.wishlistIds)
  const prevCount = commerceState.wishlistCount

  // Optimistic update with strict rollback on failure
  const nextSet = new Set(prevSet)
  if (wasWishlisted) {
    nextSet.delete(id)
    commerceState.wishlistCount = Math.max(0, prevCount - 1)
  } else {
    nextSet.add(id)
    commerceState.wishlistCount = prevCount + 1
  }
  commerceState.wishlistIds = nextSet

  try {
    const res = wasWishlisted ? await removeFromWishlist(id) : await addToWishlist(id)
    commerceState.wishlistCount = Number(res.tongSoYeuThich ?? commerceState.wishlistCount)
    if (res.trongYeuThich) {
      const s = new Set(commerceState.wishlistIds)
      s.add(id)
      commerceState.wishlistIds = s
      showCommerceToast('Đã thêm khóa học vào danh sách yêu thích.', 'success')
    } else {
      const s = new Set(commerceState.wishlistIds)
      s.delete(id)
      commerceState.wishlistIds = s
      showCommerceToast('Đã xóa khóa học khỏi danh sách yêu thích.', 'info')
    }
    return res
  } catch (error) {
    // Rollback on failure
    commerceState.wishlistIds = prevSet
    commerceState.wishlistCount = prevCount
    throw error
  }
}

export async function addCourseToCartSynced(courseId) {
  const id = Number(courseId)
  const cart = await addToCart(id)
  const ids = new Set((cart.items || []).map((i) => Number(i.maKhoaHoc)))
  commerceState.cartIds = ids
  commerceState.cartCount = Number(cart.tongSoLuong ?? ids.size)
  commerceState.cartValidCount = Number(cart.soLuongHopLe ?? ids.size)
  showCommerceToast('Đã thêm khóa học vào giỏ hàng.', 'success')
  return cart
}

export async function removeCourseFromCartSynced(courseId) {
  const id = Number(courseId)
  const cart = await removeFromCart(id)
  const ids = new Set((cart.items || []).map((i) => Number(i.maKhoaHoc)))
  commerceState.cartIds = ids
  commerceState.cartCount = Number(cart.tongSoLuong ?? ids.size)
  commerceState.cartValidCount = Number(cart.soLuongHopLe ?? ids.size)
  return cart
}

export async function moveWishlistCourseToCartSynced(courseId) {
  const id = Number(courseId)
  const res = await moveWishlistToCart(id)
  const nextWl = new Set(commerceState.wishlistIds)
  nextWl.delete(id)
  commerceState.wishlistIds = nextWl
  commerceState.wishlistCount = Number(res.tongSoYeuThich ?? nextWl.size)

  const nextCart = new Set(commerceState.cartIds)
  nextCart.add(id)
  commerceState.cartIds = nextCart
  commerceState.cartCount = Number(res.tongSoGioHang ?? nextCart.size)
  showCommerceToast('Đã chuyển khóa học vào giỏ hàng.', 'success')
  return res
}

// Clear commerce state automatically when user logs out or switches account
watch(
  () => [authState.accessToken, authState.user?.maNguoiDung],
  ([token, userId], [prevToken, prevUserId]) => {
    if (!token || !userId || (prevUserId && userId !== prevUserId) || (prevToken && token !== prevToken)) {
      resetCommerceState()
    }
    if (token && userId && getRoleName() === 'USER') {
      syncLearnerCommerceState({ force: true })
    }
  },
)
