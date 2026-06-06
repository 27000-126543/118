<template>
  <div class="statistics-container page-container">
    <div class="page-header">
      <h2 class="page-title">统计分析</h2>
      <div class="header-actions">
        <el-radio-group v-model="quickRange" @change="handleQuickRangeChange">
          <el-radio-button :value="7">最近7天</el-radio-button>
          <el-radio-button :value="30">最近30天</el-radio-button>
          <el-radio-button :value="90">最近90天</el-radio-button>
          <el-radio-button :value="365">最近1年</el-radio-button>
          <el-radio-button :value="0">全部</el-radio-button>
        </el-radio-group>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          @change="handleDateRangeChange"
        />
        <el-button type="primary" :icon="Refresh" @click="fetchAllData">刷新</el-button>
        <el-dropdown @command="handleExport">
          <el-button type="success" :icon="Download">
            导出数据 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="csv">导出为 CSV</el-dropdown-item>
              <el-dropdown-item command="excel">导出为 Excel</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <div class="metrics-row">
      <div v-for="metric in metrics" :key="metric.label" class="metric-card">
        <div class="metric-icon" :style="{ background: metric.color }">
          <el-icon :size="24" color="#fff">
            <component :is="metric.icon" />
          </el-icon>
        </div>
        <div class="metric-content">
          <div class="metric-label">{{ metric.label }}</div>
          <div class="metric-value">
            {{ metric.value }}
            <span v-if="metric.unit" class="metric-unit">{{ metric.unit }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="section-card">
      <el-tabs v-model="trendTab" @tab-change="handleTrendTabChange">
        <el-tab-pane label="模拟完成率与错误数趋势" name="completion">
          <div ref="completionChartRef" class="chart"></div>
        </el-tab-pane>
        <el-tab-pane label="磁能生成效率与极性反转频率" name="efficiency">
          <div ref="efficiencyChartRef" class="chart"></div>
        </el-tab-pane>
        <el-tab-pane label="平均迭代次数与模拟时长" name="performance">
          <div ref="performanceChartRef" class="chart"></div>
        </el-tab-pane>
        <el-tab-pane label="参数空间热力图" name="heatmap">
          <div ref="heatmapChartRef" class="chart"></div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <div class="section-title-row">
      <h3 class="section-title">参数分布统计</h3>
    </div>
    <div class="charts-row">
      <div class="chart-container">
        <h4 class="chart-title">瑞利数分布</h4>
        <div ref="rayleighChartRef" class="chart"></div>
      </div>
      <div class="chart-container">
        <h4 class="chart-title">普朗特数分布</h4>
        <div ref="prandtlChartRef" class="chart"></div>
      </div>
    </div>
    <div class="charts-row">
      <div class="chart-container">
        <h4 class="chart-title">磁雷诺数分布</h4>
        <div ref="magneticReynoldsChartRef" class="chart"></div>
      </div>
      <div class="chart-container">
        <h4 class="chart-title">粘性系数分布（对数坐标）</h4>
        <div ref="viscosityChartRef" class="chart"></div>
      </div>
    </div>

    <div class="section-title-row">
      <h3 class="section-title">极性反转统计</h3>
    </div>
    <div class="charts-row">
      <div class="chart-container">
        <h4 class="chart-title">极性反转事件时间序列</h4>
        <div ref="reversalTimeSeriesRef" class="chart"></div>
      </div>
      <div class="chart-container">
        <h4 class="chart-title">反转持续时间分布</h4>
        <div ref="reversalDurationRef" class="chart"></div>
      </div>
    </div>
    <div class="charts-row">
      <div class="chart-container full-width">
        <h4 class="chart-title">反转频率与瑞利数关系</h4>
        <div ref="reversalScatterRef" class="chart"></div>
      </div>
    </div>

    <div class="section-card">
      <div class="card-header">
        <h3 class="section-title">每日统计数据</h3>
        <el-button type="primary" link @click="handleExport('csv')">
          导出当前数据 <el-icon><Download /></el-icon>
        </el-button>
      </div>
      <el-table :data="dailyStats" style="width: 100%" border stripe>
        <el-table-column prop="date" label="日期" width="120" fixed />
        <el-table-column prop="totalSimulations" label="总模拟数" width="100" align="right" />
        <el-table-column prop="completedSimulations" label="完成数" width="100" align="right" />
        <el-table-column label="完成率" width="100" align="right">
          <template #default="{ row }">
            {{ (row.completionRate * 100).toFixed(1) }}%
          </template>
        </el-table-column>
        <el-table-column label="平均效率" width="110" align="right">
          <template #default="{ row }">
            {{ row.avgMagneticEnergyEfficiency?.toFixed(4) }}
          </template>
        </el-table-column>
        <el-table-column label="反转频率" width="110" align="right">
          <template #default="{ row }">
            {{ row.polarityReversalFrequency?.toFixed(4) }}
          </template>
        </el-table-column>
        <el-table-column label="平均迭代" width="100" align="right">
          <template #default="{ row }">
            {{ Math.round(row.avgIterationsPerSimulation) }}
          </template>
        </el-table-column>
        <el-table-column label="平均时长(小时)" width="130" align="right">
          <template #default="{ row }">
            {{ row.avgSimulationDurationHours?.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="errorCount" label="错误数" width="100" align="right" />
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { approvalAPI, simulationAPI } from '@/api'
import type { DailyStatistics, Simulation } from '@/types'
import {
  DataAnalysis, CircleCheck, Lightning, Repeat,
  Timer, Clock, Warning, CircleClose,
  Refresh, Download, ArrowDown
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const quickRange = ref(30)
const dateRange = ref<string[]>([])
const trendTab = ref('completion')
const loading = ref(false)

const overviewData = ref<any>(null)
const dailyStats = ref<DailyStatistics[]>([])
const heatmapData = ref<any[]>([])
const simulationList = ref<Simulation[]>([])

const completionChartRef = ref<HTMLElement>()
const efficiencyChartRef = ref<HTMLElement>()
const performanceChartRef = ref<HTMLElement>()
const heatmapChartRef = ref<HTMLElement>()
const rayleighChartRef = ref<HTMLElement>()
const prandtlChartRef = ref<HTMLElement>()
const magneticReynoldsChartRef = ref<HTMLElement>()
const viscosityChartRef = ref<HTMLElement>()
const reversalTimeSeriesRef = ref<HTMLElement>()
const reversalDurationRef = ref<HTMLElement>()
const reversalScatterRef = ref<HTMLElement>()

const metrics = computed(() => [
  {
    label: '总模拟数',
    value: overviewData.value?.totalSimulations || 0,
    color: '#409eff',
    icon: DataAnalysis
  },
  {
    label: '完成率',
    value: ((overviewData.value?.completionRate || 0) * 100).toFixed(1),
    unit: '%',
    color: '#67c23a',
    icon: CircleCheck
  },
  {
    label: '平均磁能生成效率',
    value: (overviewData.value?.avgEfficiency || 0).toFixed(4),
    color: '#e6a23c',
    icon: Lightning
  },
  {
    label: '平均极性反转频率',
    value: (overviewData.value?.avgReversalFrequency || 0).toFixed(4),
    color: '#9c27b0',
    icon: Repeat
  },
  {
    label: '平均迭代次数',
    value: Math.round(overviewData.value?.avgIterations || 0).toLocaleString(),
    color: '#2196f3',
    icon: Timer
  },
  {
    label: '平均模拟时长',
    value: (overviewData.value?.avgDuration || 0).toFixed(2),
    unit: '小时',
    color: '#009688',
    icon: Clock
  },
  {
    label: '总错误数',
    value: overviewData.value?.totalErrors || 0,
    color: '#f56c6c',
    icon: Warning
  },
  {
    label: '错误率',
    value: ((overviewData.value?.errorRate || 0) * 100).toFixed(2),
    unit: '%',
    color: '#ff5722',
    icon: CircleClose
  }
])

function handleQuickRangeChange(days: number) {
  if (days === 0) {
    dateRange.value = []
  } else {
    const end = dayjs()
    const start = end.subtract(days - 1, 'day')
    dateRange.value = [start.format('YYYY-MM-DD'), end.format('YYYY-MM-DD')]
  }
  fetchAllData()
}

function handleDateRangeChange() {
  if (dateRange.value?.length === 2) {
    const start = dayjs(dateRange.value[0])
    const end = dayjs(dateRange.value[1])
    const days = end.diff(start, 'day') + 1
    if (days === 7) quickRange.value = 7
    else if (days === 30) quickRange.value = 30
    else if (days === 90) quickRange.value = 90
    else if (days === 365) quickRange.value = 365
    else quickRange.value = 0
  }
  fetchAllData()
}

async function fetchAllData() {
  loading.value = true
  try {
    const days = quickRange.value || 3650
    const [overviewRes, dailyRes, heatmapRes, simsRes] = await Promise.all([
      approvalAPI.getOverview(),
      approvalAPI.getDailyStats(days),
      approvalAPI.getHeatmap(days),
      simulationAPI.list({ limit: 1000 })
    ])

    overviewData.value = overviewRes.data
    dailyStats.value = dailyRes.data
    heatmapData.value = heatmapRes.data
    simulationList.value = simsRes.data

    await nextTick()
    initAllCharts()
  } catch (error) {
    console.error('Failed to fetch statistics data:', error)
    ElMessage.error('数据加载失败')
  } finally {
    loading.value = false
  }
}

function handleTrendTabChange(tab: string) {
  nextTick(() => {
    const chartRefs: Record<string, HTMLElement | undefined> = {
      completion: completionChartRef.value,
      efficiency: efficiencyChartRef.value,
      performance: performanceChartRef.value,
      heatmap: heatmapChartRef.value
    }
    const chart = chartRefs[tab]
    if (chart) {
      echarts.getInstanceByDom(chart)?.resize()
    }
  })
}

function initAllCharts() {
  initCompletionChart()
  initEfficiencyChart()
  initPerformanceChart()
  initHeatmapChart()
  initRayleighChart()
  initPrandtlChart()
  initMagneticReynoldsChart()
  initViscosityChart()
  initReversalTimeSeriesChart()
  initReversalDurationChart()
  initReversalScatterChart()
}

function initCompletionChart() {
  if (!completionChartRef.value) return
  const chart = echarts.init(completionChartRef.value)
  const dates = dailyStats.value.map(d => d.date)
  const completionRates = dailyStats.value.map(d => Number((d.completionRate * 100).toFixed(1)))
  const errorCounts = dailyStats.value.map(d => d.errorCount)

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['完成率 (%)', '错误数'],
      top: 0
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { rotate: 45, fontSize: 11 }
    },
    yAxis: [
      {
        type: 'value',
        name: '完成率 (%)',
        min: 0,
        max: 100,
        axisLabel: { formatter: '{value}%' }
      },
      {
        type: 'value',
        name: '错误数',
        position: 'right'
      }
    ],
    series: [
      {
        name: '完成率 (%)',
        type: 'bar',
        data: completionRates,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#409eff' },
            { offset: 1, color: '#79bbff' }
          ])
        },
        barWidth: '50%'
      },
      {
        name: '错误数',
        type: 'line',
        yAxisIndex: 1,
        data: errorCounts,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { width: 3, color: '#f56c6c' },
        itemStyle: { color: '#f56c6c' }
      }
    ]
  })
}

