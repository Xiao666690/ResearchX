<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getDailyOverview, type DailyOverview } from '@/api/dashboard'

const router = useRouter()
const data = ref<DailyOverview | null>(null)
const error = ref('')
const loading = ref(false)
let refreshTimer: ReturnType<typeof setInterval> | undefined

const refresh = async () => {
  loading.value = true
  try { data.value = await getDailyOverview(); error.value = '' }
  catch (cause: any) { error.value = cause?.message || '概览加载失败' }
  finally { loading.value = false }
}
const openPaper = (knowledgeID: string, documentID: string, tab?: string) => router.push({
  name: 'pdfInfo', params: { knowledgeID, documentID }, query: tab ? { tab } : {},
})
const openPost = (postID: string) => router.push({ name: 'threadDetail', params: { postid: postID } })
const formatTime = (timestamp: number) => new Date(timestamp * 1000).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
const formatDuration = (seconds: number) => seconds < 60 ? `${seconds} 秒` : `${Math.round(seconds / 60)} 分钟`

onMounted(() => { refresh(); refreshTimer = setInterval(refresh, 60000) })
onBeforeUnmount(() => clearInterval(refreshTimer))
</script>

<template>
  <main class="overview">
    <section class="hero">
      <div><p class="eyebrow">TODAY · RESEARCH WORKSPACE</p><h2>今日科研概览</h2><p>问答、研究、论文与论坛动态汇聚在同一工作空间。</p></div>
      <button class="refresh" :disabled="loading" @click="refresh">{{ loading ? '更新中…' : '刷新数据' }}</button>
    </section>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="!data" class="empty">正在读取账户活动…</p>
    <template v-else>
      <section class="stats">
        <div class="stat"><span>今日智能问答</span><strong>{{ data.stats.askCount }}</strong><small>次提问</small></div>
        <div class="stat"><span>今日深度研究</span><strong>{{ data.stats.researchCount }}</strong><small>个目标</small></div>
        <div class="stat"><span>今日上传论文</span><strong>{{ data.stats.uploadCount }}</strong><small>篇文档</small></div>
        <div class="stat"><span>今日论文研读</span><strong>{{ data.stats.readingMinutes }}</strong><small>分钟</small></div>
      </section>
      <p class="library-total">资料库总览：{{ data.stats.libraries }} 个知识库 · {{ data.stats.documents }} 篇论文 · {{ data.stats.vectors }} 个索引块</p>
      <div class="activity-grid">
        <section class="panel"><header><h3>深度研究方向</h3><button @click="router.push('/home/research')">进入 Research →</button></header>
          <p v-if="!data.researchGoals.length" class="muted">今天还没有创建研究任务。</p>
          <button v-for="task in data.researchGoals" :key="task.taskID" class="row" @click="router.push('/home/research')"><strong>{{ task.goal }}</strong><span>{{ task.status }}</span></button>
        </section>
        <section class="panel"><header><h3>今日研读与笔记</h3><button @click="router.push('/home/library/notes')">查看笔记集 →</button></header>
          <p v-if="!data.readings.length" class="muted">今天还没有研读记录。打开论文并保持页面在前台即可开始计时。</p>
          <div v-for="item in data.readings" :key="`${item.knowledgeID}:${item.documentID}`" class="row reading">
            <div><strong>{{ item.documentName }}</strong><small>{{ item.knowledgeName }} · {{ formatDuration(item.seconds) }}</small></div>
            <button v-if="item.hasNote" @click="openPaper(item.knowledgeID, item.documentID, 'note')">查看笔记</button>
            <button v-else @click="openPaper(item.knowledgeID, item.documentID, 'note')">写笔记</button>
          </div>
        </section>
        <section class="panel"><header><h3>今日上传的论文</h3><button @click="router.push('/home/library')">进入论文库 →</button></header>
          <p v-if="!data.uploadedPapers.length" class="muted">今天还没有上传论文。</p>
          <button v-for="item in data.uploadedPapers" :key="`${item.knowledgeID}:${item.documentID}`" class="row" @click="openPaper(item.knowledgeID, item.documentID)"><strong>{{ item.documentName }}</strong><span>{{ item.knowledgeName }} · {{ item.topic }}</span></button>
        </section>
        <!-- 论坛模块已隐藏 - 恢复时取消此注释即可
        <section class="panel"><header><h3>今日发帖</h3><button @click="router.push('/home/forum/threads')">进入论坛 →</button></header>
          <p v-if="!data.myPosts.length" class="muted">今天还没有发帖。</p>
          <button v-for="post in data.myPosts" :key="post.postID" class="row" @click="openPost(post.postID)"><strong>{{ post.title }}</strong><span>{{ formatTime(post.published) }}</span></button>
        </section>
        <section class="panel wide"><header><h3>论坛新帖</h3><button @click="router.push('/home/forum/threads')">浏览全部 →</button></header>
          <p v-if="!data.newPosts.length" class="muted">暂无新帖。</p>
          <button v-for="post in data.newPosts" :key="post.postID" class="row" @click="openPost(post.postID)"><strong>{{ post.title }}</strong><span>{{ post.author }} · {{ formatTime(post.published) }}</span></button>
        </section>
        -->
      </div>
    </template>
  </main>
