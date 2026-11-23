<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Save } from 'lucide-vue-next'
import UiButton from '@/components/ui/UiButton.vue'
import { authState } from '@/service/authState'
import api from '@/service/api'

const form = reactive({ chuyenMon: '', tieuSu: '' })
const loading = ref(true)
const saving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const user = computed(() => authState.user)

async function loadProfile() {
  loading.value = true
  errorMessage.value = ''
  try {
    const { data } = await api.get('/expert/profile')
    Object.assign(form, { chuyenMon: data.chuyenMon || '', tieuSu: data.tieuSu || '' })
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể tải hồ sơ chuyên gia.'
  } finally { loading.value = false }
}

async function saveProfile() {
  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const { data } = await api.put('/expert/profile', { chuyenMon: form.chuyenMon.trim() || null, tieuSu: form.tieuSu.trim() || null })
    Object.assign(form, { chuyenMon: data.chuyenMon || '', tieuSu: data.tieuSu || '' })
    successMessage.value = 'Hồ sơ chuyên gia đã được cập nhật.'
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Không thể lưu hồ sơ. Hãy thử lại.'
  } finally { saving.value = false }
}
onMounted(loadProfile)
</script>

<template>
  <main class="max-w-3xl space-y-6">
    <header class="border-b border-border pb-5"><p class="ui-eyebrow">Tài khoản</p><h1 class="ui-page-title mt-2">Hồ sơ chuyên gia</h1><p class="mt-2 text-sm text-muted">Thông tin tài khoản được tải từ phiên đăng nhập; hồ sơ chuyên môn được lưu qua API chuyên gia.</p></header>
    <p v-if="loading" class="py-4 text-sm text-muted" role="status">Đang tải hồ sơ…</p>
    <form v-else class="max-w-2xl space-y-5" @submit.prevent="saveProfile">
      <dl class="grid gap-5 sm:grid-cols-2"><div><dt class="text-sm text-muted">Họ tên</dt><dd class="mt-1 font-medium text-navy">{{ user?.hoTen || '—' }}</dd></div><div><dt class="text-sm text-muted">Email</dt><dd class="mt-1 break-all font-medium text-navy">{{ user?.email || '—' }}</dd></div></dl>
      <label class="block text-sm font-medium text-navy">Chuyên môn<input v-model.trim="form.chuyenMon" class="ui-input mt-2" maxlength="255"></label>
      <label class="block text-sm font-medium text-navy">Tiểu sử<textarea v-model.trim="form.tieuSu" class="ui-input mt-2 min-h-32 resize-y" rows="5"></textarea></label>
      <p v-if="errorMessage" class="border-l-2 border-danger py-1 pl-3 text-sm text-danger" role="alert">{{ errorMessage }}</p><p v-if="successMessage" class="border-l-2 border-secondary py-1 pl-3 text-sm text-secondary" role="status">{{ successMessage }}</p>
      <UiButton type="submit" :loading="saving"><Save :size="15" aria-hidden="true" /> Lưu hồ sơ</UiButton>
    </form>
  </main>
</template>
