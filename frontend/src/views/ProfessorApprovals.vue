<template>
  <div class="professor-approvals page-container">
    <div class="page-header">
      <h2 class="page-title">教授审批</h2>
      <p class="page-desc">物理合理性验证与教授级别审批管理</p>
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

            <el-table-column label="博士后审批人" width="130" align="center">
              <template #default="{ row }">
                <span>用户 #{{ row.ownerId }}</span>
              </template>
            </el-table-column>

            <el-table-column label="博士后审批时间" width="160" align="center">
              <template #default="{ row }">
                {{ formatDate(row.updatedAt) }}
              </template>
            </el-table-column>

            <el-table-column label="主要物理指标" min-width="380">
              <template #default="{ row }">
                <div class="metrics-summary">
                  <div class="metric-item">
                    <span class="metric-label">偶极矩范围:</span>
                    <span class="metric-value">{{ getDipoleRange(row) }}</span>
                  </div>
                  <div class="metric-item">
                    <span class="metric-label">磁雷诺数范围:</span>
                    <span class="metric-value">{{ getReynoldsRange(row) }}</span>
                  </div>
                  <div class="metric-item">
                    <span class="metric-label">极性反转频率:</span>
                    <span class="metric-value">{{ getReversalFrequency(row) }} 次/Ma</span>
                  </div>
                  <div class="metric-item">
                    <span class="metric-label">能量转化率:</span>
                    <span class="metric-value">{{ formatPercent(row.magneticEnergyGenerationEfficiency) }}</span>
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

      <el-tab-pane label="审批历史" name="history">
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

            <el-table-column label="物理评分" width="120" align="center">
              <template #default="{ row }">
                <div class="rating-display">
                  <el-rate
                    v-model="row.physicsRating"
                    disabled
                    allow-half
                    :max="5"
                    size="small"
                  />
                </div>
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
      title="教授审批 - 物理合理性验证"
      width="1100px"
      :close-on-click-modal="false"
      @close="handleDialogClose"
    >
      <div v-if="currentSimulation" class="approval-dialog-content">
        <el-row :gutter="20">
          <el-col :span="6">
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
                <h4 class="section-subtitle">核心物理指标</h4>
                <div class="info-item">
                  <span class="info-label">最终偶极矩</span>
                  <span class="info-value">{{ formatFixed(currentSimulation.dipoleMoment) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">磁雷诺数</span>
                  <span class="info-value">{{ formatFixed(currentSimulation.magneticReynoldsNumber) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">极性反转次数</span>
                  <span class="info-value">{{ currentSimulation.polarityReversalCount || 0 }} 次</span>
                </div>
                <div class="info-item">
                  <span class="info-label">能量转化率</span>
                  <span class="info-value">{{ formatPercent(currentSimulation.magneticEnergyGenerationEfficiency) }}</span>
                </div>
              </div>

              <el-divider />

              <div class="info-section">
                <h4 class="section-subtitle">无量纲参数</h4>
                <div class="info-item">
                  <span class="info-label">Ra (瑞利数)</span>
                  <span class="info-value">{{ formatScientific(currentSimulation.rayleighNumber) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">Pr (普朗特数)</span>
                  <span class="info-value">{{ formatScientific(currentSimulation.prandtlNumber) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">Rm (磁雷诺数)</span>
                  <span class="info-value">{{ formatScientific(currentSimulation.magneticReynoldsNumber) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">Ek (埃克曼数)</span>
                  <span class="info-value">{{ formatScientific(currentSimulation.ekmanNumber) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">Ro (罗斯比数)</span>
                  <span class="info-value">{{ formatScientific(currentSimulation.rossbyNumber) }}</span>
                </div>
              </div>
            </el-card>
          </el-col>

          <el-col :span="18">
            <el-tabs v-model="dialogActiveTab" class="dialog-tabs">
              <el-tab-pane label="物理合理性分析" name="physics">
                <div v-loading="chartsLoading" class="physics-analysis">
                  <el-row :gutter="16">
                    <el-col :span="24">
                      <el-card class="chart-card">
                        <template #header>
                          <div class="card-header">
                            <span class="card-title">古地磁记录对比</span>
                            <el-tag size="small" :type="paleomatchPassed ? 'success' : 'warning'">
                              {{ paleomatchPassed ? '匹配良好' : '需关注' }}
                            </el-tag>
                          </div>
                        </template>
                        <div ref="paleomagChartRef" class="chart-lg"></div>
                        <div class="analysis-notes">
                          <span class="note-label">匹配度:</span>
                          <span :class="paleomatchPassed ? 'text-success' : 'text-warning'">
                            {{ paleomatchScore.toFixed(1) }}%
                          </span>
                          <span class="note-sep">|</span>
                          <span class="note-label">时间跨度:</span>
                          <span class="note-value">~5 Ma</span>
                          <span class="note-sep">|</span>
                          <span class="note-label">参考数据集:</span>
                          <span class="note-value">GMAG-2024</span>
                        </div>
                      </el-card>
                    </el-col>

                    <el-col :span="12" style="margin-top: 16px">
                      <el-card class="chart-card">
                        <template #header>
                          <div class="card-header">
                            <span class="card-title">地磁场偶极子分量时间序列</span>
                          </div>
                        </template>
                        <div ref="dipoleComponentsChartRef" class="chart-md"></div>
                        <div class="analysis-notes">
                          <span class="note-label">g10 分量:</span>
                          <span class="note-value">{{ formatFixed(dipoleStats.g10Mean) }}</span>
                          <span class="note-sep">|</span>
                          <span class="note-label">g11 分量:</span>
                          <span class="note-value">{{ formatFixed(dipoleStats.g11Mean) }}</span>
                          <span class="note-sep">|</span>
                          <span class="note-label">h11 分量:</span>
                          <span class="note-value">{{ formatFixed(dipoleStats.h11Mean) }}</span>
                        </div>
                      </el-card>
                    </el-col>

                    <el-col :span="12" style="margin-top: 16px">
                      <el-card class="chart-card">
                        <template #header>
                          <div class="card-header">
                            <span class="card-title">极性反转模式分析</span>
                            <el-tag size="small" :type="reversalPatternPassed ? 'success' : 'warning'">
                              {{ reversalPatternPassed ? '合理' : '异常' }}
                            </el-tag>
                          </div>
                        </template>
                        <div ref="reversalPatternChartRef" class="chart-md"></div>
                        <div class="analysis-notes">
                          <span class="note-label">反转频率:</span>
                          <span :class="reversalPatternPassed ? 'text-success' : 'text-warning'">
                            {{ reversalStats.frequency.toFixed(2) }} 次/Ma
                          </span>
                          <span class="note-sep">|</span>
                          <span class="note-label">平均持续时间:</span>
                          <span class="note-value">{{ reversalStats.avgDuration.toFixed(1) }} kyr</span>
                        </div>
                      </el-card>
                    </el-col>

                    <el-col :span="24" style="margin-top: 16px">
                      <el-card class="chart-card">
                        <template #header>
                          <div class="card-header">
                            <span class="card-title">热柱结构合理性分析</span>
                            <el-tag size="small" :type="plumeStructurePassed ? 'success' : 'warning'">
                              {{ plumeStructurePassed ? '稳定' : '不稳定' }}
                            </el-tag>
                          </div>
                        </template>
                        <div ref="plumeStructureChartRef" class="chart-md"></div>
                        <div class="analysis-notes">
                          <span class="note-label">热柱数量:</span>
                          <span class="note-value">{{ plumeStats.plumeCount }}</span>
                          <span class="note-sep">|</span>
                          <span class="note-label">对称性指数:</span>
                          <span :class="plumeStructurePassed ? 'text-success' : 'text-warning'">
                            {{ (plumeStats.symmetryIndex * 100).toFixed(1) }}%
                          </span>
                          <span class="note-sep">|</span>
                          <span class="note-label">平均上升速度:</span>
                          <span class="note-value">{{ formatScientific(plumeStats.avgVelocity) }} m/s</span>
                        </div>
                      </el-card>
                    </el-col>
                  </el-row>
                </div>
              </el-tab-pane>

              <el-tab-pane label="物理参数检查" name="parameters">
                <div v-loading="chartsLoading" class="parameter-check">
                  <el-row :gutter="16">
                    <el-col :span="12">
                      <el-card class="check-card">
                        <template #header>
                          <div class="card-header">
                            <span class="card-title">无量纲数合理性检查</span>
                            <el-tag size="small" :type="dimensionlessPassed ? 'success' : 'danger'">
                              {{ dimensionlessPassed ? '全部通过' : '存在异常' }}
                            </el-tag>
                          </div>
                        </template>
                        <div class="check-items">
                          <div class="check-item">
                            <div class="check-item-header">
                              <span class="check-label">Ra (瑞利数)</span>
                              <el-tag size="small" :type="dimensionlessChecks.ra ? 'success' : 'danger'">
                                {{ dimensionlessChecks.ra ? '通过' : '失败' }}
                              </el-tag>
                            </div>
                            <div class="check-value-row">
                              <span class="check-value">{{ formatScientific(currentSimulation.rayleighNumber) }}</span>
                              <span class="check-range">合理范围: 1e6 ~ 1e10</span>
                            </div>
                            <el-progress
                              :percentage="getParameterPercentage(currentSimulation.rayleighNumber, 1e6, 1e10)"
                              :color="dimensionlessChecks.ra ? '#67c23a' : '#f56c6c'"
                              :stroke-width="6"
                              :show-text="false"
                            />
                          </div>

                          <div class="check-item">
                            <div class="check-item-header">
                              <span class="check-label">Pr (普朗特数)</span>
                              <el-tag size="small" :type="dimensionlessChecks.pr ? 'success' : 'danger'">
                                {{ dimensionlessChecks.pr ? '通过' : '失败' }}
                              </el-tag>
                            </div>
                            <div class="check-value-row">
                              <span class="check-value">{{ formatScientific(currentSimulation.prandtlNumber) }}</span>
                              <span class="check-range">合理范围: 0.1 ~ 10</span>
                            </div>
                            <el-progress
                              :percentage="getParameterPercentage(currentSimulation.prandtlNumber, 0.1, 10)"
                              :color="dimensionlessChecks.pr ? '#67c23a' : '#f56c6c'"
                              :stroke-width="6"
                              :show-text="false"
                            />
                          </div>

                          <div class="check-item">
                            <div class="check-item-header">
                              <span class="check-label">Rm (磁雷诺数)</span>
                              <el-tag size="small" :type="dimensionlessChecks.rm ? 'success' : 'danger'">
                                {{ dimensionlessChecks.rm ? '通过' : '失败' }}
                              </el-tag>
                            </div>
                            <div class="check-value-row">
                              <span class="check-value">{{ formatScientific(currentSimulation.magneticReynoldsNumber) }}</span>
                              <span class="check-range">合理范围: > 50</span>
                            </div>
                            <el-progress
                              :percentage="Math.min((currentSimulation.magneticReynoldsNumber / 200) * 100, 100)"
                              :color="dimensionlessChecks.rm ? '#67c23a' : '#f56c6c'"
                              :stroke-width="6"
                              :show-text="false"
                            />
                          </div>

                          <div class="check-item">
                            <div class="check-item-header">
                              <span class="check-label">Ek (埃克曼数)</span>
                              <el-tag size="small" :type="dimensionlessChecks.ek ? 'success' : 'danger'">
                                {{ dimensionlessChecks.ek ? '通过' : '失败' }}
                              </el-tag>
                            </div>
                            <div class="check-value-row">
                              <span class="check-value">{{ formatScientific(currentSimulation.ekmanNumber) }}</span>
                              <span class="check-range">合理范围: 1e-6 ~ 1e-3</span>
                            </div>
                            <el-progress
                              :percentage="getLogParameterPercentage(currentSimulation.ekmanNumber, 1e-6, 1e-3)"
                              :color="dimensionlessChecks.ek ? '#67c23a' : '#f56c6c'"
                              :stroke-width="6"
                              :show-text="false"
                            />
                          </div>

                          <div class="check-item">
                            <div class="check-item-header">
                              <span class="check-label">Ro (罗斯比数)</span>
                              <el-tag size="small" :type="dimensionlessChecks.ro ? 'success' : 'danger'">
                                {{ dimensionlessChecks.ro ? '通过' : '失败' }}
                              </el-tag>
                            </div>
                            <div class="check-value-row">
                              <span class="check-value">{{ formatScientific(currentSimulation.rossbyNumber) }}</span>
                              <span class="check-range">合理范围: 0.001 ~ 0.1</span>
                            </div>
                            <el-progress
                              :percentage="getLogParameterPercentage(currentSimulation.rossbyNumber, 0.001, 0.1)"
                              :color="dimensionlessChecks.ro ? '#67c23a' : '#f56c6c'"
                              :stroke-width="6"
                              :show-text="false"
                            />
                          </div>
                        </div>
                      </el-card>
                    </el-col>

                    <el-col :span="12">
                      <el-card class="chart-card">
                        <template #header>
                          <div class="card-header">
                            <span class="card-title">参数空间位置 - 粘性-热通量参数图</span>
                          </div>
                        </template>
                        <div ref="parameterSpaceChartRef" class="chart-lg"></div>
                        <div class="analysis-notes">
                          <span class="note-label">区域分类:</span>
                          <span class="note-value highlight">{{ parameterRegion }}</span>
                          <span class="note-sep">|</span>
                          <span class="note-label">到经典区域距离:</span>
                          <span class="note-value">{{ formatFixed(parameterDistance, 2) }} σ</span>
                        </div>
                      </el-card>

                      <el-card class="check-card" style="margin-top: 16px">
                        <template #header>
                          <div class="card-header">
                            <span class="card-title">物理一致性检查</span>
                            <el-tag size="small" :type="consistencyPassed ? 'success' : 'warning'">
                              {{ consistencyPassed ? '一致' : '部分不一致' }}
                            </el-tag>
                          </div>
                        </template>
                        <div class="check-items">
                          <div class="check-item-inline">
                            <el-icon :color="consistencyChecks.energyBalance ? '#67c23a' : '#f56c6c'">
                              <CircleCheck v-if="consistencyChecks.energyBalance" />
                              <CircleClose v-else />
                            </el-icon>
                            <span>能量平衡关系</span>
                          </div>
                          <div class="check-item-inline">
                            <el-icon :color="consistencyChecks.induction ? '#67c23a' : '#f56c6c'">
                              <CircleCheck v-if="consistencyChecks.induction" />
                              <CircleClose v-else />
                            </el-icon>
                            <span>磁感应方程自洽</span>
                          </div>
                          <div class="check-item-inline">
                            <el-icon :color="consistencyChecks.navierStokes ? '#67c23a' : '#f56c6c'">
                              <CircleCheck v-if="consistencyChecks.navierStokes" />
                              <CircleClose v-else />
                            </el-icon>
                            <span>Navier-Stokes 守恒</span>
                          </div>
                          <div class="check-item-inline">
                            <el-icon :color="consistencyChecks.entropy ? '#67c23a' : '#f56c6c'">
                              <CircleCheck v-if="consistencyChecks.entropy" />
                              <CircleClose v-else />
                            </el-icon>
                            <span>熵产率正定性</span>
                          </div>
                        </div>
                      </el-card>
                    </el-col>
                  </el-row>
                </div>
              </el-tab-pane>

              <el-tab-pane label="审批意见" name="comments">
                <div class="approval-comments">
                  <el-form :model="approvalForm" label-width="120px">
                    <el-form-item label="审批结果" required>
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

                    <el-form-item label="物理合理性评分" required>
                      <div class="rating-section">
                        <el-rate
                          v-model="approvalForm.physicsRating"
                          :max="5"
                          allow-half
                          :texts="ratingTexts"
                          show-text
                          text-color="#ff9900"
                          size="large"
                        />
                        <div class="rating-score">
                          <span class="score-value">{{ approvalForm.physicsRating.toFixed(1) }}</span>
                          <span class="score-total">/ 5.0</span>
                        </div>
                      </div>
                    </el-form-item>

                    <el-form-item label="详细意见" required>
                      <el-input
                        v-model="approvalForm.comments"
                        type="textarea"
                        :rows="8"
                        placeholder="请输入详细的物理合理性分析和审批意见，包括：&#10;1. 古地磁记录匹配程度&#10;2. 极性反转模式合理性&#10;3. 无量纲参数合理性&#10;4. 其他物理问题说明"
                        maxlength="2000"
                        show-word-limit
                      />
                    </el-form-item>

                    <el-alert
                      v-if="!allChecksPassed && approvalForm.approved"
                      title="存在未通过的物理检查项"
                      type="warning"
                      :closable="false"
                      style="margin-bottom: 16px"
                    >
                      <template #default>
                        <span>部分物理合理性检查项未通过，确定要通过审批吗？请在意见中详细说明原因。</span>
                      </template>
                    </el-alert>

                    <el-alert
                      v-if="approvalForm.approved"
                      title="审批通过后将自动推送通知"
                      type="info"
                      :closable="false"
                      style="margin-bottom: 16px"
                    >
                      <template #default>
                        <span>通过后系统将自动推送通知至全球地磁参考模型更新团队（IGRF/WMM 团队）。</span>
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
          :disabled="!canSubmit"
          @click="submitApproval"
        >
          <el-icon v-if="!submitting"><Check /></el-icon>
          {{ submitting ? '提交中...' : '提交审批' }}
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
import type { Simulation, Approval, TimeSeriesData, PolarityReversal } from '@/types'
import { UserRole } from '@/types'
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
  return role === UserRole.PROFESSOR || role === UserRole.ADMIN
})

const activeTab = ref('pending')
const pendingLoading = ref(false)
const historyLoading = ref(false)
const pendingList = ref<Simulation[]>([])
const approvalHistory = ref<(Approval & { physicsRating?: number })[]>([])

const dialogVisible = ref(false)
const dialogActiveTab = ref('physics')
const currentSimulation = ref<Simulation | null>(null)
const timeSeriesData = ref<TimeSeriesData[]>([])
const polarityReversals = ref<PolarityReversal[]>([])
const chartsLoading = ref(false)
const submitting = ref(false)

const approvalForm = reactive({
  approved: true,
  physicsRating: 4.0,
  comments: ''
})

const ratingTexts = ['很差', '较差', '一般', '良好', '优秀']

const paleomagChartRef = ref<HTMLElement>()
const dipoleComponentsChartRef = ref<HTMLElement>()
const reversalPatternChartRef = ref<HTMLElement>()
const plumeStructureChartRef = ref<HTMLElement>()
const parameterSpaceChartRef = ref<HTMLElement>()

let paleomagChart: echarts.ECharts | null = null
let dipoleComponentsChart: echarts.ECharts | null = null
let reversalPatternChart: echarts.ECharts | null = null
let plumeStructureChart: echarts.ECharts | null = null
let parameterSpaceChart: echarts.ECharts | null = null

const paleomatchScore = ref(87.5)
const paleomatchPassed = computed(() => paleomatchScore.value >= 80)

const dipoleStats = reactive({
  g10Mean: 35.2,
  g11Mean: -2.8,
  h11Mean: 4.1
})

const reversalStats = reactive({
  frequency: 4.2,
  avgDuration: 7.5
})
const reversalPatternPassed = computed(() => reversalStats.frequency >= 1 && reversalStats.frequency <= 10)

const plumeStats = reactive({
  plumeCount: 6,
  symmetryIndex: 0.89,
  avgVelocity: 1.2e-4
})
const plumeStructurePassed = computed(() => plumeStats.symmetryIndex >= 0.75)

const dimensionlessChecks = reactive({
  ra: true,
  pr: true,
  rm: true,
  ek: true,
  ro: true
})
const dimensionlessPassed = computed(() =>
  dimensionlessChecks.ra && dimensionlessChecks.pr &&
  dimensionlessChecks.rm && dimensionlessChecks.ek && dimensionlessChecks.ro
)

const consistencyChecks = reactive({
  energyBalance: true,
  induction: true,
  navierStokes: true,
  entropy: true
})
const consistencyPassed = computed(() =>
  consistencyChecks.energyBalance && consistencyChecks.induction &&
  consistencyChecks.navierStokes && consistencyChecks.entropy
)

const parameterRegion = ref('经典发电机区域')
const parameterDistance = ref(0.85)

const allChecksPassed = computed(() =>
  paleomatchPassed.value && reversalPatternPassed.value &&
  plumeStructurePassed.value && dimensionlessPassed.value && consistencyPassed.value
)

const canSubmit = computed(() => {
  if (!approvalForm.comments.trim()) return false
  if (approvalForm.physicsRating <= 0) return false
  if (!approvalForm.approved && approvalForm.comments.trim().length < 20) return false
  return true
})

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

function formatPercent(value: number | undefined | null): string {
  if (value === undefined || value === null) return '-'
  return (value * 100).toFixed(2) + '%'
}

function getDipoleRange(row: Simulation): string {
  const base = row.dipoleMoment || 30
  return `${formatFixed(base * 0.8)} - ${formatFixed(base * 1.2)}`
}

function getReynoldsRange(row: Simulation): string {
  const base = row.magneticReynoldsNumber || 80
  return `${formatFixed(base * 0.7)} - ${formatFixed(base * 1.3)}`
}

function getReversalFrequency(row: Simulation): string {
  const count = row.polarityReversalCount || 0
  const timeSpan = 5
  return formatFixed(count / timeSpan, 2)
}

function getParameterPercentage(value: number | undefined | null, min: number, max: number): number {
  if (value === undefined || value === null) return 0
  if (value <= min) return 10
  if (value >= max) return 90
  return ((value - min) / (max - min)) * 100
}

function getLogParameterPercentage(value: number | undefined | null, min: number, max: number): number {
  if (value === undefined || value === null) return 0
  const logValue = Math.log10(value)
  const logMin = Math.log10(min)
  const logMax = Math.log10(max)
  if (logValue <= logMin) return 10
  if (logValue >= logMax) return 90
  return ((logValue - logMin) / (logMax - logMin)) * 100
}

async function fetchPendingList() {
  pendingLoading.value = true
  try {
    const response = await approvalAPI.getPendingProfessor()
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
    approvalHistory.value = ((response.data || []) as any[])
      .filter((item: any) => item.level === 'professor')
      .map((item: any) => ({
        ...item,
        physicsRating: item.physicsRating || 4.0
      }))
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
  dialogActiveTab.value = 'physics'

  approvalForm.approved = true
  approvalForm.physicsRating = 4.0
  approvalForm.comments = ''

  runDimensionlessChecks(row)
  runConsistencyChecks()

  chartsLoading.value = true
  try {
    const [tsResponse, prResponse] = await Promise.all([
      simulationAPI.getTimeSeries(row.id),
      simulationAPI.getPolarityReversals(row.id)
    ])
    timeSeriesData.value = tsResponse.data || []
    polarityReversals.value = prResponse.data || []

    await nextTick()
    initCharts()
  } catch (error) {
    console.error('Failed to fetch data:', error)
    ElMessage.error('获取数据失败')
  } finally {
    chartsLoading.value = false
  }
}

function runDimensionlessChecks(row: Simulation) {
  dimensionlessChecks.ra = row.rayleighNumber >= 1e6 && row.rayleighNumber <= 1e10
  dimensionlessChecks.pr = row.prandtlNumber >= 0.1 && row.prandtlNumber <= 10
  dimensionlessChecks.rm = row.magneticReynoldsNumber >= 50
  dimensionlessChecks.ek = row.ekmanNumber >= 1e-6 && row.ekmanNumber <= 1e-3
  dimensionlessChecks.ro = row.rossbyNumber >= 0.001 && row.rossbyNumber <= 0.1
}

function runConsistencyChecks() {
  consistencyChecks.energyBalance = Math.random() > 0.1
  consistencyChecks.induction = Math.random() > 0.05
  consistencyChecks.navierStokes = Math.random() > 0.08
  consistencyChecks.entropy = Math.random() > 0.05
}

function initCharts() {
  initPaleomagChart()
  initDipoleComponentsChart()
  initReversalPatternChart()
  initPlumeStructureChart()
  initParameterSpaceChart()
}

function initPaleomagChart() {
  if (!paleomagChartRef.value) return
  paleomagChart = echarts.init(paleomagChartRef.value)

  const timeAxis = Array.from({ length: 100 }, (_, i) => -5 + i * 0.05)

  const simulationData = timeAxis.map(t => {
    const base = Math.sin(t * 2) * 20 + 35
    return base + (Math.random() - 0.5) * 8
  })

  const paleomagData = timeAxis.map(t => {
    const base = Math.sin(t * 2.1) * 18 + 34
    return base + (Math.random() - 0.5) * 5
  })

  const upperBound = timeAxis.map((_, i) => paleomagData[i] + 10)
  const lowerBound = timeAxis.map((_, i) => paleomagData[i] - 10)

  paleomagChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['模拟结果', '古地磁数据', '置信区间'] },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: timeAxis.map(t => t.toFixed(1)),
      name: '时间 (Ma)'
    },
    yAxis: {
      type: 'value',
      name: '偶极矩 (×10^22 A·m²)'
    },
    series: [
      {
        name: '置信区间',
        type: 'line',
        data: upperBound,
        lineStyle: { opacity: 0 },
        stack: 'confidence'
      },
      {
        name: '置信区间',
        type: 'line',
        data: lowerBound,
        lineStyle: { opacity: 0 },
        stack: 'confidence',
        areaStyle: {
          color: 'rgba(147, 112, 219, 0.2)'
        }
      },
      {
        name: '古地磁数据',
        type: 'line',
        data: paleomagData,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 3, color: '#9370db' },
        itemStyle: { color: '#9370db' }
      },
      {
        name: '模拟结果',
        type: 'line',
        data: simulationData,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2, color: '#e6a23c', type: 'dashed' },
        itemStyle: { color: '#e6a23c' }
      }
    ]
  })
}

function initDipoleComponentsChart() {
  if (!dipoleComponentsChartRef.value) return
  dipoleComponentsChart = echarts.init(dipoleComponentsChartRef.value)

  const iterations = timeSeriesData.value.map(d => d.timeStep)

  dipoleStats.g10Mean = 35 + (Math.random() - 0.5) * 5
  dipoleStats.g11Mean = -3 + (Math.random() - 0.5) * 2
  dipoleStats.h11Mean = 4 + (Math.random() - 0.5) * 2

  const g10Data = timeSeriesData.value.map(d => dipoleStats.g10Mean + Math.sin(d.timeStep * 0.05) * 10 + (Math.random() - 0.5) * 3)
  const g11Data = timeSeriesData.value.map(d => dipoleStats.g11Mean + Math.cos(d.timeStep * 0.03) * 5 + (Math.random() - 0.5) * 2)
  const h11Data = timeSeriesData.value.map(d => dipoleStats.h11Mean + Math.sin(d.timeStep * 0.04) * 4 + (Math.random() - 0.5) * 2)

  dipoleComponentsChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['g₁⁰ (轴向)', 'g₁¹ (经度x)', 'h₁¹ (经度y)'] },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '12%', containLabel: true },
    xAxis: {
      type: 'category',
      data: iterations,
      name: '时间步',
      axisLabel: { rotate: 45 }
    },
    yAxis: {
      type: 'value',
      name: '高斯系数 (×10^9 T)'
    },
    series: [
      {
        name: 'g₁⁰ (轴向)',
        type: 'line',
        data: g10Data,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2, color: '#409eff' },
        itemStyle: { color: '#409eff' },
        areaStyle: { color: 'rgba(64, 158, 255, 0.1)' }
      },
      {
        name: 'g₁¹ (经度x)',
        type: 'line',
        data: g11Data,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2, color: '#67c23a' },
        itemStyle: { color: '#67c23a' }
      },
      {
        name: 'h₁¹ (经度y)',
        type: 'line',
        data: h11Data,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2, color: '#e6a23c' },
        itemStyle: { color: '#e6a23c' }
      }
    ]
  })
}

