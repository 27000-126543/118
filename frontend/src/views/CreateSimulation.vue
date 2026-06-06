<template>
  <div class="create-simulation page-container">
    <div class="page-header">
      <h2>新建模拟任务</h2>
      <p class="page-desc">按照以下步骤配置模拟参数，创建新的地球动力学模拟任务</p>
    </div>

    <div class="steps-wrapper">
      <el-steps :active="activeStep" finish-status="success" simple>
        <el-step title="基本信息" />
        <el-step title="参数上传" />
        <el-step title="参数配置" />
        <el-step title="网格配置" />
        <el-step title="监控阈值" />
        <el-step title="确认提交" />
      </el-steps>
    </div>

    <div class="form-card">
      <el-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-width="180px"
        label-position="right"
      >
        <div v-show="activeStep === 0" class="step-content">
          <h3 class="step-title">基本信息</h3>
          <el-form-item label="任务名称" prop="name">
            <el-input
              v-model="formData.name"
              placeholder="请输入模拟任务名称"
              maxlength="100"
              show-word-limit
            />
          </el-form-item>
          <el-form-item label="任务描述" prop="description">
            <el-input
              v-model="formData.description"
              type="textarea"
              :rows="4"
              placeholder="请输入模拟任务描述"
              maxlength="500"
              show-word-limit
            />
          </el-form-item>
        </div>

        <div v-show="activeStep === 1" class="step-content">
          <h3 class="step-title">参数上传</h3>
          <p class="step-tip">
            支持上传 .json / .txt / .dat 格式的参数文件，上传后将自动解析并填充到表单中。
            您也可以跳过此步骤，在后续页面手动配置参数。
          </p>

          <el-upload
            ref="uploadRef"
            class="upload-dragger"
            :auto-upload="false"
            :show-file-list="false"
            :on-change="handleFileChange"
            drag
            accept=".json,.txt,.dat"
          >
            <div class="upload-area" :class="{ 'upload-dragover': isDragOver }"
              @dragover.prevent="isDragOver = true"
              @dragleave.prevent="isDragOver = false"
              @drop.prevent="isDragOver = false; handleDrop($event)">
              <el-icon class="upload-icon"><UploadFilled /></el-icon>
              <div class="upload-text">
                <span v-if="!uploadedFileName">将文件拖拽到此处，或<em>点击选择文件</em></span>
                <span v-else class="upload-success">
                  <el-icon><CircleCheckFilled /></el-icon>
                  已上传：{{ uploadedFileName }}
                </span>
              </div>
              <div class="upload-hint">支持 .json、.txt、.dat 格式，单个文件不超过 10MB</div>
            </div>
          </el-upload>

          <div v-if="uploadError" class="upload-error">
            <el-icon><WarningFilled /></el-icon>
            {{ uploadError }}
          </div>

          <div v-if="parsedParams" class="parsed-params">
            <div class="parsed-header">
              <el-icon color="#67c23a"><CircleCheckFilled /></el-icon>
              <span>参数解析成功，以下字段已自动填充：</span>
            </div>
            <div class="parsed-list">
              <span v-for="(value, key) in parsedParams" :key="key" class="parsed-item">
                {{ getFieldLabel(key) }}: {{ value }}
              </span>
            </div>
          </div>
        </div>

        <div v-show="activeStep === 2" class="step-content">
          <h3 class="step-title">物理参数配置</h3>
          <p class="step-tip">请确认并调整各项物理参数，所有参数均为必填项。</p>
          
          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="地核半径 (m)" prop="coreRadius">
                <el-input-number
                  v-model="formData.coreRadius"
                  :min="1e6"
                  :max="1e7"
                  :step="1e5"
                  :precision="2"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="粘性 (Pa·s)" prop="viscosity">
                <el-input-number
                  v-model="formData.viscosity"
                  :min="1e-6"
                  :max="1e2"
                  :step="1e-3"
                  :precision="6"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="热膨胀系数 (K⁻¹)" prop="thermalExpansion">
                <el-input-number
                  v-model="formData.thermalExpansion"
                  :min="1e-7"
                  :max="1e-3"
                  :step="1e-6"
                  :precision="7"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="内核半径 (m)" prop="innerCoreRadius">
                <el-input-number
                  v-model="formData.innerCoreRadius"
                  :min="1e5"
                  :max="5e6"
                  :step="1e4"
                  :precision="2"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="内核边界热通量 (W/m²)" prop="icbHeatFlux">
                <el-input-number
                  v-model="formData.icbHeatFlux"
                  :min="0.001"
                  :max="10"
                  :step="0.01"
                  :precision="4"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="核幔边界热通量 (W/m²)" prop="cmbHeatFlux">
                <el-input-number
                  v-model="formData.cmbHeatFlux"
                  :min="0.001"
                  :max="10"
                  :step="0.01"
                  :precision="4"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="最大迭代次数" prop="maxIterations">
            <el-input-number
              v-model="formData.maxIterations"
              :min="100"
              :max="1000000"
              :step="1000"
              style="width: 100%"
            />
          </el-form-item>
        </div>

        <div v-show="activeStep === 3" class="step-content">
          <h3 class="step-title">网格配置</h3>
          <p class="step-tip">设置计算网格的分辨率，较高的分辨率会提升精度但增加计算时间。</p>

          <el-row :gutter="24">
            <el-col :span="8">
              <el-form-item label="径向网格点数" prop="nRadial">
                <el-input-number
                  v-model="formData.nRadial"
                  :min="8"
                  :max="256"
                  :step="4"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="极角网格点数" prop="nTheta">
                <el-input-number
                  v-model="formData.nTheta"
                  :min="16"
                  :max="512"
                  :step="8"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="方位角网格点数" prop="nPhi">
                <el-input-number
                  v-model="formData.nPhi"
                  :min="32"
                  :max="1024"
                  :step="16"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
          </el-row>

          <div class="grid-info">
            <el-alert type="info" :closable="false">
              <template #title>
                总网格数：{{ formatNumber(totalGridPoints) }}
                <span v-if="totalGridPoints > 1000000" class="grid-warning">
                  <el-icon><WarningFilled /></el-icon>
                  网格数较大，计算时间可能较长
                </span>
              </template>
            </el-alert>
          </div>
        </div>

        <div v-show="activeStep === 4" class="step-content">
          <h3 class="step-title">监控阈值设置</h3>
          <p class="step-tip">设置模拟过程中的监控阈值，当指标超过阈值时将触发预警。</p>

          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item label="临界磁雷诺数" prop="criticalMagneticReynolds">
                <el-input-number
                  v-model="formData.criticalMagneticReynolds"
                  :min="1"
                  :max="1000"
                  :step="1"
                  :precision="2"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="偶极子倾斜角阈值 (°)" prop="dipoleTiltThreshold">
                <el-input-number
                  v-model="formData.dipoleTiltThreshold"
                  :min="0.1"
                  :max="90"
                  :step="0.5"
                  :precision="2"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
          </el-row>

          <div class="threshold-desc">
            <div class="desc-item">
              <el-icon color="#409eff"><InfoFilled /></el-icon>
              <div>
                <strong>磁雷诺数</strong>：描述磁场与流体相互作用的无量纲参数，超过临界值可能触发磁流体动力学不稳定性。
              </div>
            </div>
            <div class="desc-item">
              <el-icon color="#409eff"><InfoFilled /></el-icon>
              <div>
                <strong>偶极子倾斜角</strong>：磁偶极子与自转轴的夹角，超过阈值可能预示极性反转事件。
              </div>
            </div>
          </div>
        </div>

        <div v-show="activeStep === 5" class="step-content">
          <h3 class="step-title">确认参数并提交</h3>
          <p class="step-tip">请仔细核对以下所有配置参数，确认无误后提交创建任务。</p>

          <div class="summary-section">
            <h4 class="summary-title">基本信息</h4>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="任务名称">{{ formData.name }}</el-descriptions-item>
              <el-descriptions-item label="任务描述">{{ formData.description || '无' }}</el-descriptions-item>
            </el-descriptions>
          </div>

          <div class="summary-section">
            <h4 class="summary-title">物理参数</h4>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="地核半径">{{ formData.coreRadius }} m</el-descriptions-item>
              <el-descriptions-item label="粘性">{{ formData.viscosity }} Pa·s</el-descriptions-item>
              <el-descriptions-item label="热膨胀系数">{{ formData.thermalExpansion }} K⁻¹</el-descriptions-item>
              <el-descriptions-item label="内核半径">{{ formData.innerCoreRadius }} m</el-descriptions-item>
              <el-descriptions-item label="内核边界热通量">{{ formData.icbHeatFlux }} W/m²</el-descriptions-item>
              <el-descriptions-item label="核幔边界热通量">{{ formData.cmbHeatFlux }} W/m²</el-descriptions-item>
              <el-descriptions-item label="最大迭代次数">{{ formData.maxIterations }}</el-descriptions-item>
            </el-descriptions>
          </div>

          <div class="summary-section">
            <h4 class="summary-title">网格配置</h4>
            <el-descriptions :column="3" border>
              <el-descriptions-item label="径向网格点数">{{ formData.nRadial }}</el-descriptions-item>
              <el-descriptions-item label="极角网格点数">{{ formData.nTheta }}</el-descriptions-item>
              <el-descriptions-item label="方位角网格点数">{{ formData.nPhi }}</el-descriptions-item>
            </el-descriptions>
            <div class="summary-grid-total">
              总网格数：{{ formatNumber(totalGridPoints) }}
            </div>
          </div>

          <div class="summary-section">
            <h4 class="summary-title">监控阈值</h4>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="临界磁雷诺数">{{ formData.criticalMagneticReynolds }}</el-descriptions-item>
              <el-descriptions-item label="偶极子倾斜角阈值">{{ formData.dipoleTiltThreshold }}°</el-descriptions-item>
            </el-descriptions>
          </div>
        </div>

        <div class="form-footer">
          <el-button
            v-if="activeStep > 0"
            @click="prevStep"
          >
            上一步
          </el-button>
          <el-button
            v-if="activeStep < 5"
            type="primary"
            @click="nextStep"
          >
            下一步
          </el-button>
          <el-button
            v-if="activeStep === 5"
            type="primary"
            :loading="submitting"
            @click="handleSubmit"
          >
            {{ submitting ? '提交中...' : '提交创建' }}
          </el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type UploadFile, type FormRules } from 'element-plus'
