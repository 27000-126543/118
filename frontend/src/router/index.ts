import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { UserRole } from '@/types'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { guest: true }
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard'
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '综合看板' }
      },
      {
        path: 'simulations',
        name: 'Simulations',
        component: () => import('@/views/SimulationList.vue'),
        meta: { title: '模拟任务列表' }
      },
      {
        path: 'simulations/create',
        name: 'CreateSimulation',
        component: () => import('@/views/CreateSimulation.vue'),
        meta: { title: '创建模拟任务' }
      },
      {
        path: 'simulations/:id',
        name: 'SimulationDetail',
        component: () => import('@/views/SimulationDetail.vue'),
        meta: { title: '模拟详情' }
      },
      {
        path: 'alerts',
        name: 'Alerts',
        component: () => import('@/views/Alerts.vue'),
        meta: { title: '预警中心' }
      },
      {
        path: 'reviews',
        name: 'Reviews',
        component: () => import('@/views/Reviews.vue'),
        meta: { title: '复核管理', roles: [UserRole.GEOPHYSICIST, UserRole.ADMIN] }
      },
      {
        path: 'approvals/postdoc',
        name: 'PostdocApprovals',
        component: () => import('@/views/PostdocApprovals.vue'),
        meta: { title: '博士后审批', roles: [UserRole.POSTDOC, UserRole.ADMIN] }
      },
      {
        path: 'approvals/professor',
        name: 'ProfessorApprovals',
        component: () => import('@/views/ProfessorApprovals.vue'),
        meta: { title: '教授审批', roles: [UserRole.PROFESSOR, UserRole.ADMIN] }
      },
      {
        path: 'recommendations',
        name: 'Recommendations',
        component: () => import('@/views/Recommendations.vue'),
        meta: { title: '智能推荐' }
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('@/views/Reports.vue'),
        meta: { title: '报告中心' }
      },
      {
        path: 'statistics',
        name: 'Statistics',
        component: () => import('@/views/Statistics.vue'),
        meta: { title: '统计分析' }
      },
      {
        path: 'admin/users',
        name: 'UserManagement',
        component: () => import('@/views/UserManagement.vue'),
        meta: { title: '用户管理', roles: [UserRole.ADMIN] }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.guest && authStore.isAuthenticated) {
    next('/dashboard')
    return
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
    return
  }

  if (to.meta.roles && authStore.user) {
    const requiredRoles = to.meta.roles as UserRole[]
    if (!requiredRoles.includes(authStore.user.role) && authStore.user.role !== UserRole.ADMIN) {
      next('/dashboard')
      return
    }
  }

  next()
})

export default router