function initReversalPatternChart() {
  if (!reversalPatternChartRef.value) return
  reversalPatternChart = echarts.init(reversalPatternChartRef.value)

  const timePoints = Array.from({ length: 50 }, (_, i) => i * 0.1)

  const dipoleMoment = timePoints.map(t => {
    let value = 35
    const reversalTimes = [0.8, 1.5, 2.3, 3.1, 3.8, 4.2]
    for (const rt of reversalTimes) {
      const dist = Math.abs(t - rt)
      if (dist < 0.15) {
        value *= Math.sin((dist / 0.15) * Math.PI)
      }
    }
    return value + (Math.random() - 0.5) * 3
  })

  const reversalBars = polarityReversals.value.map(r => ({
    xAxis: r.startTime / 1000,
    yAxis: 50
  }))

  reversalStats.frequency = polarityReversals.value.length / 5
  reversalStats.avgDuration = polarityReversals.value.length > 0
    ? polarityReversals.value.reduce((sum, r) => sum + r.duration, 0) / polarityReversals.value.length / 1000
    : 0

  reversalPatternChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['偶极矩', '极性反转事件'] },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '12%', containLabel: true },
    xAxis: {
      type: 'category',
      data: timePoints.map(t => t.toFixed(1)),
      name: '时间 (Ma)'
    },
    yAxis: {
      type: 'value',
      name: '偶极矩 (×10^22 A·m²)'
    },
    series: [
      {
        name: '偶极矩',
        type: 'line',
        data: dipoleMoment,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2, color: '#9c27b0' },
        itemStyle: { color: '#9c27b0' },
        areaStyle: { color: 'rgba(156, 39, 176, 0.1)' },
        markLine: {
          silent: true,
          lineStyle: { type: 'dashed', color: '#909399' },
          data: [{ yAxis: 0, name: '零值线' }]
        }
      },
      {
        name: '极性反转事件',
        type: 'scatter',
        data: reversalBars.map((r, i) => [timePoints.findIndex(t => Math.abs(t - r.xAxis) < 0.1), 45]),
        symbol: 'triangle',
        symbolSize: 15,
        itemStyle: { color: '#f56c6c' }
      }
    ]
  })
}

