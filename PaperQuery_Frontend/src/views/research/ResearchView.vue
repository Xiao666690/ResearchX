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
  Sparkles,
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

interface TaskDetail {
  task_id: string
  goal: string
  status: string
  created_at?: string
  updated_at?: string
  plan?: { steps: Array<{ step_id: string; title: string; skill: string }> }
  steps: StepInfo[]
  artifacts: ArtifactInfo[]
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
        <div class="eyebrow"><Sparkles :size="14" /> 深度研究</div>
        <h1>今天想研究什么？</h1>
        <p>描述目标，系统会自动完成论文检索、内容分析与报告整理。</p>
      </div>
      <div class="model-card">
        <div class="model-orb"><BrainCircuit :size="25" /></div>
        <div><small>研究模型</small><strong>DeepSeek</strong></div>
        <span class="online-dot">在线</span>
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

          <div class="section-title trace-title"><span>02</span><div><h3>执行轨迹</h3><p>查看智能体的规划与运行状态</p></div></div>
          <div class="timeline">
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

<style scoped>
.research-page { position: relative; width: 100%; height: 100vh; min-height: 0; overflow-x: hidden; overflow-y: auto; padding: 32px; color: #172033; background: linear-gradient(145deg, #f7f9ff 0%, #f8fbff 48%, #f7f5ff 100%); }
.ambient { position: absolute; border-radius: 999px; filter: blur(10px); pointer-events: none; opacity: .5; }
.ambient-one { width: 340px; height: 340px; right: -90px; top: -130px; background: radial-gradient(circle, #c8d9ff, transparent 70%); }
.ambient-two { width: 300px; height: 300px; left: 16%; top: 300px; background: radial-gradient(circle, #eadcff, transparent 70%); }
.hero-panel, .panel, .stat-card { position: relative; z-index: 1; border: 1px solid rgba(255,255,255,.85); box-shadow: 0 18px 55px rgba(57, 73, 125, .09); }
.hero-panel { overflow: hidden; padding: 34px; border-radius: 28px; background: linear-gradient(115deg, rgba(255,255,255,.96), rgba(245,248,255,.9)); }
.hero-panel::after { content: ''; position: absolute; width: 360px; height: 360px; right: -100px; top: -180px; border-radius: 50%; background: linear-gradient(135deg, rgba(74,111,255,.2), rgba(150,91,255,.14)); }
.hero-copy { position: relative; z-index: 1; }
.eyebrow { display: inline-flex; align-items: center; gap: 7px; margin-bottom: 12px; color: #5d6fe8; font-size: 11px; font-weight: 800; letter-spacing: .16em; }
.hero-copy h1 { margin: 0; color: #172033; font-size: clamp(30px, 3vw, 46px); line-height: 1.16; letter-spacing: -.04em; }
.hero-copy h1 span { background: linear-gradient(90deg, #5268ef, #9a58e8); -webkit-background-clip: text; color: transparent; }
.hero-copy p { margin: 14px 0 0; color: #69758d; font-size: 14px; }
.model-card { position: absolute; z-index: 2; right: 34px; top: 34px; display: flex; align-items: center; gap: 11px; padding: 11px 14px; border: 1px solid #e4e9f7; border-radius: 16px; background: rgba(255,255,255,.82); backdrop-filter: blur(12px); }
.model-orb { display: grid; place-items: center; width: 40px; height: 40px; border-radius: 13px; color: #fff; background: linear-gradient(135deg, #5268ef, #9c5ae9); box-shadow: 0 8px 20px rgba(92,102,224,.28); }
.model-card small, .model-card strong { display: block; }.model-card small { color: #929bb0; font-size: 10px; }.model-card strong { font-size: 14px; }
.online-dot { margin-left: 10px; color: #239a70; font-size: 11px; }.online-dot::before { content: ''; display: inline-block; width: 7px; height: 7px; margin-right: 5px; border-radius: 50%; background: #31c48d; box-shadow: 0 0 0 4px #e1f8ef; }
.composer { position: relative; z-index: 2; margin-top: 28px; padding: 7px; border: 1px solid #dfe5f3; border-radius: 20px; background: #fff; box-shadow: 0 14px 36px rgba(55,73,130,.08); }
.composer :deep(.el-textarea__inner) { padding: 15px 17px 8px; border: 0; box-shadow: none; color: #24304a; font-size: 15px; background: transparent; }
.composer-footer { display: flex; align-items: center; justify-content: space-between; padding: 7px 8px 7px 16px; border-top: 1px solid #f0f2f8; color: #8993a9; font-size: 12px; }.composer-footer > span { display: flex; align-items: center; gap: 6px; }
.research-button { height: 40px; border: 0 !important; border-radius: 12px !important; color: #fff !important; background: linear-gradient(120deg, #5368ef, #8b5ee7) !important; box-shadow: 0 8px 20px rgba(83,104,239,.24); }.research-button :deep(span) { display: flex; align-items: center; gap: 6px; }
.quick-prompts { position: relative; z-index: 2; display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 13px; }.quick-prompts > span { color: #99a2b4; font-size: 11px; }.quick-prompts button { max-width: 310px; overflow: hidden; padding: 7px 11px; border: 1px solid #e6e9f3; border-radius: 999px; color: #68738a; background: rgba(255,255,255,.72); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; transition: .2s; }.quick-prompts button:hover { color: #5669e8; border-color: #bdc8fa; background: #fff; transform: translateY(-1px); }
.stats-grid { position: relative; z-index: 1; display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 18px 0; }
.stat-card { display: flex; align-items: center; gap: 13px; min-height: 84px; padding: 18px; border-radius: 18px; color: #5368ef; background: rgba(255,255,255,.78); }.stat-card > svg { padding: 9px; width: 42px; height: 42px; border-radius: 13px; background: #edf0ff; }.stat-card strong, .stat-card span { display: block; }.stat-card strong { color: #202a40; font-size: 22px; line-height: 1; }.stat-card span { margin-top: 5px; color: #8a94a8; font-size: 11px; }.stat-card.success { color: #1c9c71; }.stat-card.success > svg { background: #e8faf3; }.stat-card.danger { color: #e06a6a; }.stat-card.danger > svg { background: #fff0f0; }.stat-card.violet { color: #8f5ddd; }.stat-card.violet > svg { background: #f4edff; }
.workspace-grid { position: relative; z-index: 1; display: grid; grid-template-columns: minmax(280px, 34%) minmax(0, 1fr); gap: 18px; align-items: start; }
.panel { border-radius: 22px; background: rgba(255,255,255,.86); backdrop-filter: blur(18px); }.history-panel { padding: 20px; }.detail-panel { min-height: 480px; padding: 24px; }
.panel-heading, .detail-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }.panel-heading span, .detail-kicker { color: #7484e8; font-size: 9px; font-weight: 800; letter-spacing: .18em; }.panel-heading h2, .detail-header h2 { margin: 2px 0 0; }.panel-heading h2 { font-size: 18px; }.detail-header h2 { max-width: 720px; font-size: 20px; line-height: 1.45; }
.icon-button { display: grid; place-items: center; width: 36px; height: 36px; padding: 0; border: 1px solid #e4e8f2; border-radius: 11px; color: #71809b; background: #fff; transition: .2s; }.icon-button:hover { color: #5368ef; border-color: #c4cdf6; transform: rotate(20deg); }
.task-card { display: flex; align-items: center; width: 100%; gap: 11px; margin-top: 11px; padding: 13px; border: 1px solid transparent; border-radius: 15px; text-align: left; background: #f8f9fc; transition: .2s; }.task-card:hover { border-color: #dfe4f5; background: #fff; transform: translateY(-1px); }.task-card.active { border-color: #cbd3fa; background: linear-gradient(120deg, #f2f4ff, #f8f4ff); box-shadow: 0 8px 22px rgba(82,104,239,.08); }.task-status { flex: none; width: 8px; height: 8px; border-radius: 50%; background: #a0a8b8; }.task-status.success { background: #2bb985; box-shadow: 0 0 0 4px #e4f8f0; }.task-status.failed { background: #ec7373; box-shadow: 0 0 0 4px #fff0f0; }.task-copy { flex: 1; min-width: 0; }.task-copy strong { display: block; overflow: hidden; color: #344057; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }.task-copy span { display: flex; align-items: center; gap: 4px; margin-top: 5px; color: #9aa3b5; font-size: 9px; }
.progress-row { margin: 20px 0 25px; padding: 14px 16px; border-radius: 14px; background: #f7f8fc; }.progress-row > div { display: flex; justify-content: space-between; margin-bottom: 8px; color: #8c96aa; font-size: 11px; }.progress-row strong { color: #55627a; }.progress-row :deep(.el-progress-bar__inner) { background: linear-gradient(90deg, #5368ef, #9d61e8); }
.section-title { display: flex; align-items: center; gap: 11px; margin: 20px 0 12px; }.section-title > span { color: #a9b1c1; font-size: 10px; font-weight: 800; }.section-title h3, .section-title p { margin: 0; }.section-title h3 { font-size: 15px; }.section-title p { margin-top: 2px; color: #9aa3b5; font-size: 10px; }.artifact-title { margin-top: 20px; }.trace-title { margin-top: 30px; }
.timeline { position: relative; }.timeline::before { content: ''; position: absolute; left: 15px; top: 12px; bottom: 12px; width: 1px; background: #e4e8f2; }.timeline-item { position: relative; display: flex; gap: 12px; margin-bottom: 10px; }.timeline-marker { z-index: 1; display: grid; place-items: center; flex: none; width: 31px; height: 31px; border: 3px solid #fff; border-radius: 50%; color: #6f7b93; background: #e9ecf3; font-size: 10px; }.timeline-marker.success { color: #1f9b70; background: #dff6ed; }.timeline-marker.failed { color: #d85959; background: #ffe9e9; }.step-card { flex: 1; padding: 12px 14px; border: 1px solid #edf0f5; border-radius: 13px; background: #fff; }.step-main, .step-meta { display: flex; align-items: center; gap: 8px; }.step-main strong { color: #364159; font-size: 12px; }.step-main code { padding: 2px 6px; border-radius: 5px; color: #6e7bd8; background: #f0f2ff; font-size: 9px; }.step-meta { margin-top: 7px; color: #9aa3b5; font-size: 10px; }.step-error { margin: 9px 0 0; padding: 8px 10px; border-radius: 8px; color: #b74e4e; background: #fff4f4; font-size: 10px; line-height: 1.5; }
.empty-state { display: grid; place-items: center; min-height: 380px; text-align: center; }.empty-state.compact { min-height: 240px; }.empty-icon { display: grid; place-items: center; width: 52px; height: 52px; margin-bottom: 10px; border-radius: 17px; color: #7382e6; background: linear-gradient(135deg, #eef1ff, #f5edff); }.empty-icon.large { width: 66px; height: 66px; border-radius: 22px; }.empty-state strong, .empty-state span { display: block; }.empty-state strong { color: #4e5970; font-size: 13px; }.empty-state span { margin-top: -105px; color: #a1a9b9; font-size: 11px; }.empty-state.compact span { margin-top: -55px; }.empty-artifact { padding: 26px; border: 1px dashed #dfe4ee; border-radius: 13px; color: #9ca5b7; text-align: center; font-size: 11px; }.artifact-item { margin-bottom: 12px; }
@media (max-width: 1050px) { .model-card { position: relative; right: auto; top: auto; width: max-content; margin-top: 18px; }.stats-grid { grid-template-columns: repeat(2, 1fr); }.workspace-grid { grid-template-columns: 1fr; } }
@media (max-width: 680px) { .research-page { padding: 14px; }.hero-panel { padding: 22px 18px; border-radius: 20px; }.hero-copy h1 { font-size: 29px; }.composer-footer { align-items: flex-start; gap: 10px; flex-direction: column; }.research-button { width: 100%; }.stats-grid { grid-template-columns: 1fr 1fr; gap: 9px; }.stat-card { min-height: 72px; padding: 12px; }.quick-prompts button { max-width: 100%; }.detail-header { align-items: flex-start; flex-direction: column; } }

/* 简约视觉：保留 PaperAgent 紫色识别，降低渐变、阴影与装饰噪音。 */
.research-page { padding: 38px 40px 64px; color: #202123; background: #fff; }
.hero-panel { max-width: 980px; margin: 0 auto; padding: 42px 0 28px; overflow: visible; border: 0; border-radius: 0; background: transparent; box-shadow: none; }
.hero-panel::after { display: none; }
.hero-copy { text-align: center; }
.eyebrow { margin-bottom: 14px; color: #6d5bd0; font-size: 12px; font-weight: 600; letter-spacing: 0; }
.hero-copy h1 { color: #202123; font-size: clamp(30px, 3vw, 42px); font-weight: 600; line-height: 1.2; letter-spacing: -.035em; }
.hero-copy p { margin-top: 12px; color: #6b6c70; font-size: 14px; }
.model-card { right: 0; top: 0; gap: 8px; padding: 7px 10px; border-color: #e5e5e5; border-radius: 10px; background: #fff; backdrop-filter: none; }
.model-orb { width: 28px; height: 28px; border-radius: 8px; color: #6d5bd0; background: #f2effb; box-shadow: none; }.model-orb svg { width: 16px; }
.model-card small { color: #8b8b8f; font-size: 9px; }.model-card strong { font-size: 11px; }
.online-dot { margin-left: 4px; color: #6b6c70; font-size: 9px; }.online-dot::before { width: 6px; height: 6px; margin-right: 4px; background: #20a779; box-shadow: none; }
.composer { margin-top: 30px; padding: 8px; border-color: #d9d9dc; border-radius: 20px; box-shadow: 0 4px 18px rgba(0,0,0,.06); transition: border-color .2s, box-shadow .2s; }.composer:focus-within { border-color: #b8b2d7; box-shadow: 0 5px 20px rgba(0,0,0,.08); }
.composer :deep(.el-textarea__inner) { padding: 14px 16px 10px; color: #252526; font-size: 15px; line-height: 1.6; }
.composer-footer { padding: 6px 7px 3px 15px; border-top: 0; color: #9b9b9f; font-size: 11px; }
.research-button { height: 38px; border-radius: 12px !important; background: #6d5bd0 !important; box-shadow: none; }.research-button:hover { background: #5e4bc2 !important; }
.quick-prompts { justify-content: center; margin-top: 14px; }.quick-prompts > span { color: #a0a0a4; }.quick-prompts button { max-width: 285px; padding: 7px 11px; border-color: #e5e5e7; border-radius: 9px; color: #5f6064; background: #fff; }.quick-prompts button:hover { color: #353539; border-color: #cfcbdc; background: #f7f7f8; transform: none; }
.stats-grid { max-width: 1200px; grid-template-columns: repeat(4,1fr); gap: 0; margin: 10px auto 18px; border: 1px solid #e8e8ea; border-radius: 14px; background: #fafafa; }
.stat-card { min-height: 68px; padding: 14px 18px; border: 0; border-radius: 0; color: #68686d !important; background: transparent; box-shadow: none; }.stat-card + .stat-card { border-left: 1px solid #e8e8ea; }.stat-card > svg,.stat-card.success > svg,.stat-card.danger > svg,.stat-card.violet > svg { width: 18px; height: 18px; padding: 0; border-radius: 0; color: #77777c; background: transparent; }.stat-card strong { color: #27272a; font-size: 18px; }.stat-card span { color: #8c8c91; font-size: 10px; }
.workspace-grid { max-width: 1200px; grid-template-columns: minmax(270px,31%) minmax(0,1fr); gap: 18px; margin: 0 auto; }
.panel { border: 1px solid #e6e6e8; border-radius: 14px; background: #fff; backdrop-filter: none; box-shadow: none; }.history-panel { padding: 16px; }.detail-panel { padding: 22px; }
.panel-heading span,.detail-kicker { color: #8b8b90; font-size: 10px; font-weight: 500; letter-spacing: 0; }.panel-heading h2 { font-size: 16px; }.detail-header h2 { font-size: 18px; font-weight: 600; }
.icon-button { width: 32px; height: 32px; border: 0; border-radius: 8px; color: #737378; background: transparent; }.icon-button:hover { color: #202123; border: 0; background: #f2f2f3; transform: none; }
.task-card { margin-top: 7px; padding: 11px; border: 0; border-radius: 10px; background: transparent; }.task-card:hover { border: 0; background: #f5f5f6; transform: none; }.task-card.active { border: 0; background: #ececee; box-shadow: none; }.task-status.success,.task-status.failed { box-shadow: none; }.task-copy strong { color: #37373a; font-weight: 500; }
.progress-row { margin: 18px 0 24px; padding: 0; background: transparent; }.progress-row :deep(.el-progress-bar__inner) { background: #6d5bd0; }
.section-title > span { color: #a1a1a6; font-weight: 500; }.section-title h3 { font-size: 14px; font-weight: 600; }
.step-card { border-color: #e8e8ea; border-radius: 10px; }.step-main strong { color: #414146; font-weight: 500; }.step-main code { color: #6254af; background: #f2f0f8; }
.empty-icon { border-radius: 50%; color: #6d5bd0; background: #f2f0f8; }.empty-icon.large { border-radius: 50%; }
@media (max-width:1050px) { .model-card { margin: 18px auto 0; }.stats-grid { grid-template-columns: repeat(2,1fr); }.stat-card:nth-child(3) { border-left: 0; border-top: 1px solid #e8e8ea; }.stat-card:nth-child(4) { border-top: 1px solid #e8e8ea; }.workspace-grid { grid-template-columns: 1fr; }.detail-panel { grid-row: 1; }.history-panel { grid-row: 2; } }
@media (max-width:680px) { .research-page { padding: 18px 14px 84px; }.hero-panel { padding: 26px 0 18px; }.hero-copy h1 { font-size: 30px; }.composer-footer { align-items: center; flex-direction: row; }.composer-footer > span { display: none; }.research-button { width: auto; margin-left: auto; }.stats-grid { gap: 0; }.stat-card { min-height: 62px; padding: 12px; }.quick-prompts { justify-content: flex-start; } }
.stat-card { width: 100%; text-align: left; cursor: pointer; }
.stat-card:hover { background: #f0edfb; }
.stat-menu { max-height: 320px; overflow-y: auto; }
.stat-menu button { display: block; width: 100%; padding: 8px 4px; border-bottom: 1px solid #ececf0; text-align: left; font-size: 12px; }
.stat-menu button:hover { color: #5e4bc2; background: #f8f6ff; }
.stat-menu p { color: #8a8a91; font-size: 12px; }
.stat-task { display: flex; align-items: center; }.stat-task .retry-link { flex: none; width: auto; color: #6d5bd0; white-space: nowrap; }
.continuation-label { display: flex; align-items: center; gap: 12px; margin: 4px 8px; color: #55489d; font-size: 11px; }.continuation-label button { text-decoration: underline; }
.detail-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }.detail-actions button { padding: 6px 9px; border: 1px solid #ccc4ed; border-radius: 7px; color: #5e4bc2; background: #f7f5ff; font-size: 11px; }.detail-actions button:hover { background: #ebe6ff; }
.elapsed-time { display: inline-flex; align-items: center; gap: 5px; color: #6152bd; font-size: 12px; font-variant-numeric: tabular-nums; white-space: nowrap; }
.research-activity { margin: 12px 0 0; color: #6b6c70; font-size: 12px; }
.workspace-grid.history-collapsed { grid-template-columns: 52px minmax(0,1fr); }.history-collapsed .history-panel { padding: 8px; }.history-collapsed .panel-heading > div { display: none; }
@media(max-width:1050px) { .workspace-grid.history-collapsed { grid-template-columns: 1fr; }.history-collapsed .history-panel { grid-row: 2; } }
</style>
