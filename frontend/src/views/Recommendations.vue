<template>
  <div class="recommendations page-container">
    <div class="page-header">
      <h2>智能参数推荐</h2>
      <p class="page-desc">基于古地磁记录，使用机器学习模型推荐最佳模拟参数</p>
    </div>

    <el-row :gutter="24">
      <el-col :span="8">
        <div class="input-card">
          <div class="card-header">
            <el-icon><Edit /></el-icon>
            <span>古地磁记录输入</span>
          </div>
          <el-form
            ref="formRef"
            :model="formData"
            :rules="rules"
            label-width="160px"
            label-position="right"
          >
            <el-form-item label="记录名称" prop="recordName">
              <el-input
                v-model="formData.recordName"
                placeholder="请输入古地磁记录名称"
              />
            </el-form-item>
            <el-form-item label="目标函数" prop="objectiveFunction">
              <el-select v-model="formData.objectiveFunction" placeholder="请选择目标函数">
                <el-option label="最小二乘法" value="least_squares" />
                <el-option label="最大似然估计" value="maximum_likelihood" />
                <el-option label="贝叶斯估计" value="bayesian" />
                <el-option label="加权平均法" value="weighted_average" />
              </el-select>
            </el-form-item>
            <el-form-item label="地质年代 (Ma)" prop="geologicalAge">
              <el-input-number
                v-model="formData.geologicalAge"
                :min="0.1"
                :max="4500"
                :step="1"
                :precision="2"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="目标偶极矩 (A·m²)" prop="targetDipoleMoment">
              <el-input-number
                v-model="formData.targetDipoleMoment"
                :min="1e20"
                :max="1e24"
                :step="1e20"
                :precision="2"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="极性反转频率 (次/Ma)" prop="targetReversalFrequency">
              <el-input-number
                v-model="formData.targetReversalFrequency"
                :min="0"
                :max="10"
                :step="0.1"
                :precision="2"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="古地磁场强度 (μT)" prop="paleointensity">
              <el-input-number
                v-model="formData.paleointensity"
                :min="1"
                :max="100"
                :step="1"
                :precision="2"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="古温度估计 (K)" prop="paleotemperature">
              <el-input-number
                v-model="formData.paleotemperature"
                :min="200"
                :max="8000"
                :step="10"
                :precision="2"
                style="width: 100%"
              />
            </el-form-item>
          </el-form>
          <div class="action-buttons">
            <el-button
              type="primary"
              :loading="loadingRecommendation"
              @click="handleGetRecommendation"
            >
              <el-icon><MagicStick /></el-icon>
              获取推荐
            </el-button>
            <el-button
              v-if="isAdmin"
              type="warning"
              :loading="trainingModel"
              @click="handleTrainModel"
            >
              <el-icon><Refresh /></el-icon>
              重新训练模型
            </el-button>
            <el-button @click="handleShowHistory">
              <el-icon><History /></el-icon>
              历史推荐记录
            </el-button>
            <el-button
              type="success"
              :disabled="!recommendationResult"
              @click="handleCreateSimulation"
            >
              <el-icon><Plus /></el-icon>
              使用推荐参数创建模拟
            </el-button>
          </div>
        </div>

        <div class="model-card">
          <div class="card-header">
            <el-icon><Cpu /></el-icon>
            <span>模型信息</span>
          </div>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="模型状态">
              <el-tag :type="modelInfo.isTrained ? 'success' : 'info'">
                {{ modelInfo.isTrained ? '已训练' : '未训练' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="训练样本数">
              {{ modelInfo.totalSamples || '0' }}
            </el-descriptions-item>
            <el-descriptions-item label="R² 分数">
              <el-progress
                :percentage="Math.round((modelInfo.r2Score || 0) * 100)"
                :color="getR2Color(modelInfo.r2Score)"
                :stroke-width="10"
              />
            </el-descriptions-item>
            <el-descriptions-item label="RMSE">
              {{ modelInfo.rmse ? modelInfo.rmse.toFixed(6) : 'N/A' }}
            </el-descriptions-item>
          </el-descriptions>
          <div class="chart-title">特征重要性</div>
          <div ref="featureImportanceChartRef" class="feature-chart"></div>
        </div>
      </el-col>

      <el-col :span="16">
        <div v-if="recommendationResult" class="result-card">
          <div class="card-header">
            <el-icon><Star /></el-icon>
            <span>智能推荐结果</span>
            <el-tag class="confidence-tag" :type="getConfidenceType(recommendationResult.confidenceScore)">
              置信度 {{ (recommendationResult.confidenceScore * 100).toFixed(1) }}%
            </el-tag>
          </div>

          <el-row :gutter="24" class="result-summary">
            <el-col :span="8">
              <div class="stat-item">
                <div class="stat-label">推荐粘性系数</div>
                <div class="stat-value">{{ formatScientific(recommendationResult.recommendedViscosity) }} Pa·s</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-item">
                <div class="stat-label">推荐内核增长速率</div>
                <div class="stat-value">{{ formatScientific(recommendationResult.recommendedInnerCoreGrowthRate) }} m/s</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-item">
                <div class="stat-label">模型版本</div>
                <div class="stat-value">{{ recommendationResult.modelVersion }}</div>
              </div>
            </el-col>
          </el-row>

          <div class="info-section">
            <div class="section-title">
              <el-icon><InfoFilled /></el-icon>
              目标古地磁记录：{{ recommendationResult.targetPaleomagneticRecord }}
            </div>
          </div>

          <div class="info-section">
            <div class="section-title">
              <el-icon><Collection /></el-icon>
              使用的特征
            </div>
            <div class="feature-tags">
              <el-tag v-for="feature in recommendationResult.usedFeatures" :key="feature" class="feature-tag">
                {{ feature }}
              </el-tag>
            </div>
          </div>

          <div class="info-section">
            <div class="section-title">
              <el-icon><List /></el-icon>
              匹配的历史模拟
            </div>
            <el-table :data="recommendationResult.matchingSimulations" size="small" stripe>
              <el-table-column prop="simulationId" label="模拟ID" width="100" />
              <el-table-column prop="simulationName" label="模拟名称" min-width="150" />
              <el-table-column prop="similarityScore" label="相似度" width="120">
                <template #default="{ row }">
                  <el-progress
                    :percentage="Math.round(row.similarityScore * 100)"
                    :stroke-width="8"
                    size="small"
                  />
                </template>
              </el-table-column>
              <el-table-column prop="viscosity" label="粘性系数 (Pa·s)" width="160">
                <template #default="{ row }">
                  {{ formatScientific(row.viscosity) }}
                </template>
              </el-table-column>
              <el-table-column prop="innerCoreGrowthRate" label="内核增长速率 (m/s)" width="180">
                <template #default="{ row }">
                  {{ formatScientific(row.innerCoreGrowthRate) }}
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <div v-else class="empty-result">
          <el-empty description="请输入古地磁记录参数并点击「获取推荐」按钮">
            <el-button type="primary" @click="handleGetRecommendation">获取推荐</el-button>
          </el-empty>
        </div>

        <el-row :gutter="24" class="charts-row">
          <el-col :span="12">
            <div class="chart-card">
              <div class="card-header">
                <el-icon><Scatter /></el-icon>
                <span>参数空间散点图</span>
              </div>
              <div ref="scatterChartRef" class="chart-container"></div>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="chart-card">
              <div class="card-header">
                <el-icon><DataLine /></el-icon>
                <span>匹配模拟雷达图</span>
              </div>
              <div ref="radarChartRef" class="chart-container"></div>
            </div>
          </el-col>
        </el-row>
      </el-col>
    </el-row>

    <el-dialog
      v-model="historyDialogVisible"
      title="历史推荐记录"
      width="900px"
      :close-on-click-modal="false"
    >
      <el-table :data="historyRecommendations" v-loading="loadingHistory" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="targetPaleomagneticRecord" label="目标记录" min-width="150" />
        <el-table-column prop="recommendedViscosity" label="推荐粘性" width="160">
          <template #default="{ row }">
            {{ formatScientific(row.recommendedViscosity) }}
          </template>
        </el-table-column>
        <el-table-column prop="recommendedInnerCoreGrowthRate" label="推荐内核增长速率" width="180">
          <template #default="{ row }">
            {{ formatScientific(row.recommendedInnerCoreGrowthRate) }}
          </template>
        </el-table-column>
        <el-table-column prop="confidenceScore" label="置信度" width="120">
          <template #default="{ row }">
            <el-tag :type="getConfidenceType(row.confidenceScore)" size="small">
              {{ (row.confidenceScore * 100).toFixed(1) }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="modelVersion" label="模型版本" width="120" />
        <el-table-column prop="createdAt" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.createdAt) }}
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="historyDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import {
  Edit,
  MagicStick,
  Refresh,
  History,
  Plus,
  Cpu,
  Star,
  InfoFilled,
  Collection,
  List,
  Scatter,
  DataLine
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { reportsAPI } from '@/api'
import { useAuthStore } from '@/stores/auth'
import type { Recommendation } from '@/types'