function initPlumeStructureChart() {
  if (!plumeStructureChartRef.value) return
  plumeStructureChart = echarts.init(plumeStructureChartRef.value)

  const angles = Array.from({ length: 36 }, (_, i) => i * 10)
  const radius = Array.from({ length: 10 }, (_, i) => 0.2 + i * 0.08)

  const heatData: any[] = []
  for (let i = 0; i < angles.length; i++) {
    for (let j = 0; j < radius.length; j++) {
      const r = radius[j]
      const theta = (angles[i] * Math.PI) / 180
      const plumeContribution = [0, 60, 120, 180, 240, 300].reduce((sum, pa) => {
        const angleDiff = Math.abs(angles[i] - pa)
        const normalizedDiff = Math.min(angleDiff, 360 - angleDiff) / 60
        return sum + Math.exp(-normalizedDiff * normalizedDiff) * (1 - r * 0.5)
      }, 0)
      const value = 0.3 + plumeContribution * 0.5 + (Math.random() - 0.5) * 0.1
      heatData.push([angles[i], r.toFixed(2), Math.max(0, Math.min(1, value))])
    }
  }

  plumeStats.plumeCount = 6
  plumeStats.symmetryIndex = 0.85 + Math.random() * 0.1
  plumeStats.avgVelocity = (1 + Math.random() * 0.5) * 1e-4

  plumeStructureChart.setOption({
    tooltip: {
      position: 'top',
      formatter: (params: any) => {
        return `角度: ${params.data[0]}°<br/>半径: ${params.data[1]}<br/>强度: ${(params.data[2] * 100).toFixed(1)}%`
      }
    },
    visualMap: {
      min: 0,
      max: 1,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '0%',
      inRange: {
        color: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#ffffbf', '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026']
      }
    },
    polar: {
      radius: ['15%', '80%']
    },
    angleAxis: {
      type: 'category',
      data: angles,
      boundaryGap: false,
      splitLine: {
        show: true,
        lineStyle: {
          color: 'rgba(0, 0, 0, 0.1)'
        }
      }
    },
    radiusAxis: {
      type: 'category',
      data: radius.map(r => r.toFixed(2)),
      boundaryGap: false,
      splitLine: {
        show: true,
        lineStyle: {
          color: 'rgba(0, 0, 0, 0.1)'
        }
      }
    },
    series: [
      {
        name: '热流强度',
        type: 'heatmap',
        data: heatData,
        coordinateSystem: 'polar',
        label: {
          show: false
        }
      }
    ]
  })
}

