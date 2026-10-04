<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { ElNotification } from 'element-plus'
import {
  ArrowUpRight,
  BookOpenCheck,
  BrainCircuit,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  FileSearch,
  FlaskConical,
  RefreshCw,
  Layers3,
  XCircle,
} from 'lucide-vue-next'
import {
  createResearchTask,
  listResearchTasks,
  getResearchTask,
} from '@/api/research'
import ArtifactPanel from './components/ArtifactPanel.vue'

interface TaskItem {
  task_id: string
  goal: string
  status: string
  mode: string
  created_at?: string
  updated_at?: string
  parent_task_id?: string
}

interface StepInfo {
  step_id: string
  title?: string
  skill_name: string
  status: string
  error?: string
  duration_ms?: number
}

interface ArtifactInfo {
  artifact_id: string
  type: string
  title: string
  data?: Record<string, any>
}

interface TraceEvent {
  sequence: number
  event_type: string
  title: string
  detail?: string
  data?: Record<string, any>
  created_at?: string
}

interface TaskDetail {
  task_id: string
  goal: string
  status: string
  created_at?: string
  updated_at?: string
  plan?: { steps: Array<{ step_id: string; title: string; skill: string }> }
  steps: StepInfo[]
  artifacts: ArtifactInfo[]
  events?: TraceEvent[]
  stop_reason?: string
  turn_count?: number
  replan_count?: number
  tool_calls?: number
  evidence_state?: { status: string; required_sources?: number; sources?: Array<unknown>; reason?: string }
}

const goal = ref('')
const creating = ref(false)
const tasks = ref<TaskItem[]>([])
const currentTask = ref<TaskDetail | null>(null)
const loadingDetail = ref(false)
const historyCollapsed = ref(true)
const parentTaskId = ref('')
const clock = ref(Date.now())
let clockTimer: ReturnType<typeof setInterval> | undefined
let pollTimer: ReturnType<typeof setInterval> | undefined
let polling = false

const isActive = (status?: string) => status === 'PENDING' || status === 'RUNNING'
const elapsedTime = (createdAt?: string) => {
  if (!createdAt) return '0 秒'
  const seconds = Math.max(0, Math.floor((clock.value - new Date(createdAt).getTime()) / 1000))
  if (seconds < 60) return `${seconds} 秒`
  return `${Math.floor(seconds / 60)} 分 ${String(seconds % 60).padStart(2, '0')} 秒`
}
const hasRecentActivity = (updatedAt?: string) =>
  Boolean(updatedAt && clock.value - new Date(updatedAt).getTime() < 20000)

const quickGoals = [
  '检索并比较近三年多模态大模型的代表性方法与数据集',
  '梳理时间序列预测领域的主流技术路线并生成综述',
  '分析 RAG 系统的评估指标、常用基准与研究趋势',
]

const successfulTasks = computed(
  () => tasks.value.filter((task) => task.status === 'SUCCESS').length,
)
const failedTasks = computed(
  () => tasks.value.filter((task) => task.status === 'FAILED').length,
)
const completedSteps = computed(
  () => currentTask.value?.steps.filter((step) => step.status === 'SUCCESS').length || 0,
)
const displaySteps = computed<StepInfo[]>(() => {
  if (!currentTask.value) return []
  const planned = (currentTask.value.plan?.steps || []).map(step => ({
    ...currentTask.value!.steps.find(result => result.step_id === step.step_id),
    step_id: step.step_id,
    title: step.title,
    skill_name: step.skill,
    status: currentTask.value!.steps.find(result => result.step_id === step.step_id)?.status || 'PENDING',
  }))
  const unplanned = currentTask.value.steps.filter(result => !planned.some(step => step.step_id === result.step_id))
  return [...planned, ...unplanned]
})
const currentProgress = computed(() => {
  const total = currentTask.value?.plan?.steps?.length || currentTask.value?.steps.length || 0
  return total ? Math.round((completedSteps.value / total) * 100) : 0
})
const traceLabels: Record<string, string> = {
  GOAL: '研究目标', PLAN: '规划', ACTION: '行动', OBSERVATION: '观察',
  EVIDENCE: '证据判断', REPLAN: '重新规划', VERIFICATION: '结果核验',
  ARTIFACT: '交付物', FINISH: '完成', STOP: '停止',
}
const evidenceLabel = (status?: string) => ({
  SUFFICIENT: '证据充分', PARTIAL: '证据不足', MISSING_EXTERNAL: '需要外部证据',
  CONFLICT: '证据冲突', UNSUPPORTED: '缺少依据', UNKNOWN: '待评估',
}[status || 'UNKNOWN'] || status || '待评估')

