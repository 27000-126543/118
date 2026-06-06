<template>
  <div class="dashboard-container page-container">
    <div class="metrics-row">
      <div v-for="metric in metrics" :key="metric.label" class="metric-card">
        <div class="metric-icon" :style="{ background: metric.color }">
          <el-icon :size="24" color="#fff">
            <component :is="metric.icon" />
          </el-icon>
        </div>
        <div class="metric-content">
          <div class="metric-label">{{ metric.label }}</div>
          <div class="metric-value">{{ metric.value }}</div>
          <div class="metric-change" :class="metric.change >= 0 ? 'metric-up' : 'metric-down'">
            <el-icon><component :is="metric.change >= 0 ? 'Top' : 'Bottom'" /></el-icon>
            {{ Math.abs(metric.change).toFixed(1) }}% 较昨日
          </div>
        </div>
      </div>
    </div>

    <div class="charts-row">
      <div class="chart-container">
        <h3 class="section-title">模拟完成率与错误数趋势</h3>
        <div ref="completionChartRef" class="chart"></div>
      </div>
      <div class="chart-container">
        <h3 class="section-title">磁能生成效率与极性反转频率</h3>
        <div ref="efficiencyChartRef" class="chart"></div>
      </div>
    </div>

    <div class="charts-row">
      <div class="chart-container">
        <h3 class="section-title">计算性能指标趋势</h3>
        <div ref="performanceChartRef" class="chart"></div>
      </div>
      <div class="chart-container">
        <h3 class="section-title">模拟任务状态分布</h3>
        <div ref="statusChartRef" class="chart"></div>
      </div>
    </div>

    <div class="recent-section">
      <el-row :gutter="24">
        <el-col :span="14">
          <div class="card-shadow recent-simulations">
            <div class="card-header">
              <h3 class="section-title" style="margin-bottom: 0">最近模拟任务</h3>
              <el-button type="primary" link @click="$router.push('/simulations')">
                查看全部 <el-icon><ArrowRight /></el-icon>
              </el-button>
            </div>
            <el-table :data="recentSimulations" style="width: 100%">
              <el-table-column prop="id" label="ID" width="80" />
              <el-table-column prop="name" label="任务名称" min-width="180" />
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="getStatusType(row.status)" size="small">
                    {{ row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="进度" width="140">
                <template #default="{ row }">
                  <el-progress :percentage="Math.round(row.progress)" :status="row.status === '异常' ? 'exception' : row.status === '完成' ? 'success' : undefined" />
                </template>
              </el-table-column>
              <el-table-column label="当前迭代" width="100" prop="currentIteration" />
              <el-table-column label="创建时间" width="160">
                <template #default="{ row }">
                  {{ formatDate(row.createdAt) }}
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-col>
        <el-col :span="10">
          <div class="card-shadow recent-alerts">
            <div class="card-header">
              <h3 class="section-title" style="margin-bottom: 0">最近预警</h3>
              <el-badge :value="pendingAlerts.length" class="item">
                <el-button type="primary" link @click="$router.push('/alerts')">
                  查看全部 <el-icon><ArrowRight /></el-icon>
                </el-button>
              </el-badge>
            </div>
            <div class="alert-list">
              <div
                v-for="alert in recentAlerts"
                :key="alert.id"
                class="alert-item"
                :class="`alert-${alert.level}`"
              >
                <div class="alert-header">
                  <el-tag :type="getAlertType(alert.level)" size="small">
                    {{ getAlertLevelText(alert.level) }}
                  </el-tag>
                  <span class="alert-time">{{ formatDate(alert.createdAt) }}</span>
                </div>
                <div class="alert-title">{{ alert.title }}</div>
                <div class="alert-message">{{ alert.message }}</div>
              </div>
              <div v-if="recentAlerts.length === 0" class="empty-state">
                <el-empty description="暂无预警信息" :image-size="60" />
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import { approvalAPI, simulationAPI, monitoringAPI } from '@/api'
import type { Simulation, Alert } from '@/types'
import { SimulationStatus, AlertLevel } from '@/types'
import {
  DataAnalysis, Warning, CircleCheck, CircleClose,
  Clock, TrendCharts, ArrowRight, Top, Bottom
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const overviewData = ref<any>(null)
const dailyStats = ref<any[]>([])
const recentSimulations = ref<Simulation[]>([])
const recentAlerts = ref<Alert[]>([])
const pendingAlerts = ref<Alert[]>([])

const completionChartRef = ref<HTMLElement>()
const efficiencyChartRef = ref<HTMLElement>()
const performanceChartRef = ref<HTMLElement>()
const statusChartRef = ref<HTMLElement>()

const metrics = computed(() => [
  {
    label: '总模拟数',
    value: overviewData.value?.totalSimulations || 0,
    change: 12.5,
    color: '#409eff',
    icon: DataAnalysis
  },
  {
    label: '完成模拟',
    value: overviewData.value?.completedSimulations || 0,
    change: 8.2,
    color: '#67c23a',
    icon: CircleCheck
  },
  {
    label: '运行中',
    value: overviewData.value?.runningSimulations || 0,
    change: -3.1,
    color: '#e6a23c',
    icon: Clock
  },
  {
    label: '异常数',
    value: overviewData.value?.errorSimulations || 0,
    change: -15.3,
    color: '#f56c6c',
    icon: CircleClose
  },
  {
    label: '极性反转总数',
    value: overviewData.value?.totalPolarityReversals || 0,
    change: 25.0,
    color: '#909399',
    icon: TrendCharts
  },
  {
    label: '审批通过',
    value: overviewData.value?.approvedSimulations || 0,
    change: 15.7,
    color: '#9c27b0',
    icon: CircleCheck
  }
])

function getStatusType(status: string) {
  const map: Record<string, any> = {
    [SimulationStatus.PENDING_VERIFICATION]: 'warning',
    [SimulationStatus.MESH_GENERATION]: 'info',
    [SimulationStatus.INITIALIZATION]: 'info',
    [SimulationStatus.ITERATING]: 'primary',
    [SimulationStatus.COMPLETED]: 'success',
    [SimulationStatus.ERROR]: 'danger',
    [SimulationStatus.ADJUSTING]: 'warning'
  }
  return map[status] || 'info'
}

function getAlertType(level: string) {
  const map: Record<string, any> = {
    [AlertLevel.INFO]: 'info',
    [AlertLevel.WARNING]: 'warning',
    [AlertLevel.CRITICAL]: 'danger'
  }
  return map[level] || 'info'
}

function getAlertLevelText(level: string) {
  const map: Record<string, string> = {
    [AlertLevel.INFO]: '信息',
    [AlertLevel.WARNING]: '警告',
    [AlertLevel.CRITICAL]: '严重'
  }
  return map[level] || level
}

function formatDate(dateStr: string) {
  return dayjs(dateStr).format('MM-DD HH:mm')
}

async function fetchData() {
  try {
    const [dashboardRes, simsRes, alertsRes] = await Promise.all([
      approvalAPI.getDashboard(30),
      simulationAPI.list({ limit: 5 }),
      monitoringAPI.getAlerts({ limit: 5 })
    ])

    overviewData.value = dashboardRes.data.overall_statistics
    dailyStats.value = dashboardRes.data.daily_statistics
    recentSimulations.value = simsRes.data
    recentAlerts.value = alertsRes.data
    pendingAlerts.value = alertsRes.data.filter((a: Alert) => a.needsReview && !a.reviewed)

    await nextTick()
    initCharts()
  } catch (error) {
    console.error('Failed to fetch dashboard data:', error)
  }
}

function initCharts() {
  if (completionChartRef.value) {
    const chart = echarts.init(completionChartRef.value)
    const dates = dailyStats.value.map(d => d.date)
    const completionRates = dailyStats.value.map(d => d.completionRate * 100)
    const errorCounts = dailyStats.value.map(d => d.errorCount)

    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['完成率 (%)', '错误数'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: dates, axisLabel: { rotate: 45 } },
      yAxis: [
        { type: 'value', name: '完成率 (%)', min: 0, max: 100 },
        { type: 'value', name: '错误数' }
      ],
      series: [
        {
          name: '完成率 (%)',
          type: 'bar',
          data: completionRates,
          itemStyle: { color: '#409eff' }
        },
        {
          name: '错误数',
          type: 'line',
          yAxisIndex: 1,
          data: errorCounts,
          itemStyle: { color: '#f56c6c' }
        }
      ]
    })
  }

  if (efficiencyChartRef.value) {
    const chart = echarts.init(efficiencyChartRef.value)
    const dates = dailyStats.value.map(d => d.date)
    const efficiency = dailyStats.value.map(d => d.avgMagneticEnergyEfficiency)
    const reversalFreq = dailyStats.value.map(d => d.polarityReversalFrequency)

    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['磁能生成效率', '极性反转频率'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: dates, axisLabel: { rotate: 45 } },
      yAxis: { type: 'value' },
      series: [
        {
          name: '磁能生成效率',
          type: 'line',
          data: efficiency,
          smooth: true,
          itemStyle: { color: '#2196f3' },
          areaStyle: { color: 'rgba(33, 150, 243, 0.1)' }
        },
        {
          name: '极性反转频率',
          type: 'line',
          data: reversalFreq,
          smooth: true,
          itemStyle: { color: '#4caf50' },
          areaStyle: { color: 'rgba(76, 175, 80, 0.1)' }
        }
      ]
    })
  }

  if (performanceChartRef.value) {
    const chart = echarts.init(performanceChartRef.value)
    const dates = dailyStats.value.map(d => d.date)
    const avgIterations = dailyStats.value.map(d => d.avgIterationsPerSimulation)
    const avgDuration = dailyStats.value.map(d => d.avgSimulationDurationHours)

    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['平均迭代次数', '平均时长(小时)'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: dates, axisLabel: { rotate: 45 } },
      yAxis: [
        { type: 'value', name: '迭代次数' },
        { type: 'value', name: '时长(小时)' }
      ],
      series: [
        {
          name: '平均迭代次数',
          type: 'bar',
          data: avgIterations,
          itemStyle: { color: '#9c27b0' }
        },
        {
          name: '平均时长(小时)',
          type: 'line',
          yAxisIndex: 1,
          data: avgDuration,
          itemStyle: { color: '#ff9800' }
        }
      ]
    })
  }

  if (statusChartRef.value) {
    const chart = echarts.init(statusChartRef.value)
    chart.setOption({
      tooltip: { trigger: 'item' },
      legend: { orient: 'vertical', right: '10%', top: 'center' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: {
          label: { show: true, fontSize: 20, fontWeight: 'bold' }
        },
        labelLine: { show: false },
        data: [
          { value: overviewData.value?.completedSimulations || 0, name: '已完成', itemStyle: { color: '#67c23a' } },
          { value: overviewData.value?.runningSimulations || 0, name: '运行中', itemStyle: { color: '#409eff' } },
          { value: overviewData.value?.pendingSimulations || 0, name: '待处理', itemStyle: { color: '#e6a23c' } },
          { value: overviewData.value?.errorSimulations || 0, name: '异常', itemStyle: { color: '#f56c6c' } }
        ]
      }]
    })
  }
}

