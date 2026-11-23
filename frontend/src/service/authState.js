import { reactive } from 'vue'

const TOKEN_KEY = 'edusuggest.accessToken'

export const authState = reactive({
  accessToken: sessionStorage.getItem(TOKEN_KEY) || '',
  user: null,
})

export function setSession(accessToken, user) {
  authState.accessToken = accessToken
  authState.user = user
  sessionStorage.setItem(TOKEN_KEY, accessToken)
}

export function setCurrentUser(user) {
  authState.user = user
}

export function clearSession() {
  authState.accessToken = ''
  authState.user = null
  sessionStorage.removeItem(TOKEN_KEY)
}