const getErrorMessage = (error: any, fallback: string) =>
  error?.response?.data?.detail || error?.response?.data?.msg || error?.message || fallback

const loadTasks = async () => {
  try {
    const resp = await listResearchTasks()
    if (resp?.data) {
      tasks.value = resp.data
      if (!currentTask.value && tasks.value.length > 0) {
        await selectTask(tasks.value[0].task_id)
      }
    }
  } catch (e: any) {
    console.error(e)
  }
}

const handleCreate = async () => {
  if (!goal.value.trim()) return
  creating.value = true
  try {
    const resp = await createResearchTask(goal.value.trim(), 'research', [], parentTaskId.value || undefined)
    if (resp?.data) {
      ElNotification.success(`任务已创建：${resp.data.task_id}`)
      goal.value = ''
      parentTaskId.value = ''
      await loadTasks()
      await selectTask(resp.data.task_id)
    }
  } catch (e: any) {
    ElNotification.error({ title: '创建失败', message: getErrorMessage(e, '任务创建失败') })
  } finally {
    creating.value = false
  }
}

const retryTask = async (task: Pick<TaskItem, 'task_id' | 'goal'>) => {
  goal.value = task.goal
  parentTaskId.value = task.task_id
  await handleCreate()
}

const continueFromTask = (task: TaskDetail) => {
  parentTaskId.value = task.task_id
  goal.value = `基于“${task.goal}”的研究结果，进一步研究：`
  document.querySelector('.hero-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const focusTask = async (taskId: string) => {
  await selectTask(taskId)
  document.getElementById('research-detail')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const focusArtifact = (artifactId: string) => {
  document.getElementById(`artifact-${artifactId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

const selectTask = async (taskId: string) => {
  loadingDetail.value = true
  try {
    const resp = await getResearchTask(taskId)
    if (resp?.data) {
      currentTask.value = resp.data
    }
  } catch (e: any) {
    ElNotification.error({ title: '加载失败', message: getErrorMessage(e, '任务详情加载失败') })
  } finally {
    loadingDetail.value = false
  }
}

const statusType = (status: string): 'success' | 'danger' | 'warning' | 'info' => {
  if (status === 'SUCCESS') return 'success'
  if (status === 'FAILED') return 'danger'
  if (status === 'RUNNING') return 'warning'
  return 'info'
}

const statusLabel = (status: string) => {
  if (status === 'SUCCESS') return '已完成'
  if (status === 'FAILED') return '执行失败'
  if (status === 'RUNNING') return '执行中'
  if (status === 'PENDING') return '排队中'
  return '等待中'
}

const formatTime = (value?: string) => {
  if (!value) return '刚刚'
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(() => {
  loadTasks()
  clockTimer = setInterval(() => { clock.value = Date.now() }, 1000)
  pollTimer = setInterval(async () => {
    if (polling || !tasks.value.some(task => isActive(task.status))) return
    polling = true
    try {
      await loadTasks()
      if (currentTask.value && isActive(currentTask.value.status)) await selectTask(currentTask.value.task_id)
    } finally { polling = false }
  }, 3000)
})
onBeforeUnmount(() => { clearInterval(clockTimer); clearInterval(pollTimer) })
</script>

<template>
  <main class="research-page">
    <section class="hero-panel">
      <div class="hero-copy">
        <div class="eyebrow"><Layers3 :size="14" /> RESEARCH / 深度研究</div>
        <h1>今天想研究什么？</h1>
        <p>写下研究目标，ResearchX 会依据证据逐步推进，并记录每一次判断。</p>
      </div>

      <div class="composer">
        <div v-if="parentTaskId" class="continuation-label">接续任务 {{ parentTaskId }} <button type="button" @click="parentTaskId = ''">取消关联</button></div>
        <el-input
          v-model="goal"
          type="textarea"
          :autosize="{ minRows: 3, maxRows: 6 }"
          resize="none"
          placeholder="描述你的研究目标，例如：检索并比较相关论文的方法、数据集与实验结论……"
          @keydown.ctrl.enter="handleCreate"
        />
        <div class="composer-footer">
          <span>Ctrl + Enter 发送</span>
          <el-button
            class="research-button"
            :disabled="!goal.trim() || creating"
            :loading="creating"
            @click="handleCreate"
          >
            开始研究 <ArrowUpRight v-if="!creating" :size="17" />
          </el-button>
        </div>
      </div>

      <div class="quick-prompts">
        <span>试试这些方向</span>
        <button v-for="item in quickGoals" :key="item" type="button" @click="goal = item">
          {{ item }}
        </button>
      </div>
    </section>

    <section class="stats-grid">
      <el-popover trigger="click" placement="bottom" :width="370"><template #reference><button class="stat-card"><FlaskConical /><div><strong>{{ tasks.length }}</strong><span>全部研究任务</span></div></button></template><div class="stat-menu"><button v-for="task in tasks" :key="task.task_id" @click="focusTask(task.task_id)">{{ task.goal }} · {{ statusLabel(task.status) }}</button><p v-if="!tasks.length">暂无任务</p></div></el-popover>
      <el-popover trigger="click" placement="bottom" :width="370"><template #reference><button class="stat-card success"><CheckCircle2 /><div><strong>{{ successfulTasks }}</strong><span>成功完成</span></div></button></template><div class="stat-menu"><button v-for="task in tasks.filter(item => item.status === 'SUCCESS')" :key="task.task_id" @click="focusTask(task.task_id)">{{ task.goal }}</button><p v-if="!successfulTasks">暂无已完成任务</p></div></el-popover>
      <el-popover trigger="click" placement="bottom" :width="370"><template #reference><button class="stat-card danger"><XCircle /><div><strong>{{ failedTasks }}</strong><span>需要关注</span></div></button></template><div class="stat-menu"><div v-for="task in tasks.filter(item => item.status === 'FAILED')" :key="task.task_id" class="stat-task"><button @click="focusTask(task.task_id)">{{ task.goal }}</button><button class="retry-link" @click="retryTask(task)">重新执行</button></div><p v-if="!failedTasks">暂无失败任务</p></div></el-popover>
      <el-popover trigger="click" placement="bottom" :width="370"><template #reference><button class="stat-card violet"><BookOpenCheck /><div><strong>{{ currentTask?.artifacts.length || 0 }}</strong><span>当前交付物</span></div></button></template><div class="stat-menu"><button v-for="artifact in currentTask?.artifacts || []" :key="artifact.artifact_id" @click="focusArtifact(artifact.artifact_id)">{{ artifact.title }}</button><p v-if="!currentTask?.artifacts.length">当前任务暂无交付物</p></div></el-popover>
    </section>

    <section class="workspace-grid" :class="{ 'history-collapsed': historyCollapsed }">
      <aside class="panel history-panel">
        <div class="panel-heading">
          <div><span>最近</span><h2>历史任务</h2></div>
          <button class="icon-button" type="button" :title="historyCollapsed ? '展开历史任务' : '收起历史任务'" @click="historyCollapsed = !historyCollapsed"><ChevronRight v-if="historyCollapsed" :size="17" /><ChevronLeft v-else :size="17" /></button>
          <button v-if="!historyCollapsed" class="icon-button" type="button" title="刷新" @click="loadTasks"><RefreshCw :size="17" /></button>
        </div>

        <div v-if="!historyCollapsed && tasks.length === 0" class="empty-state compact">
          <div class="empty-icon"><FileSearch :size="26" /></div>
          <strong>还没有研究记录</strong><span>从上方输入一个研究目标开始</span>
        </div>
        <button
          v-for="task in historyCollapsed ? [] : tasks"
          :key="task.task_id"
          type="button"
          class="task-card"
          :class="{ active: currentTask?.task_id === task.task_id }"
          @click="selectTask(task.task_id)"
        >
          <span class="task-status" :class="task.status.toLowerCase()" />
          <div class="task-copy">
            <strong>{{ task.goal }}</strong>
            <span><Clock3 :size="12" /> {{ formatTime(task.created_at) }} · {{ task.task_id }}</span>
          </div>
          <el-tag :type="statusType(task.status)" size="small" effect="light">{{ statusLabel(task.status) }}</el-tag>
        </button>
      </aside>

      <section id="research-detail" class="panel detail-panel" v-loading="loadingDetail">
        <div v-if="!currentTask" class="empty-state">
          <div class="empty-icon large"><BrainCircuit :size="34" /></div>
          <strong>选择一个研究任务</strong><span>执行步骤与研究交付物会显示在这里</span>
        </div>
        <template v-else>
          <div class="detail-header">
            <div>
              <span class="detail-kicker">TASK {{ currentTask.task_id }}</span>
              <h2>{{ currentTask.goal }}</h2>
            </div>
            <div class="detail-actions"><span v-if="isActive(currentTask.status)" class="elapsed-time"><Clock3 :size="15" /> 已研究 {{ elapsedTime(currentTask.created_at) }}</span><button v-if="currentTask.status === 'FAILED'" type="button" @click="retryTask(currentTask)">重新执行</button><button v-if="currentTask.status === 'SUCCESS'" type="button" @click="continueFromTask(currentTask)">基于结果继续研究</button><el-tag :type="statusType(currentTask.status)" size="large" effect="light">{{ statusLabel(currentTask.status) }}</el-tag></div>
          </div>

          <p v-if="isActive(currentTask.status)" class="research-activity">
            {{ currentTask.status === 'PENDING' ? '任务已创建，等待执行。' : hasRecentActivity(currentTask.updated_at) ? '研究任务近期有进展，正在继续执行。' : currentTask.plan ? '正在等待当前研究步骤返回；任务会继续运行，不受页面等待时间限制。' : '正在规划研究步骤，复杂任务可能需要较长时间。' }}
          </p>

          <div class="progress-row">
            <div><span>执行进度</span><strong>{{ completedSteps }} / {{ currentTask.plan?.steps?.length || currentTask.steps.length }} 步</strong></div>
            <el-progress :percentage="currentProgress" :stroke-width="9" :show-text="false" />
          </div>

          <div class="section-title artifact-title"><span>01</span><div><h3>研究结果</h3><p>{{ currentTask.artifacts.length }} 项结构化交付物</p></div></div>
          <div v-if="currentTask.artifacts.length === 0" class="empty-artifact">
            当前任务尚未生成研究结果
          </div>
          <div v-for="artifact in currentTask.artifacts" :id="`artifact-${artifact.artifact_id}`" :key="artifact.artifact_id">
          <ArtifactPanel
            :key="artifact.artifact_id"
            :artifact="artifact"
            class="artifact-item"
          />
          </div>

          <div class="section-title trace-title"><span>02</span><div><h3>Agent Trace</h3><p>观察规划、行动、证据判断和重新规划</p></div></div>
          <div v-if="currentTask.events?.length" class="trace-summary">
            <span>行动 {{ currentTask.turn_count || 0 }}</span><span>工具调用 {{ currentTask.tool_calls || 0 }}</span><span>重新规划 {{ currentTask.replan_count || 0 }}</span>
            <span class="evidence-badge" :class="(currentTask.evidence_state?.status || 'UNKNOWN').toLowerCase()">{{ evidenceLabel(currentTask.evidence_state?.status) }} · {{ currentTask.evidence_state?.sources?.length || 0 }}/{{ currentTask.evidence_state?.required_sources || 1 }} 来源</span>
          </div>
          <p v-if="currentTask.stop_reason && currentTask.status === 'FAILED'" class="stop-reason">停止原因：{{ currentTask.stop_reason }}</p>
          <div v-if="currentTask.events?.length" class="timeline agent-timeline">
            <div v-for="event in currentTask.events" :key="event.sequence" class="timeline-item">
              <div class="timeline-marker event-marker" :class="event.event_type.toLowerCase()"><RefreshCw v-if="event.event_type === 'PLAN' || event.event_type === 'REPLAN'" :size="14" /><CheckCircle2 v-else-if="event.event_type === 'FINISH'" :size="14" /><XCircle v-else-if="event.event_type === 'STOP'" :size="14" /><span v-else>{{ event.sequence }}</span></div>
              <div class="step-card event-card" :class="event.event_type.toLowerCase()"><div class="event-topline"><span>{{ traceLabels[event.event_type] || event.event_type }}</span><small>{{ formatTime(event.created_at) }}</small></div><strong>{{ event.title }}</strong><p v-if="event.detail">{{ event.detail }}</p><code v-if="event.event_type === 'ACTION' && event.data?.input">{{ JSON.stringify(event.data.input) }}</code></div>
            </div>
          </div>
          <div v-else class="timeline">
            <div v-for="(step, index) in displaySteps" :key="step.step_id" class="timeline-item">
              <div class="timeline-marker" :class="step.status.toLowerCase()">
                <CheckCircle2 v-if="step.status === 'SUCCESS'" :size="17" />
                <XCircle v-else-if="step.status === 'FAILED'" :size="17" />
                <span v-else>{{ index + 1 }}</span>
              </div>
              <div class="step-card">
                <div class="step-main"><strong>{{ step.title || step.skill_name }}</strong><code>{{ step.skill_name }}</code></div>
                <div class="step-meta">
                  <el-tag :type="statusType(step.status)" size="small">{{ statusLabel(step.status) }}</el-tag>
                  <span v-if="step.duration_ms != null">{{ (step.duration_ms / 1000).toFixed(2) }} 秒</span>
                </div>
                <p v-if="step.error" class="step-error">{{ step.error }}</p>
              </div>
            </div>
          </div>

        </template>
      </section>
    </section>
  </main>
</template>

<style scoped src="./research-refined.css"></style>