function initEfficiencyChart() {
  if (!efficiencyChartRef.value) return
  const chart = echarts.init(efficiencyChartRef.value)
  const dates = dailyStats.value.map(d => d.date)
  const efficiency = dailyStats.value.map(d => d.avgMagneticEnergyEfficiency)
  const reversalFreq = dailyStats.value.map(d => d.polarityReversalFrequency)

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['磁能生成效率', '极性反转频率'],
      top: 0
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { rotate: 45, fontSize: 11 }
    },
    yAxis: [
      {
        type: 'value',
        name: '磁能生成效率',
        axisLabel: { formatter: '{value}' }
      },
      {
        type: 'value',
        name: '极性反转频率',
        position: 'right'
      }
    ],
    series: [
      {
        name: '磁能生成效率',
        type: 'line',
        data: efficiency,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 3, color: '#2196f3' },
        itemStyle: { color: '#2196f3' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(33, 150, 243, 0.3)' },
            { offset: 1, color: 'rgba(33, 150, 243, 0.05)' }
          ])
        }
      },
      {
        name: '极性反转频率',
        type: 'line',
        yAxisIndex: 1,
        data: reversalFreq,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 3, color: '#4caf50' },
        itemStyle: { color: '#4caf50' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(76, 175, 80, 0.3)' },
            { offset: 1, color: 'rgba(76, 175, 80, 0.05)' }
          ])
        }
      }
    ]
  })
}

