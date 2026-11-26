<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Save } from 'lucide-vue-next'
import UiButton from '@/components/ui/UiButton.vue'
import UiSkeleton from '@/components/ui/UiSkeleton.vue'
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
    const { data } = await api.put('/users/me', {
      hoTen: form.fullName.trim(),
      soDienThoai: form.phone.trim() || null,
    })
    setCurrentUser(data)
    Object.assign(form, { fullName: data.hoTen || '', phone: data.soDienThoai || '' })
    successMessage.value = 'Hồ sơ quản trị đã được cập nhật.'
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể cập nhật hồ sơ. Hãy kiểm tra kết nối rồi thử lại.'
  } finally {
    saving.value = false
  }
}

onMounted(loadProfile)
</script>

<template>
  <div class="max-w-3xl space-y-6">
    <section>
      <p class="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Tài khoản</p>
      <h1 class="mt-1 font-display text-2xl font-bold tracking-tight text-navy">Hồ sơ quản trị</h1>
      <p class="mt-1.5 text-sm text-slate-600">
        Quản lý thông tin liên hệ của tài khoản quản trị hệ thống.
      </p>
    </section>

    <section class="rounded-2xl border border-border bg-surface p-6 shadow-xs">
      <div v-if="loading" class="space-y-4">
        <UiSkeleton variant="rect" height="60px" rounded="0.75rem" />
        <UiSkeleton variant="rect" height="120px" rounded="0.75rem" />
      </div>

      <form v-else class="space-y-5" @submit.prevent="saveProfile">
        <dl class="grid gap-4 rounded-xl bg-background/80 p-4 sm:grid-cols-2 text-sm">
          <div>
            <dt class="text-xs font-medium text-slate-500">Tên tài khoản</dt>
            <dd class="mt-1 font-semibold text-navy">{{ username || '—' }}</dd>
          </div>
          <div>
            <dt class="text-xs font-medium text-slate-500">Email</dt>
            <dd class="mt-1 break-all font-semibold text-navy">{{ email || '—' }}</dd>
          </div>
        </dl>

        <div class="grid gap-4 sm:grid-cols-2">
          <div>
            <label for="admin-fullname" class="mb-1.5 block text-xs font-semibold text-navy">
              Họ và tên <span class="text-danger">*</span>
            </label>
            <input
              id="admin-fullname"
              v-model.trim="form.fullName"
              class="ui-input"
              autocomplete="name"
              maxlength="255"
              required
            >
          </div>

          <div>
            <label for="admin-phone" class="mb-1.5 block text-xs font-semibold text-navy">
              Số điện thoại
            </label>
            <input
              id="admin-phone"
              v-model.trim="form.phone"
              class="ui-input"
              autocomplete="tel"
              type="tel"
              placeholder="09xx xxx xxx"
            >
          </div>
        </div>

        <p v-if="errorMessage" class="rounded-xl border border-danger/25 bg-danger/5 px-3.5 py-2.5 text-xs font-medium text-danger" role="alert">
          {{ errorMessage }}
        </p>
        <p v-if="successMessage" class="rounded-xl border border-teal/25 bg-teal/5 px-3.5 py-2.5 text-xs font-medium text-teal-dark" role="status">
          {{ successMessage }}
        </p>

        <div class="flex justify-end border-t border-border/70 pt-4">
          <UiButton type="submit" :loading="saving" class="inline-flex items-center gap-1.5">
            <Save :size="15" aria-hidden="true" />
            <span>Lưu thay đổi</span>
          </UiButton>
        </div>
      </form>
    </section>
  </div>
</template>
