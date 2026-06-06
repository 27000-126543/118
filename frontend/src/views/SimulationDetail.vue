<template>
  <div class="simulation-detail page-container">
    <el-page-header @back="goBack" content="模拟详情">
      <template #extra>
        <el-tag :type="getStatusType(simulation?.status)" size="large">
          {{ simulation?.status }}
        </el-tag>
      </template>
    </el-page-header>

    <div v-loading="loading" class="detail-content">
      <el-card class="info-card card-shadow" v-if="simulation">
        <div class="info-header">
          <div class="info-main">
            <h2 class="simulation-name">{{ simulation.name }}</h2>
            <div class="info-meta">
              <span class="info-item">
                <el-icon><InfoFilled /></el-icon>
                ID: {{ simulation.id }}
              </span>
              <span class="info-item">
                <el-icon><User /></el-icon>
                创建人: {{ simulation.ownerId }}
              </span>
              <span class="info-item">
                <el-icon><Clock /></el-icon>
                创建时间: {{ formatDate(simulation.createdAt) }}
              </span>
              <span v-if="simulation.startedAt" class="info-item">
                <el-icon><VideoPlay /></el-icon>
                开始时间: {{ formatDate(simulation.startedAt) }}
              </span>
            </div>
            <p class="simulation-desc" v-if="simulation.description">
              {{ simulation.description }}
            </p>
          </div>
          <div class="info-actions">
            <el-button type="primary" :icon="VideoPlay" :disabled="!canStart" @click="handleStart">
              启动
            </el-button>
            <el-button type="warning" :icon="VideoPause" :disabled="!canPause" @click="handlePause">
              暂停
            </el-button>
            <el-button type="info" :icon="RefreshRight" :disabled="!canRestart" @click="handleRestart">
              重新开始
            </el-button>
            <el-button type="success" :icon="Document" @click="handleGenerateReport">
              生成报告
            </el-button>
            <el-dropdown @command="handleExport">
              <el-button type="primary" :icon="Download">
                导出 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="fields">导出场数据</el-dropdown-item>
                  <el-dropdown-item command="timeseries">导出时间序列</el-dropdown-item>
                  <el-dropdown-item command="parameters">导出参数</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>

        <div class="progress-section">
          <div class="progress-header">
            <span class="progress-label">计算进度</span>
            <span class="progress-value">
              {{ simulation.currentIteration }} / {{ simulation.maxIterations }} 迭代
              ({{ simulation.progress.toFixed(1) }}%)
            </span>
          </div>
          <el-progress
            :percentage="Math.round(simulation.progress)"
            :status="getProgressStatus(simulation.status)"
            :stroke-width="12"
          />
        </div>
      </el-card>

      <el-tabs v-model="activeTab" class="detail-tabs">
        <el-tab-pane label="概览" name="overview">
          <el-row :gutter="24">
            <el-col :span="24">
              <el-card class="card-shadow params-card">
                <template #header>
                  <div class="card-header">
                    <h3 class="section-title">参数概览</h3>
                    <el-tag type="info">输入参数</el-tag>
                  </div>
                </template>
                <el-row :gutter="24">
                  <el-col :span="6" v-for="param in inputParams" :key="param.key">
                    <div class="param-item">
                      <div class="param-label">{{ param.label }}</div>
                      <div class="param-value">{{ formatValue(simulation[param.key], param.unit) }}</div>
                    </div>
                  </el-col>
                </el-row>
              </el-card>
            </el-col>

            <el-col :span="24" style="margin-top: 24px">
              <el-card class="card-shadow params-card">
                <template #header>
                  <div class="card-header">
                    <h3 class="section-title">无量纲数</h3>
                    <el-tag type="success">计算结果</el-tag>
                  </div>
                </template>
                <el-row :gutter="24">
                  <el-col :span="6" v-for="param in dimensionlessParams" :key="param.key">
                    <div class="param-item">
                      <div class="param-label">{{ param.label }}</div>
                      <div class="param-value">{{ formatValue(simulation[param.key], param.unit) }}</div>
                    </div>
                  </el-col>
                </el-row>
              </el-card>
            </el-col>

            <el-col :span="24" style="margin-top: 24px">
              <el-card class="card-shadow">
                <template #header>
                  <div class="card-header">
                    <h3 class="section-title">极性反转事件</h3>
                    <el-tag type="warning" v-if="simulation.hasPolarityReversal">
                      {{ simulation.polarityReversalCount }} 次反转
                    </el-tag>
                  </div>
                </template>
                <div class="timeline-container" v-if="polarityReversals.length > 0">
                  <el-timeline>
                    <el-timeline-item
                      v-for="(reversal, index) in polarityReversals"
                      :key="reversal.id"
                      :timestamp="`迭代 ${reversal.startIteration} - ${reversal.endIteration || '进行中'}`"
                      placement="top"
                    >
                      <el-card shadow="hover">
                        <h4 class="reversal-title">
                          极性反转 #{{ index + 1 }}
                          <el-tag size="small" :type="getReversalType(reversal.reversalType)">
                            {{ reversal.reversalType }}
                          </el-tag>
                        </h4>
                        <div class="reversal-info">
                          <span>开始时间: {{ reversal.startTime.toFixed(2) }} kyr</span>
                          <span v-if="reversal.endTime">结束时间: {{ reversal.endTime.toFixed(2) }} kyr</span>
                          <span v-if="reversal.duration">持续时间: {{ reversal.duration.toFixed(2) }} kyr</span>
                        </div>
                      </el-card>
                    </el-timeline-item>
                  </el-timeline>
                </div>
                <el-empty v-else description="暂无极性反转事件" :image-size="80" />
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>

        <el-tab-pane label="实时监控" name="monitoring">
          <div class="ws-status" :class="wsConnected ? 'connected' : 'disconnected'">
            <el-icon><Connection /></el-icon>
            {{ wsConnected ? '实时连接已建立' : '实时连接已断开' }}
          </div>

          <el-row :gutter="24">
            <el-col :span="12">
              <el-card class="card-shadow chart-card">
                <template #header>
                  <h3 class="section-title">磁能/动能演化</h3>
                </template>
                <div ref="energyChartRef" class="chart"></div>
              </el-card>
            </el-col>

            <el-col :span="12">
              <el-card class="card-shadow chart-card">
                <template #header>
                  <h3 class="section-title">偶极矩/倾斜角演化</h3>
                </template>
                <div ref="dipoleChartRef" class="chart"></div>
              </el-card>
            </el-col>

            <el-col :span="24" style="margin-top: 24px">
              <el-card class="card-shadow chart-card">
                <template #header>
                  <h3 class="section-title">磁雷诺数演化</h3>
                </template>
                <div ref="reynoldsChartRef" class="chart"></div>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>

        <el-tab-pane label="场可视化" name="visualization">
          <el-card class="card-shadow">
            <el-empty description="场可视化功能开发中..." :image-size="120">
              <template #description>
                <p>该功能将展示磁场、速度场和温度场的三维可视化</p>
              </template>
            </el-empty>
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="历史数据" name="history">
          <el-card class="card-shadow">
            <template #header>
              <div class="card-header">
                <h3 class="section-title">时间序列数据</h3>
                <el-button type="primary" link :icon="Download" @click="handleExport('timeseries')">
                  导出数据
                </el-button>
              </div>
            </template>
            <el-table :data="timeSeriesData" style="width: 100%" max-height="600">
              <el-table-column prop="timeStep" label="时间步" width="80" fixed />
              <el-table-column prop="simulationTime" label="模拟时间 (kyr)" width="140">
                <template #default="{ row }">
                  {{ row.simulationTime?.toFixed(4) }}
                </template>
              </el-table-column>
              <el-table-column prop="magneticEnergy" label="磁能">
                <template #default="{ row }">
                  {{ row.magneticEnergy?.toExponential(4) }}
                </template>
              </el-table-column>
              <el-table-column prop="kineticEnergy" label="动能">
                <template #default="{ row }">
                  {{ row.kineticEnergy?.toExponential(4) }}
                </template>
              </el-table-column>
              <el-table-column prop="dipoleMoment" label="偶极矩">
                <template #default="{ row }">
                  {{ row.dipoleMoment?.toFixed(4) }}
                </template>
              </el-table-column>
              <el-table-column prop="dipoleTilt" label="倾斜角 (°)">
                <template #default="{ row }">
                  {{ row.dipoleTilt?.toFixed(2) }}
                </template>
              </el-table-column>
              <el-table-column prop="magneticReynolds" label="磁雷诺数">
                <template #default="{ row }">
                  {{ row.magneticReynolds?.toFixed(2) }}
                </template>
              </el-table-column>
              <el-table-column prop="innerCoreSymmetry" label="内核对称性">
                <template #default="{ row }">
                  {{ row.innerCoreSymmetry?.toFixed(4) }}
                </template>
              </el-table-column>
              <el-table-column prop="temperatureAnomaly" label="温度异常">
                <template #default="{ row }">
                  {{ row.temperatureAnomaly?.toExponential(4) }}
                </template>
              </el-table-column>
              <el-table-column prop="velocityMagnitude" label="速度大小">
                <template #default="{ row }">
                  {{ row.velocityMagnitude?.toExponential(4) }}
                </template>
              </el-table-column>
              <el-table-column label="记录时间" width="160">
                <template #default="{ row }">
                  {{ formatDate(row.createdAt) }}
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="参数调整记录" name="adjustments">
          <el-card class="card-shadow">
            <template #header>
              <h3 class="section-title">参数调整历史</h3>
            </template>
            <el-table :data="adjustmentLogs" style="width: 100%">
              <el-table-column prop="id" label="ID" width="80" />
              <el-table-column label="调整人" width="120">
                <template #default="{ row }">
                  用户 #{{ row.reviewerId }}
                </template>
              </el-table-column>
              <el-table-column label="CMB 热通量" width="180">
                <template #default="{ row }">
                  <span v-if="row.oldCmbHeatFlux !== null && row.newCmbHeatFlux !== null">
                    {{ row.oldCmbHeatFlux?.toFixed(2) }} → {{ row.newCmbHeatFlux?.toFixed(2) }}
                  </span>
                  <span v-else class="no-change">-</span>
                </template>
              </el-table-column>
              <el-table-column label="内核半径" width="180">
                <template #default="{ row }">
                  <span v-if="row.oldInnerCoreRadius !== null && row.newInnerCoreRadius !== null">
                    {{ row.oldInnerCoreRadius?.toFixed(3) }} → {{ row.newInnerCoreRadius?.toFixed(3) }}
                  </span>
                  <span v-else class="no-change">-</span>
                </template>
              </el-table-column>
              <el-table-column label="黏度" width="180">
                <template #default="{ row }">
                  <span v-if="row.oldViscosity !== null && row.newViscosity !== null">
                    {{ row.oldViscosity?.toExponential(2) }} → {{ row.newViscosity?.toExponential(2) }}
                  </span>
                  <span v-else class="no-change">-</span>
                </template>
              </el-table-column>
              <el-table-column prop="reason" label="调整原因" min-width="200" />
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.approved ? 'success' : 'warning'" size="small">
                    {{ row.approved ? '已批准' : '待审批' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="调整时间" width="160">
                <template #default="{ row }">
                  {{ formatDate(row.createdAt) }}
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-if="adjustmentLogs.length === 0" description="暂无参数调整记录" />
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="审批记录" name="approvals">
          <el-card class="card-shadow">
            <template #header>
              <div class="card-header">
                <h3 class="section-title">审批记录</h3>
                <el-tag :type="getApprovalType(simulation?.approvalStatus)">
                  {{ simulation?.approvalStatus }}
                </el-tag>
              </div>
            </template>
            <el-table :data="approvalRecords" style="width: 100%">
              <el-table-column prop="id" label="ID" width="80" />
              <el-table-column label="审批人" width="120">
                <template #default="{ row }">
                  用户 #{{ row.approverId }}
                </template>
              </el-table-column>
              <el-table-column prop="level" label="审批级别" width="120">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.level === 'professor' ? 'danger' : 'warning'">
                    {{ row.level === 'professor' ? '教授' : '博士后' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="comments" label="审批意见" min-width="200" />
              <el-table-column label="结果" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.approved ? 'success' : 'danger'" size="small">
                    {{ row.approved ? '通过' : '拒绝' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="审批时间" width="160">
                <template #default="{ row }">
                  {{ formatDate(row.createdAt) }}
                </template>
              </el-table-column>
            </el-table>
            <el-empty v-if="approvalRecords.length === 0" description="暂无审批记录" />
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  simulationAPI, reportsAPI, approvalAPI
} from '@/api'
import type {
  Simulation, TimeSeriesData, PolarityReversal, Approval, ParameterAdjustment
} from '@/types'
import { SimulationStatus, ApprovalStatus } from '@/types'
import {
  InfoFilled, User, Clock, VideoPlay, VideoPause, RefreshRight,
  Document, Download, ArrowDown, Connection
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()

const simulationId = computed(() => Number(route.params.id))

const loading = ref(true)
const activeTab = ref('overview')
const simulation = ref<Simulation | null>(null)
const timeSeriesData = ref<TimeSeriesData[]>([])
const polarityReversals = ref<PolarityReversal[]>([])
const adjustmentLogs = ref<ParameterAdjustment[]>([])
const approvalRecords = ref<Approval[]>([])
const wsConnected = ref(false)

const energyChartRef = ref<HTMLElement>()
const dipoleChartRef = ref<HTMLElement>()
const dipoleChartInstance = ref<echarts.ECharts | null>(null)
const reynoldsChartRef = ref<HTMLElement>()
const reynoldsChartInstance = ref<echarts.ECharts | null>(null)

let energyChartInstance: echarts.ECharts | null = null
let ws: WebSocket | null = null
let reconnectTimer: number | null = null

const inputParams = [
  { key: 'coreRadius', label: '核心半径', unit: 'm' },
  { key: 'viscosity', label: '黏度', unit: 'm²/s' },
  { key: 'thermalExpansion', label: '热膨胀系数', unit: 'K⁻¹' },
  { key: 'icbHeatFlux', label: 'ICB 热通量', unit: 'W/m²' },
  { key: 'cmbHeatFlux', label: 'CMB 热通量', unit: 'W/m²' },
  { key: 'innerCoreRadius', label: '内核半径', unit: 'm' },
  { key: 'maxIterations', label: '最大迭代次数', unit: '' },
  { key: 'relaxationTime', label: '弛豫时间', unit: 'kyr' }
]

const dimensionlessParams = [
  { key: 'rayleighNumber', label: '瑞利数 (Ra)', unit: '' },
  { key: 'prandtlNumber', label: '普朗特数 (Pr)', unit: '' },
  { key: 'magneticReynoldsNumber', label: '磁雷诺数 (Rm)', unit: '' },
  { key: 'ekmanNumber', label: '埃克曼数 (Ek)', unit: '' },
  { key: 'rossbyNumber', label: '罗斯比数 (Ro)', unit: '' },
  { key: 'magneticEnergyGenerationEfficiency', label: '磁能生成效率', unit: '' }
]

const canStart = computed(() => {
  const status = simulation.value?.status
  return status === SimulationStatus.PENDING_VERIFICATION ||
         status === SimulationStatus.MESH_GENERATION ||
         status === SimulationStatus.INITIALIZATION ||
         status === SimulationStatus.ERROR ||
         status === SimulationStatus.COMPLETED
})

const canPause = computed(() => {
  return simulation.value?.status === SimulationStatus.ITERATING
})

const canRestart = computed(() => {
  const status = simulation.value?.status
  return status === SimulationStatus.COMPLETED ||
         status === SimulationStatus.ERROR ||
         status === SimulationStatus.NEEDS_REVIEW
})

function getStatusType(status: string | undefined) {
  if (!status) return 'info'
  const map: Record<string, any> = {
    [SimulationStatus.PENDING_VERIFICATION]: 'warning',
    [SimulationStatus.MESH_GENERATION]: 'info',
    [SimulationStatus.INITIALIZATION]: 'info',
    [SimulationStatus.ITERATING]: 'primary',
    [SimulationStatus.COMPLETED]: 'success',
    [SimulationStatus.ERROR]: 'danger',
    [SimulationStatus.NEEDS_REVIEW]: 'warning',
    [SimulationStatus.ADJUSTING]: 'warning'
  }
  return map[status] || 'info'
}

function getProgressStatus(status: string | undefined) {
  if (!status) return undefined
  if (status === SimulationStatus.ERROR) return 'exception'
  if (status === SimulationStatus.COMPLETED) return 'success'
  return undefined
}

function getReversalType(type: string) {
  const map: Record<string, any> = {
    'full': 'success',
    'partial': 'warning',
    'attempt': 'info'
  }
  return map[type] || 'info'
}

function getApprovalType(status: string | undefined) {
  if (!status) return 'info'
  const map: Record<string, any> = {
    [ApprovalStatus.PENDING]: 'warning',
    [ApprovalStatus.POSTDOC_APPROVED]: 'primary',
    [ApprovalStatus.PROFESSOR_APPROVED]: 'success',
    [ApprovalStatus.REJECTED]: 'danger'
  }
  return map[status] || 'info'
}

function formatDate(dateStr: string | undefined) {
  if (!dateStr) return '-'
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm:ss')
}

function formatValue(value: any, unit: string) {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'number') {
    if (Math.abs(value) >= 1e6 || (Math.abs(value) < 0.001 && value !== 0)) {
      return `${value.toExponential(4)} ${unit}`.trim()
    }
    return `${value.toFixed(4)} ${unit}`.trim()
  }
  return `${value} ${unit}`.trim()
}

function goBack() {
  router.push('/simulations')
}

async function fetchSimulationDetail() {
  try {
    const res = await simulationAPI.get(simulationId.value)
    simulation.value = res.data
  } catch (error) {
    console.error('Failed to fetch simulation detail:', error)
    ElMessage.error('获取模拟详情失败')
  }
}

async function fetchTimeSeries() {
  try {
    const res = await simulationAPI.getTimeSeries(simulationId.value)
    timeSeriesData.value = res.data
  } catch (error) {
    console.error('Failed to fetch time series:', error)
  }
}

async function fetchPolarityReversals() {
  try {
    const res = await simulationAPI.getPolarityReversals(simulationId.value)
    polarityReversals.value = res.data
  } catch (error) {
    console.error('Failed to fetch polarity reversals:', error)
  }
}

async function fetchAdjustmentLogs() {
  try {
    const res = await simulationAPI.getAdjustmentLogs(simulationId.value)
    adjustmentLogs.value = res.data
  } catch (error) {
    console.error('Failed to fetch adjustment logs:', error)
  }
}

async function fetchApprovalRecords() {
  try {
    const res = await approvalAPI.getSimulationApprovals(simulationId.value)
    approvalRecords.value = res.data
  } catch (error) {
    console.error('Failed to fetch approval records:', error)
  }
}

async function handleStart() {
  try {
    await ElMessageBox.confirm('确定要启动该模拟任务吗？', '确认启动', {
      type: 'warning'
    })
    await simulationAPI.start(simulationId.value)
    ElMessage.success('模拟任务已启动')
    fetchSimulationDetail()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Failed to start simulation:', error)
      ElMessage.error('启动失败')
    }
  }
}

async function handlePause() {
  try {
    await ElMessageBox.confirm('确定要暂停该模拟任务吗？', '确认暂停', {
      type: 'warning'
    })
    await simulationAPI.update(simulationId.value, { status: SimulationStatus.NEEDS_REVIEW })
    ElMessage.success('模拟任务已暂停')
    fetchSimulationDetail()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Failed to pause simulation:', error)
      ElMessage.error('暂停失败')
    }
  }
}

async function handleRestart() {
  try {
    await ElMessageBox.confirm('确定要重新开始该模拟任务吗？这将重置所有进度。', '确认重启', {
      type: 'warning'
    })
    await simulationAPI.restartAdjusted(simulationId.value)
    ElMessage.success('模拟任务已重新启动')
    fetchSimulationDetail()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Failed to restart simulation:', error)
      ElMessage.error('重启失败')
    }
  }
}

async function handleGenerateReport() {
  try {
    await reportsAPI.generateReport(simulationId.value)
    ElMessage.success('报告生成中，请稍后...')
  } catch (error) {
    console.error('Failed to generate report:', error)
    ElMessage.error('生成报告失败')
  }
}

async function handleExport(command: string) {
  try {
    let response: any
    let filename = ''
    switch (command) {
      case 'fields':
        response = await reportsAPI.exportFields(simulationId.value)
        filename = `fields_${simulationId.value}.nc`
        break
      case 'timeseries':
        response = await reportsAPI.exportTimeSeries(simulationId.value)
        filename = `timeseries_${simulationId.value}.csv`
        break
      case 'parameters':
        response = await reportsAPI.exportParameters(simulationId.value)
        filename = `parameters_${simulationId.value}.json`
        break
    }
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    console.error('Failed to export:', error)
    ElMessage.error('导出失败')
  }
}

function initCharts() {
  if (energyChartRef.value) {
    energyChartInstance = echarts.init(energyChartRef.value)
    updateEnergyChart()
  }

  if (dipoleChartRef.value) {
    dipoleChartInstance.value = echarts.init(dipoleChartRef.value)
    updateDipoleChart()
  }

  if (reynoldsChartRef.value) {
    reynoldsChartInstance.value = echarts.init(reynoldsChartRef.value)
    updateReynoldsChart()
  }
}

function updateEnergyChart() {
  if (!energyChartInstance) return

  const iterations = timeSeriesData.value.map(d => d.timeStep)
  const magneticEnergy = timeSeriesData.value.map(d => d.magneticEnergy)
  const kineticEnergy = timeSeriesData.value.map(d => d.kineticEnergy)

  energyChartInstance.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['磁能', '动能'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: iterations,
      name: '时间步',
      axisLabel: { rotate: 45 }
    },
    yAxis: {
      type: 'value',
      name: '能量',
      scale: true
    },
    series: [
      {
        name: '磁能',
        type: 'line',
        data: magneticEnergy,
        smooth: true,
        showSymbol: false,
        itemStyle: { color: '#f56c6c' },
        areaStyle: { color: 'rgba(245, 108, 108, 0.1)' }
      },
      {
        name: '动能',
        type: 'line',
        data: kineticEnergy,
        smooth: true,
        showSymbol: false,
        itemStyle: { color: '#409eff' },
        areaStyle: { color: 'rgba(64, 158, 255, 0.1)' }
      }
    ]
  })
}

