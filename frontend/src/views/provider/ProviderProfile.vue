<script setup>
import { onBeforeUnmount, reactive, ref } from 'vue'
import { Save, Upload } from 'lucide-vue-next'
import { getProviderProfile, saveProviderProfile } from '@/service/providerService'
import ToastMessage from '@/components/reviewer/ToastMessage.vue'

const profile = getProviderProfile()
const form = reactive({ ...profile })
const originalEmail = profile.email
const generatedObjectUrls = new Set()
const errorMessage = ref('')
const toastMessage = ref('')
const savedAvatarUrl = ref(profile.avatarUrl)

function setAvatar(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const url = URL.createObjectURL(file)
  generatedObjectUrls.add(url)
  form.avatarUrl = url
}

function save() {
  try {
    saveProviderProfile(form)
    savedAvatarUrl.value = form.avatarUrl
    errorMessage.value = ''
    toastMessage.value = 'Đã cập nhật hồ sơ minh họa trong phiên.'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Không thể lưu hồ sơ.'
  }
}

onBeforeUnmount(() => {
  for (const url of generatedObjectUrls) {
    if (url !== savedAvatarUrl.value) URL.revokeObjectURL(url)
  }
})
</script>

<template>
  <div class="mx-auto max-w-4xl space-y-5">
    <section>
      <p class="text-sm text-muted">Tài khoản</p>
      <h2 class="mt-1 text-2xl font-bold tracking-tight text-navy">Hồ sơ cá nhân</h2>
      <p class="mt-2 text-sm text-muted">Dữ liệu hồ sơ là bản minh họa, chỉ lưu trong phiên làm việc.</p>
    </section>

    <form class="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6" @submit.prevent="save">
      <div class="flex flex-wrap items-center gap-4 border-b border-slate-100 pb-5">
        <img v-if="form.avatarUrl" :src="form.avatarUrl" alt="Ảnh đại diện Provider" class="size-16 rounded-full object-cover">
        <span v-else class="flex size-16 items-center justify-center rounded-full bg-primary/10 text-lg font-bold text-primary">{{ form.fullName.split(' ').slice(-1)[0]?.[0] || 'P' }}</span>
        <label class="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-navy hover:bg-background"><Upload :size="14" aria-hidden="true" /> Chọn avatar
          <input type="file" accept="image/*" class="sr-only" @change="setAvatar">
        </label>
        <span class="text-xs text-muted">Ảnh chỉ có hiệu lực trong phiên này.</span>
      </div>
      <div class="mt-5 grid gap-4 sm:grid-cols-2">
        <label class="text-sm font-semibold text-navy">Họ tên *
          <input v-model="form.fullName" required class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
        </label>
        <label class="text-sm font-semibold text-navy">Email
          <input :value="originalEmail" type="email" disabled class="mt-1.5 w-full rounded-xl border border-slate-200 bg-background px-3 py-2.5 text-sm font-normal text-muted" aria-describedby="email-note">
          <span id="email-note" class="mt-1 block text-xs font-normal text-muted">Email không thể đổi trước khi có xác minh từ Backend.</span>
        </label>
        <label class="text-sm font-semibold text-navy">Số điện thoại
          <input v-model="form.phone" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
        </label>
        <label class="text-sm font-semibold text-navy">Đơn vị / tổ chức
          <input v-model="form.organization" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15">
        </label>
        <label class="text-sm font-semibold text-navy sm:col-span-2">Chuyên môn
          <textarea v-model="form.expertise" rows="2" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"></textarea>
        </label>
        <label class="text-sm font-semibold text-navy sm:col-span-2">Kinh nghiệm
          <textarea v-model="form.experience" rows="3" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"></textarea>
        </label>
        <label class="text-sm font-semibold text-navy sm:col-span-2">Giới thiệu bản thân
          <textarea v-model="form.introduction" rows="4" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"></textarea>
        </label>
      </div>
      <p class="mt-4 rounded-xl border border-slate-200 bg-background p-3 text-xs leading-5 text-muted">Đổi mật khẩu chưa khả dụng vì dự án chưa có API xác thực. Không nhập hoặc lưu mật khẩu tại giao diện mock.</p>
      <p v-if="errorMessage" class="mt-4 rounded-lg border border-primary/20 bg-primary/5 p-3 text-sm text-primary" role="alert">{{ errorMessage }}</p>
      <button type="submit" class="mt-5 inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90"><Save :size="15" aria-hidden="true" /> Lưu hồ sơ</button>
    </form>
    <ToastMessage :message="toastMessage" @close="toastMessage = ''" />
  </div>
</template>
