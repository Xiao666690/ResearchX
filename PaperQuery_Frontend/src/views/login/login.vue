<script setup lang="ts">
import { Search, FileText, ListChecks } from 'lucide-vue-next'
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { ElNotification } from 'element-plus'
import { login, register } from '@/api/auth'
import paperAgentMark from '@/assets/img/paperagent-mark.png'

const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const registering = ref(false)
const teamName = ref('') // 注册时填团队名 = 提交加入申请（待管理员审批）
const busy = ref(false)
const router = useRouter()

const url = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001'

// 向后端发送登录请求并将用户信息存储到 Vuex 和 localStorage 中
const Login = async () => {
  if (busy.value) return
  if (registering.value && password.value !== confirmPassword.value) {
    ElNotification.error({ title: '注册失败', message: '两次输入的密码不一致' })
    return
  }
  busy.value = true
  const user = {
    username: username.value,
    password: password.value,
  }

  try {
    if (registering.value) {
      const res = await register(url, {
        username: username.value,
        password: password.value,
        teamName: teamName.value,
      })
      registering.value = false
      confirmPassword.value = ''
      ElNotification.success({ title: '注册成功', message: res?.msg || '请使用新账户登录' })
      return
    }
    await login(url, user)
    ElNotification({
      title: '登录成功',
      type: 'success',
      customClass: 'login-notify-fade-up',
    })
    router.push('/home')
  } catch (error) {
    if (error instanceof Error) {
      ElNotification({
        title: registering.value ? '注册失败' : '登录失败',
        type: 'error',
        message: error.message,
        customClass: 'login-notify-fade-up',
      })
      console.error('登录失败:', error)
    } else {
      // 处理非 Error 对象的情况
      ElNotification({
        title: registering.value ? '注册失败' : '登录失败',
        type: 'error',
        message: '发生未知错误',
        customClass: 'login-notify-fade-up',
      })
    }
  } finally { busy.value = false }
}
</script>

