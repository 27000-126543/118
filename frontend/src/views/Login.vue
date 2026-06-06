<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <el-icon :size="64" color="#409eff">
          <Planet />
        </el-icon>
        <h1 class="title">地核多物理场耦合模拟平台</h1>
        <p class="subtitle">Geodynamo Multi-Physics Simulation Platform</p>
      </div>

      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="用户名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          class="login-button"
          :loading="loading"
          @click="handleLogin"
        >
          登录
        </el-button>
      </el-form>

      <div class="demo-accounts">
        <el-divider content-position="center">演示账户</el-divider>
        <div class="account-list">
          <div v-for="account in demoAccounts" :key="account.username" class="account-item">
            <span class="role">{{ account.role }}</span>
            <span class="credentials">{{ account.username }} / {{ account.password }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock, Planet } from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()

const loginFormRef = ref<FormInstance>()
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const loginRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const demoAccounts = [
  { role: '管理员', username: 'admin', password: 'admin123' },
  { role: '博士后', username: 'postdoc1', password: 'postdoc123' },
  { role: '教授', username: 'professor1', password: 'professor123' },
  { role: '地磁学家', username: 'geophysicist1', password: 'geo123' },
  { role: '首席科学家', username: 'chief1', password: 'chief123' },
  { role: '研究员', username: 'researcher1', password: 'researcher123' }
]

async function handleLogin() {
  if (!loginFormRef.value) return

  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        await authStore.login(loginForm.username, loginForm.password)
        ElMessage.success('登录成功')
        router.push('/dashboard')
      } catch (error: any) {
        ElMessage.error(error.response?.data?.detail || '登录失败，请检查用户名和密码')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped lang="css">
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 480px;
  background: #fff;
  border-radius: 16px;
  padding: 48px 40px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.login-header {
  text-align: center;
  margin-bottom: 40px;
}

.title {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
  margin: 16px 0 8px;
}

.subtitle {
  font-size: 14px;
  color: #909399;
}

.login-form {
  margin-bottom: 32px;
}

.login-button {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  margin-top: 16px;
}

.demo-accounts {
  margin-top: 24px;
}

.account-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.account-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 13px;
}

.role {
  color: #909399;
  font-weight: 500;
}

.credentials {
  color: #606266;
  font-family: 'Courier New', monospace;
}
</style>