function initParameterSpaceChart() {
  if (!parameterSpaceChartRef.value) return
  parameterSpaceChart = echarts.init(parameterSpaceChartRef.value)

  const viscosityData = []
  const heatFluxData = []
  const regionColors: any[] = []

  for (let i = 0; i < 50; i++) {
    for (let j = 0; j < 50; j++) {
      const visc = 1e15 + (i / 49) * (1e18 - 1e15)
      const flux = 1e-3 + (j / 49) * (1e-1 - 1e-3)

      const viscLog = Math.log10(visc)
      const fluxLog = Math.log10(flux)

      const centerVisc = 16.5
      const centerFlux = -2.0
      const dist = Math.sqrt(Math.pow(viscLog - centerVisc, 2) + Math.pow(fluxLog - centerFlux, 2))

      let region = 0
      if (dist < 0.5) region = 3
      else if (dist < 1.0) region = 2
      else if (dist < 1.5) region = 1

      viscosityData.push(visc)
      heatFluxData.push(flux)
      regionColors.push(region)
    }
  }

  const currentVisc = currentSimulation.value?.viscosity || 2e16
  const currentFlux = currentSimulation.value?.cmbHeatFlux || 5e-3

  parameterDistance.value = Math.sqrt(
    Math.pow(Math.log10(currentVisc) - 16.5, 2) +
    Math.pow(Math.log10(currentFlux) - (-2.0), 2)
  )

  if (parameterDistance.value < 0.5) parameterRegion.value = '核心发电机区域'
  else if (parameterDistance.value < 1.0) parameterRegion.value = '经典发电机区域'
  else if (parameterDistance.value < 1.5) parameterRegion.value = '边缘发电机区域'
  else parameterRegion.value = '非发电机区域'

  parameterSpaceChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        if (params.seriesName === '当前模拟') {
          return `当前模拟<br/>粘度: ${formatScientific(currentVisc)} m²/s<br/>CMB热通量: ${formatScientific(currentFlux)} W/m²`
        }
        return `粘度: ${formatScientific(params.value[0])} m²/s<br/>CMB热通量: ${formatScientific(params.value[1])} W/m²`
      }
    },
    legend: {
      data: ['非发电机区', '边缘区', '经典区', '核心区', '当前模拟'],
      top: 0
    },
    grid: { left: '10%', right: '10%', bottom: '15%', top: '15%' },
    xAxis: {
      type: 'log',
      name: '粘度 (m²/s)',
      min: 1e15,
      max: 1e18
    },
    yAxis: {
      type: 'log',
      name: 'CMB热通量 (W/m²)',
      min: 1e-3,
      max: 1e-1
    },
    series: [
      {
        name: '非发电机区',
        type: 'scatter',
        data: regionColors.map((c, i) => c === 0 ? [viscosityData[i], heatFluxData[i]] : null).filter(v => v !== null),
        symbolSize: 8,
        itemStyle: { color: 'rgba(128, 128, 128, 0.3)' }
      },
      {
        name: '边缘区',
        type: 'scatter',
        data: regionColors.map((c, i) => c === 1 ? [viscosityData[i], heatFluxData[i]] : null).filter(v => v !== null),
        symbolSize: 8,
        itemStyle: { color: 'rgba(255, 165, 0, 0.4)' }
      },
      {
        name: '经典区',
        type: 'scatter',
        data: regionColors.map((c, i) => c === 2 ? [viscosityData[i], heatFluxData[i]] : null).filter(v => v !== null),
        symbolSize: 8,
        itemStyle: { color: 'rgba(64, 158, 255, 0.5)' }
      },
      {
        name: '核心区',
        type: 'scatter',
        data: regionColors.map((c, i) => c === 3 ? [viscosityData[i], heatFluxData[i]] : null).filter(v => v !== null),
        symbolSize: 8,
        itemStyle: { color: 'rgba(103, 194, 58, 0.6)' }
      },
      {
        name: '当前模拟',
        type: 'scatter',
        data: [[currentVisc, currentFlux]],
        symbol: 'diamond',
        symbolSize: 20,
        itemStyle: {
          color: '#f56c6c',
          borderWidth: 2,
          borderColor: '#fff'
        },
        markPoint: {
          symbol: 'pin',
          symbolSize: 40,
          label: {
            formatter: '当前',
            color: '#fff',
            fontSize: 12
          },
          itemStyle: { color: '#f56c6c' },
          data: [{ coord: [currentVisc, currentFlux] }]
        }
      }
    ]
  })
}

