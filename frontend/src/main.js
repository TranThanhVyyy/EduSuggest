import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'

createApp(App).use(router).mount('#app')

window.addEventListener('edusuggest:auth-expired', () => {
  const currentRoute = router.currentRoute.value
  if (['login', 'register', 'admin-login'].includes(currentRoute.name)) return

  void router.replace({
    name: 'login',
    query: { redirect: currentRoute.fullPath },
  })
})
