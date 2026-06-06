export enum SimulationStatus {
  PENDING_VERIFICATION = '待校验',
  MESH_GENERATION = '网格生成',
  INITIALIZATION = '初始化',
  ITERATING = '发电机迭代',
  COMPLETED = '完成',
  ERROR = '异常',
  NEEDS_REVIEW = '需复核',
  ADJUSTING = '参数调整'
}

export enum AlertLevel {
  INFO = 'info',
  WARNING = 'warning',
  CRITICAL = 'critical'
}

export enum ApprovalStatus {
  PENDING = '待审批',
  POSTDOC_APPROVED = '博士后通过',
  PROFESSOR_APPROVED = '教授通过',
  REJECTED = '已拒绝'
}

export enum UserRole {
  ADMIN = 'admin',
  POSTDOC = 'postdoc',
  PROFESSOR = 'professor',
  GEOPHYSICIST = 'geophysicist',
  CHIEF_SCIENTIST = 'chief_scientist',
  RESEARCHER = 'researcher'
}

export interface User {
  id: number
  username: string
  email: string
  fullName: string
  role: UserRole
  isActive: boolean
  createdAt: string
}

export interface Simulation {
  id: number
  name: string
  description: string
  ownerId: number
  status: SimulationStatus
  progress: number
  currentIteration: number
  maxIterations: number

  coreRadius: number
  viscosity: number
  thermalExpansion: number
  icbHeatFlux: number
  cmbHeatFlux: number
  innerCoreRadius: number
  magneticReynoldsCritical: number
  dipoleTiltThreshold: number
  rayleighNumber: number
  prandtlNumber: number
  magneticReynoldsNumber: number
  ekmanNumber: number
  rossbyNumber: number

  relaxationTime: number
  dipoleMoment: number
  dipoleTilt: number
  innerCoreSymmetry: number
  totalMagneticEnergy: number
  totalKineticEnergy: number
  magneticEnergyGenerationEfficiency: number

  warningCount: number
  hasPolarityReversal: boolean
  polarityReversalCount: number

  approvalStatus: ApprovalStatus
  submittedForApproval: boolean

  errorMessage: string
  startedAt: string
  completedAt: string
  createdAt: string
  updatedAt: string
}

export interface Alert {
  id: number
  simulationId: number
  recipientId: number
  level: AlertLevel
  title: string
  message: string
  metricName: string
  metricValue: number
  threshold: number
  isRead: boolean
  needsReview: boolean
  reviewed: boolean
  createdAt: string
}

export interface Review {
  id: number
  simulationId: number
  reviewerId: number
  alertId: number
  comments: string
  approved: boolean
  suggestCmbAdjustment: number
  suggestInnerCoreAdjustment: number
  suggestViscosityAdjustment: number
  createdAt: string
}

export interface Approval {
  id: number
  simulationId: number
  approverId: number
  level: string
  comments: string
  approved: boolean
  createdAt: string
}

export interface TimeSeriesData {
  id: number
  simulationId: number
  timeStep: number
  simulationTime: number
  magneticEnergy: number
  kineticEnergy: number
  dipoleMoment: number
  dipoleTilt: number
  magneticReynolds: number
  innerCoreSymmetry: number
  temperatureAnomaly: number
  velocityMagnitude: number
  createdAt: string
}

export interface PolarityReversal {
  id: number
  simulationId: number
  startTime: number
  endTime: number
  startIteration: number
  endIteration: number
  reversalType: string
  duration: number
  createdAt: string
}

export interface DailyStatistics {
  id: number
  date: string
  totalSimulations: number
  completedSimulations: number
  completionRate: number
  avgMagneticEnergyEfficiency: number
  polarityReversalFrequency: number
  avgIterationsPerSimulation: number
  avgSimulationDurationHours: number
  errorCount: number
}

export interface Recommendation {
  id: number
  targetPaleomagneticRecord: string
  recommendedViscosity: number
  recommendedInnerCoreGrowthRate: number
  confidenceScore: number
  matchingSimulations: any[]
  usedFeatures: string[]
  modelVersion: string
  createdAt: string
}

export interface ParameterAdjustment {
  id: number
  simulationId: number
  reviewerId: number
  oldCmbHeatFlux: number | null
  newCmbHeatFlux: number | null
  oldInnerCoreRadius: number | null
  newInnerCoreRadius: number | null
  oldViscosity: number | null
  newViscosity: number | null
  reason: string
  approved: boolean
  createdAt: string
}

export interface DashboardData {
  overallStatistics: {
    totalSimulations: number
    completedSimulations: number
    runningSimulations: number
    errorSimulations: number
    pendingSimulations: number
    overallCompletionRate: number
    totalPolarityReversals: number
    approvedSimulations: number
    approvalRate: number
  }
  dailyStatistics: DailyStatistics[]
  charts: {
    completionTrend: string
    efficiencyTrend: string
    performanceTrend: string
  }
}
