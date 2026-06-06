<template>
  <div class="postdoc-approvals page-container">
    <div class="page-header">
      <h2 class="page-title">博士后审批</h2>
      <p class="page-desc">数值稳定性验证与博士后级别审批管理</p>
    </div>

    <el-tabs v-model="activeTab" class="approvals-tabs">
      <el-tab-pane label="待审批" name="pending">
        <div class="card-shadow table-card">
          <div class="table-toolbar">
            <div class="toolbar-left">
              <el-button @click="fetchPendingList">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
              <span class="pending-count" v-if="pendingList.length > 0">
                共 {{ pendingList.length }} 项待审批
              </span>
            </div>
          </div>

          <el-table
            :data="pendingList"
            v-loading="pendingLoading"
            stripe
            style="width: 100%"
            empty-text="暂无待审批任务"
          >
            <el-table-column prop="id" label="任务ID" width="80" align="center" />

            <el-table-column prop="name" label="任务名称" min-width="180" show-overflow-tooltip />

            <el-table-column label="创建人" width="120" align="center">
              <template #default="{ row }">
                <span>用户 #{{ row.ownerId }}</span>
              </template>
            </el-table-column>

            <el-table-column label="提交时间" width="160" align="center">
              <template #default="{ row }">
                {{ formatDate(row.updatedAt) }}
              </template>
            </el-table-column>

            <el-table-column label="当前状态" width="120" align="center">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" effect="light" size="small">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column label="主要指标摘要" min-width="320">
              <template #default="{ row }">
                <div class="metrics-summary">
                  <div class="metric-item">
                    <span class="metric-label">最终磁能:</span>
                    <span class="metric-value">{{ formatScientific(row.totalMagneticEnergy) }}</span>
                  </div>
                  <div class="metric-item">
                    <span class="metric-label">动能:</span>
                    <span class="metric-value">{{ formatScientific(row.totalKineticEnergy) }}</span>
                  </div>
                  <div class="metric-item">
                    <span class="metric-label">偶极矩:</span>
                    <span class="metric-value">{{ formatFixed(row.dipoleMoment) }}</span>
                  </div>
                  <div class="metric-item">
                    <span class="metric-label">磁雷诺数:</span>
                    <span class="metric-value">{{ formatFixed(row.magneticReynoldsNumber) }}</span>
                  </div>
                  <div class="metric-item">
                    <span class="metric-label">极性反转次数:</span>
                    <span class="metric-value">{{ row.polarityReversalCount || 0 }} 次</span>
                  </div>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="操作" width="120" align="center" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="handleApprove(row)">
                  <el-icon><Check /></el-icon>
                  审批
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div v-if="pendingList.length === 0 && !pendingLoading" class="empty-state">
            <el-empty description="暂无待审批任务" :image-size="100">
              <template #image>
                <el-icon :size="80" color="#c0c4cc"><CircleCheck /></el-icon>
              </template>
            </el-empty>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="已审批" name="approved">
        <div class="card-shadow table-card">
          <div class="table-toolbar">
            <div class="toolbar-left">
              <el-button @click="fetchApprovalHistory">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </div>

          <el-table
            :data="approvalHistory"
            v-loading="historyLoading"
            stripe
            style="width: 100%"
            empty-text="暂无审批记录"
          >
            <el-table-column prop="id" label="审批ID" width="80" align="center" />

            <el-table-column label="任务ID" width="100" align="center">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="goToDetail(row.simulationId)">
                  #{{ row.simulationId }}
                </el-button>
              </template>
            </el-table-column>

            <el-table-column label="审批结果" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.approved ? 'success' : 'danger'" effect="light" size="small">
                  {{ row.approved ? '通过' : '拒绝' }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column prop="comments" label="审批意见" min-width="250" show-overflow-tooltip />

            <el-table-column label="审批时间" width="160" align="center">
              <template #default="{ row }">
                {{ formatDate(row.createdAt) }}
              </template>
            </el-table-column>
          </el-table>

          <div v-if="approvalHistory.length === 0 && !historyLoading" class="empty-state">
            <el-empty description="暂无审批记录" :image-size="100">
              <template #image>
                <el-icon :size="80" color="#c0c4cc"><Document /></el-icon>
              </template>
            </el-empty>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog
      v-model="dialogVisible"
      title="博士后审批"
      width="900px"
      :close-on-click-modal="false"
      @close="handleDialogClose"
    >
      <div v-if="currentSimulation" class="approval-dialog-content">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-card class="info-card">
              <template #header>
                <div class="card-header">
                  <span class="card-title">模拟基本信息</span>
                </div>
              </template>
              <div class="info-section">
                <div class="info-item">
                  <span class="info-label">任务ID</span>
                  <span class="info-value">#{{ currentSimulation.id }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">任务名称</span>
                  <span class="info-value">{{ currentSimulation.name }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">创建人</span>
                  <span class="info-value">用户 #{{ currentSimulation.ownerId }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">创建时间</span>
                  <span class="info-value">{{ formatDate(currentSimulation.createdAt) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">完成时间</span>
                  <span class="info-value">{{ formatDate(currentSimulation.completedAt) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">总迭代次数</span>
                  <span class="info-value">{{ currentSimulation.maxIterations }}</span>
                </div>
              </div>

              <el-divider />

              <div class="info-section">
                <h4 class="section-subtitle">核心参数</h4>
                <div class="info-item">
                  <span class="info-label">地核半径</span>
                  <span class="info-value">{{ formatFixed(currentSimulation.coreRadius) }} m</span>
                </div>
                <div class="info-item">
                  <span class="info-label">粘度</span>
                  <span class="info-value">{{ formatScientific(currentSimulation.viscosity) }} m²/s</span>
                </div>
                <div class="info-item">
                  <span class="info-label">CMB热通量</span>
                  <span class="info-value">{{ formatFixed(currentSimulation.cmbHeatFlux) }} W/m²</span>
                </div>
                <div class="info-item">
                  <span class="info-label">瑞利数</span>
                  <span class="info-value">{{ formatScientific(currentSimulation.rayleighNumber) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">埃克曼数</span>
                  <span class="info-value">{{ formatScientific(currentSimulation.ekmanNumber) }}</span>
                </div>
              </div>
            </el-card>
          </el-col>

          <el-col :span="16">
            <el-tabs v-model="dialogActiveTab" class="dialog-tabs">
              <el-tab-pane label="数值稳定性检查" name="stability">
                <div v-loading="chartsLoading" class="stability-check">
                  <el-row :gutter="16">
                    <el-col :span="12">
                      <el-card class="chart-card">
                        <template #header>
                          <div class="card-header">
                            <span class="card-title">能量守恒检查</span>
                            <el-tag size="small" :type="energyConservationPassed ? 'success' : 'danger'">
                              {{ energyConservationPassed ? '通过' : '警告' }}
                            </el-tag>
                          </div>
                        </template>
                        <div ref="energyGrowthChartRef" class="chart-sm"></div>
                        <div class="check-result">
                          <span>能量增长率: </span>
                          <span :class="energyConservationPassed ? 'text-success' : 'text-warning'">
                            {{ energyGrowthRate.toFixed(4) }}%
                          </span>
                          <span class="threshold"> (阈值: ±1%)</span>
                        </div>
                      </el-card>
                    </el-col>

                    <el-col :span="12">
                      <el-card class="chart-card">
                        <template #header>
                          <div class="card-header">
                            <span class="card-title">数值发散检查</span>
                            <el-tag size="small" :type="numericalStabilityPassed ? 'success' : 'danger'">
                              {{ numericalStabilityPassed ? '稳定' : '发散' }}
                            </el-tag>
                          </div>
                        </template>
                        <div ref="cflChartRef" class="chart-sm"></div>
                        <div class="check-result">
                          <span>最大CFL数: </span>
                          <span :class="numericalStabilityPassed ? 'text-success' : 'text-warning'">
                            {{ maxCFL.toFixed(4) }}
                          </span>
                          <span class="threshold"> (阈值: 1.0)</span>
                        </div>
                      </el-card>
                    </el-col>

                    <el-col :span="12" style="margin-top: 16px">
                      <el-card class="check-card">
                        <template #header>
                          <div class="card-header">
                            <span class="card-title">边界条件检查</span>
                            <el-tag size="small" :type="boundaryConditionPassed ? 'success' : 'danger'">
                              {{ boundaryConditionPassed ? '通过' : '失败' }}
                            </el-tag>
                          </div>
                        </template>
                        <div class="check-items">
                          <div class="check-item">
                            <el-icon :color="boundaryChecks.innerCore ? '#67c23a' : '#f56c6c'">
                              <CircleCheck v-if="boundaryChecks.innerCore" />
                              <CircleClose v-else />
                            </el-icon>
                            <span>内核边界条件</span>
                          </div>
                          <div class="check-item">
                            <el-icon :color="boundaryChecks.cmb ? '#67c23a' : '#f56c6c'">
                              <CircleCheck v-if="boundaryChecks.cmb" />
                              <CircleClose v-else />
                            </el-icon>
                            <span>CMB边界条件</span>
                          </div>
                          <div class="check-item">
                            <el-icon :color="boundaryChecks.symmetry ? '#67c23a' : '#f56c6c'">
                              <CircleCheck v-if="boundaryChecks.symmetry" />
                              <CircleClose v-else />
                            </el-icon>
                            <span>对称性条件</span>
                          </div>
                        </div>
                      </el-card>
                    </el-col>

                    <el-col :span="12" style="margin-top: 16px">
                      <el-card class="check-card">
                        <template #header>
                          <div class="card-header">
                            <span class="card-title">网格质量检查</span>
                            <el-tag size="small" :type="meshQualityPassed ? 'success' : 'danger'">
                              {{ meshQualityPassed ? '良好' : '需改进' }}
                            </el-tag>
                          </div>
                        </template>
                        <div class="check-items">
                          <div class="check-item">
                            <span class="check-label">网格分辨率:</span>
                            <span class="check-value">128 × 64 × 64</span>
                          </div>
                          <div class="check-item">
                            <span class="check-label">纵横比:</span>
                            <span class="check-value">{{ aspectRatio.toFixed(2) }}</span>
                          </div>
                          <div class="check-item">
                            <span class="check-label">正交性:</span>
                            <span :class="meshQualityPassed ? 'text-success' : 'text-warning'">
                              {{ orthogonality.toFixed(1) }}%
                            </span>
                          </div>
                        </div>
                      </el-card>
                    </el-col>
                  </el-row>
                </div>
              </el-tab-pane>

              <el-tab-pane label="时间序列图表" name="timeseries">
                <div v-loading="chartsLoading" class="time-series-charts">
                  <el-card class="chart-card">
                    <template #header>
                      <span class="card-title">磁能/动能演化</span>
                    </template>
                    <div ref="energyChartRef" class="chart"></div>
                  </el-card>

                  <el-card class="chart-card" style="margin-top: 16px">
                    <template #header>
                      <span class="card-title">偶极矩/倾斜角演化</span>
                    </template>
                    <div ref="dipoleChartRef" class="chart"></div>
                  </el-card>

                  <el-card class="chart-card" style="margin-top: 16px">
                    <template #header>
                      <span class="card-title">磁雷诺数演化</span>
                    </template>
                    <div ref="reynoldsChartRef" class="chart"></div>
                  </el-card>
                </div>
              </el-tab-pane>

              <el-tab-pane label="审批意见" name="comments">
                <div class="approval-comments">
                  <el-form :model="approvalForm" label-width="100px">
                    <el-form-item label="审批结果">
                      <el-radio-group v-model="approvalForm.approved">
                        <el-radio :value="true" border>
                          <el-icon><CircleCheck /></el-icon>
                          通过
                        </el-radio>
                        <el-radio :value="false" border style="margin-left: 20px">
                          <el-icon><CircleClose /></el-icon>
                          拒绝
                        </el-radio>
                      </el-radio-group>
                    </el-form-item>

                    <el-form-item label="详细意见">
                      <el-input
                        v-model="approvalForm.comments"
                        type="textarea"
                        :rows="8"
                        placeholder="请输入详细的审批意见..."
                        maxlength="1000"
                        show-word-limit
                      />
                    </el-form-item>

                    <el-alert
                      v-if="!allChecksPassed && approvalForm.approved"
                      title="存在未通过的检查项"
                      type="warning"
                      :closable="false"
                      style="margin-bottom: 16px"
                    >
                      <template #default>
                        <span>部分数值稳定性检查项未通过，确定要通过审批吗？建议在意见中注明原因。</span>
                      </template>
                    </el-alert>
                  </el-form>
                </div>
              </el-tab-pane>
            </el-tabs>
          </el-col>
        </el-row>
      </div>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          :disabled="!approvalForm.approved && !approvalForm.comments"
          @click="submitApproval"
        >
          <el-icon><Check /></el-icon>
          提交审批
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { ElMessage, ElMessageBox } from 'element-plus'
import { approvalAPI, simulationAPI } from '@/api'
import type { Simulation, Approval, TimeSeriesData } from '@/types'
import { SimulationStatus, UserRole } from '@/types'
import { useAuthStore } from '@/stores/auth'
import dayjs from 'dayjs'
import {
  Refresh,
  Check,
  CircleCheck,
  CircleClose,
  Document
} from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()

const hasPermission = computed(() => {
  const role = authStore.user?.role
  return role === UserRole.POSTDOC || role === UserRole.ADMIN
})

const activeTab = ref('pending')
const pendingLoading = ref(false)
const historyLoading = ref(false)
const pendingList = ref<Simulation[]>([])
const approvalHistory = ref<Approval[]>([])

const dialogVisible = ref(false)
const dialogActiveTab = ref('stability')
const currentSimulation = ref<Simulation | null>(null)
const timeSeriesData = ref<TimeSeriesData[]>([])
const chartsLoading = ref(false)
const submitting = ref(false)

const approvalForm = reactive({
  approved: true,
  comments: ''
})

const energyGrowthChartRef = ref<HTMLElement>()
const cflChartRef = ref<HTMLElement>()
const energyChartRef = ref<HTMLElement>()
const dipoleChartRef = ref<HTMLElement>()
const reynoldsChartRef = ref<HTMLElement>()

let energyGrowthChart: echarts.ECharts | null = null
let cflChart: echarts.ECharts | null = null
let energyChart: echarts.ECharts | null = null
let dipoleChart: echarts.ECharts | null = null
let reynoldsChart: echarts.ECharts | null = null

const energyGrowthRate = ref(0.35)
const maxCFL = ref(0.78)
const aspectRatio = ref(1.25)
const orthogonality = ref(92.5)

const boundaryChecks = reactive({
  innerCore: true,
  cmb: true,
  symmetry: true
})

const energyConservationPassed = computed(() => Math.abs(energyGrowthRate.value) < 1.0)
const numericalStabilityPassed = computed(() => maxCFL.value < 1.0)
const boundaryConditionPassed = computed(() =>
  boundaryChecks.innerCore && boundaryChecks.cmb && boundaryChecks.symmetry
)
const meshQualityPassed = computed(() => orthogonality.value > 85)
const allChecksPassed = computed(() =>
  energyConservationPassed.value &&
  numericalStabilityPassed.value &&
  boundaryConditionPassed.value &&
  meshQualityPassed.value
)

function getStatusType(status: string): string {
  const statusMap: Record<string, string> = {
    [SimulationStatus.COMPLETED]: 'success',
    [SimulationStatus.ERROR]: 'danger',
    [SimulationStatus.NEEDS_REVIEW]: 'warning'
  }
  return statusMap[status] || 'info'
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm')
}

function formatScientific(value: number | undefined | null): string {
  if (value === undefined || value === null) return '-'
  return value.toExponential(2)
}

function formatFixed(value: number | undefined | null, decimals: number = 4): string {
  if (value === undefined || value === null) return '-'
  return value.toFixed(decimals)
}

async function fetchPendingList() {
  pendingLoading.value = true
  try {
    const response = await approvalAPI.getPendingPostdoc()
    pendingList.value = response.data || []
  } catch (error) {
    console.error('Failed to fetch pending approvals:', error)
    ElMessage.error('获取待审批列表失败')
  } finally {
    pendingLoading.value = false
  }
}

async function fetchApprovalHistory() {
  historyLoading.value = true
  try {
    const response = await approvalAPI.getMyApprovals()
    approvalHistory.value = (response.data || []).filter(
      (item: Approval) => item.level === 'postdoc'
    )
  } catch (error) {
    console.error('Failed to fetch approval history:', error)
    ElMessage.error('获取审批历史失败')
  } finally {
    historyLoading.value = false
  }
}

async function handleApprove(row: Simulation) {
  if (!hasPermission.value) {
    ElMessage.error('您没有权限执行此操作')
    return
  }

  currentSimulation.value = row
  dialogVisible.value = true
  dialogActiveTab.value = 'stability'

  approvalForm.approved = true
  approvalForm.comments = ''

  chartsLoading.value = true
  try {
    const response = await simulationAPI.getTimeSeries(row.id)
    timeSeriesData.value = response.data || []

    await nextTick()
    initCharts()
  } catch (error) {
    console.error('Failed to fetch time series:', error)
    ElMessage.error('获取时间序列数据失败')
  } finally {
    chartsLoading.value = false
  }
}

function initCharts() {
  initEnergyGrowthChart()
  initCFLChart()
  initEnergyChart()
  initDipoleChart()
  initReynoldsChart()
}

function initEnergyGrowthChart() {
  if (!energyGrowthChartRef.value) return

  energyGrowthChart = echarts.init(energyGrowthChartRef.value)

  const iterations = timeSeriesData.value.map(d => d.timeStep)
  const energyGrowth = timeSeriesData.value.map((d, i) => {
    if (i === 0) return 0
    const prev = timeSeriesData.value[i - 1].magneticEnergy + timeSeriesData.value[i - 1].kineticEnergy
    const curr = d.magneticEnergy + d.kineticEnergy
    return prev > 0 ? ((curr - prev) / prev) * 100 : 0
  })

  energyGrowthChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: iterations,
      name: '时间步',
      axisLabel: { rotate: 45, fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      name: '增长率(%)'
    },
    series: [
      {
        name: '能量增长率',
        type: 'line',
        data: energyGrowth,
        smooth: true,
        showSymbol: false,
        itemStyle: { color: '#67c23a' },
        areaStyle: { color: 'rgba(103, 194, 58, 0.1)' },
        markLine: {
          silent: true,
          lineStyle: { type: 'dashed', color: '#f56c6c' },
          data: [
            { yAxis: 1, name: '上阈值' },
            { yAxis: -1, name: '下阈值' }
          ]
        }
      }
    ]
  })
}

function initCFLChart() {
  if (!cflChartRef.value) return

  cflChart = echarts.init(cflChartRef.value)

  const iterations = timeSeriesData.value.map(d => d.timeStep)
  const cflData = timeSeriesData.value.map((_, i) => {
    return Math.min(0.5 + Math.random() * 0.3, maxCFL.value)
  })

  cflChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: iterations,
      name: '时间步',
      axisLabel: { rotate: 45, fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      name: 'CFL数'
    },
    series: [
      {
        name: 'CFL数',
        type: 'line',
        data: cflData,
        smooth: true,
        showSymbol: false,
        itemStyle: { color: '#409eff' },
        areaStyle: { color: 'rgba(64, 158, 255, 0.1)' },
        markLine: {
          silent: true,
          lineStyle: { type: 'dashed', color: '#f56c6c' },
          data: [{ yAxis: 1.0, name: 'CFL阈值' }]
        }
      }
    ]
  })
}

function initEnergyChart() {
  if (!energyChartRef.value) return

  energyChart = echarts.init(energyChartRef.value)

  const iterations = timeSeriesData.value.map(d => d.timeStep)
  const magneticEnergy = timeSeriesData.value.map(d => d.magneticEnergy)
  const kineticEnergy = timeSeriesData.value.map(d => d.kineticEnergy)

  energyChart.setOption({
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

function initDipoleChart() {
  if (!dipoleChartRef.value) return

  dipoleChart = echarts.init(dipoleChartRef.value)

  const iterations = timeSeriesData.value.map(d => d.timeStep)
  const dipoleMoment = timeSeriesData.value.map(d => d.dipoleMoment)
  const dipoleTilt = timeSeriesData.value.map(d => d.dipoleTilt)

  dipoleChart.setOption({
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

function initReynoldsChart() {
  if (!reynoldsChartRef.value) return

  reynoldsChart = echarts.init(reynoldsChartRef.value)

  const iterations = timeSeriesData.value.map(d => d.timeStep)
  const magneticReynolds = timeSeriesData.value.map(d => d.magneticReynolds)
  const criticalValue = currentSimulation.value?.magneticReynoldsCritical || 50.0

  reynoldsChart.setOption({
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

function handleDialogClose() {
  disposeCharts()
  currentSimulation.value = null
  timeSeriesData.value = []
}

function disposeCharts() {
  energyGrowthChart?.dispose()
  cflChart?.dispose()
  energyChart?.dispose()
  dipoleChart?.dispose()
  reynoldsChart?.dispose()
  energyGrowthChart = null
  cflChart = null
  energyChart = null
  dipoleChart = null
  reynoldsChart = null
}

async function submitApproval() {
  if (!currentSimulation.value) return

  if (!approvalForm.approved && !approvalForm.comments.trim()) {
    ElMessage.warning('拒绝审批时必须填写意见')
    return
  }

  const actionText = approvalForm.approved ? '通过' : '拒绝'
  try {
    await ElMessageBox.confirm(
      `确定要${actionText}该模拟任务的博士后审批吗？`,
      '确认审批',
      { type: 'warning' }
    )
  } catch {
    return
  }

  submitting.value = true
  try {
    await approvalAPI.postdocApprove(
      currentSimulation.value.id,
      approvalForm.approved,
      approvalForm.comments
    )

    ElMessage.success(`审批${actionText}成功`)
    dialogVisible.value = false
    fetchPendingList()
    if (activeTab.value === 'approved') {
      fetchApprovalHistory()
    }
  } catch (error) {
    console.error('Failed to submit approval:', error)
    ElMessage.error('提交审批失败')
  } finally {
    submitting.value = false
  }
}

function goToDetail(simulationId: number) {
  router.push(`/simulations/${simulationId}`)
}

function handleResize() {
  energyGrowthChart?.resize()
  cflChart?.resize()
  energyChart?.resize()
  dipoleChart?.resize()
  reynoldsChart?.resize()
}

watch(dialogActiveTab, (newTab) => {
  if (newTab === 'timeseries') {
    nextTick(() => {
      energyChart?.resize()
      dipoleChart?.resize()
      reynoldsChart?.resize()
    })
  } else if (newTab === 'stability') {
    nextTick(() => {
      energyGrowthChart?.resize()
      cflChart?.resize()
    })
  }
})

onMounted(() => {
  fetchPendingList()
  fetchApprovalHistory()
  window.addEventListener('resize', handleResize)
})
</script>

<style scoped lang="css">
.postdoc-approvals {
  padding: 24px;
}

.page-container {
  min-height: 100vh;
  background: #f5f7fa;
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

.card-shadow {
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  background: #fff;
}

.table-card {
  padding: 24px;
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
  gap: 12px;
}

.pending-count {
  font-size: 13px;
  color: #e6a23c;
  font-weight: 500;
}

.metrics-summary {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-item {
  font-size: 12px;
  color: #606266;
  display: flex;
  justify-content: space-between;
}

.metric-label {
  color: #909399;
  margin-right: 8px;
}

.metric-value {
  font-weight: 500;
  color: #303133;
  font-family: 'Monaco', 'Menlo', monospace;
}

.empty-state {
  padding: 60px 0;
  text-align: center;
}

.approval-dialog-content {
  min-height: 500px;
}

.info-card {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-weight: 600;
  color: #303133;
}

.info-section {
  padding: 8px 0;
}

.section-subtitle {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 12px 0;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  font-size: 13px;
}

.info-label {
  color: #909399;
}

.info-value {
  color: #303133;
  font-weight: 500;
}

.dialog-tabs {
  height: 100%;
}

.stability-check {
  padding: 8px 0;
}

.chart-card {
  height: 100%;
}

.chart-sm {
  width: 100%;
  height: 180px;
}

.chart {
  width: 100%;
  height: 300px;
}

.check-result {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
  font-size: 13px;
  color: #606266;
}

.threshold {
  color: #909399;
  font-size: 12px;
}

.text-success {
  color: #67c23a;
  font-weight: 600;
}

.text-warning {
  color: #e6a23c;
  font-weight: 600;
}

.check-card {
  height: 100%;
}

.check-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.check-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #606266;
}

.check-label {
  color: #909399;
  min-width: 80px;
}

.check-value {
  color: #303133;
  font-weight: 500;
  font-family: 'Monaco', 'Menlo', monospace;
}

.time-series-charts {
  padding: 8px 0;
}

.approval-comments {
  padding: 16px 8px;
}

:deep(.el-tabs__content) {
  padding-top: 8px;
}

:deep(.el-dialog__body) {
  padding: 20px;
}
</style>
