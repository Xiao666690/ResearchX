<script setup lang="ts">
import { ArrowUpRight, BookOpenCheck, FileSearch, Layers3 } from 'lucide-vue-next'
import TodayOverview from './TodayOverview.vue'

const username = localStorage.getItem('username') || '研究者'
</script>

<template>
  <main class="dashboard-shell">
    <section class="welcome-hero">
      <div class="hero-content">
        <div class="hero-eyebrow">RESEARCHX / WORKSPACE</div>
        <h1>从一个好问题，<br /><em>走向可信的结论。</em></h1>
        <p>{{ username }}，欢迎回来。继续整理文献、追踪证据，推进今天的研究。</p>
        <router-link to="/home/research" class="hero-cta">开始一项研究 <ArrowUpRight :size="17" /></router-link>
      </div>
      <div class="hero-aside">
        <span class="aside-index">RESEARCH PROCESS / 01—03</span>
        <div><span>01</span><strong>定义问题</strong></div>
        <div><span>02</span><strong>辨认证据</strong></div>
        <div><span>03</span><strong>沉淀成果</strong></div>
      </div>
    </section>
    <div class="section-heading"><span>WORKSPACE</span><h2>接下来，去哪里？</h2></div>
    <section class="quick-grid">
      <router-link to="/home/research" class="quick-card research"><div class="quick-icon"><Layers3 :size="21" /></div><div><strong>深度研究</strong><p>提出目标，查看每一步研究判断与成果。</p></div><ArrowUpRight class="quick-arrow" :size="18" /></router-link>
      <router-link to="/home/library" class="quick-card library"><div class="quick-icon"><BookOpenCheck :size="23" /></div><div><strong>论文资料库</strong><p>管理文献与笔记，沉淀可复用的知识。</p></div><ArrowUpRight class="quick-arrow" :size="19" /></router-link>
      <router-link to="/home/chat" class="quick-card ask"><div class="quick-icon"><FileSearch :size="23" /></div><div><strong>智能问答</strong><p>从已有论文与外部证据中寻找答案。</p></div><ArrowUpRight class="quick-arrow" :size="19" /></router-link>
    </section>
    <TodayOverview />
  </main>
</template>

<style scoped src="./dashboard-refined.css"></style>