function updateDipoleChart() {
  if (!dipoleChartInstance.value) return

  const iterations = timeSeriesData.value.map(d => d.timeStep)
  const dipoleMoment = timeSeriesData.value.map(d => d.dipoleMoment)
  const dipoleTilt = timeSeriesData.value.map(d => d.dipoleTilt)

  dipoleChartInstance.value.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['偶极矩', '倾斜角'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: iterations,
      name: '时间步',
      axisLabel: { rotate: 45 }
    },
    yAxis: [
      {
        type: 'value',
        name: '偶极矩',
        position: 'left'
      },
      {
        type: 'value',
        name: '倾斜角 (°)',
        position: 'right',
        min: 0,
        max: 90
      }
    ],
    series: [
      {
        name: '偶极矩',
        type: 'line',
        data: dipoleMoment,
        smooth: true,
        showSymbol: false,
        itemStyle: { color: '#67c23a' },
        yAxisIndex: 0
      },
      {
        name: '倾斜角',
        type: 'line',
        data: dipoleTilt,
        smooth: true,
        showSymbol: false,
        itemStyle: { color: '#e6a23c' },
        yAxisIndex: 1
      }
    ]
  })
}

function updateReynoldsChart() {
  if (!reynoldsChartInstance.value) return

  const iterations = timeSeriesData.value.map(d => d.timeStep)
  const magneticReynolds = timeSeriesData.value.map(d => d.magneticReynolds)
  const criticalValue = simulation.value?.magneticReynoldsCritical || 50.0

  reynoldsChartInstance.value.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['磁雷诺数', '临界值'] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: iterations,
      name: '时间步',
      axisLabel: { rotate: 45 }
    },
    yAxis: {
      type: 'value',
      name: '磁雷诺数'
    },
    series: [
      {
        name: '磁雷诺数',
        type: 'line',
        data: magneticReynolds,
        smooth: true,
        showSymbol: false,
        itemStyle: { color: '#9c27b0' },
        areaStyle: { color: 'rgba(156, 39, 176, 0.1)' }
      },
      {
        name: '临界值',
        type: 'line',
        data: new Array(iterations.length).fill(criticalValue),
        lineStyle: {
          type: 'dashed',
          color: '#f56c6c',
          width: 2
        },
        symbol: 'none'
      }
    ]
  })
}

