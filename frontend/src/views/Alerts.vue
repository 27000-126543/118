<template>
  <div class="alerts-container page-container">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">预警中心</h2>
        <p class="page-desc">查看和管理系统产生的所有预警信息</p>
      </div>
      <div class="header-right">
        <el-badge :value="unreadCount" :max="99" class="unread-badge" v-if="unreadCount > 0">
          <el-button type="primary" @click="fetchUnreadCount">
            <el-icon><Bell /></el-icon>
            未读预警
          </el-button>
        </el-badge>
      </div>
    </div>

    <div class="card-shadow filter-card">
      <el-form :model="filterForm" inline class="filter-form">
        <el-form-item label="预警等级">
          <el-select
            v-model="filterForm.level"
            placeholder="全部等级"
            clearable
            style="width: 140px"
          >
            <el-option label="信息" value="info" />
            <el-option label="警告" value="warning" />
            <el-option label="严重" value="critical" />
          </el-select>
        </el-form-item>

        <el-form-item label="状态">
          <el-select
            v-model="filterForm.isRead"
            placeholder="全部状态"
            clearable
            style="width: 140px"
          >
            <el-option label="未读" :value="false" />
            <el-option label="已读" :value="true" />
          </el-select>
        </el-form-item>

        <el-form-item label="需复核">
          <el-select
            v-model="filterForm.needsReview"
            placeholder="全部"
            clearable
            style="width: 140px"
          >
            <el-option label="是" :value="true" />
            <el-option label="否" :value="false" />
          </el-select>
        </el-form-item>

        <el-form-item label="模拟ID">
          <el-input
            v-model="filterForm.simulationId"
            placeholder="请输入模拟ID"
            clearable
            style="width: 140px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>

        <el-form-item label="搜索">
          <el-input
            v-model="filterForm.keyword"
            placeholder="搜索预警标题"
            clearable
            style="width: 220px"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
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
          <el-button
            type="primary"
            :disabled="selectedIds.length === 0"
            @click="handleBatchMarkRead"
          >
            <el-icon><Check /></el-icon>
            批量标记已读
          </el-button>
          <el-button
            type="success"
            :disabled="selectedIds.length === 0"
            @click="handleBatchMarkReviewed"
          >
            <el-icon><CircleCheck /></el-icon>
            批量标记已复核
          </el-button>
          <el-button
            type="danger"
            :disabled="selectedIds.length === 0"
            @click="handleBatchDelete"
          >
            <el-icon><Delete /></el-icon>
            批量删除
          </el-button>
          <span v-if="selectedIds.length > 0" class="selected-count">
            已选择 {{ selectedIds.length }} 项
          </span>
        </div>
        <div class="toolbar-right">
          <el-button @click="fetchList">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </div>

      <el-table
        :data="tableData"
        v-loading="loading"
        style="width: 100%"
        @selection-change="handleSelectionChange"
        :row-class-name="getRowClassName"
        empty-text="暂无数据"
      >
        <el-table-column type="selection" width="55" align="center" />

        <el-table-column label="预警等级" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getLevelTagType(row.level)" effect="light" size="small" class="level-tag">
              {{ getLevelLabel(row.level) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="预警信息" min-width="300">
          <template #default="{ row }">
            <div class="alert-info">
              <div class="alert-title">
                <el-icon v-if="!row.isRead" class="unread-dot"><Dot /></el-icon>
                <span :class="{ 'title-unread': !row.isRead }">{{ row.title }}</span>
                <el-tag v-if="row.needsReview" type="warning" size="small" effect="plain" class="review-tag">
                  需复核
                </el-tag>
                <el-tag v-if="row.reviewed" type="success" size="small" effect="plain" class="review-tag">
                  已复核
                </el-tag>
              </div>
              <div class="alert-message">{{ row.message }}</div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="指标信息" width="240">
          <template #default="{ row }">
            <div class="metric-info">
              <div class="metric-item">
                <span class="metric-label">指标名:</span>
                <span class="metric-value">{{ row.metricName || '-' }}</span>
              </div>
              <div class="metric-item">
                <span class="metric-label">当前值:</span>
                <span class="metric-value highlight">{{ formatMetricValue(row.metricValue) }}</span>
              </div>
              <div class="metric-item">
                <span class="metric-label">阈值:</span>
                <span class="metric-value">{{ formatMetricValue(row.threshold) }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="所属模拟" width="140" align="center">
          <template #default="{ row }">
            <div class="simulation-info">
              <span class="simulation-id">#{{ row.simulationId }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="创建时间" width="160" align="center">
          <template #default="{ row }">
            {{ formatDate(row.createdAt) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="240" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="!row.isRead"
              type="primary"
              link
              size="small"
              @click="handleMarkRead(row)"
            >
              <el-icon><Check /></el-icon>
              标记已读
            </el-button>
            <el-button
              v-if="row.needsReview && !row.reviewed"
              type="success"
              link
              size="small"
              @click="handleMarkReviewed(row)"
            >
              <el-icon><CircleCheck /></el-icon>
              标记已复核
            </el-button>
            <el-button
              type="primary"
              link
              size="small"
              @click="handleViewSimulation(row)"
            >
              <el-icon><View /></el-icon>
              查看模拟
            </el-button>
          </template>
        </el-table-column>

        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-content">
              <el-descriptions :column="3" border size="small">
                <el-descriptions-item label="预警ID">
                  {{ row.id }}
                </el-descriptions-item>
                <el-descriptions-item label="预警等级">
                  <el-tag :type="getLevelTagType(row.level)" effect="light" size="small">
                    {{ getLevelLabel(row.level) }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="接收者ID">
                  {{ row.recipientId }}
                </el-descriptions-item>
                <el-descriptions-item label="预警标题">
                  {{ row.title }}
                </el-descriptions-item>
                <el-descriptions-item label="预警消息" :span="2">
                  {{ row.message }}
                </el-descriptions-item>
                <el-descriptions-item label="指标名称">
                  {{ row.metricName || '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="指标当前值">
                  <span class="highlight">{{ formatMetricValue(row.metricValue) }}</span>
                </el-descriptions-item>
                <el-descriptions-item label="预警阈值">
                  {{ formatMetricValue(row.threshold) }}
                </el-descriptions-item>
                <el-descriptions-item label="读取状态">
                  <el-tag :type="row.isRead ? 'success' : 'warning'" effect="light" size="small">
                    {{ row.isRead ? '已读' : '未读' }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="是否需复核">
                  <el-tag :type="row.needsReview ? 'warning' : 'info'" effect="light" size="small">
                    {{ row.needsReview ? '是' : '否' }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="复核状态">
                  <el-tag :type="row.reviewed ? 'success' : 'info'" effect="light" size="small">
                    {{ row.reviewed ? '已复核' : '未复核' }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="创建时间" :span="2">
                  {{ formatDateTime(row.createdAt) }}
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="tableData.length === 0 && !loading" class="empty-state">
        <el-empty description="暂无预警信息" :image-size="100">
          <template #image>
            <el-icon :size="80" color="#c0c4cc"><Bell /></el-icon>
          </template>
        </el-empty>
      </div>

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

    <el-dialog v-model="deleteDialogVisible" title="确认删除" width="400px">
      <div class="delete-confirm">
        <el-icon class="warning-icon" size="48" color="#f56c6c"><Warning /></el-icon>
        <p>确定要删除选中的 <strong>{{ selectedIds.length }}</strong> 条预警吗？</p>
        <p class="warning-text">此操作不可恢复，相关数据将被永久删除。</p>
      </div>
      <template #footer>
        <el-button @click="deleteDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmDelete">确认删除</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { monitoringAPI } from '@/api'
import type { Alert } from '@/types'
import { AlertLevel } from '@/types'
import dayjs from 'dayjs'
import {
  Search,
  Refresh,
  Check,
  CircleCheck,
  Delete,
  View,
  Bell,
  Dot,
  Warning
} from '@element-plus/icons-vue'

const router = useRouter()

const loading = ref(false)
const tableData = ref<Alert[]>([])
const selectedIds = ref<number[]>([])
const unreadCount = ref(0)
const deleteDialogVisible = ref(false)

const filterForm = reactive({
  level: '',
  isRead: null as boolean | null,
  needsReview: null as boolean | null,
  simulationId: '',
  keyword: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

function getLevelLabel(level: AlertLevel): string {
  const labelMap: Record<AlertLevel, string> = {
    [AlertLevel.INFO]: '信息',
    [AlertLevel.WARNING]: '警告',
    [AlertLevel.CRITICAL]: '严重'
  }
  return labelMap[level] || '未知'
}

function getLevelTagType(level: AlertLevel): 'primary' | 'warning' | 'danger' | 'info' {
  const typeMap: Record<AlertLevel, 'primary' | 'warning' | 'danger' | 'info'> = {
    [AlertLevel.INFO]: 'primary',
    [AlertLevel.WARNING]: 'warning',
    [AlertLevel.CRITICAL]: 'danger'
  }
  return typeMap[level] || 'info'
}

function getRowClassName({ row }: { row: Alert }): string {
  const classes: string[] = []
  if (!row.isRead) {
    classes.push('row-unread')
  }
  classes.push(`level-${row.level}`)
  return classes.join(' ')
}

function formatMetricValue(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-'
  if (Math.abs(value) >= 1e6 || (Math.abs(value) < 0.001 && value !== 0)) {
    return value.toExponential(4)
  }
  return value.toFixed(4)
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm')
}

function formatDateTime(dateStr: string): string {
  if (!dateStr) return '-'
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm:ss')
}

async function fetchList() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: pagination.page,
      page_size: pagination.pageSize
    }

    if (filterForm.level) {
      params.level = filterForm.level
    }
    if (filterForm.isRead !== null) {
      params.is_read = filterForm.isRead
    }
    if (filterForm.needsReview !== null) {
      params.needs_review = filterForm.needsReview
    }
    if (filterForm.simulationId) {
      params.simulation_id = filterForm.simulationId
    }
    if (filterForm.keyword) {
      params.keyword = filterForm.keyword
    }

    const response = await monitoringAPI.getAlerts(params)
    tableData.value = response.data.items || response.data || []
    pagination.total = response.data.total || tableData.value.length
  } catch (error) {
    console.error('Failed to fetch alerts:', error)
    ElMessage.error('获取预警列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchUnreadCount() {
  try {
    const response = await monitoringAPI.getUnreadCount()
    unreadCount.value = response.data.unread_count || response.data.count || response.data || 0
  } catch (error) {
    console.error('Failed to fetch unread count:', error)
  }
}

function handleSearch() {
  pagination.page = 1
  fetchList()
}

function handleReset() {
  filterForm.level = ''
  filterForm.isRead = null
  filterForm.needsReview = null
  filterForm.simulationId = ''
  filterForm.keyword = ''
  pagination.page = 1
  fetchList()
}

function handleSelectionChange(selection: Alert[]) {
  selectedIds.value = selection.map(item => item.id)
}

function handleSizeChange(size: number) {
  pagination.pageSize = size
  pagination.page = 1
  fetchList()
}

function handlePageChange(page: number) {
  pagination.page = page
  fetchList()
}

async function handleMarkRead(row: Alert) {
  try {
    await monitoringAPI.markRead(row.id)
    ElMessage.success('已标记为已读')
    row.isRead = true
    fetchUnreadCount()
  } catch (error) {
    console.error('Failed to mark as read:', error)
    ElMessage.error('标记失败')
  }
}

async function handleMarkReviewed(row: Alert) {
  try {
    await monitoringAPI.markReviewed(row.id)
    ElMessage.success('已标记为已复核')
    row.reviewed = true
  } catch (error) {
    console.error('Failed to mark as reviewed:', error)
    ElMessage.error('标记失败')
  }
}

function handleViewSimulation(row: Alert) {
  router.push(`/simulations/${row.simulationId}`)
}

async function handleBatchMarkRead() {
  if (selectedIds.value.length === 0) return

  try {
    await Promise.all(selectedIds.value.map(id => monitoringAPI.markRead(id)))
    ElMessage.success(`已批量标记 ${selectedIds.value.length} 条预警为已读`)
    selectedIds.value = []
    fetchList()
    fetchUnreadCount()
  } catch (error) {
    console.error('Failed to batch mark read:', error)
    ElMessage.error('批量标记失败')
  }
}

async function handleBatchMarkReviewed() {
  if (selectedIds.value.length === 0) return

  try {
    await Promise.all(selectedIds.value.map(id => monitoringAPI.markReviewed(id)))
    ElMessage.success(`已批量标记 ${selectedIds.value.length} 条预警为已复核`)
    selectedIds.value = []
    fetchList()
  } catch (error) {
    console.error('Failed to batch mark reviewed:', error)
    ElMessage.error('批量标记失败')
  }
}

function handleBatchDelete() {
  if (selectedIds.value.length === 0) return
  deleteDialogVisible.value = true
}

async function confirmDelete() {
  if (selectedIds.value.length === 0) return

  try {
    await Promise.all(selectedIds.value.map(id => monitoringAPI.deleteAlert(id)))
    ElMessage.success('批量删除成功')
    deleteDialogVisible.value = false
    selectedIds.value = []
    fetchList()
    fetchUnreadCount()
  } catch (error) {
    console.error('Failed to batch delete:', error)
    ElMessage.error('批量删除失败')
  }
}

onMounted(() => {
  fetchList()
  fetchUnreadCount()
})
</script>

<style scoped lang="css">
.alerts-container {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.header-left {
  flex: 1;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px 0;
}

.page-desc {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

.unread-badge {
  margin-right: 8px;
}

.filter-card {
  padding: 20px 24px;
  margin-bottom: 16px;
  background: #fff;
  border-radius: 12px;
}

.filter-form {
  margin-bottom: 0;
}

.filter-form .el-form-item {
  margin-bottom: 0;
  margin-right: 16px;
}

.table-card {
  padding: 24px;
  background: #fff;
  border-radius: 12px;
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

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selected-count {
  margin-left: 8px;
  font-size: 13px;
  color: #909399;
}

.level-tag {
  font-weight: 500;
}

.alert-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.alert-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.title-unread {
  font-weight: 600;
}

.unread-dot {
  color: #f56c6c;
  font-size: 8px;
}

.review-tag {
  margin-left: 4px;
}

.alert-message {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}

.metric-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.metric-item {
  font-size: 13px;
  color: #606266;
}

.metric-label {
  color: #909399;
  margin-right: 4px;
}

.metric-value {
  font-weight: 500;
  color: #303133;
}

.metric-value.highlight {
  color: #f56c6c;
}

.simulation-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.simulation-id {
  font-size: 13px;
  font-weight: 500;
  color: #409eff;
}

.highlight {
  color: #f56c6c;
  font-weight: 500;
}

.expand-content {
  padding: 12px 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.empty-state {
  padding: 60px 0;
  text-align: center;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
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

.warning-text {
  color: #f56c6c !important;
  font-size: 13px;
}

:deep(.el-table .row-unread) {
  background-color: #f0f9ff;
}

:deep(.el-table .row-unread:hover > td) {
  background-color: #ecf5ff !important;
}

:deep(.el-table__row.level-info) {
  border-left: 3px solid #409eff;
}

:deep(.el-table__row.level-warning) {
  border-left: 3px solid #e6a23c;
}

:deep(.el-table__row.level-critical) {
  border-left: 3px solid #f56c6c;
}
</style>