import {
  UploadFilled,
  CircleCheckFilled,
  WarningFilled,
  InfoFilled
} from '@element-plus/icons-vue'
import { simulationAPI } from '@/api'

const router = useRouter()
const formRef = ref<FormInstance>()
const uploadRef = ref()
const activeStep = ref(0)
const submitting = ref(false)
const isDragOver = ref(false)
const uploadedFileName = ref('')
const uploadError = ref('')
const parsedParams = ref<Record<string, any> | null>(null)

const formData = reactive({
  name: '',
  description: '',
  coreRadius: 3.48e6,
  viscosity: 1e-2,
  thermalExpansion: 1e-5,
  icbHeatFlux: 0.1,
  cmbHeatFlux: 0.05,
  innerCoreRadius: 1.22e6,
  maxIterations: 10000,
  nRadial: 32,
  nTheta: 64,
  nPhi: 128,
  criticalMagneticReynolds: 50.0,
  dipoleTiltThreshold: 10.0
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入任务名称', trigger: 'blur' },
    { min: 2, max: 100, message: '任务名称长度在 2 到 100 个字符', trigger: 'blur' }
  ],
  description: [
    { required: true, message: '请输入任务描述', trigger: 'blur' }
  ],
  coreRadius: [
    { required: true, message: '请输入地核半径', trigger: 'blur' }
  ],
  viscosity: [
    { required: true, message: '请输入粘性', trigger: 'blur' }
  ],
  thermalExpansion: [
    { required: true, message: '请输入热膨胀系数', trigger: 'blur' }
  ],
  icbHeatFlux: [
    { required: true, message: '请输入内核边界热通量', trigger: 'blur' }
  ],
  cmbHeatFlux: [
    { required: true, message: '请输入核幔边界热通量', trigger: 'blur' }
  ],
  innerCoreRadius: [
    { required: true, message: '请输入内核半径', trigger: 'blur' }
  ],
  maxIterations: [
    { required: true, message: '请输入最大迭代次数', trigger: 'blur' }
  ],
  nRadial: [
    { required: true, message: '请输入径向网格点数', trigger: 'blur' }
  ],
  nTheta: [
    { required: true, message: '请输入极角网格点数', trigger: 'blur' }
  ],
  nPhi: [
    { required: true, message: '请输入方位角网格点数', trigger: 'blur' }
  ],
  criticalMagneticReynolds: [
    { required: true, message: '请输入临界磁雷诺数', trigger: 'blur' }
  ],
  dipoleTiltThreshold: [
    { required: true, message: '请输入偶极子倾斜角阈值', trigger: 'blur' }
  ]
}