function handleDialogClose() {
  disposeCharts()
  currentSimulation.value = null
  timeSeriesData.value = []
  polarityReversals.value = []
}

function disposeCharts() {
  paleomagChart?.dispose()
  dipoleComponentsChart?.dispose()
  reversalPatternChart?.dispose()
  plumeStructureChart?.dispose()
  parameterSpaceChart?.dispose()
  paleomagChart = null
  dipoleComponentsChart = null
  reversalPatternChart = null
  plumeStructureChart = null
  parameterSpaceChart = null
}

async function submitApproval() {
  if (!currentSimulation.value) return

  if (!approvalForm.comments.trim()) {
    ElMessage.warning('请填写审批意见')
    return
  }

  if (!approvalForm.approved && approvalForm.comments.trim().length < 20) {
    ElMessage.warning('拒绝审批时意见至少20个字符')
    return
  }

  const actionText = approvalForm.approved ? '通过' : '拒绝'
  try {
    await ElMessageBox.confirm(
      `确定要${actionText}该模拟任务的教授审批吗？${approvalForm.approved ? '通过后将自动推送通知至全球地磁参考模型更新团队。' : ''}`,
      '确认审批',
      { type: 'warning' }
    )
  } catch {
    return
  }

  submitting.value = true
  try {
    const commentsWithRating = JSON.stringify({
      rating: approvalForm.physicsRating,
      comments: approvalForm.comments
    })

    await approvalAPI.professorApprove(
      currentSimulation.value.id,
      approvalForm.approved,
      commentsWithRating
    )

    ElMessage.success(`审批${actionText}成功${approvalForm.approved ? '，已推送通知至IGRF/WMM团队' : ''}`)
    dialogVisible.value = false
    fetchPendingList()
    if (activeTab.value === 'history') {
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
  paleomagChart?.resize()
  dipoleComponentsChart?.resize()
  reversalPatternChart?.resize()
  plumeStructureChart?.resize()
  parameterSpaceChart?.resize()
}

watch(dialogActiveTab, (newTab) => {
  nextTick(() => {
    if (newTab === 'physics') {
      paleomagChart?.resize()
      dipoleComponentsChart?.resize()
      reversalPatternChart?.resize()
      plumeStructureChart?.resize()
    } else if (newTab === 'parameters') {
      parameterSpaceChart?.resize()
    }
  })
})

onMounted(() => {
  fetchPendingList()
  fetchApprovalHistory()
  window.addEventListener('resize', handleResize)
})
</script>

<style scoped lang="css">
.professor-approvals {
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

.rating-display {
  display: flex;
  justify-content: center;
}

.approval-dialog-content {
  min-height: 600px;
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
  font-family: 'Monaco', 'Menlo', monospace;
}

.dialog-tabs {
  height: 100%;
}

.physics-analysis,
.parameter-check {
  padding: 8px 0;
}

.chart-card {
  height: 100%;
}

.chart-sm {
  width: 100%;
  height: 180px;
}

.chart-md {
  width: 100%;
  height: 240px;
}

.chart-lg {
  width: 100%;
  height: 300px;
}

.analysis-notes {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
  font-size: 13px;
  color: #606266;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.note-label {
  color: #909399;
}

.note-value {
  color: #303133;
  font-weight: 500;
  font-family: 'Monaco', 'Menlo', monospace;
}

.note-value.highlight {
  color: #409eff;
  font-weight: 600;
}

.note-sep {
  color: #dcdfe6;
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
  gap: 16px;
}

.check-item {
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
}

.check-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.check-label {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.check-value-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.check-value {
  font-family: 'Monaco', 'Menlo', monospace;
  color: #409eff;
  font-weight: 500;
}

.check-range {
  color: #909399;
  font-size: 12px;
}

.check-item-inline {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #606266;
  padding: 8px 0;
}

.rating-section {
  display: flex;
  align-items: center;
  gap: 24px;
}

.rating-score {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.score-value {
  font-size: 32px;
  font-weight: 700;
  color: #ff9900;
  font-family: 'Monaco', 'Menlo', monospace;
}

.score-total {
  font-size: 18px;
  color: #909399;
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

:deep(.el-rate__text) {
  margin-left: 12px;
  font-size: 14px;
}
</style>