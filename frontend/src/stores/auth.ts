import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/types'
import { authAPI } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(JSON.parse(localStorage.getItem('user') || 'null'))

  const isAuthenticated = computed(() => !!token.value)
  const userRole = computed(() => user.value?.role)

  async function login(username: string, password: string) {
    console.log('[AuthStore] login called, username:', username)
    const response = await authAPI.login(username, password)
    console.log('[AuthStore] login response received:', response.status)
    const data = response.data
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)
    console.log('[AuthStore] token saved:', data.access_token?.substring(0, 30))

    const userResponse = await authAPI.getCurrentUser()
    console.log('[AuthStore] getCurrentUser response received')
    user.value = userResponse.data
    localStorage.setItem('user', JSON.stringify(userResponse.data))
    console.log('[AuthStore] user saved:', userResponse.data)

    return userResponse.data
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  async function register(userData: any) {
    const response = await authAPI.register(userData)
    return response.data
  }

  return {
    token,
    user,
    isAuthenticated,
    userRole,
    login,
    logout,
    register
  }
})
