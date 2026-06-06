<template>
  <div class="reviews-container page-container">
    <div class="page-header">
      <h2 class="page-title">复核管理</h2>
      <p class="page-desc">管理和复核模拟预警，调整参数并重新计算</p>
    </div>

    <div class="card-shadow tabs-card">
      <el-tabs v-model="activeTab" class="reviews-tabs">
        <el-tab-pane label="待复核" name="pending">
          <div class="table-toolbar">
            <div class="toolbar-left">
              <el-button @click="fetchPendingAlerts">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
              <span class="count-badge">
                共 <strong>{{ pendingAlerts.length }}</strong> 条待复核
              </span>
            </div>
          </div>

          <el-table
            :data="sortedPendingAlerts"
            v-loading="pendingLoading"
            stripe
            style="width: 100%"
            empty-text="暂无待复核预警"
          >
            <el-table-column label="等级" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="getAlertLevelType(row.level)" effect="dark" size="small">
                  {{ getAlertLevelText(row.level) }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />

            <el-table-column prop="message" label="消息" min-width="220" show-overflow-tooltip />

            <el-table-column label="相关模拟" width="120" align="center">
              <template #default="{ row }">
                <span class="simulation-link" @click="goToSimulation(row.simulationId)">
                  #{{ row.simulationId }}
                </span>
              </template>
            </el-table-column>

            <el-table-column label="指标信息" min-width="200">
              <template #default="{ row }">
                <div class="metric-info">
                  <div class="metric-row">
                    <span class="metric-label">指标:</span>
                    <span class="metric-name">{{ row.metricName || '-' }}</span>
                  </div>
                  <div class="metric-row">
                    <span class="metric-label">当前值:</span>
                    <span class="metric-value highlight">{{ row.metricValue?.toFixed(4) || '-' }}</span>
                    <span class="metric-label" style="margin-left: 12px;">阈值:</span>
                    <span class="metric-value">{{ row.threshold?.toFixed(4) || '-' }}</span>
                  </div>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="创建时间" width="160" align="center">
              <template #default="{ row }">
                {{ formatDate(row.createdAt) }}
              </template>
            </el-table-column>

            <el-table-column label="操作" width="120" align="center" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="openReviewDialog(row)">
                  <el-icon><Check /></el-icon>
                  复核
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div v-if="pendingAlerts.length === 0 && !pendingLoading" class="empty-state">
            <el-empty description="暂无待复核预警" :image-size="100">
              <template #image>
                <el-icon :size="80" color="#c0c4cc"><CircleCheck /></el-icon>
              </template>
            </el-empty>
          </div>
        </el-tab-pane>

        <el-tab-pane label="已复核" name="reviewed">
          <div class="table-toolbar">
            <div class="toolbar-left">
              <el-button @click="fetchReviewedAlerts">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </div>

          <el-table
            :data="reviewedAlerts"
            v-loading="reviewedLoading"
            stripe
            style="width: 100%"
            empty-text="暂无已复核记录"
          >
            <el-table-column label="等级" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="getAlertLevelType(row.level)" effect="dark" size="small">
                  {{ getAlertLevelText(row.level) }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column prop="title" label="标题" min-width="150" show-overflow-tooltip />

            <el-table-column label="复核结果" width="100" align="center">
              <template #default="{ row }">
                <el-tag
                  :type="row.latestReview?.approved ? 'success' : 'danger'"
                  effect="light"
                  size="small"
                >
                  {{ row.latestReview?.approved ? '通过' : '拒绝' }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column label="复核人" width="120" align="center">
              <template #default="{ row }">
                {{ row.latestReview?.reviewerName || '-' }}
              </template>
            </el-table-column>

            <el-table-column label="复核时间" width="160" align="center">
              <template #default="{ row }">
                {{ formatDate(row.latestReview?.createdAt) }}
              </template>
            </el-table-column>

            <el-table-column label="调整参数" min-width="280">
              <template #default="{ row }">
                <div class="adjustment-info">
                  <div v-if="row.latestReview?.suggestCmbAdjustment" class="adjustment-item">
                    <span class="adjustment-label">CMB热通量:</span>
                    <span class="adjustment-value">
                      {{ row.latestReview.suggestCmbAdjustment > 0 ? '+' : '' }}
                      {{ row.latestReview.suggestCmbAdjustment.toFixed(4) }}
                    </span>
                  </div>
                  <div v-if="row.latestReview?.suggestInnerCoreAdjustment" class="adjustment-item">
                    <span class="adjustment-label">内核半径:</span>
                    <span class="adjustment-value">
                      {{ row.latestReview.suggestInnerCoreAdjustment > 0 ? '+' : '' }}
                      {{ row.latestReview.suggestInnerCoreAdjustment.toFixed(4) }}
                    </span>
                  </div>
                  <div v-if="row.latestReview?.suggestViscosityAdjustment" class="adjustment-item">
                    <span class="adjustment-label">粘性系数:</span>
                    <span class="adjustment-value">
                      {{ row.latestReview.suggestViscosityAdjustment > 0 ? '+' : '' }}
                      {{ row.latestReview.suggestViscosityAdjustment.toExponential(2) }}
                    </span>
                  </div>
                  <span v-if="!hasAnyAdjustment(row.latestReview)" class="no-adjustment">
                    无调整
                  </span>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="复核意见" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.latestReview?.comments || '-' }}
              </template>
            </el-table-column>

            <el-table-column label="操作" width="180" align="center" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="row.simulationStatus === SimulationStatus.ADJUSTING"
                  type="success"
                  link
                  size="small"
                  :loading="restartingIds.includes(row.simulationId)"
                  @click="handleRestartSimulation(row)"
                >
                  <el-icon><VideoPlay /></el-icon>
                  重新计算
                </el-button>
                <el-button
                  v-if="row.latestReview"
                  type="primary"
                  link
                  size="small"
                  @click="viewReviewHistory(row)"
                >
                  <el-icon><View /></el-icon>
                  历史
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div v-if="reviewedAlerts.length === 0 && !reviewedLoading" class="empty-state">
            <el-empty description="暂无已复核记录" :image-size="100">
              <template #image>
                <el-icon :size="80" color="#c0c4cc"><Document /></el-icon>
              </template>
            </el-empty>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-dialog
      v-model="reviewDialogVisible"
      title="预警复核"
      width="700px"
      :close-on-click-modal="false"
    >
      <div v-if="currentAlert" class="review-dialog-content">
        <div class="alert-detail-section">
          <h4 class="section-title">预警详情</h4>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="等级">
              <el-tag :type="getAlertLevelType(currentAlert.level)" effect="dark" size="small">
                {{ getAlertLevelText(currentAlert.level) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="模拟ID">
              <span class="simulation-link" @click="goToSimulation(currentAlert.simulationId)">
                #{{ currentAlert.simulationId }}
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="标题" :span="2">
              {{ currentAlert.title }}
            </el-descriptions-item>
            <el-descriptions-item label="消息" :span="2">
              {{ currentAlert.message }}
            </el-descriptions-item>
            <el-descriptions-item label="指标名称">
              {{ currentAlert.metricName || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatDate(currentAlert.createdAt) }}
            </el-descriptions-item>
            <el-descriptions-item label="当前值">
              <span class="highlight">{{ currentAlert.metricValue?.toFixed(4) || '-' }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="阈值">
              {{ currentAlert.threshold?.toFixed(4) || '-' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <div v-if="currentSimulation" class="simulation-detail-section">
          <h4 class="section-title">模拟基本信息</h4>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="模拟名称">
              {{ currentSimulation.name }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="getStatusType(currentSimulation.status)" effect="light" size="small">
                {{ currentSimulation.status }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="CMB热通量">
              {{ currentSimulation.cmbHeatFlux?.toFixed(4) || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="内核半径">
              {{ currentSimulation.innerCoreRadius?.toFixed(4) || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="粘性系数" :span="2">
              {{ currentSimulation.viscosity?.toExponential(2) || '-' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <el-divider />

        <el-form
          ref="reviewFormRef"
          :model="reviewForm"
          :rules="reviewRules"
          label-width="140px"
          class="review-form"
        >
          <el-form-item label="复核结果" prop="approved">
            <el-radio-group v-model="reviewForm.approved">
              <el-radio :value="true">
                <el-icon style="color: #67c23a"><CircleCheck /></el-icon>
                通过
              </el-radio>
              <el-radio :value="false">
                <el-icon style="color: #f56c6c"><CircleClose /></el-icon>
                拒绝
              </el-radio>
            </el-radio-group>
          </el-form-item>

          <el-divider content-position="left">建议调整参数</el-divider>

          <el-form-item label="CMB热通量调整值">
            <el-input-number
              v-model="reviewForm.suggestCmbAdjustment"
              :precision="4"
              :step="0.0001"
              style="width: 100%"
              placeholder="输入调整值（可为正负）"
            />
            <span class="form-tip">
              当前值: {{ currentSimulation?.cmbHeatFlux?.toFixed(4) || '-' }}
            </span>
          </el-form-item>

          <el-form-item label="内核半径调整值">
            <el-input-number
              v-model="reviewForm.suggestInnerCoreAdjustment"
              :precision="4"
              :step="0.0001"
              style="width: 100%"
              placeholder="输入调整值（可为正负）"
            />
            <span class="form-tip">
              当前值: {{ currentSimulation?.innerCoreRadius?.toFixed(4) || '-' }}
            </span>
          </el-form-item>

          <el-form-item label="粘性系数调整值">
            <el-input-number
              v-model="reviewForm.suggestViscosityAdjustment"
              :precision="6"
              :step="0.000001"
              style="width: 100%"
              placeholder="输入调整值（可为正负）"
            />
            <span class="form-tip">
              当前值: {{ currentSimulation?.viscosity?.toExponential(2) || '-' }}
            </span>
          </el-form-item>

          <el-divider />

          <el-form-item label="复核意见" prop="comments">
            <el-input
              v-model="reviewForm.comments"
              type="textarea"
              :rows="4"
              placeholder="请输入复核意见（必填）"
              maxlength="500"
              show-word-limit
            />
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          @click="submitReview"
        >
          <el-icon><Check /></el-icon>
          提交复核
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="historyDialogVisible"
      title="复核历史记录"
      width="700px"
    >
      <div v-if="historyLoading" class="loading-container">
        <el-loading text="加载中..." />
      </div>
      <div v-else class="history-content">
        <div v-if="reviewHistory.length === 0" class="empty-state">
          <el-empty description="暂无复核历史" :image-size="80" />
        </div>
        <el-timeline v-else>
          <el-timeline-item
            v-for="review in reviewHistory"
            :key="review.id"
            :timestamp="formatDate(review.createdAt)"
            :type="review.approved ? 'success' : 'danger'"
          >
            <div class="review-history-item">
              <div class="review-header">
                <el-tag
                  :type="review.approved ? 'success' : 'danger'"
                  effect="light"
                  size="small"
                >
                  {{ review.approved ? '通过' : '拒绝' }}
                </el-tag>
                <span class="reviewer-name">{{ review.reviewerName || '未知用户' }}</span>
              </div>
              <div v-if="hasAnyAdjustment(review)" class="adjustment-list">
                <div v-if="review.suggestCmbAdjustment" class="adjustment-row">
                  <span class="adjustment-label">CMB热通量:</span>
                  <span class="adjustment-value">
                    {{ review.suggestCmbAdjustment > 0 ? '+' : '' }}
                    {{ review.suggestCmbAdjustment.toFixed(4) }}
                  </span>
                </div>
                <div v-if="review.suggestInnerCoreAdjustment" class="adjustment-row">
                  <span class="adjustment-label">内核半径:</span>
                  <span class="adjustment-value">
                    {{ review.suggestInnerCoreAdjustment > 0 ? '+' : '' }}
                    {{ review.suggestInnerCoreAdjustment.toFixed(4) }}
                  </span>
                </div>
                <div v-if="review.suggestViscosityAdjustment" class="adjustment-row">
                  <span class="adjustment-label">粘性系数:</span>
                  <span class="adjustment-value">
                    {{ review.suggestViscosityAdjustment > 0 ? '+' : '' }}
                    {{ review.suggestViscosityAdjustment.toExponential(2) }}
                  </span>
                </div>
              </div>
              <div class="review-comments">
                {{ review.comments }}
              </div>
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { monitoringAPI, simulationAPI } from '@/api'
import type { Alert, Review, Simulation } from '@/types'
import { AlertLevel, SimulationStatus } from '@/types'
import dayjs from 'dayjs'
import {
  Refresh,
  Check,
  CircleCheck,
  CircleClose,
  Document,
  VideoPlay,
  View
} from '@element-plus/icons-vue'

const router = useRouter()

const activeTab = ref('pending')
const pendingLoading = ref(false)
const reviewedLoading = ref(false)
const historyLoading = ref(false)
const submitting = ref(false)
const restartingIds = ref<number[]>([])

const pendingAlerts = ref<Alert[]>([])
const reviewedAlerts = ref<(Alert & { latestReview?: Review & { reviewerName?: string } })[]>([])
const reviewHistory = ref<(Review & { reviewerName?: string })[]>([])

const reviewDialogVisible = ref(false)
const historyDialogVisible = ref(false)
const currentAlert = ref<Alert | null>(null)
const currentSimulation = ref<Simulation | null>(null)
const reviewFormRef = ref<FormInstance>()

const reviewForm = reactive({
  simulationId: 0,
  alertId: 0,
  approved: true as boolean | null,
  suggestCmbAdjustment: null as number | null,
  suggestInnerCoreAdjustment: null as number | null,
  suggestViscosityAdjustment: null as number | null,
  comments: ''
})

const reviewRules: FormRules = {
  approved: [
    { required: true, message: '请选择复核结果', trigger: 'change' }
  ],
  comments: [
    { required: true, message: '请输入复核意见', trigger: 'blur' },
    { min: 2, message: '复核意见至少2个字符', trigger: 'blur' }
  ]
}

const sortedPendingAlerts = computed(() => {
  const levelOrder: Record<string, number> = {
    [AlertLevel.CRITICAL]: 0,
    [AlertLevel.WARNING]: 1,
    [AlertLevel.INFO]: 2
  }
  return [...pendingAlerts.value].sort((a, b) => {
    const levelDiff = (levelOrder[a.level] ?? 99) - (levelOrder[b.level] ?? 99)
    if (levelDiff !== 0) return levelDiff
    return dayjs(b.createdAt).valueOf() - dayjs(a.createdAt).valueOf()
  })
})

function getAlertLevelType(level: string): string {
  const typeMap: Record<string, string> = {
    [AlertLevel.CRITICAL]: 'danger',
    [AlertLevel.WARNING]: 'warning',
    [AlertLevel.INFO]: 'primary'
  }
  return typeMap[level] || 'info'
}

function getAlertLevelText(level: string): string {
  const textMap: Record<string, string> = {
    [AlertLevel.CRITICAL]: '严重',
    [AlertLevel.WARNING]: '警告',
    [AlertLevel.INFO]: '提示'
  }
  return textMap[level] || level
}

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

function formatDate(dateStr?: string): string {
  if (!dateStr) return '-'
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm')
}

function hasAnyAdjustment(review?: Review | null): boolean {
  if (!review) return false
  return !!(review.suggestCmbAdjustment || review.suggestInnerCoreAdjustment || review.suggestViscosityAdjustment)
}

async function fetchPendingAlerts() {
  pendingLoading.value = true
  try {
    const response = await monitoringAPI.getAlerts({ unread_only: false })
    const allAlerts: Alert[] = response.data.items || response.data || []
    pendingAlerts.value = allAlerts.filter(
      alert => alert.needsReview && !alert.reviewed
    )
  } catch (error) {
    console.error('Failed to fetch pending alerts:', error)
    ElMessage.error('获取待复核预警失败')
  } finally {
    pendingLoading.value = false
  }
}

async function fetchReviewedAlerts() {
  reviewedLoading.value = true
  try {
    const response = await monitoringAPI.getAlerts({ unread_only: false })
    const allAlerts: Alert[] = response.data.items || response.data || []
    const reviewedList = allAlerts.filter(alert => alert.reviewed)

    const alertsWithReviews = await Promise.all(
      reviewedList.map(async alert => {
        try {
          const reviewsResponse = await monitoringAPI.getSimulationReviews(alert.simulationId)
          const reviews: (Review & { reviewerName?: string })[] =
            reviewsResponse.data.items || reviewsResponse.data || []
          const latestReview = reviews
            .filter(r => r.alertId === alert.id)
            .sort((a, b) => dayjs(b.createdAt).valueOf() - dayjs(a.createdAt).valueOf())[0]

          let simulationStatus: SimulationStatus | undefined
          try {
            const simResponse = await simulationAPI.get(alert.simulationId)
            simulationStatus = simResponse.data.status
          } catch {
            // ignore
          }

          return {
            ...alert,
            latestReview,
            simulationStatus
          }
        } catch {
          return {
            ...alert,
            latestReview: undefined,
            simulationStatus: undefined
          }
        }
      })
    )

    reviewedAlerts.value = alertsWithReviews.sort(
      (a, b) =>
        dayjs(b.latestReview?.createdAt || b.createdAt).valueOf() -
        dayjs(a.latestReview?.createdAt || a.createdAt).valueOf()
    )
  } catch (error) {
    console.error('Failed to fetch reviewed alerts:', error)
    ElMessage.error('获取已复核记录失败')
  } finally {
    reviewedLoading.value = false
  }
}

async function openReviewDialog(alert: Alert) {
  currentAlert.value = alert
  reviewForm.simulationId = alert.simulationId
  reviewForm.alertId = alert.id
  reviewForm.approved = true
  reviewForm.suggestCmbAdjustment = null
  reviewForm.suggestInnerCoreAdjustment = null
  reviewForm.suggestViscosityAdjustment = null
  reviewForm.comments = ''

  try {
    const response = await simulationAPI.get(alert.simulationId)
    currentSimulation.value = response.data
  } catch (error) {
    console.error('Failed to fetch simulation:', error)
    currentSimulation.value = null
  }

  reviewDialogVisible.value = true
}

async function submitReview() {
  if (!reviewFormRef.value) return
  if (reviewForm.approved === null) {
    ElMessage.warning('请选择复核结果')
    return
  }

  await reviewFormRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      const submitData = {
        simulationId: reviewForm.simulationId,
        alertId: reviewForm.alertId,
        approved: reviewForm.approved,
        comments: reviewForm.comments,
        suggestCmbAdjustment: reviewForm.suggestCmbAdjustment,
        suggestInnerCoreAdjustment: reviewForm.suggestInnerCoreAdjustment,
        suggestViscosityAdjustment: reviewForm.suggestViscosityAdjustment
      }

      await monitoringAPI.createReview(submitData)
      ElMessage.success('复核提交成功')

      if (reviewForm.approved && hasAnyAdjustment(submitData as Review)) {
        try {
          await simulationAPI.update(reviewForm.simulationId, {
            status: SimulationStatus.ADJUSTING
          })
        } catch (error) {
          console.error('Failed to update simulation status:', error)
        }
      }

      reviewDialogVisible.value = false
      fetchPendingAlerts()
      if (activeTab.value === 'reviewed') {
        fetchReviewedAlerts()
      }
    } catch (error) {
      console.error('Failed to submit review:', error)
      ElMessage.error('复核提交失败')
    } finally {
      submitting.value = false
    }
  })
}

async function handleRestartSimulation(row: any) {
  ElMessageBox.confirm(
    `确定要使用调整后的参数重新启动模拟 #${row.simulationId} 吗？`,
    '重新计算确认',
    {
      confirmButtonText: '确认启动',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    restartingIds.value.push(row.simulationId)
    try {
      await simulationAPI.restartAdjusted(row.simulationId)
      ElMessage.success('模拟已重新启动')
      fetchReviewedAlerts()
    } catch (error) {
      console.error('Failed to restart simulation:', error)
      ElMessage.error('重启失败')
    } finally {
      restartingIds.value = restartingIds.value.filter(id => id !== row.simulationId)
    }
  }).catch(() => {})
}

async function viewReviewHistory(row: Alert) {
  historyDialogVisible.value = true
  historyLoading.value = true
  try {
    const response = await monitoringAPI.getSimulationReviews(row.simulationId)
    const allReviews: (Review & { reviewerName?: string })[] =
      response.data.items || response.data || []
    reviewHistory.value = allReviews
      .filter(r => r.alertId === row.id)
      .sort((a, b) => dayjs(b.createdAt).valueOf() - dayjs(a.createdAt).valueOf())
  } catch (error) {
    console.error('Failed to fetch review history:', error)
    ElMessage.error('获取复核历史失败')
  } finally {
    historyLoading.value = false
  }
}

function goToSimulation(simulationId: number) {
  router.push(`/simulations/${simulationId}`)
}

onMounted(() => {
  fetchPendingAlerts()
})
</script>

<style scoped lang="css">
.reviews-container {
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

.tabs-card {
  padding: 24px;
  background: #fff;
  border-radius: 12px;
}

.reviews-tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
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

.count-badge {
  font-size: 13px;
  color: #909399;
}

.count-badge strong {
  color: #f56c6c;
  font-size: 16px;
  margin: 0 4px;
}

.simulation-link {
  color: #409eff;
  cursor: pointer;
  font-weight: 500;
}

.simulation-link:hover {
  text-decoration: underline;
}

.metric-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-row {
  font-size: 13px;
}

.metric-label {
  color: #909399;
  margin-right: 4px;
}

.metric-name {
  color: #303133;
  font-weight: 500;
}

.metric-value {
  color: #606266;
}

.metric-value.highlight {
  color: #f56c6c;
  font-weight: 600;
}

.adjustment-info {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  font-size: 13px;
}

.adjustment-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.adjustment-label {
  color: #909399;
}

.adjustment-value {
  color: #409eff;
  font-weight: 500;
}

.no-adjustment {
  color: #c0c4cc;
  font-size: 13px;
}

.empty-state {
  padding: 60px 0;
  text-align: center;
}

.review-dialog-content {
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 8px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 12px 0;
}

.alert-detail-section,
.simulation-detail-section {
  margin-bottom: 16px;
}

.highlight {
  color: #f56c6c;
  font-weight: 600;
}

.review-form {
  margin-top: 8px;
}

.form-tip {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.review-history-item {
  padding: 4px 0;
}

.review-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.reviewer-name {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.adjustment-list {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 8px;
}

.adjustment-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  margin-bottom: 4px;
}

.adjustment-row:last-child {
  margin-bottom: 0;
}

.review-comments {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  background: #fafafa;
  padding: 10px 12px;
  border-radius: 6px;
  border-left: 3px solid #409eff;
}
</style>