function connectWebSocket() {
  if (ws) {
    ws.close()
  }

  const token = localStorage.getItem('token')
  const wsUrl = `ws://localhost:8000/api/simulations/ws/${simulationId.value}${token ? `?token=${token}` : ''}`

  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('WebSocket connected')
    wsConnected.value = true
    if (reconnectTimer) {
      clearInterval(reconnectTimer)
      reconnectTimer = null
    }
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      handleWebSocketMessage(data)
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error)
    }
  }

  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
    wsConnected.value = false
  }

  ws.onclose = () => {
    console.log('WebSocket disconnected')
    wsConnected.value = false
    if (!reconnectTimer) {
      reconnectTimer = window.setInterval(() => {
        console.log('Attempting to reconnect...')
        connectWebSocket()
      }, 5000)
    }
  }
}

function handleWebSocketMessage(data: any) {
  if (data.type === 'update') {
    const newData = data.payload

    if (simulation.value) {
      simulation.value.progress = newData.progress
      simulation.value.currentIteration = newData.iteration
      simulation.value.status = newData.status
      simulation.value.totalMagneticEnergy = newData.metrics.magnetic_energy
      simulation.value.totalKineticEnergy = newData.metrics.kinetic_energy
      simulation.value.dipoleMoment = newData.metrics.dipole_moment
      simulation.value.dipoleTilt = newData.metrics.dipole_tilt
      simulation.value.magneticReynoldsNumber = newData.metrics.magnetic_reynolds
      simulation.value.innerCoreSymmetry = newData.metrics.inner_core_symmetry
    }

    const newTimePoint: TimeSeriesData = {
      id: Date.now(),
      simulationId: simulationId.value,
      timeStep: newData.iteration,
      simulationTime: newData.iteration * 0.001,
      magneticEnergy: newData.metrics.magnetic_energy,
      kineticEnergy: newData.metrics.kinetic_energy,
      dipoleMoment: newData.metrics.dipole_moment,
      dipoleTilt: newData.metrics.dipole_tilt,
      magneticReynolds: newData.metrics.magnetic_reynolds,
      innerCoreSymmetry: newData.metrics.inner_core_symmetry,
      temperatureAnomaly: 0,
      velocityMagnitude: 0,
      createdAt: new Date().toISOString()
    }

    timeSeriesData.value.push(newTimePoint)

    if (timeSeriesData.value.length > 1000) {
      timeSeriesData.value = timeSeriesData.value.slice(-1000)
    }

    updateEnergyChart()
    updateDipoleChart()
    updateReynoldsChart()
  } else if (data.type === 'polarity_reversal') {
    fetchPolarityReversals()
    if (simulation.value) {
      simulation.value.hasPolarityReversal = true
      simulation.value.polarityReversalCount += 1
    }
    ElMessage.info('检测到新的极性反转事件')
  } else if (data.type === 'status_change') {
    if (simulation.value) {
      simulation.value.status = data.payload.status
    }
    ElMessage.info(`模拟状态已更新: ${data.payload.status}`)
  }
}