interface PaleomagneticInput {
  recordName: string
  objectiveFunction: string
  geologicalAge: number
  targetDipoleMoment: number
  targetReversalFrequency: number
  paleointensity: number
  paleotemperature: number
}

interface MatchingSimulation {
  simulationId: number
  simulationName: string
  similarityScore: number
  viscosity: number
  innerCoreGrowthRate: number
  dipoleMoment: number
  reversalFrequency: number
  paleointensity: number
  paleotemperature: number
}

interface RecommendationResult {
  id: number
  targetPaleomagneticRecord: string
  recommendedViscosity: number
  recommendedInnerCoreGrowthRate: number
  confidenceScore: number
  matchingSimulations: MatchingSimulation[]
  usedFeatures: string[]
  modelVersion: string
  createdAt: string
}

interface ModelInfo {
  isTrained: boolean
  totalSamples: number
  featureImportance: { name: string; importance: number }[]
  r2Score: number
  rmse: number
}

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const featureImportanceChartRef = ref<HTMLElement>()
const scatterChartRef = ref<HTMLElement>()
const radarChartRef = ref<HTMLElement>()

let featureImportanceChart: echarts.ECharts | null = null
let scatterChart: echarts.ECharts | null = null
let radarChart: echarts.ECharts | null = null

const loadingRecommendation = ref(false)
const trainingModel = ref(false)
const loadingHistory = ref(false)
const historyDialogVisible = ref(false)
const loadingModelInfo = ref(false)

