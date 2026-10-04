<script setup lang="ts">
import { ArrowRight, BookOpen, FileSearch, Layers3 } from 'lucide-vue-next'
import { ElNotification } from 'element-plus'
import { login, register } from '@/api/auth'
import researchXMark from '@/assets/img/researchx-mark.svg'

const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const registering = ref(false)
const teamName = ref('')
const busy = ref(false)
const router = useRouter()
const url = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001'

const submit = async () => {
  if (busy.value) return
  if (registering.value && password.value !== confirmPassword.value) {
    ElNotification.error({ title: '注册失败', message: '两次输入的密码不一致' })
    return
  }
  busy.value = true
  try {
    if (registering.value) {
      const res = await register(url, {
        username: username.value, password: password.value, teamName: teamName.value,
      })
      registering.value = false
      confirmPassword.value = ''
      ElNotification.success({ title: '注册成功', message: res?.msg || '请使用新账户登录' })
      return
    }
    await login(url, { username: username.value, password: password.value })
    ElNotification.success({ title: '欢迎来到 ResearchX' })
    router.push('/home')
  } catch (error) {
    ElNotification.error({
      title: registering.value ? '注册失败' : '登录失败',
      message: error instanceof Error ? error.message : '请稍后重试',
    })
  } finally {
    busy.value = false
  }
}

const toggleMode = () => {
  registering.value = !registering.value
  confirmPassword.value = ''
}
</script>

<template>
  <main class="auth-page">
    <header class="site-header">
      <a class="site-brand" href="#top" aria-label="ResearchX 首页">
        <img class="brand-symbol" :src="researchXMark" alt="" />
        <span>ResearchX</span>
      </a>
      <div class="header-right"><a href="#capabilities">产品能力</a><button type="button" @click="toggleMode">{{ registering ? '返回登录' : '创建账户' }} <ArrowRight :size="15" /></button></div>
    </header>

    <div id="top" class="auth-content">
      <section class="story-panel">
        <div class="story-copy">
          <div class="eyebrow"><span class="eyebrow-line" /> RESEARCHX · EVIDENCE-LED RESEARCH</div>
          <h1 class="brand-slogan" aria-label="Beyond Answers. Toward Discovery.">
            <span class="slogan-line" aria-hidden="true"><span class="slogan-word slogan-word-1">Beyond</span> <span class="slogan-word slogan-word-2">Answers.</span></span>
            <span class="slogan-line" aria-hidden="true"><span class="slogan-word slogan-word-3">Toward</span> <span class="slogan-word slogan-word-4 discovery-word">Discovery.</span></span>
          </h1>
          <p class="story-translation">不止于回答，迈向真正的发现。</p>
          <p class="story-description">从问题出发，检索文献、核验证据、形成有依据的研究成果。让探索的每一步，都清晰可见。</p>
          <div class="story-actions"><a href="#capabilities">了解 ResearchX <ArrowRight :size="17" /></a></div>
        </div>
        <div class="research-sequence" aria-label="ResearchX 研究流程">
          <div><span>01</span><strong>提出问题</strong><small>确定清晰的研究目标</small></div>
          <div><span>02</span><strong>核验证据</strong><small>让来源支撑每个判断</small></div>
          <div><span>03</span><strong>形成成果</strong><small>沉淀可回看的研究过程</small></div>
        </div>
      </section>

      <section class="form-column">
        <div class="auth-card">
          <div class="card-top"><span class="card-overline">WORKSPACE ACCESS</span><span class="card-index">01 / 01</span></div>
          <div class="card-heading"><h2>{{ registering ? '创建研究空间' : '欢迎回来' }}</h2><p>{{ registering ? '填写以下信息，建立你的 ResearchX 账户。' : '登录后继续你的论文阅读与研究任务。' }}</p></div>
          <form class="auth-form" @submit.prevent="submit">
            <label for="username">用户名</label>
            <input id="username" v-model="username" name="username" autocomplete="username" placeholder="你的用户名" required />
            <label for="password">密码</label>
            <input id="password" v-model="password" name="password" type="password" :autocomplete="registering ? 'new-password' : 'current-password'" :minlength="registering ? 8 : undefined" placeholder="输入密码" required />
            <template v-if="registering">
              <label for="confirm-password">确认密码</label>
              <input id="confirm-password" v-model="confirmPassword" name="confirm-password" type="password" autocomplete="new-password" placeholder="再次输入密码" required />
              <label for="team-name">团队名 <span>选填</span></label>
              <input id="team-name" v-model="teamName" name="team-name" autocomplete="off" placeholder="填写团队管理员名字，如 admin" />
              <p class="field-note">填写团队名将提交加入申请，待管理员审核后生效。</p>
            </template>
            <button class="submit-button" type="submit" :disabled="busy"><span>{{ busy ? '请稍候…' : registering ? '创建账户' : '进入 ResearchX' }}</span><ArrowRight :size="18" /></button>
          </form>
          <div class="card-bottom"><span>{{ registering ? '已经有账户？' : '初次来到 ResearchX？' }}</span><button type="button" @click="toggleMode">{{ registering ? '立即登录' : '创建账户' }}</button></div>
        </div>
        <p class="access-note">让好的研究，从清晰的第一步开始。</p>
      </section>
    </div>

    <footer id="capabilities" class="capability-bar">
      <div><BookOpen :size="16" /><strong>文献管理</strong></div>
      <div><FileSearch :size="16" /><strong>证据研究</strong></div>
      <div><Layers3 :size="16" /><strong>成果沉淀</strong></div>
      <p>© ResearchX</p>
    </footer>
  </main>
</template>

<style scoped src="./login-refined.css"></style>