function handleResize() {
  energyChartInstance?.resize()
  dipoleChartInstance.value?.resize()
  reynoldsChartInstance.value?.resize()
}

watch(activeTab, (newTab) => {
  if (newTab === 'monitoring') {
    nextTick(() => {
      if (!energyChartInstance) {
        initCharts()
      } else {
        updateEnergyChart()
        updateDipoleChart()
        updateReynoldsChart()
      }
    })
  }
})

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([
      fetchSimulationDetail(),
      fetchTimeSeries(),
      fetchPolarityReversals(),
      fetchAdjustmentLogs(),
      fetchApprovalRecords()
    ])

    await nextTick()
    initCharts()
    connectWebSocket()
  } finally {
    loading.value = false
  }

  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  if (ws) {
    ws.close()
    ws = null
  }
  if (reconnectTimer) {
    clearInterval(reconnectTimer)
    reconnectTimer = null
  }
  if (energyChartInstance) {
    energyChartInstance.dispose()
    energyChartInstance = null
  }
  if (dipoleChartInstance.value) {
    dipoleChartInstance.value.dispose()
    dipoleChartInstance.value = null
  }
  if (reynoldsChartInstance.value) {
    reynoldsChartInstance.value.dispose()
    reynoldsChartInstance.value = null
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped lang="css">
.simulation-detail {
  padding: 24px;
}

.page-container {
  min-height: 100vh;
  background: #f5f7fa;
}

.detail-content {
  margin-top: 20px;
}

.card-shadow {
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  margin-bottom: 24px;
}

.info-card {
  margin-bottom: 24px;
}

.info-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 20px;
}