const isAdmin = authStore.userRole === 'admin'

const formData = reactive<PaleomagneticInput>({
  recordName: '',
  objectiveFunction: 'least_squares',
  geologicalAge: 100,
  targetDipoleMoment: 8e22,
  targetReversalFrequency: 4,
  paleointensity: 50,
  paleotemperature: 5000
})

const rules: FormRules = {
  recordName: [
    { required: true, message: '请输入记录名称', trigger: 'blur' }
  ],
  objectiveFunction: [
    { required: true, message: '请选择目标函数', trigger: 'change' }
  ],
  geologicalAge: [
    { required: true, message: '请输入地质年代', trigger: 'blur' }
  ],
  targetDipoleMoment: [
    { required: true, message: '请输入目标偶极矩', trigger: 'blur' }
  ],
  targetReversalFrequency: [
    { required: true, message: '请输入极性反转频率', trigger: 'blur' }
  ],
  paleointensity: [
    { required: true, message: '请输入古地磁场强度', trigger: 'blur' }
  ],
  paleotemperature: [
    { required: true, message: '请输入古温度估计', trigger: 'blur' }
  ]
}

const recommendationResult = ref<RecommendationResult | null>(null)
const historyRecommendations = ref<Recommendation[]>([])

const modelInfo = reactive<ModelInfo>({
  isTrained: false,
  totalSamples: 0,
  featureImportance: [],
  r2Score: 0,
  rmse: 0
})

function formatScientific(num: number): string {
  if (num === 0) return '0'
  const exp = Math.floor(Math.log10(Math.abs(num)))
  const mantissa = num / Math.pow(10, exp)
  return `${mantissa.toFixed(2)} × 10^${exp}`
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN')
}

function getConfidenceType(score: number): 'success' | 'warning' | 'info' | 'danger' {
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'warning'
  if (score >= 0.4) return 'info'
  return 'danger'
}

function getR2Color(score: number): string {
  if (!score) return '#dcdfe6'
  if (score >= 0.8) return '#67c23a'
  if (score >= 0.6) return '#e6a23c'
  if (score >= 0.4) return '#f56c6c'
  return '#909399'
}