</template>

<style scoped>
.overview { width: 100%; min-width: 0; }.hero { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 20px 24px; border: 1px solid #e3e6ef; border-radius: 16px; background: linear-gradient(110deg, #fff, #f0f3ff); }.hero h2 { font-size: 24px; font-weight: 700; color: #1f2937; }.hero p:last-child { color: #64748b; font-size: 13px; }.eyebrow { color: #6d5bd0; font-size: 10px; font-weight: 700; letter-spacing: .12em; }.refresh { padding: 8px 12px; border: 1px solid #c7c9e5; border-radius: 8px; background: white; white-space: nowrap; font-size: 12px; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 16px; }.stat { padding: 17px 18px; border: 1px solid #e3e6ef; border-radius: 14px; background: white; }.stat span,.stat small { display: block; color: #64748b; font-size: 12px; }.stat strong { display: inline-block; margin: 7px 4px 0 0; font-size: 30px; color: #242437; }.stat small { display: inline; }.library-total { margin: 12px 2px 18px; color: #7a8291; font-size: 12px; }
.activity-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; align-items: stretch; }.panel { min-width: 0; min-height: 130px; border: 1px solid #e3e6ef; border-radius: 14px; padding: 16px 18px; background: white; }.panel.wide { grid-column: 1 / -1; min-height: 94px; }.panel header { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 8px; }.panel h3 { font-size: 16px; font-weight: 700; }.panel header button { color: #6254b9; font-size: 12px; white-space: nowrap; }.row { display: flex; justify-content: space-between; align-items: center; width: 100%; gap: 12px; padding: 10px 2px; border-bottom: 1px solid #f0f1f5; text-align: left; }.row:last-child { border-bottom: 0; }.row strong { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; font-weight: 550; }.row span,.row small { display: block; flex: none; color: #8a90a0; font-size: 11px; }.row:not(.reading):hover strong { color: #6254b9; }.reading > div { min-width: 0; }.reading button { flex: none; padding: 5px 8px; border-radius: 6px; background: #f0efff; color: #6254b9; font-size: 11px; }.muted,.empty { color: #94a3b8; font-size: 13px; padding: 16px 0; }.error { margin: 12px 0; color: #b91c1c; font-size: 13px; }
@media(max-width: 1050px) { .stats { grid-template-columns: repeat(2, 1fr); } .activity-grid { grid-template-columns: 1fr; }.panel.wide { grid-column: auto; } }
@media(max-width: 600px) { .hero { align-items: flex-start; }.stats { gap: 8px; }.stat { padding: 12px; }.stat strong { font-size: 24px; } }
</style>