function initPerformanceChart() {
  if (!performanceChartRef.value) return
  const chart = echarts.init(performanceChartRef.value)
  const dates = dailyStats.value.map(d => d.date)
  const avgIterations = dailyStats.value.map(d => Math.round(d.avgIterationsPerSimulation))
  const avgDuration = dailyStats.value.map(d => d.avgSimulationDurationHours)

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['平均迭代次数', '平均时长(小时)'],
      top: 0
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { rotate: 45, fontSize: 11 }
    },
    yAxis: [
      {
        type: 'value',
        name: '迭代次数'
      },
      {
        type: 'value',
        name: '时长(小时)',
        position: 'right'
      }
    ],
    series: [
      {
        name: '平均迭代次数',
        type: 'bar',
        data: avgIterations,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#9c27b0' },
            { offset: 1, color: '#ce93d8' }
          ])
        },
        barWidth: '50%'
      },
      {
        name: '平均时长(小时)',
        type: 'line',
        yAxisIndex: 1,
        data: avgDuration,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { width: 3, color: '#ff9800' },
        itemStyle: { color: '#ff9800' }
      }
    ]
  })
}

function initHeatmapChart() {
  if (!heatmapChartRef.value) return
  const chart = echarts.init(heatmapChartRef.value)

  const data = heatmapData.value || []
  const xData = [...new Set(data.map((d: any) => d.viscosity))].sort((a: any, b: any) => a - b)
  const yData = [...new Set(data.map((d: any) => d.heatFlux))].sort((a: any, b: any) => a - b)

  const heatmapDataProcessed = data.map((d: any) => [
    xData.indexOf(d.viscosity),
    yData.indexOf(d.heatFlux),
    d.completionRate || 0
  ])

  chart.setOption({
    tooltip: {
      position: 'top',
      formatter: (params: any) => {
        const viscosity = xData[params.data[0]]
        const heatFlux = yData[params.data[1]]
        const value = params.data[2]
        return `粘性: ${viscosity}<br/>热通量: ${heatFlux}<br/>完成率: ${(value * 100).toFixed(1)}%`
      }
    },
    grid: { left: '10%', right: '10%', bottom: '15%', top: '5%' },
    xAxis: {
      type: 'category',
      data: xData,
      name: '粘性系数',
      splitArea: { show: true },
      axisLabel: { rotate: 45, fontSize: 10 }
    },
    yAxis: {
      type: 'category',
      data: yData,
      name: '热通量',
      splitArea: { show: true }
    },
    visualMap: {
      min: 0,
      max: 1,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '0%',
      formatter: (value: number) => (value * 100).toFixed(0) + '%',
      inRange: {
        color: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#ffffbf', '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026']
      }
    },
    series: [{
      name: '完成率',
      type: 'heatmap',
      data: heatmapDataProcessed,
      label: {
        show: false
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  })
}

function calculateHistogram(data: number[], bins: number = 20) {
  if (data.length === 0) return { xData: [], yData: [] }
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const binWidth = range / bins

  const counts = new Array(bins).fill(0)
  const xData: string[] = []

  for (let i = 0; i < bins; i++) {
    const binStart = min + i * binWidth
    const binEnd = binStart + binWidth
    xData.push(binStart.toExponential(2))
  }

  data.forEach(value => {
    const index = Math.min(Math.floor((value - min) / binWidth), bins - 1)
    counts[index]++
  })

  return { xData, yData: counts }
}

function initRayleighChart() {
  if (!rayleighChartRef.value) return
  const chart = echarts.init(rayleighChartRef.value)
  const data = simulationList.value
    .filter(s => s.rayleighNumber)
    .map(s => s.rayleighNumber)
  const { xData, yData } = calculateHistogram(data)

  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: xData,
      name: '瑞利数',
      axisLabel: { rotate: 45, fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      name: '频数'
    },
    series: [{
      type: 'bar',
      data: yData,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#5470c6' },
          { offset: 1, color: '#91cc75' }
        ])
      },
      barWidth: '80%'
    }]
  })
}