const totalGridPoints = computed(() => {
  return formData.nRadial * formData.nTheta * formData.nPhi
})

const fieldLabels: Record<string, string> = {
  coreRadius: '地核半径',
  viscosity: '粘性',
  thermalExpansion: '热膨胀系数',
  icbHeatFlux: '内核边界热通量',
  cmbHeatFlux: '核幔边界热通量',
  innerCoreRadius: '内核半径',
  maxIterations: '最大迭代次数',
  nRadial: '径向网格点数',
  nTheta: '极角网格点数',
  nPhi: '方位角网格点数',
  criticalMagneticReynolds: '临界磁雷诺数',
  dipoleTiltThreshold: '偶极子倾斜角阈值'
}

function getFieldLabel(key: string): string {
  return fieldLabels[key] || key
}

function formatNumber(num: number): string {
  return num.toLocaleString('zh-CN')
}

function validateCurrentStep(): boolean {
  if (activeStep.value === 0) {
    let valid = true
    formRef.value?.validateField(['name', 'description'], (isValid) => {
      valid = isValid
    })
    return valid
  }
  if (activeStep.value === 2) {
    let valid = true
    formRef.value?.validateField(
      ['coreRadius', 'viscosity', 'thermalExpansion', 'icbHeatFlux', 'cmbHeatFlux', 'innerCoreRadius', 'maxIterations'],
      (isValid) => { valid = isValid }
    )
    return valid
  }
  if (activeStep.value === 3) {
    let valid = true
    formRef.value?.validateField(['nRadial', 'nTheta', 'nPhi'], (isValid) => {
      valid = isValid
    })
    return valid
  }
  if (activeStep.value === 4) {
    let valid = true
    formRef.value?.validateField(
      ['criticalMagneticReynolds', 'dipoleTiltThreshold'],
      (isValid) => { valid = isValid }
    )
    return valid
  }
  return true
}