onMounted(() => {
  fetchData()

  window.addEventListener('resize', () => {
    echarts.getInstanceByDom(completionChartRef.value as any)?.resize()
    echarts.getInstanceByDom(efficiencyChartRef.value as any)?.resize()
    echarts.getInstanceByDom(performanceChartRef.value as any)?.resize()
    echarts.getInstanceByDom(statusChartRef.value as any)?.resize()
  })
})
</script>

<style scoped lang="css">
.dashboard-container {
  padding: 24px;
}

.metrics-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: transform 0.3s, box-shadow 0.3s;
}

.metric-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.metric-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.metric-content {
  flex: 1;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  margin-top: 4px;
}

.metric-label {
  font-size: 14px;
  color: #909399;
}

.charts-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.chart-container {
  padding: 20px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.chart {
  width: 100%;
  height: 300px;
}

.recent-section {
  margin-top: 8px;
}

.recent-simulations, .recent-alerts {
  background: #fff;
  padding: 24px;
  border-radius: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.alert-item {
  padding: 12px 16px;
  background: #fafafa;
  border-radius: 8px;
  border-left: 4px solid #409eff;
}

.alert-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.alert-time {
  font-size: 12px;
  color: #909399;
}

.alert-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.alert-message {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}

.empty-state {
  padding: 40px;
  text-align: center;
}

.item {
  margin-top: 0;
}
</style>
