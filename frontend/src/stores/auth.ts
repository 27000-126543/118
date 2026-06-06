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
    const response = await authAPI.login(username, password)
    const data = response.data
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)

    const userResponse = await authAPI.getCurrentUser()
    user.value = userResponse.data
    localStorage.setItem('user', JSON.stringify(userResponse.data))

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