async function handleFileChange(file: UploadFile) {
  await processFile(file.raw as File)
}

async function handleDrop(event: DragEvent) {
  const files = event.dataTransfer?.files
  if (files && files.length > 0) {
    await processFile(files[0])
  }
}

async function processFile(file: File) {
  uploadError.value = ''
  parsedParams.value = null

  const allowedExtensions = ['.json', '.txt', '.dat']
  const fileName = file.name.toLowerCase()
  const hasValidExtension = allowedExtensions.some(ext => fileName.endsWith(ext))

  if (!hasValidExtension) {
    uploadError.value = '文件格式不支持，请上传 .json、.txt 或 .dat 格式的文件'
    return
  }

  if (file.size > 10 * 1024 * 1024) {
    uploadError.value = '文件大小超过限制，单个文件不能超过 10MB'
    return
  }

  try {
    const response = await simulationAPI.uploadParams(file)
    const data = response.data

    uploadedFileName.value = file.name

    const parsed: Record<string, any> = {}
    for (const key of Object.keys(data)) {
      if (key in formData && typeof data[key] === 'number') {
        ;(formData as any)[key] = data[key]
        parsed[key] = data[key]
      }
    }

    if (Object.keys(parsed).length > 0) {
      parsedParams.value = parsed
      ElMessage.success(`成功解析 ${Object.keys(parsed).length} 个参数`)
    } else {
      ElMessage.info('文件已上传，但未解析到可识别的参数')
    }
  } catch (error: any) {
    uploadError.value = error.response?.data?.detail || '参数文件解析失败，请检查文件格式'
    uploadedFileName.value = ''
  }
}