async function handleGetRecommendation() {
  try {
    await formRef.value?.validate()
  } catch (error) {
    ElMessage.error('请完善所有必填项')
    return
  }

  loadingRecommendation.value = true
  try {
    const response = await reportsAPI.getRecommendation({
      record_name: formData.recordName,
      objective_function: formData.objectiveFunction,
      geological_age: formData.geologicalAge,
      target_dipole_moment: formData.targetDipoleMoment,
      target_reversal_frequency: formData.targetReversalFrequency,
      paleointensity: formData.paleointensity,
      paleotemperature: formData.paleotemperature
    }, 5)

    const data = response.data
    recommendationResult.value = {
      id: data.id,
      targetPaleomagneticRecord: data.targetPaleomagneticRecord,
      recommendedViscosity: data.recommendedViscosity,
      recommendedInnerCoreGrowthRate: data.recommendedInnerCoreGrowthRate,
      confidenceScore: data.confidenceScore,
      matchingSimulations: data.matchingSimulations || [],
      usedFeatures: data.usedFeatures || [],
      modelVersion: data.modelVersion,
      createdAt: data.createdAt
    }

    ElMessage.success('获取推荐成功')

    await nextTick()
    updateScatterChart()
    updateRadarChart()
    await loadModelInfo()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '获取推荐失败，请稍后重试')
  } finally {
    loadingRecommendation.value = false
  }
}

async function handleTrainModel() {
  trainingModel.value = true
  try {
    await reportsAPI.trainModel()
    ElMessage.success('模型训练任务已提交，请稍后刷新查看')
    await loadModelInfo()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '训练模型失败，请稍后重试')
  } finally {
    trainingModel.value = false
  }
}

async function handleShowHistory() {
  historyDialogVisible.value = true
  loadingHistory.value = true
  try {
    const response = await reportsAPI.listRecommendations(20)
    historyRecommendations.value = response.data
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '获取历史记录失败')
  } finally {
    loadingHistory.value = false
  }
}

function handleCreateSimulation() {
  if (!recommendationResult.value) return

  router.push({
    path: '/simulations/create',
    query: {
      viscosity: recommendationResult.value.recommendedViscosity.toString(),
      innerCoreGrowthRate: recommendationResult.value.recommendedInnerCoreGrowthRate.toString(),
      fromRecommendation: 'true',
      recommendationId: recommendationResult.value.id.toString()
    }
  })
}

async function loadModelInfo() {
  loadingModelInfo.value = true
  try {
    const response = await reportsAPI.getModelInfo()
    const data = response.data
    modelInfo.isTrained = data.isTrained
    modelInfo.totalSamples = data.totalSamples
    modelInfo.featureImportance = data.featureImportance || []
    modelInfo.r2Score = data.r2Score
    modelInfo.rmse = data.rmse

    await nextTick()
    updateFeatureImportanceChart()
  } catch (error: any) {
    console.error('Failed to load model info:', error)
  } finally {
    loadingModelInfo.value = false
  }
}

function initFeatureImportanceChart() {
  if (!featureImportanceChartRef.value) return
  featureImportanceChart = echarts.init(featureImportanceChartRef.value)
  updateFeatureImportanceChart()
}

function updateFeatureImportanceChart() {
  if (!featureImportanceChart || !modelInfo.featureImportance.length) return

  const sortedFeatures = [...modelInfo.featureImportance].sort((a, b) => a.importance - b.importance)

  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const data = params[0]
        return `${data.name}<br/>重要性: ${(data.value * 100).toFixed(2)}%`
      }
    },
    grid: {
      left: '3%',
      right: '10%',
      bottom: '3%',
      top: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      max: 1,
      axisLabel: {
        formatter: (value: number) => `${(value * 100).toFixed(0)}%`
      }
    },
    yAxis: {
      type: 'category',
      data: sortedFeatures.map(f => f.name),
      axisLabel: {
        fontSize: 11
      }
    },
    series: [{
      type: 'bar',
      data: sortedFeatures.map(f => f.importance),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#83bff6' },
          { offset: 0.5, color: '#188df0' },
          { offset: 1, color: '#188df0' }
        ]),
        borderRadius: [0, 4, 4, 0]
      },
      label: {
        show: true,
        position: 'right',
        formatter: (params: any) => `${(params.value * 100).toFixed(1)}%`,
        fontSize: 11
      }
    }]
  }

  featureImportanceChart.setOption(option)
}

