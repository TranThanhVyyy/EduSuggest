<script setup>
import { computed, reactive, ref } from 'vue'
import { Eye, EyeOff, GraduationCap, KeyRound } from 'lucide-vue-next'
import { useRoute } from 'vue-router'

const route = useRoute()
const isRegister = computed(() => route.name === 'register')
const passwordVisible = ref(false)
const confirmVisible = ref(false)
const submitting = ref(false)
const attempted = ref(false)
const errors = reactive({})
const message = ref('')
const form = reactive({
  fullName: '',
  email: '',
  phone: '',
  password: '',
  confirmPassword: '',
  agree: false,
  remember: false,
})

function validate() {
  Object.keys(errors).forEach((key) => delete errors[key])
  if (isRegister.value && !form.fullName.trim()) errors.fullName = 'Nhập họ và tên.'
  if (!form.email.trim()) errors.email = 'Nhập email.'
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) errors.email = 'Email chưa đúng định dạng.'
  if (isRegister.value && form.phone && !/^[+()\d\s.-]{7,20}$/.test(form.phone.trim())) errors.phone = 'Số điện thoại chưa đúng định dạng.'
  if (!form.password) errors.password = 'Nhập mật khẩu.'
  else if (isRegister.value && form.password.length < 8) errors.password = 'Mật khẩu cần ít nhất 8 ký tự.'
  if (isRegister.value && form.password !== form.confirmPassword) errors.confirmPassword = 'Mật khẩu xác nhận chưa khớp.'
  if (isRegister.value && !form.agree) errors.agree = 'Bạn cần đồng ý với điều khoản.'
  return Object.keys(errors).length === 0
}

async function submit() {
  attempted.value = true
  message.value = ''
  if (!validate()) return
  submitting.value = true
  await new Promise((resolve) => setTimeout(resolve, 300))
  submitting.value = false
  message.value = isRegister.value
    ? 'API đăng ký chưa được tích hợp. Chưa tạo tài khoản hoặc cấp vai trò User.'
    : 'API xác thực chưa được tích hợp. Chưa đăng nhập và không tạo phiên.'
}
</script>

