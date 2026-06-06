<template>
  <el-container class="main-container">
    <el-aside width="240px" class="sidebar">
      <div class="logo">
        <el-icon :size="28" color="#409eff">
          <Monitor />
        </el-icon>
        <span class="logo-text">地核模拟平台</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        class="sidebar-menu"
        router
        background-color="#1f2d3d"
        text-color="#c0ccda"
        active-text-color="#409eff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>综合看板</span>
        </el-menu-item>
        <el-sub-menu index="simulations">
          <template #title>
            <el-icon><Operation /></el-icon>
            <span>模拟任务</span>
          </template>
          <el-menu-item index="/simulations">任务列表</el-menu-item>
          <el-menu-item index="/simulations/create">新建任务</el-menu-item>
        </el-sub-menu>
        <el-menu-item index="/alerts">
          <el-badge :value="unreadCount" :hidden="unreadCount === 0" class="item">
            <el-icon><Warning /></el-icon>
            <span>预警中心</span>
          </el-badge>
        </el-menu-item>
        <el-menu-item v-if="showReviews" index="/reviews">
          <el-icon><EditPen /></el-icon>
          <span>复核管理</span>
        </el-menu-item>
        <el-menu-item v-if="showPostdocApprovals" index="/approvals/postdoc">
          <el-icon><CircleCheck /></el-icon>
          <span>博士后审批</span>
        </el-menu-item>
        <el-menu-item v-if="showProfessorApprovals" index="/approvals/professor">
          <el-icon><Medal /></el-icon>
          <span>教授审批</span>
        </el-menu-item>
        <el-menu-item index="/recommendations">
          <el-icon><MagicStick /></el-icon>
          <span>智能推荐</span>
        </el-menu-item>
        <el-menu-item index="/reports">
          <el-icon><Document /></el-icon>
          <span>报告中心</span>
        </el-menu-item>
        <el-menu-item index="/statistics">
          <el-icon><TrendCharts /></el-icon>
          <span>统计分析</span>
        </el-menu-item>
        <el-menu-item v-if="isAdmin" index="/admin/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentPageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" :icon="UserFilled" />
              <span class="username">{{ authStore.user?.fullName || authStore.user?.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item command="settings">设置</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { UserRole } from '@/types'
import { monitoringAPI } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  UserFilled, ArrowDown, Monitor, DataAnalysis,
  Operation, Warning, EditPen, CircleCheck,
  Medal, MagicStick, Document, TrendCharts, User
} from '@element-plus/icons-vue'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const unreadCount = ref(0)

const activeMenu = computed(() => route.path)

const currentPageTitle = computed(() => {
  return (route.meta.title as string) || '地核模拟平台'
})

const isAdmin = computed(() => authStore.user?.role === UserRole.ADMIN)
const showReviews = computed(() =>
  [UserRole.GEOPHYSICIST, UserRole.ADMIN, UserRole.CHIEF_SCIENTIST].includes(authStore.user?.role as UserRole)
)
const showPostdocApprovals = computed(() =>
  [UserRole.POSTDOC, UserRole.ADMIN].includes(authStore.user?.role as UserRole)
)
const showProfessorApprovals = computed(() =>
  [UserRole.PROFESSOR, UserRole.ADMIN].includes(authStore.user?.role as UserRole)
)

async function fetchUnreadCount() {
  try {
    const response = await monitoringAPI.getUnreadCount()
    unreadCount.value = response.data.unread_count
  } catch (error) {
    console.error('Failed to fetch unread count:', error)
  }
}

function handleCommand(command: string) {
  switch (command) {
    case 'profile':
      ElMessage.info('个人中心功能开发中')
      break
    case 'settings':
      ElMessage.info('设置功能开发中')
      break
    case 'logout':
      ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        authStore.logout()
        router.push('/login')
        ElMessage.success('已退出登录')
      }).catch(() => {})
      break
  }
}

onMounted(() => {
  fetchUnreadCount()
  setInterval(fetchUnreadCount, 30000)
})
</script>

<style scoped lang="css">
.main-container {
  height: 100vh;
}

.sidebar {
  background-color: #1f2d3d;
  transition: width 0.3s;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 0 20px;
  border-bottom: 1px solid #304156;
}

.logo-text {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
}

.sidebar-menu {
  border-right: none;
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.user-info:hover {
  background-color: #f5f7fa;
}

.username {
  font-size: 14px;
  color: #303133;
}

.main-content {
  background-color: #f0f2f5;
  padding: 0;
  overflow-x: hidden;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.item {
  margin-top: 0;
}
</style>
