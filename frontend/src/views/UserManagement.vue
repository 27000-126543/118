<template>
  <div class="user-management-container page-container">
    <div class="page-header">
      <h2 class="page-title">用户管理</h2>
      <p class="page-desc">管理系统用户及角色权限配置</p>
    </div>

    <div class="card-shadow filter-card">
      <el-form :model="searchForm" inline class="search-form">
        <el-form-item label="搜索">
          <el-input
            v-model="searchForm.keyword"
            placeholder="用户名/邮箱/全名"
            clearable
            style="width: 240px"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="角色">
          <el-select
            v-model="searchForm.role"
            placeholder="全部角色"
            clearable
            style="width: 160px"
          >
            <el-option
              v-for="role in roleOptions"
              :key="role.value"
              :label="role.label"
              :value="role.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="状态">
          <el-select
            v-model="searchForm.status"
            placeholder="全部状态"
            clearable
            style="width: 140px"
          >
            <el-option label="正常" :value="true" />
            <el-option label="禁用" :value="false" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="card-shadow table-card">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <el-button type="primary" @click="handleCreate">
            <el-icon><Plus /></el-icon>
            新增用户
          </el-button>
          <el-button @click="fetchUsers">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
        <div class="toolbar-right">
          <span class="data-count">共 {{ pagination.total }} 位用户</span>
        </div>
      </div>

      <el-table
        :data="tableData"
        v-loading="loading"
        stripe
        style="width: 100%"
        empty-text="暂无用户数据"
      >
        <el-table-column prop="id" label="用户ID" width="90" align="center" />

        <el-table-column prop="username" label="用户名" width="140" />

        <el-table-column prop="email" label="邮箱" min-width="200" show-overflow-tooltip />

        <el-table-column prop="fullName" label="全名" width="140" />

        <el-table-column label="角色" width="140" align="center">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.role)" effect="light" size="small">
              {{ getRoleLabel(row.role) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.isActive"
              :loading="row.statusLoading"
              active-text="正常"
              inactive-text="禁用"
              :before-change="() => beforeToggleStatus(row)"
              @change="() => handleToggleStatus(row)"
            />
          </template>
        </el-table-column>

        <el-table-column label="创建时间" width="180" align="center">
          <template #default="{ row }">
            {{ formatDate(row.createdAt) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="220" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="handleEdit(row)">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button type="warning" size="small" link @click="handleResetPassword(row)">
              <el-icon><Key /></el-icon>
              重置密码
            </el-button>
            <el-button type="danger" size="small" link @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <div class="card-shadow roles-card">
      <h3 class="section-title">角色权限说明</h3>
      <el-row :gutter="16">
        <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="role in roleDescriptions" :key="role.role">
          <div class="role-card" :class="`role-card-${role.role}`">
            <div class="role-header">
              <el-tag :type="getRoleTagType(role.role)" effect="dark" size="large">
                {{ role.label }}
              </el-tag>
            </div>
            <p class="role-desc">{{ role.description }}</p>
          </div>
        </el-col>
      </el-row>
    </div>

    <el-dialog
      v-model="userDialogVisible"
      :title="isEditMode ? '编辑用户' : '新增用户'"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="userFormRef"
        :model="userForm"
        :rules="userFormRules"
        label-width="90px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="userForm.username"
            placeholder="请输入用户名"
            :disabled="isEditMode"
          />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input v-model="userForm.email" placeholder="请输入邮箱地址" />
        </el-form-item>

        <el-form-item label="全名" prop="fullName">
          <el-input v-model="userForm.fullName" placeholder="请输入全名" />
        </el-form-item>

        <el-form-item label="角色" prop="role">
          <el-select v-model="userForm.role" placeholder="请选择角色" style="width: 100%">
            <el-option
              v-for="role in roleOptions"
              :key="role.value"
              :label="role.label"
              :value="role.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          v-if="!isEditMode"
          label="密码"
          prop="password"
        >
          <el-input
            v-model="userForm.password"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>

        <el-form-item
          v-if="!isEditMode"
          label="确认密码"
          prop="confirmPassword"
        >
          <el-input
            v-model="userForm.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            show-password
          />
        </el-form-item>

        <el-form-item
          v-if="isEditMode"
          label="新密码"
          prop="password"
        >
          <el-input
            v-model="userForm.password"
            type="password"
            placeholder="留空则不修改密码"
            show-password
          />
        </el-form-item>

        <el-form-item
          v-if="isEditMode && userForm.password"
          label="确认密码"
          prop="confirmPassword"
        >
          <el-input
            v-model="userForm.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            show-password
          />
        </el-form-item>

        <el-form-item label="状态" prop="isActive">
          <el-switch
            v-model="userForm.isActive"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitUser" :loading="submitting">
          {{ isEditMode ? '保存修改' : '创建用户' }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="resetPasswordDialogVisible"
      title="重置密码"
      width="420px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="resetPasswordFormRef"
        :model="resetPasswordForm"
        :rules="resetPasswordFormRules"
        label-width="90px"
      >
        <el-form-item label="用户名">
          <el-input v-model="resetPasswordTarget?.username" disabled />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input
            v-model="resetPasswordForm.newPassword"
            type="password"
            placeholder="请输入新密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="resetPasswordForm.confirmPassword"
            type="password"
            placeholder="请再次输入新密码"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetPasswordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleConfirmResetPassword" :loading="resetting">
          确认重置
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="deleteDialogVisible" title="确认删除" width="420px">
      <div class="delete-confirm">
        <el-icon class="warning-icon" size="48" color="#f56c6c"><Warning /></el-icon>
        <p>确定要删除用户 <strong>"{{ deleteTarget?.username }}"</strong> 吗？</p>
        <p class="warning-text">此操作不可恢复，用户相关数据将被永久删除。</p>
      </div>
      <template #footer>
        <el-button @click="deleteDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmDelete" :loading="deleting">确认删除</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { authAPI } from '@/api'
import type { User } from '@/types'
import { UserRole } from '@/types'
import dayjs from 'dayjs'
import {
  Search,
  Refresh,
  Plus,
  Edit,
  Key,
  Delete,
  Warning
} from '@element-plus/icons-vue'

interface UserTableData extends User {
  statusLoading: boolean
}

const loading = ref(false)
const submitting = ref(false)
const deleting = ref(false)
const resetting = ref(false)

const allUsers = ref<UserTableData[]>([])
const tableData = computed(() => {
  const start = (pagination.page - 1) * pagination.pageSize
  const end = start + pagination.pageSize
  return filteredUsers.value.slice(start, end)
})

const searchForm = reactive({
  keyword: '',
  role: '',
  status: '' as boolean | string
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const filteredUsers = computed(() => {
  let result = [...allUsers.value]

  if (searchForm.keyword) {
    const keyword = searchForm.keyword.toLowerCase()
    result = result.filter(
      user =>
        user.username.toLowerCase().includes(keyword) ||
        user.email.toLowerCase().includes(keyword) ||
        user.fullName?.toLowerCase().includes(keyword)
    )
  }

  if (searchForm.role) {
    result = result.filter(user => user.role === searchForm.role)
  }

  if (searchForm.status !== '') {
    result = result.filter(user => user.isActive === searchForm.status)
  }

  pagination.total = result.length
  return result
})

const userDialogVisible = ref(false)
const isEditMode = ref(false)
const editUserId = ref<number | null>(null)
const userFormRef = ref<FormInstance>()
const userForm = reactive({
  username: '',
  email: '',
  fullName: '',
  role: UserRole.RESEARCHER,
  password: '',
  confirmPassword: '',
  isActive: true
})

const validateConfirmPassword = (_rule: any, value: string, callback: any) => {
  if (value && value !== userForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const userFormRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  fullName: [
    { required: true, message: '请输入全名', trigger: 'blur' }
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const resetPasswordDialogVisible = ref(false)
const resetPasswordFormRef = ref<FormInstance>()
const resetPasswordTarget = ref<User | null>(null)
const resetPasswordForm = reactive({
  newPassword: '',
  confirmPassword: ''
})

const validateResetConfirmPassword = (_rule: any, value: string, callback: any) => {
  if (value && value !== resetPasswordForm.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const resetPasswordFormRules: FormRules = {
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateResetConfirmPassword, trigger: 'blur' }
  ]
}

const deleteDialogVisible = ref(false)
const deleteTarget = ref<User | null>(null)

const roleOptions = [
  { value: UserRole.ADMIN, label: '管理员' },
  { value: UserRole.POSTDOC, label: '博士后' },
  { value: UserRole.PROFESSOR, label: '教授' },
  { value: UserRole.GEOPHYSICIST, label: '地磁学家' },
  { value: UserRole.CHIEF_SCIENTIST, label: '首席科学家' },
  { value: UserRole.RESEARCHER, label: '研究员' }
]

const roleDescriptions = [
  { role: UserRole.ADMIN, label: '管理员', description: '系统管理员，拥有所有权限' },
  { role: UserRole.POSTDOC, label: '博士后', description: '负责数值稳定性验证' },
  { role: UserRole.PROFESSOR, label: '教授', description: '负责物理合理性确认' },
  { role: UserRole.GEOPHYSICIST, label: '地磁学家', description: '负责预警复核和参数调整' },
  { role: UserRole.CHIEF_SCIENTIST, label: '首席科学家', description: '可暂停/恢复课题组任务' },
  { role: UserRole.RESEARCHER, label: '研究员', description: '可创建和运行模拟' }
]

function getRoleLabel(role: string): string {
  const option = roleOptions.find(r => r.value === role)
  return option ? option.label : role
}

function getRoleTagType(role: string): '' | 'success' | 'warning' | 'info' | 'primary' | 'danger' {
  const typeMap: Record<string, '' | 'success' | 'warning' | 'info' | 'primary' | 'danger'> = {
    [UserRole.ADMIN]: 'purple',
    [UserRole.POSTDOC]: '',
    [UserRole.PROFESSOR]: 'warning',
    [UserRole.GEOPHYSICIST]: 'success',
    [UserRole.CHIEF_SCIENTIST]: 'danger',
    [UserRole.RESEARCHER]: 'info'
  }
  return typeMap[role] || 'info'
}

function formatDate(dateStr: string): string {
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm:ss')
}

async function fetchUsers() {
  loading.value = true
  try {
    const response = await authAPI.listUsers()
    allUsers.value = response.data.map((user: User) => ({
      ...user,
      statusLoading: false
    }))
    pagination.total = allUsers.value.length
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '获取用户列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
}

function handleReset() {
  searchForm.keyword = ''
  searchForm.role = ''
  searchForm.status = ''
  pagination.page = 1
}

function handlePageChange() {
  // computed will handle the rest
}

function handleSizeChange() {
  pagination.page = 1
}

function handleCreate() {
  isEditMode.value = false
  editUserId.value = null
  userForm.username = ''
  userForm.email = ''
  userForm.fullName = ''
  userForm.role = UserRole.RESEARCHER
  userForm.password = ''
  userForm.confirmPassword = ''
  userForm.isActive = true
  userDialogVisible.value = true
}

function handleEdit(row: User) {
  isEditMode.value = true
  editUserId.value = row.id
  userForm.username = row.username
  userForm.email = row.email
  userForm.fullName = row.fullName
  userForm.role = row.role
  userForm.password = ''
  userForm.confirmPassword = ''
  userForm.isActive = row.isActive
  userDialogVisible.value = true
}

async function handleSubmitUser() {
  if (!userFormRef.value) return

  const rules = { ...userFormRules }
  if (isEditMode.value && !userForm.password) {
    delete rules.password
    delete rules.confirmPassword
  }

  await userFormRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      const userData = {
        username: userForm.username,
        email: userForm.email,
        full_name: userForm.fullName,
        role: userForm.role,
        is_active: userForm.isActive,
        ...(userForm.password ? { password: userForm.password } : {})
      }

      if (isEditMode.value && editUserId.value) {
        await authAPI.updateUser(editUserId.value, userData)
        ElMessage.success('用户信息更新成功')
      } else {
        await authAPI.register({
          ...userData,
          password: userForm.password
        })
        ElMessage.success('用户创建成功')
      }

      userDialogVisible.value = false
      fetchUsers()
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
      submitting.value = false
    }
  })
}

async function beforeToggleStatus(row: UserTableData) {
  try {
    await ElMessageBox.confirm(
      `确定要${row.isActive ? '禁用' : '启用'}用户 "${row.username}" 吗？`,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    return true
  } catch {
    return false
  }
}

async function handleToggleStatus(row: UserTableData) {
  row.statusLoading = true
  try {
    await authAPI.toggleUserStatus(row.id)
    ElMessage.success(`用户已${row.isActive ? '启用' : '禁用'}`)
    fetchUsers()
  } catch (error: any) {
    row.isActive = !row.isActive
    ElMessage.error(error.response?.data?.detail || '状态切换失败')
  } finally {
    row.statusLoading = false
  }
}

function handleDelete(row: User) {
  deleteTarget.value = row
  deleteDialogVisible.value = true
}

async function confirmDelete() {
  if (!deleteTarget.value) return

  deleting.value = true
  try {
    await authAPI.deleteUser(deleteTarget.value.id)
    ElMessage.success('用户删除成功')
    deleteDialogVisible.value = false
    deleteTarget.value = null
    fetchUsers()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '删除失败')
  } finally {
    deleting.value = false
  }
}

function handleResetPassword(row: User) {
  resetPasswordTarget.value = row
  resetPasswordForm.newPassword = ''
  resetPasswordForm.confirmPassword = ''
  resetPasswordDialogVisible.value = true
}

async function handleConfirmResetPassword() {
  if (!resetPasswordFormRef.value || !resetPasswordTarget.value) return

  await resetPasswordFormRef.value.validate(async (valid) => {
    if (!valid) return

    resetting.value = true
    try {
      await authAPI.resetPassword(
        resetPasswordTarget.value!.id,
        resetPasswordForm.newPassword
      )
      ElMessage.success('密码重置成功')
      resetPasswordDialogVisible.value = false
      resetPasswordTarget.value = null
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '密码重置失败')
    } finally {
      resetting.value = false
    }
  })
}

onMounted(() => {
  fetchUsers()
})
</script>

<style scoped>
.user-management-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  margin-bottom: 4px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.page-desc {
  font-size: 14px;
  color: #909399;
}

.filter-card {
  background: #fff;
  padding: 16px 20px;
}

.search-form {
  margin: 0;
}

.table-card {
  background: #fff;
  padding: 20px;
}

.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.data-count {
  font-size: 14px;
  color: #909399;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.roles-card {
  background: #fff;
  padding: 20px;
}

.role-card {
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 16px;
  transition: all 0.3s ease;
  border: 1px solid #ebeef5;
}

.role-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.role-card-admin {
  border-left: 4px solid #a855f7;
}

.role-card-postdoc {
  border-left: 4px solid #409eff;
}

.role-card-professor {
  border-left: 4px solid #e6a23c;
}

.role-card-geophysicist {
  border-left: 4px solid #67c23a;
}

.role-card-chief_scientist {
  border-left: 4px solid #f56c6c;
}

.role-card-researcher {
  border-left: 4px solid #909399;
}

.role-header {
  margin-bottom: 12px;
}

.role-desc {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
  margin: 0;
}

.delete-confirm {
  text-align: center;
  padding: 20px 0;
}

.warning-icon {
  margin-bottom: 16px;
}

.delete-confirm p {
  margin: 8px 0;
  color: #606266;
}

.delete-confirm strong {
  color: #303133;
}

.warning-text {
  color: #f56c6c !important;
  font-size: 13px;
}

:deep(.el-tag--purple) {
  --el-tag-bg-color: #f3e8ff;
  --el-tag-border-color: #e9d5ff;
  --el-tag-text-color: #a855f7;
}

:deep(.el-tag--dark.el-tag--purple) {
  --el-tag-bg-color: #a855f7;
  --el-tag-border-color: #a855f7;
  --el-tag-text-color: #fff;
}
</style>
