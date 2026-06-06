<template>
  <div class="simulation-list-container page-container">
    <div class="page-header">
      <h2 class="page-title">模拟任务列表</h2>
      <p class="page-desc">管理和监控所有地球发电机模拟任务</p>
    </div>

    <div class="card-shadow filter-card">
      <el-form :model="searchForm" inline class="search-form">
        <el-form-item label="任务名称">
          <el-input
            v-model="searchForm.name"
            placeholder="请输入任务名称"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="状态">
          <el-select
            v-model="searchForm.status"
            placeholder="全部状态"
            clearable
            style="width: 160px"
          >
            <el-option
              v-for="status in statusOptions"
              :key="status.value"
              :label="status.label"
              :value="status.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="创建时间">
          <el-date-picker
            v-model="searchForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 280px"
          />
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
            新建任务
          </el-button>
          <el-button @click="fetchList">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
          <el-dropdown @command="handleBatchAction" :disabled="selectedIds.length === 0">
            <el-button :disabled="selectedIds.length === 0">
              <el-icon><Operation /></el-icon>
              批量操作
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="start" :disabled="!canBatchStart">
                  <el-icon><VideoPlay /></el-icon>
                  批量启动
                </el-dropdown-item>
                <el-dropdown-item command="delete" class="danger-item">
                  <el-icon><Delete /></el-icon>
                  批量删除
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <span v-if="selectedIds.length > 0" class="selected-count">
            已选择 {{ selectedIds.length }} 项
          </span>
        </div>
      </div>

      <el-table
        :data="tableData"
        v-loading="loading"
        stripe
        style="width: 100%"
        @selection-change="handleSelectionChange"
        empty-text="暂无数据"
      >
        <el-table-column type="selection" width="55" align="center" />

        <el-table-column prop="id" label="ID" width="80" align="center" />

        <el-table-column prop="name" label="任务名称" min-width="180" show-overflow-tooltip />

        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" effect="light" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="进度" width="180">
          <template #default="{ row }">
            <el-progress
              :percentage="Math.round(row.progress)"
              :status="getProgressStatus(row.status)"
              :stroke-width="8"
              :show-text="true"
            />
          </template>
        </el-table-column>

        <el-table-column label="当前迭代" width="100" align="center">
          <template #default="{ row }">
            {{ row.currentIteration || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="总迭代" width="100" align="center">
          <template #default="{ row }">
            {{ row.maxIterations || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="核心参数" min-width="200">
          <template #default="{ row }">
            <div class="params-summary">
              <div class="param-item">
                <span class="param-label">地核半径:</span>
                <span class="param-value">{{ row.coreRadius?.toFixed(2) || '-' }}</span>
              </div>
              <div class="param-item">
                <span class="param-label">粘性:</span>
                <span class="param-value">{{ row.viscosity?.toExponential(2) || '-' }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="创建时间" width="160" align="center">
          <template #default="{ row }">
            {{ formatDate(row.createdAt) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="280" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleView(row)">
              <el-icon><View /></el-icon>
              详情
            </el-button>
            <el-button
              v-if="canStart(row)"
              type="success"
              link
              size="small"
              @click="handleStart(row)"
            >
              <el-icon><VideoPlay /></el-icon>
              启动
            </el-button>
            <el-button
              v-if="canPause(row)"
              type="warning"
              link
              size="small"
              @click="handlePause(row)"
            >
              <el-icon><VideoPause /></el-icon>
              暂停
            </el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
            <el-dropdown @command="(cmd: string) => handleMoreAction(cmd, row)" trigger="click">
              <el-button type="primary" link size="small">
                更多
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="report">
                    <el-icon><Document /></el-icon>
                    生成报告
                  </el-dropdown-item>
                  <el-dropdown-item command="export">
                    <el-icon><Download /></el-icon>
                    导出数据
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="tableData.length === 0 && !loading" class="empty-state">
        <el-empty description="暂无模拟任务" :image-size="100">
          <template #image>
            <el-icon :size="80" color="#c0c4cc"><DataLine /></el-icon>
          </template>
          <el-button type="primary" @click="handleCreate">
            <el-icon><Plus /></el-icon>
            新建第一个任务
          </el-button>
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
        <p>确定要删除模拟任务 <strong>"{{ deleteTarget?.name }}"</strong> 吗？</p>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { simulationAPI, reportsAPI } from '@/api'
import type { Simulation } from '@/types'
import { SimulationStatus } from '@/types'
import dayjs from 'dayjs'
import {
  Search,
  Refresh,
  Plus,
  Operation,
  ArrowDown,
  VideoPlay,
  VideoPause,
  Delete,
  View,
  Document,
  Download,
  DataLine,
  Warning
} from '@element-plus/icons-vue'

const loading = ref(false)
const tableData = ref<Simulation[]>([])
const selectedIds = ref<number[]>([])
const deleteDialogVisible = ref(false)
const deleteTarget = ref<Simulation | null>(null)

const searchForm = reactive({
  name: '',
  status: '',
  dateRange: [] as string[]
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const statusOptions = [
  { value: SimulationStatus.PENDING_VERIFICATION, label: SimulationStatus.PENDING_VERIFICATION },
  { value: SimulationStatus.MESH_GENERATION, label: SimulationStatus.MESH_GENERATION },
  { value: SimulationStatus.INITIALIZATION, label: SimulationStatus.INITIALIZATION },
  { value: SimulationStatus.ITERATING, label: SimulationStatus.ITERATING },
  { value: SimulationStatus.COMPLETED, label: SimulationStatus.COMPLETED },
  { value: SimulationStatus.ERROR, label: SimulationStatus.ERROR },
  { value: SimulationStatus.NEEDS_REVIEW, label: SimulationStatus.NEEDS_REVIEW },
  { value: SimulationStatus.ADJUSTING, label: SimulationStatus.ADJUSTING }
]

const canBatchStart = computed(() => {
  return tableData.value
    .filter(row => selectedIds.value.includes(row.id))
    .every(row => canStart(row))
})

function getStatusType(status: string): string {
  const statusMap: Record<string, string> = {
    [SimulationStatus.PENDING_VERIFICATION]: 'warning',
    [SimulationStatus.MESH_GENERATION]: 'primary',
    [SimulationStatus.INITIALIZATION]: 'primary',
    [SimulationStatus.ITERATING]: 'primary',
    [SimulationStatus.COMPLETED]: 'success',
    [SimulationStatus.ERROR]: 'danger',
    [SimulationStatus.NEEDS_REVIEW]: 'warning',
    [SimulationStatus.ADJUSTING]: 'warning'
  }
  return statusMap[status] || 'info'
}

function getProgressStatus(status: string): '' | 'success' | 'exception' | 'warning' {
  if (status === SimulationStatus.COMPLETED) return 'success'
  if (status === SimulationStatus.ERROR) return 'exception'
  return ''
}

function canStart(row: Simulation): boolean {
  const startableStatuses = [
    SimulationStatus.PENDING_VERIFICATION,
    SimulationStatus.INITIALIZATION,
    SimulationStatus.ERROR,
    SimulationStatus.ADJUSTING,
    SimulationStatus.NEEDS_REVIEW
  ]
  return startableStatuses.includes(row.status as SimulationStatus)
}

function canPause(row: Simulation): boolean {
  return row.status === SimulationStatus.ITERATING ||
         row.status === SimulationStatus.MESH_GENERATION
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm')
}

async function fetchList() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: pagination.page,
      page_size: pagination.pageSize
    }

    if (searchForm.name) {
      params.name = searchForm.name
    }
    if (searchForm.status) {
      params.status = searchForm.status
    }
    if (searchForm.dateRange?.length === 2) {
      params.start_date = searchForm.dateRange[0]
      params.end_date = searchForm.dateRange[1]
    }

    const response = await simulationAPI.list(params)
    tableData.value = response.data.items || response.data || []
    pagination.total = response.data.total || tableData.value.length
  } catch (error) {
    console.error('Failed to fetch simulation list:', error)
    ElMessage.error('获取模拟任务列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  fetchList()
}

function handleReset() {
  searchForm.name = ''
  searchForm.status = ''
  searchForm.dateRange = []
  pagination.page = 1
  fetchList()
}

function handleSelectionChange(selection: Simulation[]) {
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

function handleCreate() {
  ElMessage.info('新建任务功能开发中...')
}

function handleView(row: Simulation) {
  ElMessage.info(`查看任务 #${row.id} 详情`)
}

async function handleStart(row: Simulation) {
  try {
    await simulationAPI.start(row.id)
    ElMessage.success(`任务 ${row.name} 已启动`)
    fetchList()
  } catch (error) {
    console.error('Failed to start simulation:', error)
    ElMessage.error('启动失败')
  }
}

function handlePause(row: Simulation) {
  ElMessage.info(`暂停任务 ${row.name} 功能开发中...`)
}

function handleDelete(row: Simulation) {
  deleteTarget.value = row
  deleteDialogVisible.value = true
}

async function confirmDelete() {
  if (!deleteTarget.value) return

  try {
    await simulationAPI.delete(deleteTarget.value.id)
    ElMessage.success('删除成功')
    deleteDialogVisible.value = false
    deleteTarget.value = null
    fetchList()
  } catch (error) {
    console.error('Failed to delete simulation:', error)
    ElMessage.error('删除失败')
  }
}

async function handleGenerateReport(row: Simulation) {
  try {
    await reportsAPI.generateReport(row.id)
    ElMessage.success(`报告生成中，请稍后在报告中心查看`)
  } catch (error) {
    console.error('Failed to generate report:', error)
    ElMessage.error('生成报告失败')
  }
}

function handleExport(row: Simulation) {
  ElMessage.info(`导出任务 ${row.name} 数据功能开发中...`)
}

function handleMoreAction(command: string, row: Simulation) {
  switch (command) {
    case 'report':
      handleGenerateReport(row)
      break
    case 'export':
      handleExport(row)
      break
  }
}

async function handleBatchAction(command: string) {
  if (selectedIds.value.length === 0) return

  switch (command) {
    case 'start':
      try {
        await Promise.all(selectedIds.value.map(id => simulationAPI.start(id)))
        ElMessage.success(`已批量启动 ${selectedIds.value.length} 个任务`)
        selectedIds.value = []
        fetchList()
      } catch (error) {
        console.error('Failed to batch start:', error)
        ElMessage.error('批量启动失败')
      }
      break
    case 'delete':
      ElMessageBox.confirm(
        `确定要删除选中的 ${selectedIds.value.length} 个任务吗？此操作不可恢复。`,
        '批量删除确认',
        {
          confirmButtonText: '确认删除',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(async () => {
        try {
          await Promise.all(selectedIds.value.map(id => simulationAPI.delete(id)))
          ElMessage.success('批量删除成功')
          selectedIds.value = []
          fetchList()
        } catch (error) {
          console.error('Failed to batch delete:', error)
          ElMessage.error('批量删除失败')
        }
      }).catch(() => {})
      break
  }
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped lang="css">
.simulation-list-container {
  padding: 24px;
}

.page-header {
  margin-bottom: 20px;
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

.filter-card {
  padding: 20px 24px;
  margin-bottom: 16px;
  background: #fff;
  border-radius: 12px;
}

.search-form {
  margin-bottom: 0;
}

.search-form .el-form-item {
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

.selected-count {
  margin-left: 8px;
  font-size: 13px;
  color: #909399;
}

.params-summary {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.param-item {
  font-size: 13px;
  color: #606266;
}

.param-label {
  color: #909399;
  margin-right: 4px;
}

.param-value {
  font-weight: 500;
  color: #303133;
}

.empty-state {
  padding: 60px 0;
  text-align: center;
}

.empty-state .el-empty__description {
  margin-bottom: 16px;
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

.danger-item {
  color: #f56c6c;
}

.danger-item:hover {
  color: #f56c6c !important;
}
</style>
