<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { Eye, EyeOff, GraduationCap, KeyRound, LoaderCircle } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import { getRoleLandingRouteName, loginAccount, registerAccount } from '@/service/authService'

const route = useRoute()
const router = useRouter()
const isRegister = computed(() => route.name === 'register')
const passwordVisible = ref(false)
const confirmVisible = ref(false)
const submitting = ref(false)
const attempted = ref(false)
const errors = reactive({})
const message = ref('')
const successMessage = ref(false)
const form = reactive({
  username: '',
  fullName: '',
  email: '',
  phone: '',
  password: '',
  confirmPassword: '',
  agree: false,
})

if (route.query.authError === 'unavailable') {
  attempted.value = true
  message.value = 'Không thể xác minh phiên đăng nhập hiện tại. Vui lòng kiểm tra kết nối và thử lại.'
}

watch(() => route.name, (name, previousName) => {
  const justRegistered = previousName === 'register' && name === 'login' && successMessage.value
  Object.keys(errors).forEach((key) => delete errors[key])
  form.password = ''
  form.confirmPassword = ''
  if (justRegistered) return

  attempted.value = false
  message.value = ''
  successMessage.value = false
  passwordVisible.value = false
  confirmVisible.value = false
})

function validate() {
  Object.keys(errors).forEach((key) => delete errors[key])
  message.value = ''
  successMessage.value = false
  const username = form.username.trim()
  if (!username) errors.username = 'Nhập tên tài khoản.'
  else if (!/^[A-Za-z0-9._-]{3,50}$/.test(username)) {
    errors.username = 'Tên tài khoản gồm các ký tự: chữ không dấu, số, dấu chấm, gạch dưới hoặc gạch ngang.'
  }
  if (isRegister.value && !form.fullName.trim()) errors.fullName = 'Nhập họ và tên.'
  else if (isRegister.value && form.fullName.trim().length > 255) errors.fullName = 'Họ tên tối đa 255 ký tự.'
  if (isRegister.value && !form.email.trim()) errors.email = 'Nhập email.'
  else if (isRegister.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) errors.email = 'Email chưa đúng định dạng.'
  if (isRegister.value && form.phone.length > 20) errors.phone = 'Số điện thoại tối đa 20 ký tự.'
  if (!form.password) errors.password = 'Nhập mật khẩu.'
  else if (isRegister.value && form.password.length < 8) errors.password = 'Mật khẩu cần ít nhất 8 ký tự.'
  else if (form.password.length > 128) errors.password = 'Mật khẩu tối đa 128 ký tự.'
  if (isRegister.value && form.password !== form.confirmPassword) errors.confirmPassword = 'Mật khẩu xác nhận chưa khớp.'
  if (isRegister.value && !form.agree) errors.agree = 'Bạn cần đồng ý với điều khoản.'
  return Object.keys(errors).length === 0
}

function displayApiError(error) {
  const status = error.response?.status
  const detail = error.response?.data?.detail
  if (status === 401) {
    message.value = 'Tên tài khoản hoặc mật khẩu không chính xác.'
    return
  }
  if (status === 409) {
    const conflict = String(detail || '').toLowerCase()
    if (conflict.includes('username')) {
      errors.username = 'Tên tài khoản này đã được sử dụng.'
    } else if (conflict.includes('email')) {
      errors.email = 'Email này đã được đăng ký.'
    } else {
      message.value = 'Tên tài khoản hoặc email đã được sử dụng.'
    }
    return
  }
  if (status === 422 && Array.isArray(detail)) {
    const messages = {
      tenTaiKhoan: 'Tên tài khoản không hợp lệ (3–50 ký tự, chữ không dấu, số, dấu chấm, gạch dưới hoặc gạch ngang).',
      hoTen: 'Họ tên không hợp lệ hoặc vượt quá 255 ký tự.',
      email: 'Email chưa đúng định dạng.',
      soDienThoai: 'Số điện thoại vượt quá 20 ký tự.',
      matKhau: 'Mật khẩu phải có từ 8 ký tự.',
    }
    const fieldNames = {
      tenTaiKhoan: 'username',
      hoTen: 'fullName',
      soDienThoai: 'phone',
      matKhau: 'password',
    }
    let mappedError = false
    for (const issue of detail) {
      const field = issue.loc?.[issue.loc.length - 1]
      if (messages[field]) {
        errors[fieldNames[field] || field] = messages[field]
        mappedError = true
      }
    }
    if (!mappedError) message.value = 'Vui lòng kiểm tra lại thông tin đã nhập.'
    return
  }
  if (status === 503) {
    message.value = 'Dịch vụ đăng ký hiện chưa sẵn sàng. Vui lòng thử lại sau.'
    return
  }
  message.value = 'Không thể kết nối dịch vụ. Vui lòng thử lại.'
}