function initScatterChart() {
  if (!scatterChartRef.value) return
  scatterChart = echarts.init(scatterChartRef.value)
  updateScatterChart()
}

function updateScatterChart() {
  if (!scatterChart) return

  const historicalData: number[][] = recommendationResult.value?.matchingSimulations
    .map(s => [Math.log10(s.viscosity), Math.log10(s.innerCoreGrowthRate), s.similarityScore]) || []

  const recommendedData: number[][] = recommendationResult.value
    ? [[Math.log10(recommendationResult.value.recommendedViscosity), Math.log10(recommendationResult.value.recommendedInnerCoreGrowthRate), 1]]
    : []

  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const data = params.data
        if (params.seriesName === '推荐点') {
          return `推荐参数<br/>粘性系数: ${formatScientific(Math.pow(10, data[0]))} Pa·s<br/>内核增长速率: ${formatScientific(Math.pow(10, data[1]))} m/s`
        }
        return `历史模拟 #${params.dataIndex + 1}<br/>粘性系数: ${formatScientific(Math.pow(10, data[0]))} Pa·s<br/>内核增长速率: ${formatScientific(Math.pow(10, data[1]))} m/s<br/>相似度: ${(data[2] * 100).toFixed(1)}%`
      }
    },
    legend: {
      data: ['历史模拟', '推荐点'],
      top: 0
    },
    grid: {
      left: '10%',
      right: '10%',
      bottom: '15%',
      top: '15%'
    },
    xAxis: {
      type: 'value',
      name: 'log₁₀(粘性系数 Pa·s)',
      nameLocation: 'middle',
      nameGap: 30,
      axisLabel: {
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      name: 'log₁₀(内核增长速率 m/s)',
      nameLocation: 'middle',
      nameGap: 40,
      axisLabel: {
        fontSize: 10
      }
    },
    series: [
      {
        name: '历史模拟',
        type: 'scatter',
        data: historicalData,
        symbolSize: (data: number[]) => 10 + data[2] * 20,
        itemStyle: {
          color: new echarts.graphic.RadialGradient(0.4, 0.3, 1, [
            { offset: 0, color: 'rgba(129, 140, 248, 0.8)' },
            { offset: 1, color: 'rgba(99, 102, 241, 0.6)' }
          ])
        },
        emphasis: {
          itemStyle: {
            color: 'rgba(99, 102, 241, 1)',
            shadowBlur: 10,
            shadowColor: 'rgba(99, 102, 241, 0.5)'
          }
        }
      },
      {
        name: '推荐点',
        type: 'scatter',
        data: recommendedData,
        symbolSize: 30,
        symbol: 'diamond',
        itemStyle: {
          color: '#f56c6c',
          shadowBlur: 10,
          shadowColor: 'rgba(245, 108, 108, 0.5)'
        },
        label: {
          show: true,
          position: 'top',
          formatter: '推荐',
          color: '#f56c6c',
          fontWeight: 'bold'
        },
        zlevel: 10
      }
    ]
  }

  scatterChart.setOption(option)
}

function initRadarChart() {
  if (!radarChartRef.value) return
  radarChart = echarts.init(radarChartRef.value)
  updateRadarChart()
}