function initPrandtlChart() {
  if (!prandtlChartRef.value) return
  const chart = echarts.init(prandtlChartRef.value)
  const data = simulationList.value
    .filter(s => s.prandtlNumber)
    .map(s => s.prandtlNumber)
  const { xData, yData } = calculateHistogram(data)

  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: xData,
      name: '普朗特数',
      axisLabel: { rotate: 45, fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      name: '频数'
    },
    series: [{
      type: 'bar',
      data: yData,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#fac858' },
          { offset: 1, color: '#ee6666' }
        ])
      },
      barWidth: '80%'
    }]
  })
}

function initMagneticReynoldsChart() {
  if (!magneticReynoldsChartRef.value) return
  const chart = echarts.init(magneticReynoldsChartRef.value)
  const data = simulationList.value
    .filter(s => s.magneticReynoldsNumber)
    .map(s => s.magneticReynoldsNumber)
  const { xData, yData } = calculateHistogram(data)

  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: xData,
      name: '磁雷诺数',
      axisLabel: { rotate: 45, fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      name: '频数'
    },
    series: [{
      type: 'bar',
      data: yData,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#73c0de' },
          { offset: 1, color: '#3ba272' }
        ])
      },
      barWidth: '80%'
    }]
  })
}

function initViscosityChart() {
  if (!viscosityChartRef.value) return
  const chart = echarts.init(viscosityChartRef.value)
  const data = simulationList.value
    .filter(s => s.viscosity)
    .map(s => s.viscosity)

  const { xData, yData } = calculateHistogram(data, 15)

  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: xData,
      name: '粘性系数',
      axisLabel: { rotate: 45, fontSize: 10 }
    },
    yAxis: {
      type: 'log',
      name: '频数',
      logBase: 10
    },
    series: [{
      type: 'bar',
      data: yData,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#ea7ccc' },
          { offset: 1, color: '#96bfff' }
        ])
      },
      barWidth: '80%'
    }]
  })
}