async function submit() {
  attempted.value = true
  message.value = ''
  successMessage.value = false
  if (!validate()) return
  submitting.value = true
  try {
    if (isRegister.value) {
      const createdUser = await registerAccount(form)
      form.username = createdUser.tenTaiKhoan
      message.value = 'Tạo tài khoản thành công. Vui lòng đăng nhập.'
      successMessage.value = true
      form.password = ''
      form.confirmPassword = ''
      await router.replace({ name: 'login' })
      return
    }

    const user = await loginAccount(form.username.trim(), form.password)
    const redirect = route.query.redirect
    if (typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//')) {
      await router.replace(redirect)
    } else {
      await router.replace({ name: getRoleLandingRouteName(user) })
    }
  } catch (error) {
    displayApiError(error)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main v-if="!isRegister" class="auth-screen auth-screen--login">
    <header class="auth-topbar">
      <RouterLink :to="{ name: 'home' }" class="auth-brand" aria-label="EduSuggest">
        <span class="auth-brand__mark"><GraduationCap :size="21" aria-hidden="true" /></span>
        <span>EduSuggest</span>
      </RouterLink>
      <div class="auth-topbar__aside">
        <span class="hidden text-sm text-muted sm:inline">Bạn mới với EduSuggest?</span>
        <RouterLink :to="{ name: 'register' }" class="auth-text-link">Tạo tài khoản <span aria-hidden="true"></span></RouterLink>
      </div>
    </header>

    <div class="login-layout">
      <section class="login-editorial" aria-labelledby="login-title">
        <p class="auth-eyebrow"><span></span> Học tập theo mục tiêu</p>
        <h1 id="login-title">Mỗi bước học<br>mở ra <em>một hướng mới.</em></h1>
        <p class="login-editorial__copy">Khám phá khóa học phù hợp, giữ nhịp tiến bộ và xây dựng con đường học tập của riêng bạn.</p>
        <div class="login-editorial__note">
          <span class="login-editorial__index">01</span>
          <span>Tri thức tốt bắt đầu từ một lựa chọn đúng.</span>
        </div>
      </section>

      <section class="auth-form-panel login-form-panel" aria-labelledby="auth-title">
        <div class="auth-form-heading">
          <p class="auth-eyebrow">Không gian học tập của bạn</p>
          <h2 id="auth-title">Chào mừng trở lại</h2>
          <p>Đăng nhập bằng tên tài khoản EduSuggest.</p>
        </div>

        <form class="auth-form" novalidate @submit.prevent="submit">
          <UiField id="auth-username" label="Tên tài khoản" required :error="errors.username">
            <template #default="{ describedBy }">
              <input id="auth-username" v-model="form.username" required minlength="3" maxlength="50" autocomplete="username" placeholder="Ví dụ: nguyenvana" class="ui-input" :aria-invalid="Boolean(errors.username)" :aria-describedby="describedBy">
            </template>
          </UiField>
          <UiField id="auth-password" label="Mật khẩu" required :error="errors.password">
            <template #default="{ describedBy }">
              <span class="auth-password-control">
                <input id="auth-password" v-model="form.password" required minlength="1" maxlength="128" :type="passwordVisible ? 'text' : 'password'" autocomplete="current-password" placeholder="Nhập mật khẩu" class="ui-input" :aria-invalid="Boolean(errors.password)" :aria-describedby="describedBy">
                <button type="button" class="auth-password-toggle" :aria-label="passwordVisible ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'" @click="passwordVisible = !passwordVisible">
                  <EyeOff v-if="passwordVisible" :size="17" aria-hidden="true" /><Eye v-else :size="17" aria-hidden="true" />
                </button>
              </span>
            </template>
          </UiField>
          <p v-if="attempted && message" class="auth-feedback" :class="successMessage ? 'auth-feedback--success' : 'auth-feedback--error'" :role="successMessage ? 'status' : 'alert'">{{ message }}</p>
          <UiButton type="submit" class="auth-submit" :loading="submitting">
            <LoaderCircle v-if="submitting" :size="17" class="animate-spin" aria-hidden="true" />
            {{ submitting ? 'Đang xác thực...' : 'Đăng nhập' }}
          </UiButton>
        </form>
       
      </section>
    </div>
    <footer class="auth-footer"><span>EDUSUGGEST</span><span>Học tập có định hướng, tiến bộ có ý nghĩa.</span></footer>
  </main>

  <main v-else class="auth-screen auth-screen--register">
    <header class="auth-topbar">
      <RouterLink :to="{ name: 'home' }" class="auth-brand" aria-label="EduSuggest">
        <span class="auth-brand__mark"><GraduationCap :size="21" aria-hidden="true" /></span>
        <span>EduSuggest</span>
      </RouterLink>
      <div class="auth-topbar__aside">
        <span class="hidden text-sm text-muted sm:inline">Đã có tài khoản?</span>
        <RouterLink :to="{ name: 'login' }" class="auth-text-link">Đăng nhập <span aria-hidden="true"></span></RouterLink>
      </div>
    </header>

    <div class="register-layout">
      <aside class="register-editorial" aria-labelledby="register-title">
        <p class="auth-eyebrow"><span></span> Bắt đầu từ hôm nay</p>
        <h1 id="register-title">Một tài khoản.<br><em>Nhiều khả năng.</em></h1>
        <p class="register-editorial__copy">Tạo không gian học tập của bạn và tìm những nội dung phù hợp với mục tiêu phía trước.</p>
        <ol class="register-steps" aria-label="Các bước bắt đầu">
          <li><span>01</span><span>Tạo hồ sơ học tập</span></li>
          <li><span>02</span><span>Khám phá nội dung</span></li>
          <li><span>03</span><span>Tiến bộ theo nhịp riêng</span></li>
        </ol>
      </aside>

      <section class="auth-form-panel register-form-panel" aria-labelledby="auth-title">
        <div class="auth-form-heading">
          <p class="auth-eyebrow">Đăng ký miễn phí</p>
          <h2 id="auth-title">Tạo tài khoản</h2>
          <p>Thông tin của bạn sẽ được dùng để thiết lập hồ sơ người học.</p>
        </div>

        <form class="auth-form register-form" novalidate @submit.prevent="submit">
          <UiField id="auth-name" label="Họ và tên" required :error="errors.fullName">
            <template #default="{ describedBy }">
              <input id="auth-name" v-model="form.fullName" required maxlength="255" autocomplete="name" placeholder="Nguyễn Văn An" class="ui-input" :aria-invalid="Boolean(errors.fullName)" :aria-describedby="describedBy">
            </template>
          </UiField>
          <UiField id="auth-username" label="Tên tài khoản" required :error="errors.username" hint="">
            <template #default="{ describedBy }">
              <input id="auth-username" v-model="form.username" required minlength="3" maxlength="50" autocomplete="username" placeholder="nguyenvana" class="ui-input" :aria-invalid="Boolean(errors.username)" :aria-describedby="describedBy">
            </template>
          </UiField>
          <UiField id="auth-email" label="Email" required :error="errors.email" hint="">
            <template #default="{ describedBy }">
              <input id="auth-email" v-model="form.email" required type="email" autocomplete="email" placeholder="ban@example.com" class="ui-input" :aria-invalid="Boolean(errors.email)" :aria-describedby="describedBy">
            </template>
          </UiField>
          <UiField id="auth-phone" label="Số điện thoại" :error="errors.phone" hint="">
            <template #default="{ describedBy }">
              <input id="auth-phone" v-model="form.phone" maxlength="20" type="tel" autocomplete="tel" placeholder="090 123 4567" class="ui-input" :aria-invalid="Boolean(errors.phone)" :aria-describedby="describedBy">
            </template>
          </UiField>
          <UiField id="auth-password" label="Mật khẩu" required :error="errors.password" hint="">
            <template #default="{ describedBy }">
              <span class="auth-password-control">
                <input id="auth-password" v-model="form.password" required minlength="8" maxlength="128" :type="passwordVisible ? 'text' : 'password'" autocomplete="new-password" placeholder="Tạo mật khẩu" class="ui-input" :aria-invalid="Boolean(errors.password)" :aria-describedby="describedBy">
                <button type="button" class="auth-password-toggle" :aria-label="passwordVisible ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'" @click="passwordVisible = !passwordVisible">
                  <EyeOff v-if="passwordVisible" :size="17" aria-hidden="true" /><Eye v-else :size="17" aria-hidden="true" />
                </button>
              </span>
            </template>
          </UiField>
          <UiField id="auth-confirm-password" label="Xác nhận mật khẩu" required :error="errors.confirmPassword">
            <template #default="{ describedBy }">
              <span class="auth-password-control">
                <input id="auth-confirm-password" v-model="form.confirmPassword" required :type="confirmVisible ? 'text' : 'password'" autocomplete="new-password" placeholder="Nhập lại mật khẩu" class="ui-input" :aria-invalid="Boolean(errors.confirmPassword)" :aria-describedby="describedBy">
                <button type="button" class="auth-password-toggle" :aria-label="confirmVisible ? 'Ẩn mật khẩu xác nhận' : 'Hiện mật khẩu xác nhận'" @click="confirmVisible = !confirmVisible">
                  <EyeOff v-if="confirmVisible" :size="17" aria-hidden="true" /><Eye v-else :size="17" aria-hidden="true" />
                </button>
              </span>
            </template>
          </UiField>
          <div class="register-form__actions">
            <label class="auth-consent">
              <input v-model="form.agree" type="checkbox" class="size-4 accent-primary" :aria-invalid="Boolean(errors.agree)">
              <span>Tôi đồng ý với điều khoản sử dụng và chính sách quyền riêng tư.</span>
            </label>
            <p v-if="errors.agree" class="auth-inline-error" role="alert">{{ errors.agree }}</p>
            <p class="auth-role-note">Tạo tài khoản mới thành công sẽ  chuyển sang phần đăng nhập</p>
            <p v-if="attempted && message" class="auth-feedback" :class="successMessage ? 'auth-feedback--success' : 'auth-feedback--error'" :role="successMessage ? 'status' : 'alert'">{{ message }}</p>
            <UiButton type="submit" class="auth-submit" :loading="submitting">
              <LoaderCircle v-if="submitting" :size="17" class="animate-spin" aria-hidden="true" />
              {{ submitting ? 'Đang tạo tài khoản...' : 'Tạo tài khoản' }}
            </UiButton>
          </div>
        </form>
      </section>
    </div>
    <footer class="auth-footer"><span>EDUSUGGEST</span><span>Học tập có định hướng, tiến bộ có ý nghĩa.</span></footer>
  </main>
</template>

<style scoped>
.auth-screen {
  --auth-content-width: 1160px;
  min-height: 100vh;
  min-height: 100svh;
  padding: 0 clamp(20px, 5vw, 76px);
  background: var(--color-background);
  color: var(--color-ink);
}

.auth-topbar,
.auth-footer {
  width: min(100%, var(--auth-content-width));
  margin-inline: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.auth-topbar {
  min-height: 84px;
  border-bottom: 1px solid var(--color-border);
}

.auth-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--color-navy);
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  text-decoration: none;
}

.auth-brand__mark {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: var(--es-radius-control);
  background: var(--color-primary);
  color: var(--color-brand-accent);
}

.auth-topbar__aside {
  display: flex;
  align-items: center;
  gap: 16px;
}

.auth-text-link {
  color: var(--color-primary);
  font-size: 0.9rem;
  font-weight: 700;
  text-decoration: none;
}

.auth-text-link:hover { color: var(--color-accent); }
.auth-text-link:focus-visible,
.auth-brand:focus-visible,
.auth-password-toggle:focus-visible {
  outline: 3px solid var(--color-brand-accent);
  outline-offset: 3px;
}

.login-layout,
.register-layout {
  width: min(100%, var(--auth-content-width));
  margin: 0 auto;
  display: grid;
}

.login-layout {
  min-height: min(690px, calc(100svh - 144px));
  grid-template-columns: minmax(0, 1.1fr) minmax(360px, 0.9fr);
  align-items: center;
}

.login-editorial {
  min-height: 470px;
  padding: clamp(36px, 6vw, 86px) clamp(30px, 5vw, 72px) 40px 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  border-right: 1px solid var(--color-border);
}

.auth-eyebrow {
  margin: 0;
  color: var(--color-secondary);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.13em;
  line-height: 1.5;
  text-transform: uppercase;
}

.auth-eyebrow > span {
  display: inline-block;
  width: 20px;
  height: 2px;
  margin: 0 7px 3px 0;
  background: var(--color-brand-accent);
}

.login-editorial h1,
.register-editorial h1 {
  margin: 23px 0 0;
  color: var(--color-navy);
  font-family: var(--font-display);
  font-size: clamp(2.65rem, 5.1vw, 4.6rem);
  font-weight: 500;
  letter-spacing: -0.045em;
  line-height: 1.04;
}

.login-editorial h1 em,
.register-editorial h1 em {
  color: var(--color-accent);
  font-weight: 500;
}

.login-editorial__copy,
.register-editorial__copy {
  max-width: 410px;
  margin: 25px 0 0;
  color: var(--color-muted);
  font-size: 1rem;
  line-height: 1.75;
}

.login-editorial__note {
  margin-top: 58px;
  display: flex;
  align-items: center;
  gap: 15px;
  color: var(--color-secondary);
  font-size: 0.85rem;
}

.login-editorial__index {
  color: var(--color-accent);
  font-family: var(--font-display);
  font-size: 1.45rem;
}

.auth-form-panel {
  width: 100%;
  background: var(--color-surface);
}

.login-form-panel {
  max-width: 440px;
  justify-self: end;
  padding: clamp(28px, 4vw, 52px);
}

.auth-form-heading h2 {
  margin: 10px 0 0;
  color: var(--color-navy);
  font-family: var(--font-display);
  font-size: clamp(1.8rem, 3vw, 2.35rem);
  font-weight: 500;
  letter-spacing: -0.035em;
  line-height: 1.15;
}

.auth-form-heading > p:last-child {
  margin: 10px 0 0;
  color: var(--color-muted);
  font-size: 0.92rem;
  line-height: 1.6;
}

.auth-form {
  margin-top: 30px;
  display: grid;
  gap: 20px;
}

.auth-password-control {
  position: relative;
  display: block;
}

.auth-password-control :deep(.ui-input) { padding-right: 48px; }

.auth-password-toggle {
  position: absolute;
  top: 50%;
  right: 8px;
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  transform: translateY(-50%);
  border: 0;
  border-radius: var(--es-radius-control);
  background: transparent;
  color: var(--color-muted);
  cursor: pointer;
}

.auth-password-toggle:hover { background: var(--color-background); color: var(--color-primary); }

.auth-submit { width: 100%; min-height: 48px; }

.auth-feedback {
  margin: 0;
  padding: 12px 14px;
  border-left: 3px solid var(--color-danger);
  background: rgb(163 62 53 / 7%);
  color: var(--color-danger);
  font-size: 0.875rem;
  line-height: 1.55;
}

.auth-feedback--success {
  border-left-color: var(--color-success);
  background: rgb(53 107 85 / 8%);
  color: var(--color-success);
}

.auth-form-footnote {
  margin: 24px 0 0;
  padding-top: 17px;
  border-top: 1px solid var(--color-border);
  color: var(--color-muted);
  font-size: 0.75rem;
  line-height: 1.6;
}

.auth-footer {
  min-height: 60px;
  border-top: 1px solid var(--color-border);
  color: var(--color-muted);
  font-size: 0.72rem;
}

.auth-footer span:first-child { color: var(--color-secondary); font-weight: 700; letter-spacing: 0.13em; }

.register-layout {
  min-height: calc(100svh - 145px);
  grid-template-columns: minmax(250px, 0.72fr) minmax(0, 1.28fr);
  align-items: stretch;
  padding-block: 28px;
}

.register-editorial {
  padding: clamp(30px, 4vw, 56px) clamp(24px, 3.5vw, 48px);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  background: var(--color-navy);
  color: white;
}

.register-editorial .auth-eyebrow { color: var(--color-brand-accent); }
.register-editorial h1 { color: white; font-size: clamp(2.35rem, 4vw, 3.65rem); }
.register-editorial h1 em { color: var(--color-brand-accent); }
.register-editorial__copy { color: rgb(255 255 255 / 72%); font-size: 0.92rem; }

.register-steps {
  width: 100%;
  margin: 46px 0 0;
  padding: 0;
  list-style: none;
}

.register-steps li {
  min-height: 48px;
  display: flex;
  align-items: center;
  gap: 14px;
  border-top: 1px solid rgb(255 255 255 / 18%);
  color: rgb(255 255 255 / 88%);
  font-size: 0.82rem;
}

.register-steps li span:first-child { color: var(--color-brand-accent); font-family: var(--font-display); font-size: 1.1rem; }

.register-form-panel {
  align-self: center;
  padding: clamp(26px, 4vw, 48px);
}

.register-form {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 18px;
  row-gap: 16px;
}

.register-form :deep(.ui-field__hint) { min-height: 1.25em; }

.register-form__actions {
  grid-column: 1 / -1;
  display: grid;
  gap: 13px;
  padding-top: 3px;
}

.auth-consent {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  color: var(--color-muted);
  font-size: 0.78rem;
  line-height: 1.5;
  cursor: pointer;
}

.auth-consent input { flex: none; margin-top: 2px; }
.auth-inline-error { margin: -7px 0 0; color: var(--color-danger); font-size: 0.78rem; }

.auth-role-note {
  margin: 0;
  padding: 10px 12px;
  border-left: 2px solid var(--color-secondary);
  background: var(--color-background);
  color: var(--color-muted);
  font-size: 0.76rem;
  line-height: 1.5;
}

@media (max-width: 900px) {
  .login-layout { min-height: calc(100svh - 144px); grid-template-columns: minmax(0, 1fr) minmax(310px, 0.88fr); }
  .login-editorial { padding-right: 28px; }
  .login-editorial h1 { font-size: clamp(2.45rem, 6vw, 3.7rem); }
  .login-form-panel { padding: 28px; }
  .register-layout { grid-template-columns: minmax(220px, 0.65fr) minmax(0, 1.35fr); }
  .register-editorial { padding-inline: 25px; }
  .register-form-panel { padding: 28px; }
  .register-form { grid-template-columns: 1fr; }
  .register-form__actions { grid-column: 1; }
}

@media (max-width: 640px) {
  .auth-screen { padding-inline: 18px; }
  .auth-topbar { min-height: 68px; }
  .auth-topbar__aside { gap: 0; }
  .login-layout,
  .register-layout { display: flex; flex-direction: column; }
  .login-layout { min-height: auto; padding-block: 28px 34px; }
  .login-editorial {
    min-height: auto;
    padding: 20px 0 23px;
    border-right: 0;
    border-bottom: 1px solid var(--color-border);
  }
  .login-editorial h1 { margin-top: 15px; font-size: clamp(2.25rem, 11vw, 3.2rem); }
  .login-editorial__copy { margin-top: 14px; font-size: 0.9rem; }
  .login-editorial__note { margin-top: 18px; font-size: 0.78rem; }
  .login-form-panel { max-width: none; padding: 25px 0 0; background: transparent; }
  .auth-form { margin-top: 22px; gap: 17px; }
  .auth-form-footnote { margin-top: 18px; }
  .auth-footer { min-height: 52px; gap: 14px; font-size: 0.65rem; }
  .auth-footer span:last-child { text-align: right; }
  .register-layout { min-height: auto; padding-block: 16px 28px; }
  .register-editorial { padding: 24px 22px; }
  .register-editorial h1 { margin-top: 13px; font-size: clamp(2.15rem, 10vw, 2.8rem); }
  .register-editorial__copy { margin-top: 12px; font-size: 0.86rem; }
  .register-steps { display: none; }
  .register-form-panel { padding: 25px 0 4px; background: transparent; }
  .register-form { margin-top: 20px; gap: 14px; }
  .register-form :deep(.ui-field__hint) { min-height: 0; }
  .register-form__actions { gap: 11px; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; }
}
</style>