<template>
  <main class="login-page">
    <section class="login-shell">
      <!-- 左侧品牌叙事区（≥1024px 显示，<1024px 隐藏） -->
      <div class="brand-panel">
        <div class="brand-panel-inner">
          <div class="brand-logo">
            <span class="brand-logo-badge">
              <img :src="paperAgentMark" alt="PaperAgent 标志" />
            </span>
            <span class="brand-wordmark">PaperAgent</span>
          </div>

          <div class="brand-headline">
            <h1>可信智能研究工作台</h1>
            <p>阅读、理解与研究你的论文</p>
          </div>

          <div class="brand-features">
            <div class="feature-card">
              <span class="feature-icon"><Search /></span>
              <span class="feature-text">证据可溯源</span>
            </div>
            <div class="feature-card">
              <span class="feature-icon"><FileText /></span>
              <span class="feature-text">混合检索问答</span>
            </div>
            <div class="feature-card">
              <span class="feature-icon"><ListChecks /></span>
              <span class="feature-text">科研任务编排</span>
            </div>
          </div>
        </div>

        <p class="brand-tagline">Your private workspace for academic discovery.</p>
      </div>

      <!-- 右侧登录表单区 -->
      <div class="form-panel">
        <Card class="login-card">
          <form @submit.prevent="Login">
            <CardHeader>
              <CardTitle>{{ registering ? '创建 PaperAgent 账户' : '欢迎回来' }}</CardTitle>
              <p class="card-description">{{ registering ? '注册后即可建立自己的论文库与研究工作空间' : '登录后继续访问你的论文库与研究任务' }}</p>
            </CardHeader>

            <CardContent>
              <div class="grid items-center w-full gap-4">
                <div class="flex flex-col space-y-1.5">
                  <Label for="username">用户名</Label>
                  <Input
                    id="username"
                    v-model="username"
                    placeholder="请输入用户名"
                    autocomplete="username"
                    required
                  />
                </div>
                <div class="flex flex-col space-y-1.5">
                  <Label for="password">密码</Label>
                  <Input
                    id="password"
                    v-model="password"
                    type="password"
                    placeholder="请输入密码"
                    :autocomplete="registering ? 'new-password' : 'current-password'"
                    :minlength="registering ? 8 : undefined"
                    required
                  />
                </div>
                <div v-if="registering" class="flex flex-col space-y-1.5">
                  <Label for="confirm-password">确认密码</Label>
                  <Input id="confirm-password" v-model="confirmPassword" type="password" autocomplete="new-password" placeholder="再次输入密码" required />
                </div>
                <div v-if="registering" class="flex flex-col space-y-1.5">
                  <Label for="team-name">团队名（可选）</Label>
                  <Input
                    id="team-name"
                    v-model="teamName"
                    placeholder="填写团队管理员名字，如 admin"
                    autocomplete="off"
                  />
                  <p class="team-name-hint">填了团队名 = 提交加入申请，管理员通过后生效</p>
                </div>
              </div>
            </CardContent>
            <CardFooter class="login-footer">
              <Button type="submit" class="login-button" :disabled="busy">{{ busy ? '请稍候…' : registering ? '注册账户' : '登录' }}</Button>
              <button type="button" class="auth-switch" @click="registering = !registering; confirmPassword = ''">{{ registering ? '已有账户？返回登录' : '没有账户？立即注册' }}</button>
              <p v-if="!registering">请使用已创建的账户登录</p>
            </CardFooter>
          </form>
        </Card>
      </div>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  display: grid;
  width: 100%;
  min-height: 100vh;
  place-items: center;
  color: #333333;
  background: #e9e6f9;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text",
    "PingFang SC", "Helvetica Neue", Arial, sans-serif;
}
.login-shell {
  display: flex;
  width: 100%;
  min-height: 100vh;
  align-items: center;
  justify-content: center;
  position: relative;
  background: #e9e6f9;
}
.login-shell::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(109, 91, 208, 0.15) 1px, transparent 1px),
    linear-gradient(90deg, rgba(109, 91, 208, 0.15) 1px, transparent 1px);
  background-size: 44px 44px;
  -webkit-mask-image: linear-gradient(90deg, #000 0%, #000 50%, transparent 100%);
  mask-image: linear-gradient(90deg, #000 0%, #000 50%, transparent 100%);
}

/* ===== 左侧品牌叙事区（新拟物浅色同色系，右区布局留空） ===== */
.brand-panel {
  display: none;
  flex: none;
  width: 55%;
  min-height: 100vh;
  flex-direction: column;
  justify-content: center;
  padding: 32px 24px 128px 150px;
  color: #333333;
  position: relative;
  overflow: hidden;
  background: #e9e6f9;
  box-sizing: border-box;
}
.brand-panel-inner {
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: center;
  gap: 38px;
  position: relative;
}
.brand-logo {
  display: flex;
  align-items: center;
  gap: 13px;
  margin-bottom: 12px;
}
.brand-logo-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 68px;
  height: 68px;
  border-radius: 50%;
  background: #e7e9f0;
  box-shadow:
    4px 4px 8px #acb2bd,
    -4px -4px 8px #ffffff;
}
.brand-logo-badge img {
  width: 48px;
  height: 48px;
  object-fit: contain;
}
.brand-wordmark {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #333333;
}
.brand-headline h1 {
  margin: 0;
  font-size: 44px;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: 0.01em;
  color: #333333;
}
.brand-headline p {
  margin: 14px 0 0;
  color: #6b7280;
  font-size: 16px;
}
.brand-features {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-width: 360px;
}
.feature-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 19px 22px;
  border: none;
  border-radius: 16px;
  background: #e7e9f0;
  box-shadow:
    4px 4px 8px #acb2bd,
    -4px -4px 8px #ffffff;
  font-size: 17px;
  font-weight: 500;
  color: #333333;
  transition: all 0.3s ease-in-out;
}
.feature-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #e9e6f9;
  color: #6d5bd0;
  flex-shrink: 0;
  box-shadow:
    inset 2px 2px 4px rgba(0, 0, 0, 0.08),
    inset -2px -2px 4px rgba(255, 255, 255, 0.8);
}
.feature-icon :deep(svg) {
  width: 24px;
  height: 24px;
}
.brand-tagline {
  margin: 0;
  color: #6b7280;
  font-size: 12px;
  letter-spacing: 0.04em;
}