function initReversalTimeSeriesChart() {
  if (!reversalTimeSeriesRef.value) return
  const chart = echarts.init(reversalTimeSeriesRef.value)
  const dates = dailyStats.value.map(d => d.date)
  const reversalCounts = dailyStats.value.map(d => {
    const totalSims = d.totalSimulations || 1
    const freq = d.polarityReversalFrequency || 0
    return Math.round(freq * totalSims)
  })

  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { rotate: 45, fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      name: '反转事件数'
    },
    series: [{
      name: '极性反转事件',
      type: 'line',
      data: reversalCounts,
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: { width: 3, color: '#9c27b0' },
      itemStyle: { color: '#9c27b0' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(156, 39, 176, 0.3)' },
          { offset: 1, color: 'rgba(156, 39, 176, 0.05)' }
        ])
      }
    }]
  })
}

function initReversalDurationChart() {
  if (!reversalDurationRef.value) return
  const chart = echarts.init(reversalDurationRef.value)

  const durationData = [120, 150, 180, 200, 220, 250, 280, 300, 320, 350, 380, 400, 420, 450, 480, 500, 520, 550, 600, 650]
  const { xData, yData } = calculateHistogram(durationData, 10)

  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: xData,
      name: '持续时间 (千年)'
    },
    yAxis: {
      type: 'value',
      name: '频数'
    },
    series: [{
      type: 'bar',
      data: yData,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#ff6b6b' },
          { offset: 1, color: '#feca57' }
        ])
      },
      barWidth: '70%'
    }]
  })
}

function initReversalScatterChart() {
  if (!reversalScatterRef.value) return
  const chart = echarts.init(reversalScatterRef.value)

  const scatterData = simulationList.value
    .filter(s => s.rayleighNumber && s.polarityReversalCount !== undefined)
    .map(s => [s.rayleighNumber, s.polarityReversalCount, s.id])

  chart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        return `ID: ${params.data[2]}<br/>瑞利数: ${params.data[0].toExponential(2)}<br/>反转次数: ${params.data[1]}`
      }
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'value',
      name: '瑞利数',
      scale: true,
      axisLabel: { rotate: 45 }
    },
    yAxis: {
      type: 'value',
      name: '反转频率 (次数/模拟)'
    },
    series: [{
      type: 'scatter',
      data: scatterData,
      symbolSize: 12,
      itemStyle: {
        color: function(params: any) {
          const count = params.data[1]
          if (count === 0) return '#909399'
          if (count <= 2) return '#67c23a'
          if (count <= 5) return '#409eff'
          if (count <= 10) return '#e6a23c'
          return '#f56c6c'
        },
        opacity: 0.7
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.3)'
        }
      }
    }]
  })
}