.info-main {
  flex: 1;
}

.simulation-name {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
  margin: 0 0 12px 0;
}

.info-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 12px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
}

.info-item .el-icon {
  color: #909399;
}

.simulation-desc {
  font-size: 14px;
  color: #606266;
  margin: 0;
  line-height: 1.6;
}

.info-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-content: flex-start;
}

.progress-section {
  margin-top: 16px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.progress-label {
  font-weight: 600;
  color: #303133;
}

.progress-value {
  color: #606266;
  font-size: 13px;
}

.detail-tabs {
  margin-top: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.params-card {
  margin-bottom: 0;
}

.param-item {
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
  margin-bottom: 16px;
}

.param-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 6px;
}

.param-value {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  font-family: 'Monaco', 'Menlo', monospace;
}

.timeline-container {
  max-height: 500px;
  overflow-y: auto;
  padding-right: 16px;
}

.reversal-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 8px 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.reversal-info {
  display: flex;
  gap: 20px;
  font-size: 13px;
  color: #606266;
}

.ws-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
}

.ws-status.connected {
  background: #f0f9eb;
  color: #67c23a;
}

.ws-status.disconnected {
  background: #fef0f0;
  color: #f56c6c;
}

.chart-card {
  height: 100%;
}

.chart {
  width: 100%;
  height: 350px;
}

.no-change {
  color: #c0c4cc;
}

:deep(.el-tabs__content) {
  padding-top: 8px;
}

:deep(.el-timeline-item__timestamp) {
  color: #909399;
}
</style>