/* ===== 右侧登录表单区 ===== */
.form-panel {
  display: flex;
  flex: none;
  width: 45%;
  min-height: 100vh;
  align-items: center;
  justify-content: center;
  padding: 28px;
  box-sizing: border-box;
  background: transparent;
}
.login-card {
  width: 100%;
  max-width: 390px;
  border: none;
  border-radius: 24px;
  background: #e9ebf2;
  transition: all 0.3s ease-in-out;
  box-shadow:
    8px 8px 16px #acb2bd,
    -8px -8px 16px #ffffff;
}
.login-card :deep(h3) {
  font-size: 19px;
  font-weight: 600;
  color: #333333;
}
.card-description {
  margin: 5px 0 0;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.5;
}
.login-card :deep(input) {
  height: 48px;
  padding: 0 16px;
  border: none;
  border-radius: 14px;
  background: #d5dbe6;
  color: #333333;
  box-shadow:
    inset 6px 6px 12px #acb2bd,
    inset -6px -6px 12px #ffffff;
  transition: box-shadow 0.3s ease-in-out;
}
.login-card :deep(input:focus) {
  outline: none;
  box-shadow:
    inset 2px 2px 4px #acb2bd,
    inset -2px -2px 4px #ffffff,
    0 0 0 3px rgba(109, 91, 208, 0.2);
}
.team-name-hint {
  margin: 0;
  color: #8a8fa3;
  font-size: 11px;
  line-height: 1.4;
}
.login-footer {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 0 24px 24px;
}
.login-button {
  width: 100%;
  height: 48px;
  border: none;
  border-radius: 14px;
  color: #fff;
  background: #6d5bd0;
  box-shadow:
    8px 8px 16px #acb2bd,
    -8px -8px 16px #ffffff;
  transition: all 0.3s ease-in-out;
}
.login-button:hover {
  background: #5e4bc2;
  box-shadow:
    4px 4px 8px #acb2bd,
    -4px -4px 8px #ffffff;
}
.login-button:active {
  box-shadow:
    inset 4px 4px 8px #acb2bd,
    inset -4px -4px 8px #ffffff;
}
.login-footer p {
  margin: 0;
  color: #6b7280;
  font-size: 10px;
  text-align: center;
}
.auth-switch { color: #5e4bc2; font-size: 13px; font-weight: 600; }
.auth-switch:hover { text-decoration: underline; }

/* ===== 响应式降级：<1024px 只保留表单 ===== */
@media (min-width: 1024px) {
  .brand-panel {
    display: flex;
  }
}
@media (max-width: 1023px) {
  .brand-panel {
    display: none;
  }
  .form-panel {
    width: 100%;
    padding: 18px;
  }
  .login-card {
    border-radius: 22px;
    box-shadow: none;
  }
}
</style>

<style>
/* 登录弹窗：淡入 + 上滑（弹窗 teleport 到 body，故用非 scoped 全局样式覆盖） */
.login-notify-fade-up {
  animation-name: login-notify-fade-in-up !important;
  animation-duration: 600ms !important;
  animation-timing-function: cubic-bezier(0.16, 1, 0.3, 1) !important;
  animation-fill-mode: both !important;
  border-radius: 16px !important;
  box-shadow:
    6px 6px 12px #b8bcc2,
    -6px -6px 12px #ffffff !important;
}

@keyframes login-notify-fade-in-up {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .login-notify-fade-up {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
  }
}
</style>