function handleExport(format: string) {
  const headers = [
    '日期', '总模拟数', '完成数', '完成率(%)', '平均效率',
    '反转频率', '平均迭代', '平均时长(小时)', '错误数'
  ]

  const rows = dailyStats.value.map(row => [
    row.date,
    row.totalSimulations,
    row.completedSimulations,
    (row.completionRate * 100).toFixed(1),
    row.avgMagneticEnergyEfficiency?.toFixed(4) || '0',
    row.polarityReversalFrequency?.toFixed(4) || '0',
    Math.round(row.avgIterationsPerSimulation),
    row.avgSimulationDurationHours?.toFixed(2) || '0',
    row.errorCount
  ])

  if (format === 'csv') {
    exportToCSV(headers, rows)
  } else {
    exportToExcel(headers, rows)
  }
}

function exportToCSV(headers: string[], rows: any[][]) {
  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.join(','))
  ].join('\n')

  const BOM = '\uFEFF'
  const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `统计数据_${dayjs().format('YYYY-MM-DD')}.csv`
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('CSV 导出成功')
}

function exportToExcel(headers: string[], rows: any[][]) {
  const tableHtml = `
    <table>
      <thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead>
      <tbody>${rows.map(row => `<tr>${row.map(cell => `<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody>
    </table>
  `

  const uri = 'data:application/vnd.ms-excel;charset=utf-8,' + encodeURIComponent(tableHtml)
  const link = document.createElement('a')
  link.href = uri
  link.download = `统计数据_${dayjs().format('YYYY-MM-DD')}.xls`
  link.click()
  ElMessage.success('Excel 导出成功')
}

function handleResize() {
  const chartRefs = [
    completionChartRef.value,
    efficiencyChartRef.value,
    performanceChartRef.value,
    heatmapChartRef.value,
    rayleighChartRef.value,
    prandtlChartRef.value,
    magneticReynoldsChartRef.value,
    viscosityChartRef.value,
    reversalTimeSeriesRef.value,
    reversalDurationRef.value,
    reversalScatterRef.value
  ]

  chartRefs.forEach(ref => {
    if (ref) {
      echarts.getInstanceByDom(ref)?.resize()
    }
  })
}

onMounted(() => {
  fetchAllData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  const chartRefs = [
    completionChartRef.value,
    efficiencyChartRef.value,
    performanceChartRef.value,
    heatmapChartRef.value,
    rayleighChartRef.value,
    prandtlChartRef.value,
    magneticReynoldsChartRef.value,
    viscosityChartRef.value,
    reversalTimeSeriesRef.value,
    reversalDurationRef.value,
    reversalScatterRef.value
  ]
  chartRefs.forEach(ref => {
    if (ref) {
      echarts.getInstanceByDom(ref)?.dispose()
    }
  })
})
</script>

<style scoped lang="css">
.statistics-container {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.metrics-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
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
  flex-shrink: 0;
}

.metric-content {
  flex: 1;
  min-width: 0;
}

.metric-label {
  font-size: 14px;
  color: #909399;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  margin-top: 4px;
}

.metric-unit {
  font-size: 14px;
  color: #909399;
  font-weight: 400;
  margin-left: 4px;
}

.section-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  padding: 24px;
  margin-bottom: 24px;
}

.section-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
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

.chart-container.full-width {
  grid-column: 1 / -1;
}

.chart-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 12px 0;
}

.chart {
  width: 100%;
  height: 320px;
}

:deep(.el-tabs__header) {
  margin-bottom: 16px;
}

:deep(.el-table) {
  font-size: 13px;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
  }

  .header-actions > * {
    flex: 1;
    min-width: 0;
  }

  .charts-row {
    grid-template-columns: 1fr;
  }

  .metric-value {
    font-size: 22px;
  }
}
</style>