function nextStep() {
  if (!validateCurrentStep()) {
    return
  }
  if (activeStep.value < 5) {
    activeStep.value++
  }
}

function prevStep() {
  if (activeStep.value > 0) {
    activeStep.value--
  }
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch (error) {
    ElMessage.error('请完善所有必填项')
    return
  }

  submitting.value = true
  try {
    const submitData = { ...formData }
    await simulationAPI.create(submitData)
    ElMessage.success('模拟任务创建成功！')
    router.push('/simulations')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '创建失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped lang="css">
.create-simulation {
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

.steps-wrapper {
  background: #fff;
  padding: 24px 32px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  margin-bottom: 24px;
}

.form-card {
  background: #fff;
  padding: 32px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.step-content {
  min-height: 400px;
}

.step-title {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.step-tip {
  margin: 0 0 24px 0;
  padding: 12px 16px;
  background: #ecf5ff;
  border-left: 4px solid #409eff;
  border-radius: 4px;
  color: #606266;
  font-size: 13px;
}

.upload-dragger {
  margin-bottom: 16px;
}

.upload-area {
  padding: 40px;
  text-align: center;
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
  transition: all 0.3s;
}

.upload-area:hover {
  border-color: #409eff;
}

.upload-area.upload-dragover {
  border-color: #409eff;
  background: #ecf5ff;
}

.upload-icon {
  font-size: 64px;
  color: #c0c4cc;
  margin-bottom: 16px;
}

.upload-text {
  font-size: 16px;
  color: #606266;
  margin-bottom: 8px;
}

.upload-text em {
  color: #409eff;
  font-style: normal;
}

.upload-success {
  color: #67c23a;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.upload-hint {
  font-size: 12px;
  color: #909399;
}

.upload-error {
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #fef0f0;
  border: 1px solid #fbc4c4;
  border-radius: 4px;
  color: #f56c6c;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.parsed-params {
  margin-bottom: 16px;
  padding: 16px;
  background: #f0f9eb;
  border: 1px solid #e1f3d8;
  border-radius: 8px;
}

.parsed-header {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #67c23a;
  font-weight: 600;
  margin-bottom: 12px;
}

.parsed-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
}

.parsed-item {
  padding: 4px 12px;
  background: #fff;
  border: 1px solid #e1f3d8;
  border-radius: 4px;
  font-size: 13px;
  color: #606266;
}

.grid-info {
  margin-top: 16px;
}

.grid-warning {
  margin-left: 16px;
  color: #e6a23c;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.threshold-desc {
  margin-top: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.desc-item {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  color: #606266;
  font-size: 13px;
  line-height: 1.6;
}

.desc-item strong {
  color: #303133;
}

.summary-section {
  margin-bottom: 24px;
}

.summary-title {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.summary-grid-total {
  margin-top: 12px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
  font-weight: 600;
  color: #303133;
}

.form-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid #ebeef5;
}
</style>