function updateRadarChart() {
  if (!radarChart || !recommendationResult.value) return

  const indicators = [
    { name: '偶极矩', max: 1 },
    { name: '反转频率', max: 1 },
    { name: '磁场强度', max: 1 },
    { name: '古温度', max: 1 },
    { name: '粘性系数', max: 1 },
    { name: '内核增长', max: 1 }
  ]

  const targetValues = [
    formData.targetDipoleMoment / 1e23,
    formData.targetReversalFrequency / 10,
    formData.paleointensity / 100,
    formData.paleotemperature / 8000,
    Math.log10(recommendationResult.value.recommendedViscosity) / 3 + 2,
    Math.log10(recommendationResult.value.recommendedInnerCoreGrowthRate) / 10 + 2
  ].map(v => Math.min(1, Math.max(0, v)))

  const seriesData: any[] = [
    {
      name: '目标值',
      value: targetValues,
      lineStyle: { width: 3 },
      areaStyle: {
        color: 'rgba(245, 108, 108, 0.3)'
      },
      itemStyle: { color: '#f56c6c' }
    }
  ]

  const colors = ['#409eff', '#67c23a', '#e6a23c', '#909399', '#722ed1']
  recommendationResult.value.matchingSimulations.slice(0, 3).forEach((sim, index) => {
    const simValues = [
      sim.dipoleMoment / 1e23,
      sim.reversalFrequency / 10,
      sim.paleointensity / 100,
      sim.paleotemperature / 8000,
      Math.log10(sim.viscosity) / 3 + 2,
      Math.log10(sim.innerCoreGrowthRate) / 10 + 2
    ].map(v => Math.min(1, Math.max(0, v)))

    seriesData.push({
      name: `匹配模拟 ${index + 1}`,
      value: simValues,
      lineStyle: { width: 2, type: 'dashed' },
      areaStyle: {
        color: `${colors[index]}20`
      },
      itemStyle: { color: colors[index] }
    })
  })

  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'item'
    },
    legend: {
      data: seriesData.map(d => d.name),
      bottom: 0,
      type: 'scroll'
    },
    radar: {
      indicator: indicators,
      center: ['50%', '50%'],
      radius: '60%',
      startAngle: 90,
      splitNumber: 4,
      shape: 'polygon',
      axisName: {
        fontSize: 11,
        color: '#606266'
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(64, 158, 255, 0.05)', 'rgba(64, 158, 255, 0.1)']
        }
      }
    },
    series: [{
      type: 'radar',
      data: seriesData
    }]
  }

  radarChart.setOption(option)
}

function handleResize() {
  featureImportanceChart?.resize()
  scatterChart?.resize()
  radarChart?.resize()
}

onMounted(async () => {
  await nextTick()
  initFeatureImportanceChart()
  initScatterChart()
  initRadarChart()
  await loadModelInfo()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  featureImportanceChart?.dispose()
  scatterChart?.dispose()
  radarChart?.dispose()
})

watch(
  () => [featureImportanceChartRef.value, scatterChartRef.value, radarChartRef.value],
  () => {
    nextTick(() => {
      if (!featureImportanceChart && featureImportanceChartRef.value) {
        initFeatureImportanceChart()
      }
      if (!scatterChart && scatterChartRef.value) {
        initScatterChart()
      }
      if (!radarChart && radarChartRef.value) {
        initRadarChart()
      }
    })
  }
)
</script>

<style scoped lang="css">
.recommendations {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.page-desc {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.input-card,
.model-card,
.result-card,
.chart-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  margin-bottom: 24px;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 24px;
  border-bottom: 1px solid #ebeef5;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.card-header .el-icon {
  color: #409eff;
}

.input-card :deep(.el-form) {
  padding: 24px;
}

.action-buttons {
  padding: 0 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.action-buttons .el-button {
  width: 100%;
  justify-content: center;
  gap: 8px;
}

.model-card {
  padding-bottom: 16px;
}

.model-card :deep(.el-descriptions) {
  margin: 16px 24px;
}

.chart-title {
  padding: 16px 24px 8px;
  font-size: 14px;
  font-weight: 600;
  color: #606266;
}

.feature-chart {
  height: 240px;
  padding: 0 16px;
}

.result-card .card-header {
  justify-content: space-between;
}

.confidence-tag {
  margin-left: auto;
}

.result-summary {
  padding: 24px;
}

.stat-item {
  text-align: center;
  padding: 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
  border-radius: 8px;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.info-section {
  margin: 0 24px 24px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 12px;
}

.section-title .el-icon {
  color: #409eff;
}

.feature-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.feature-tag {
  font-size: 13px;
}

.empty-result {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  padding: 60px 24px;
  margin-bottom: 24px;
}

.charts-row {
  margin-top: 0;
}

.chart-container {
  height: 350px;
  padding: 8px;
}

@media (max-width: 1200px) {
  .charts-row .el-col {
    width: 100% !important;
  }
}
</style>
