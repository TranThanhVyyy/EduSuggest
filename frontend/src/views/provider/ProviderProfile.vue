<script setup>
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { Save, Upload } from 'lucide-vue-next'
import { authState } from '@/service/authState'
import { loadProviderProfile, providerErrorMessage, updateProviderProfile } from '@/service/providerApiService'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'

const form = reactive({
  fullName: authState.user?.hoTen || '',
  email: authState.user?.email || '',
  expertise: '',
  introduction: '',
  avatarUrl: '',
})
const errorMessage = ref('')
const toastMessage = ref('')
const isLoading = ref(true)
const isSaving = ref(false)
const generatedObjectUrls = new Set()

onMounted(async () => {
  try {
    const profile = await loadProviderProfile()
    form.expertise = profile.chuyenMon || ''
    form.introduction = profile.tieuSu || ''
  } catch (error) {
    errorMessage.value = providerErrorMessage(error, 'Không thể tải hồ sơ Provider từ Backend.')
  } finally {
    isLoading.value = false
  }
})

function setAvatar(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const url = URL.createObjectURL(file)
  generatedObjectUrls.add(url)
  form.avatarUrl = url
}

async function save() {
  if (isSaving.value) return
  isSaving.value = true
  try {
    const saved = await updateProviderProfile(form)
    form.expertise = saved.chuyenMon || ''
    form.introduction = saved.tieuSu || ''
    errorMessage.value = ''
    toastMessage.value = 'Đã lưu hồ sơ Provider trên Backend.'
  } catch (error) {
    errorMessage.value = providerErrorMessage(error, 'Không thể lưu hồ sơ Provider.')
  } finally {
    isSaving.value = false
  }
}

onBeforeUnmount(() => generatedObjectUrls.forEach((url) => URL.revokeObjectURL(url)))
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-5">
    <section>
      <p class="text-sm text-muted">Tài khoản</p>
      <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">Hồ sơ cá nhân</h2>
      <p class="mt-2 text-sm text-muted">Chuyên môn và giới thiệu được đồng bộ với hồ sơ Provider trên Backend.</p>
    </section>

    <p v-if="isLoading" class="rounded-xl border border-slate-200 bg-white p-4 text-sm text-muted" role="status">Đang tải hồ sơ Provider…</p>
    <form v-else class="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6" @submit.prevent="save">
      <div class="flex flex-wrap items-center gap-4 border-b border-slate-100 pb-5">
        <img v-if="form.avatarUrl" :src="form.avatarUrl" alt="Ảnh đại diện Provider" class="size-16 rounded-full object-cover">
        <span v-else class="flex size-16 items-center justify-center rounded-full bg-primary/10 text-lg font-bold text-primary">{{ form.fullName.split(' ').slice(-1)[0]?.[0] || 'P' }}</span>
        <label class="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-navy hover:bg-background"><Upload :size="14" aria-hidden="true" /> Chọn avatar
          <input type="file" accept="image/*" class="sr-only" @change="setAvatar">
        </label>
        <span class="text-xs text-muted">Avatar chỉ xem trong phiên; Backend chưa có API lưu ảnh.</span>
      </div>
      <div class="mt-5 grid gap-4 sm:grid-cols-2">
        <label class="text-sm font-semibold text-navy">Họ tên
          <input :value="form.fullName" disabled class="mt-1.5 w-full rounded-xl border border-slate-200 bg-background px-3 py-2.5 text-sm font-normal text-muted">
        </label>
        <label class="text-sm font-semibold text-navy">Email
          <input :value="form.email" disabled class="mt-1.5 w-full rounded-xl border border-slate-200 bg-background px-3 py-2.5 text-sm font-normal text-muted">
        </label>
        <label class="text-sm font-semibold text-navy sm:col-span-2">Chuyên môn
          <textarea v-model="form.expertise" rows="2" maxlength="255" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"></textarea>
        </label>
        <label class="text-sm font-semibold text-navy sm:col-span-2">Giới thiệu bản thân
          <textarea v-model="form.introduction" rows="4" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"></textarea>
        </label>
      </div>
      <p class="mt-4 rounded-xl border border-slate-200 bg-background p-3 text-xs leading-5 text-muted">API hiện chỉ lưu chuyên môn và tiểu sử. Tên, email, tổ chức, kinh nghiệm và avatar không được gửi hoặc lưu cục bộ như dữ liệu nghiệp vụ.</p>
      <p v-if="errorMessage" class="mt-4 rounded-lg border border-primary/20 bg-primary/5 p-3 text-sm text-primary" role="alert">{{ errorMessage }}</p>
      <button type="submit" :disabled="isSaving" class="mt-5 inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"><Save :size="15" aria-hidden="true" /> {{ isSaving ? 'Đang lưu…' : 'Lưu hồ sơ' }}</button>
    </form>
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
