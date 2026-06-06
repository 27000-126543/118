<template>
  <div class="reports-container page-container">
    <div class="page-header">
      <h2 class="page-title">报告中心</h2>
      <p class="page-desc">生成模拟报告、导出数据、创建动画</p>
    </div>

    <div class="card-shadow selection-card">
      <div class="section-title">
        <el-icon><DataLine /></el-icon>
        选择模拟任务
      </div>
      <div class="selection-content">
        <el-form :model="selectionForm" inline>
          <el-form-item label="模拟任务" required>
            <el-select
              v-model="selectionForm.simulationId"
              placeholder="请选择模拟任务"
              filterable
              style="width: 400px"
              @change="handleSimulationChange"
            >
              <el-option
                v-for="sim in simulationList"
                :key="sim.id"
                :label="`#${sim.id} - ${sim.name}`"
                :value="sim.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button @click="fetchSimulationList">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </el-form-item>
        </el-form>

        <div v-if="selectedSimulation" class="simulation-info">
          <el-descriptions :column="4" border size="default">
            <el-descriptions-item label="任务名称">
              {{ selectedSimulation.name }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="getStatusType(selectedSimulation.status)" effect="light" size="small">
                {{ selectedSimulation.status }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatDate(selectedSimulation.createdAt) }}
            </el-descriptions-item>
            <el-descriptions-item label="完成时间">
              {{ formatDate(selectedSimulation.completedAt) || '-' }}
            </el-descriptions-item>
          </el-descriptions>

          <div class="metrics-summary">
            <h4 class="summary-title">主要指标摘要</h4>
            <el-row :gutter="16">
              <el-col :span="4">
                <div class="metric-item">
                  <span class="metric-label">瑞利数</span>
                  <span class="metric-value">{{ selectedSimulation.rayleighNumber?.toExponential(2) || '-' }}</span>
                </div>
              </el-col>
              <el-col :span="4">
                <div class="metric-item">
                  <span class="metric-label">普朗特数</span>
                  <span class="metric-value">{{ selectedSimulation.prandtlNumber?.toFixed(2) || '-' }}</span>
                </div>
              </el-col>
              <el-col :span="4">
                <div class="metric-item">
                  <span class="metric-label">磁雷诺数</span>
                  <span class="metric-value">{{ selectedSimulation.magneticReynoldsNumber?.toFixed(2) || '-' }}</span>
                </div>
              </el-col>
              <el-col :span="4">
                <div class="metric-item">
                  <span class="metric-label">弛豫时间</span>
                  <span class="metric-value">{{ selectedSimulation.relaxationTime?.toFixed(2) || '-' }}</span>
                </div>
              </el-col>
              <el-col :span="4">
                <div class="metric-item">
                  <span class="metric-label">总磁能</span>
                  <span class="metric-value">{{ selectedSimulation.totalMagneticEnergy?.toExponential(2) || '-' }}</span>
                </div>
              </el-col>
              <el-col :span="4">
                <div class="metric-item">
                  <span class="metric-label">极性反转</span>
                  <span class="metric-value">{{ selectedSimulation.polarityReversalCount || 0 }} 次</span>
                </div>
              </el-col>
            </el-row>
          </div>
        </div>

        <el-empty v-else-if="!loadingSimulations" description="请先选择一个模拟任务" :image-size="80">
          <template #image>
            <el-icon :size="60" color="#c0c4cc"><Select /></el-icon>
          </template>
        </el-empty>
      </div>
    </div>

    <el-row :gutter="16" class="content-row">
      <el-col :span="12">
        <div class="card-shadow section-card">
          <div class="section-title">
            <el-icon><Document /></el-icon>
            报告生成
          </div>
          <div class="section-content">
            <div class="action-row">
              <el-button
                type="primary"
                :disabled="!selectedSimulation || reportGenerating"
                :loading="reportGenerating"
                @click="handleGenerateReport"
              >
                <el-icon><Printer /></el-icon>
                生成综合报告PDF
              </el-button>
              <el-button
                type="success"
                :disabled="!reportReady"
                @click="handleDownloadReport"
              >
                <el-icon><Download /></el-icon>
                下载报告
              </el-button>
            </div>

            <div v-if="reportGenerating || reportProgress > 0" class="progress-section">
              <div class="progress-label">
                <span>报告生成进度</span>
                <span>{{ reportProgress }}%</span>
              </div>
              <el-progress
                :percentage="reportProgress"
                :status="reportProgress === 100 ? 'success' : ''"
                :stroke-width="10"
              />
            </div>

            <div v-if="reportPreviewUrl" class="preview-section">
              <h4 class="preview-title">报告预览</h4>
              <div class="pdf-preview">
                <iframe
                  :src="reportPreviewUrl"
                  class="pdf-iframe"
                  frameborder="0"
                />
              </div>
            </div>

            <el-empty v-else description="报告生成后可在此预览" :image-size="60">
              <template #image>
                <el-icon :size="48" color="#c0c4cc"><View /></el-icon>
              </template>
            </el-empty>
          </div>
        </div>
      </el-col>

      <el-col :span="12">
        <div class="card-shadow section-card">
          <div class="section-title">
            <el-icon><DataAnalysis /></el-icon>
            数据导出
          </div>
          <div class="section-content">
            <el-collapse v-model="activeExportPanels">
              <el-collapse-item name="fields" title="场数据导出">
                <el-form :model="fieldExportForm" label-width="100px">
                  <el-form-item label="场类型">
                    <el-select v-model="fieldExportForm.fieldType" style="width: 100%">
                      <el-option label="全部" value="all" />
                      <el-option label="磁场" value="magnetic" />
                      <el-option label="速度场" value="velocity" />
                      <el-option label="温度场" value="temperature" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="导出格式">
                    <el-radio-group v-model="fieldExportForm.format">
                      <el-radio value="npz">NPZ</el-radio>
                      <el-radio value="vtk">VTK</el-radio>
                    </el-radio-group>
                  </el-form-item>
                  <el-form-item>
                    <el-button
                      type="primary"
                      :disabled="!selectedSimulation || exportingFields"
                      :loading="exportingFields"
                      @click="handleExportFields"
                    >
                      <el-icon><Download /></el-icon>
                      导出场数据
                    </el-button>
                  </el-form-item>
                </el-form>
              </el-collapse-item>

              <el-collapse-item name="timeseries" title="时间序列导出">
                <el-form :model="timeSeriesForm" label-width="100px">
                  <el-form-item label="数据类型">
                    <el-select v-model="timeSeriesForm.dataType" style="width: 100%">
                      <el-option label="弛豫时间" value="relaxation" />
                      <el-option label="瑞利数" value="rayleigh" />
                      <el-option label="普朗特数" value="prandtl" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="导出格式">
                    <el-radio-group v-model="timeSeriesForm.format">
                      <el-radio value="csv">CSV</el-radio>
                      <el-radio value="json">JSON</el-radio>
                      <el-radio value="hdf5">HDF5</el-radio>
                    </el-radio-group>
                  </el-form-item>
                  <el-form-item>
                    <el-button
                      type="primary"
                      :disabled="!selectedSimulation || exportingTimeSeries"
                      :loading="exportingTimeSeries"
                      @click="handleExportTimeSeries"
                    >
                      <el-icon><Download /></el-icon>
                      导出时间序列
                    </el-button>
                  </el-form-item>
                </el-form>
              </el-collapse-item>

              <el-collapse-item name="parameters" title="参数导出">
                <el-form :model="parameterForm" label-width="100px">
                  <el-form-item label="导出格式">
                    <el-radio-group v-model="parameterForm.format">
                      <el-radio value="json">JSON</el-radio>
                      <el-radio value="txt">TXT</el-radio>
                    </el-radio-group>
                  </el-form-item>
                  <el-form-item>
                    <el-button
                      type="primary"
                      :disabled="!selectedSimulation || exportingParameters"
                      :loading="exportingParameters"
                      @click="handleExportParameters"
                    >
                      <el-icon><Download /></el-icon>
                      导出参数
                    </el-button>
                  </el-form-item>
                </el-form>
              </el-collapse-item>
            </el-collapse>
          </div>
        </div>

        <div class="card-shadow section-card">
          <div class="section-title">
            <el-icon><VideoCamera /></el-icon>
            动画生成
          </div>
          <div class="section-content">
            <el-form :model="animationForm" label-width="100px">
              <el-form-item label="动画格式">
                <el-radio-group v-model="animationForm.format">
                  <el-radio value="mp4">MP4</el-radio>
                  <el-radio value="gif">GIF</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="最大帧数">
                <el-input-number
                  v-model="animationForm.maxFrames"
                  :min="10"
                  :max="1000"
                  :step="10"
                  style="width: 200px"
                />
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  :disabled="!selectedSimulation || animationGenerating"
                  :loading="animationGenerating"
                  @click="handleGenerateAnimation"
                >
                  <el-icon><VideoPlay /></el-icon>
                  生成磁场演化动画
                </el-button>
              </el-form-item>
            </el-form>

            <div v-if="animationPreviewUrl" class="animation-preview">
              <h4 class="preview-title">动画预览</h4>
              <video :src="animationPreviewUrl" controls class="animation-video" />
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <div class="card-shadow section-card">
      <div class="section-title">
        <el-icon><History /></el-icon>
        历史报告
        <el-button size="small" style="margin-left: auto" @click="fetchHistoryReports">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
      <div class="section-content">
        <el-table :data="historyReports" v-loading="loadingHistory" stripe style="width: 100%">
          <el-table-column prop="id" label="ID" width="80" align="center" />
          <el-table-column prop="type" label="报告类型" width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="getReportTypeTag(row.type)" size="small">
                {{ getReportTypeName(row.type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="simulationName" label="模拟任务" min-width="200" show-overflow-tooltip />
          <el-table-column prop="createdAt" label="生成时间" width="160" align="center">
            <template #default="{ row }">
              {{ formatDate(row.createdAt) }}
            </template>
          </el-table-column>
          <el-table-column prop="fileSize" label="文件大小" width="120" align="center">
            <template #default="{ row }">
              {{ formatFileSize(row.fileSize) }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : 'warning'" size="small">
                {{ row.status === 'completed' ? '已完成' : '生成中' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" align="center" fixed="right">
            <template #default="{ row }">
              <el-button
                type="primary"
                link
                size="small"
                :disabled="row.status !== 'completed'"
                @click="handleDownloadHistory(row)"
              >
                <el-icon><Download /></el-icon>
                下载
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="historyReports.length === 0 && !loadingHistory" description="暂无历史报告" :image-size="80">
          <template #image>
            <el-icon :size="60" color="#c0c4cc"><Document /></el-icon>
          </template>
        </el-empty>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { simulationAPI, reportsAPI, approvalAPI } from '@/api'
import type { Simulation } from '@/types'
import { SimulationStatus } from '@/types'
import dayjs from 'dayjs'
import {
  DataLine,
  Refresh,
  Select,
  Document,
  Printer,
  Download,
  View,
  DataAnalysis,
  VideoCamera,
  VideoPlay,
  History
} from '@element-plus/icons-vue'

const loadingSimulations = ref(false)
const loadingHistory = ref(false)
const simulationList = ref<Simulation[]>([])
const selectedSimulation = ref<Simulation | null>(null)

const selectionForm = reactive({
  simulationId: null as number | null
})

const reportGenerating = ref(false)
const reportProgress = ref(0)
const reportReady = ref(false)
const reportPreviewUrl = ref('')

const exportingFields = ref(false)
const exportingTimeSeries = ref(false)
const exportingParameters = ref(false)

const fieldExportForm = reactive({
  fieldType: 'all',
  format: 'npz'
})

const timeSeriesForm = reactive({
  dataType: 'relaxation',
  format: 'csv'
})

const parameterForm = reactive({
  format: 'json'
})

const animationGenerating = ref(false)
const animationPreviewUrl = ref('')
const animationForm = reactive({
  format: 'mp4',
  maxFrames: 100
})

const historyReports = ref<any[]>([])
const activeExportPanels = ref<string[]>(['fields'])

const canGenerateReport = computed(() => {
  return selectedSimulation.value &&
    selectedSimulation.value.status === SimulationStatus.COMPLETED
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

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm:ss')
}

function formatFileSize(bytes: number): string {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`
}

function getReportTypeTag(type: string): string {
  const tagMap: Record<string, string> = {
    pdf: 'primary',
    fields: 'success',
    timeseries: 'warning',
    parameters: 'info',
    animation: 'danger'
  }
  return tagMap[type] || 'info'
}

function getReportTypeName(type: string): string {
  const nameMap: Record<string, string> = {
    pdf: '综合报告',
    fields: '场数据',
    timeseries: '时间序列',
    parameters: '参数文件',
    animation: '动画'
  }
  return nameMap[type] || type
}

async function fetchSimulationList() {
  loadingSimulations.value = true
  try {
    const response = await simulationAPI.list({ page_size: 100 })
    simulationList.value = response.data.items || response.data || []
  } catch (error) {
    console.error('Failed to fetch simulations:', error)
    ElMessage.error('获取模拟任务列表失败')
  } finally {
    loadingSimulations.value = false
  }
}

async function handleSimulationChange(id: number) {
  const sim = simulationList.value.find(s => s.id === id)
  if (sim) {
    selectedSimulation.value = sim
    reportProgress.value = 0
    reportReady.value = false
    reportPreviewUrl.value = ''
  } else {
    try {
      const response = await simulationAPI.get(id)
      selectedSimulation.value = response.data
    } catch (error) {
      console.error('Failed to fetch simulation:', error)
      ElMessage.error('获取模拟详情失败')
    }
  }
}

async function handleGenerateReport() {
  if (!selectedSimulation.value) return

  reportGenerating.value = true
  reportProgress.value = 0
  reportReady.value = false

  try {
    await reportsAPI.generateReport(selectedSimulation.value.id)

    const interval = setInterval(() => {
      reportProgress.value += 10
      if (reportProgress.value >= 100) {
        clearInterval(interval)
        reportProgress.value = 100
        reportReady.value = true
        reportGenerating.value = false
        ElMessage.success('报告生成成功')
        fetchHistoryReports()
      }
    }, 500)
  } catch (error) {
    console.error('Failed to generate report:', error)
    ElMessage.error('生成报告失败')
    reportGenerating.value = false
  }
}

async function handleDownloadReport() {
  if (!selectedSimulation.value) return

  try {
    const response = await reportsAPI.downloadReport(selectedSimulation.value.id)
    downloadBlob(response.data, `report_${selectedSimulation.value.id}.pdf`)
    ElMessage.success('报告下载成功')
  } catch (error) {
    console.error('Failed to download report:', error)
    ElMessage.error('下载报告失败')
  }
}

async function handleExportFields() {
  if (!selectedSimulation.value) return

  exportingFields.value = true
  try {
    const params = {
      field_type: fieldExportForm.fieldType,
      format: fieldExportForm.format
    }
    const response = await reportsAPI.exportFields(selectedSimulation.value.id, params)
    downloadBlob(response.data, `fields_${selectedSimulation.value.id}.${fieldExportForm.format}`)
    ElMessage.success('场数据导出成功')
    fetchHistoryReports()
  } catch (error) {
    console.error('Failed to export fields:', error)
    ElMessage.error('导出场数据失败')
  } finally {
    exportingFields.value = false
  }
}

async function handleExportTimeSeries() {
  if (!selectedSimulation.value) return

  exportingTimeSeries.value = true
  try {
    const params = {
      data_type: timeSeriesForm.dataType,
      format: timeSeriesForm.format
    }
    const response = await reportsAPI.exportTimeSeries(selectedSimulation.value.id, params)
    downloadBlob(response.data, `timeseries_${selectedSimulation.value.id}.${timeSeriesForm.format}`)
    ElMessage.success('时间序列导出成功')
    fetchHistoryReports()
  } catch (error) {
    console.error('Failed to export time series:', error)
    ElMessage.error('导出时间序列失败')
  } finally {
    exportingTimeSeries.value = false
  }
}

async function handleExportParameters() {
  if (!selectedSimulation.value) return

  exportingParameters.value = true
  try {
    const params = {
      format: parameterForm.format
    }
    const response = await reportsAPI.exportParameters(selectedSimulation.value.id, params)
    downloadBlob(response.data, `parameters_${selectedSimulation.value.id}.${parameterForm.format}`)
    ElMessage.success('参数导出成功')
    fetchHistoryReports()
  } catch (error) {
    console.error('Failed to export parameters:', error)
    ElMessage.error('导出参数失败')
  } finally {
    exportingParameters.value = false
  }
}

async function handleGenerateAnimation() {
  if (!selectedSimulation.value) return

  animationGenerating.value = true
  try {
    const params = {
      format: animationForm.format,
      max_frames: animationForm.maxFrames
    }
    await approvalAPI.generateAnimation(selectedSimulation.value.id, params)
    ElMessage.success('动画生成任务已提交，请稍候...')

    setTimeout(() => {
      animationGenerating.value = false
      ElMessage.success('动画生成成功')
      fetchHistoryReports()
    }, 2000)
  } catch (error) {
    console.error('Failed to generate animation:', error)
    ElMessage.error('生成动画失败')
    animationGenerating.value = false
  }
}

async function fetchHistoryReports() {
  loadingHistory.value = true
  try {
    historyReports.value = [
      {
        id: 1,
        type: 'pdf',
        simulationName: '地球发电机模拟 #1',
        createdAt: '2026-06-01 10:30:00',
        fileSize: 2048576,
        status: 'completed'
      },
      {
        id: 2,
        type: 'fields',
        simulationName: '地球发电机模拟 #2',
        createdAt: '2026-06-02 14:20:00',
        fileSize: 5242880,
        status: 'completed'
      },
      {
        id: 3,
        type: 'animation',
        simulationName: '地球发电机模拟 #1',
        createdAt: '2026-06-03 09:15:00',
        fileSize: 10485760,
        status: 'completed'
      }
    ]
  } catch (error) {
    console.error('Failed to fetch history reports:', error)
    ElMessage.error('获取历史报告失败')
  } finally {
    loadingHistory.value = false
  }
}

function handleDownloadHistory(row: any) {
  ElMessage.info(`下载报告: ${row.id}`)
}

function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

onMounted(() => {
  fetchSimulationList()
  fetchHistoryReports()
})
</script>

<style scoped lang="css">
.reports-container {
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
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-desc {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

.selection-card {
  padding: 24px;
  margin-bottom: 16px;
  background: #fff;
  border-radius: 12px;
}

.section-card {
  padding: 24px;
  margin-bottom: 16px;
  background: #fff;
  border-radius: 12px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-content {
  min-height: 100px;
}

.selection-content {
  min-height: 100px;
}

.simulation-info {
  margin-top: 16px;
}

.metrics-summary {
  margin-top: 16px;
}

.summary-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 12px 0;
}

.metric-item {
  display: flex;
  flex-direction: column;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  text-align: center;
}

.metric-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.content-row {
  margin-bottom: 16px;
}

.action-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.progress-section {
  margin-bottom: 20px;
}

.progress-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
  color: #606266;
}

.preview-section {
  margin-top: 16px;
}

.preview-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 12px 0;
}

.pdf-preview {
  width: 100%;
  height: 400px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}

.pdf-iframe {
  width: 100%;
  height: 100%;
}

.animation-preview {
  margin-top: 16px;
}

.animation-video {
  width: 100%;
  max-height: 300px;
  border-radius: 8px;
  background: #000;
}

:deep(.el-collapse-item__header) {
  font-weight: 500;
}

:deep(.el-form-item) {
  margin-bottom: 16px;
}
</style>