<template>
  <div class="mx-auto grid max-w-5xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm lg:grid-cols-[0.85fr_1.15fr]">
    <aside class="hidden flex-col justify-between bg-navy p-8 text-white lg:flex">
      <RouterLink :to="{ name: 'home' }" class="inline-flex items-center gap-3">
        <span class="flex size-11 items-center justify-center rounded-xl bg-primary"><GraduationCap :size="23" aria-hidden="true" /></span>
        <span class="text-xl font-bold">EduSuggest</span>
      </RouterLink>
      <div>
        <p class="text-sm font-semibold text-accent">Học tập theo mục tiêu của bạn</p>
        <h1 class="mt-3 text-3xl font-bold leading-tight">{{ isRegister ? 'Bắt đầu hành trình học tập.' : 'Chào mừng bạn quay lại.' }}</h1>
        <p class="mt-4 text-sm leading-6 text-white/65">Đây là giao diện minh họa. Xác thực sẽ chỉ hoạt động sau khi kết nối Backend.</p>
      </div>
      <RouterLink :to="{ name: 'home' }" class="text-sm text-white/70 hover:text-white">← Quay về trang chủ</RouterLink>
    </aside>

    <section class="p-5 sm:p-8 lg:p-10">
      <RouterLink :to="{ name: 'home' }" class="inline-flex items-center gap-2 text-sm font-bold text-navy lg:hidden"><GraduationCap :size="20" class="text-primary" aria-hidden="true" /> EduSuggest</RouterLink>
      <div class="mt-5 flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary lg:mt-0"><KeyRound :size="20" aria-hidden="true" /></div>
      <p class="mt-4 text-xs font-semibold uppercase tracking-wide text-primary">Tài khoản người học</p>
      <h2 class="mt-1 text-2xl font-bold text-navy">{{ isRegister ? 'Tạo tài khoản User' : 'Đăng nhập' }}</h2>
      <p class="mt-2 text-sm leading-6 text-muted">{{ isRegister ? 'Tài khoản công khai mặc định là User. Không có lựa chọn Reviewer, Admin hoặc Provider.' : 'Đăng nhập bằng tài khoản EduSuggest của bạn.' }}</p>

      <form class="mt-6 space-y-4" novalidate @submit.prevent="submit">
        <label v-if="isRegister" class="block text-sm font-semibold text-navy">Họ và tên *
          <input v-model="form.fullName" autocomplete="name" class="mt-1.5 w-full rounded-xl border px-3 py-2.5 text-sm font-normal outline-none focus:ring-2 focus:ring-primary/15" :class="errors.fullName ? 'border-primary' : 'border-slate-200 focus:border-primary'" :aria-invalid="Boolean(errors.fullName)" aria-describedby="auth-name-error">
          <span v-if="errors.fullName" id="auth-name-error" class="mt-1 block text-xs text-primary" role="alert">{{ errors.fullName }}</span>
        </label>
        <label class="block text-sm font-semibold text-navy">Email *
          <input v-model="form.email" type="email" autocomplete="email" class="mt-1.5 w-full rounded-xl border px-3 py-2.5 text-sm font-normal outline-none focus:ring-2 focus:ring-primary/15" :class="errors.email ? 'border-primary' : 'border-slate-200 focus:border-primary'" :aria-invalid="Boolean(errors.email)" aria-describedby="auth-email-error">
          <span v-if="errors.email" id="auth-email-error" class="mt-1 block text-xs text-primary" role="alert">{{ errors.email }}</span>
        </label>
        <label v-if="isRegister" class="block text-sm font-semibold text-navy">Số điện thoại
          <input v-model="form.phone" type="tel" autocomplete="tel" class="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-normal outline-none focus:border-primary focus:ring-2 focus:ring-primary/15" :aria-invalid="Boolean(errors.phone)">
          <span v-if="errors.phone" class="mt-1 block text-xs text-primary" role="alert">{{ errors.phone }}</span>
        </label>
        <label class="block text-sm font-semibold text-navy">Mật khẩu *
          <span class="relative mt-1.5 block">
            <input v-model="form.password" :type="passwordVisible ? 'text' : 'password'" :autocomplete="isRegister ? 'new-password' : 'current-password'" class="w-full rounded-xl border px-3 py-2.5 pr-11 text-sm font-normal outline-none focus:ring-2 focus:ring-primary/15" :class="errors.password ? 'border-primary' : 'border-slate-200 focus:border-primary'" :aria-invalid="Boolean(errors.password)">
            <button type="button" class="absolute right-2 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center rounded-lg text-muted hover:bg-background" :aria-label="passwordVisible ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'" @click="passwordVisible = !passwordVisible">
              <EyeOff v-if="passwordVisible" :size="16" aria-hidden="true" /><Eye v-else :size="16" aria-hidden="true" />
            </button>
          </span>
          <span v-if="errors.password" class="mt-1 block text-xs text-primary" role="alert">{{ errors.password }}</span>
          <span v-else-if="isRegister" class="mt-1 block text-xs font-normal text-muted">Tối thiểu 8 ký tự.</span>
        </label>
        <label v-if="isRegister" class="block text-sm font-semibold text-navy">Xác nhận mật khẩu *
          <span class="relative mt-1.5 block">
            <input v-model="form.confirmPassword" :type="confirmVisible ? 'text' : 'password'" autocomplete="new-password" class="w-full rounded-xl border px-3 py-2.5 pr-11 text-sm font-normal outline-none focus:ring-2 focus:ring-primary/15" :class="errors.confirmPassword ? 'border-primary' : 'border-slate-200 focus:border-primary'" :aria-invalid="Boolean(errors.confirmPassword)">
            <button type="button" class="absolute right-2 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center rounded-lg text-muted hover:bg-background" :aria-label="confirmVisible ? 'Ẩn mật khẩu xác nhận' : 'Hiện mật khẩu xác nhận'" @click="confirmVisible = !confirmVisible">
              <EyeOff v-if="confirmVisible" :size="16" aria-hidden="true" /><Eye v-else :size="16" aria-hidden="true" />
            </button>
          </span>
          <span v-if="errors.confirmPassword" class="mt-1 block text-xs text-primary" role="alert">{{ errors.confirmPassword }}</span>
        </label>
        <label v-if="!isRegister" class="flex items-center gap-2 text-sm text-muted">
          <input v-model="form.remember" type="checkbox" class="size-4 accent-primary"> Ghi nhớ đăng nhập (chưa khả dụng)
        </label>
        <label v-if="isRegister" class="flex items-start gap-2 text-sm text-muted">
          <input v-model="form.agree" type="checkbox" class="mt-0.5 size-4 accent-primary" :aria-invalid="Boolean(errors.agree)">
          <span>Đồng ý với điều khoản sử dụng và chính sách quyền riêng tư.</span>
        </label>
        <p v-if="errors.agree" class="text-xs text-primary" role="alert">{{ errors.agree }}</p>
        <p v-if="attempted && message" class="rounded-xl border border-primary/15 bg-primary/5 p-3 text-sm leading-5 text-navy" role="alert">{{ message }}</p>
        <button type="submit" class="w-full rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-60" :disabled="submitting">{{ submitting ? 'Đang xử lý...' : (isRegister ? 'Tạo tài khoản' : 'Đăng nhập') }}</button>
      </form>

      <p class="mt-5 text-center text-sm text-muted">
        {{ isRegister ? 'Đã có tài khoản?' : 'Chưa có tài khoản?' }}
        <RouterLink :to="{ name: isRegister ? 'login' : 'register' }" class="font-semibold text-primary hover:underline">{{ isRegister ? 'Đăng nhập' : 'Đăng ký' }}</RouterLink>
      </p>
      <p class="mt-5 rounded-xl border border-slate-200 bg-background p-3 text-xs leading-5 text-muted">Không gửi mật khẩu đến bất kỳ nơi nào trong bản demo này; biểu mẫu không tạo tài khoản hoặc phiên đăng nhập.</p>
    </section>
  </div>
</template>
