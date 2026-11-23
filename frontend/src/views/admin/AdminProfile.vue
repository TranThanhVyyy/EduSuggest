<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Save } from 'lucide-vue-next'
import UiButton from '@/components/ui/UiButton.vue'
import { authState, setCurrentUser } from '@/service/authState'
import { loadCurrentUser } from '@/service/authService'
import api from '@/service/api'

const form = reactive({ fullName: '', phone: '' })
const loading = ref(true)
const saving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const username = computed(() => authState.user?.tenTaiKhoan || '')
const email = computed(() => authState.user?.email || '')

async function loadProfile() {
  loading.value = true
  errorMessage.value = ''
  try {
    const user = await loadCurrentUser()
    if (user) Object.assign(form, { fullName: user.hoTen || '', phone: user.soDienThoai || '' })
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể tải hồ sơ. Hãy thử tải lại trang.'
  } finally {
    loading.value = false
  }
}

async function saveProfile() {
  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const { data } = await api.put('/users/me', { hoTen: form.fullName.trim(), soDienThoai: form.phone.trim() || null })
    setCurrentUser(data)
    Object.assign(form, { fullName: data.hoTen || '', phone: data.soDienThoai || '' })
    successMessage.value = 'Hồ sơ đã được cập nhật.'
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể cập nhật hồ sơ. Hãy kiểm tra kết nối rồi thử lại.'
  } finally {
    saving.value = false
  }
}

onMounted(loadProfile)
</script>

<template>
  <main class="max-w-3xl space-y-6">
    <header class="border-b border-border pb-5"><p class="ui-eyebrow">Tài khoản</p><h1 class="ui-page-title mt-2">Hồ sơ quản trị</h1><p class="mt-2 text-sm text-muted">Thông tin được tải và lưu qua tài khoản hiện tại.</p></header>
    <p v-if="loading" class="py-4 text-sm text-muted" role="status">Đang tải hồ sơ…</p>
    <form v-else class="max-w-2xl space-y-5" @submit.prevent="saveProfile">
      <div class="grid gap-5 sm:grid-cols-2">
        <label class="text-sm font-medium text-navy">Họ và tên<input v-model.trim="form.fullName" class="ui-input mt-2" autocomplete="name" maxlength="255" required></label>
        <label class="text-sm font-medium text-navy">Tên tài khoản<input :value="username" class="ui-input mt-2" disabled></label>
        <label class="text-sm font-medium text-navy">Email<input :value="email" class="ui-input mt-2" disabled type="email"></label>
        <label class="text-sm font-medium text-navy">Số điện thoại<input v-model.trim="form.phone" class="ui-input mt-2" autocomplete="tel" type="tel"></label>
      </div>
      <p v-if="errorMessage" class="border-l-2 border-danger py-1 pl-3 text-sm text-danger" role="alert">{{ errorMessage }}</p>
      <p v-if="successMessage" class="border-l-2 border-secondary py-1 pl-3 text-sm text-secondary" role="status">{{ successMessage }}</p>
      <UiButton type="submit" :loading="saving"><Save :size="15" aria-hidden="true" /> Lưu thay đổi</UiButton>
    </form>
  </main>
</template>
