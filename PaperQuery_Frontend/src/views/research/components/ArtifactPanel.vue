<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'
import { CalendarDays, ExternalLink, FileText, Users } from 'lucide-vue-next'

interface ArtifactData {
  artifact_id: string
  type: string
  title: string
  data?: Record<string, any>
}

const props = defineProps<{ artifact: ArtifactData }>()

const highlightCode = (str: string, lang: string): string => {
  if (lang && hljs.getLanguage(lang)) {
    try {
      return (
        '<pre class="hljs"><code>' +
        hljs.highlight(lang, str, true).value +
        '</code></pre>'
      )
    } catch (e) {
      console.error(e)
    }
  }
  return '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + '</code></pre>'
}

const md = new MarkdownIt({
  breaks: true,
  // 模型输出属于不可信内容，不允许注入任意 HTML。
  html: false,
  linkify: true,
  highlight: highlightCode,
})

const markdown = computed(() => {
  const d = props.artifact.data || {}
  return d.markdown || d.report || ''
})

const tableData = computed<{ columns: string[]; rows: Array<Record<string, any>> } | null>(() => {
  const d = props.artifact.data || {}
  if (props.artifact.type === 'comparison_table') {
    if (d.columns && d.rows) {
      return { columns: d.columns, rows: d.rows }
    }
    // 尝试解析 raw JSON
    if (typeof d.raw === 'string') {
      try {
        const parsed = JSON.parse(d.raw)
        if (parsed.columns && parsed.rows) {
          return { columns: parsed.columns, rows: parsed.rows }
        }
      } catch {
        /* ignore */
      }
    }
  }
  return null
})

const rawText = computed(() => {
  const d = props.artifact.data || {}
  if (typeof d.raw === 'string') return d.raw
  return JSON.stringify(d, null, 2)
})

const papers = computed<Array<Record<string, any>>>(() => {
  if (props.artifact.type !== 'paper_list') return []
  return props.artifact.data?.papers || []
})

const formatAuthors = (authors: unknown) => {
  if (!Array.isArray(authors) || authors.length === 0) return '作者信息暂缺'
  const names = authors.slice(0, 4).join('、')
  return authors.length > 4 ? `${names} 等` : names
}
</script>

<template>
  <article class="artifact-card">
    <div class="artifact-header">
      <div class="artifact-heading">
        <span class="artifact-icon"><FileText :size="16" /></span>
        <div><small>研究结果</small><strong>{{ artifact.title }}</strong></div>
      </div>
      <el-tag size="small" effect="light">{{ artifact.type }}</el-tag>
    </div>

    <!-- Markdown 报告 -->
    <div
      v-if="artifact.type === 'research_report' && markdown"
      class="render"
      v-html="md.render(markdown)"
    />

    <!-- 论文检索结果 -->
    <div v-else-if="papers.length" class="paper-list">
      <a
        v-for="(paper, index) in papers"
        :key="paper.openalex_id || paper.doi || paper.pdf_url || index"
        class="paper-item"
        :href="paper.pdf_url || paper.doi || undefined"
        :target="paper.pdf_url || paper.doi ? '_blank' : undefined"
        rel="noopener noreferrer"
      >
        <span class="paper-index">{{ String(index + 1).padStart(2, '0') }}</span>
        <div class="paper-copy">
          <strong>{{ paper.title || '未命名论文' }}</strong>
          <div class="paper-meta">
            <span><Users :size="12" /> {{ formatAuthors(paper.authors) }}</span>
            <span v-if="paper.published"><CalendarDays :size="12" /> {{ paper.published }}</span>
            <span>来源：{{ paper.venue || (paper.provider === 'arxiv' ? 'arXiv 预印本' : '来源未注明') }}<template v-if="paper.source_type"> · {{ paper.source_type }}</template></span>
          </div>
          <p v-if="paper.summary">{{ paper.summary }}</p>
        </div>
        <ExternalLink v-if="paper.pdf_url || paper.doi" :size="16" class="external-icon" />
      </a>
    </div>

    <!-- 对比表 -->
    <el-table v-else-if="tableData" :data="tableData.rows" border size="small" max-height="400">
      <el-table-column
        v-for="col in tableData.columns"
        :key="col"
        :prop="col"
        :label="col"
      />
    </el-table>

    <!-- 其他：展示原始文本 -->
    <pre v-else class="raw-output">{{ rawText }}</pre>
  </article>
</template>

<style scoped>
.artifact-card { overflow: hidden; border: 1px solid #e6e6e8; border-radius: 11px; background: #fff; }
.artifact-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 13px 15px; border-bottom: 1px solid #ececee; background: #fafafa; }.artifact-heading { display: flex; align-items: center; gap: 10px; min-width: 0; }.artifact-icon { display: grid; place-items: center; flex: none; width: 30px; height: 30px; border-radius: 8px; color: #6d5bd0; background: #f0eef8; }.artifact-heading small,.artifact-heading strong { display: block; }.artifact-heading small { color: #96969b; font-size: 8px; font-weight: 500; letter-spacing: 0; }.artifact-heading strong { overflow: hidden; margin-top: 2px; color: #3c3c40; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
:deep(.render) { padding: 18px; color: #465169; font-size: 13px; line-height: 1.75; }:deep(.render h1),:deep(.render h2),:deep(.render h3) { color: #253049; }:deep(.render table) { width: 100%; border-collapse: collapse; }:deep(.render th),:deep(.render td) { padding: 8px; border: 1px solid #e3e7f0; }
.paper-list { display: grid; gap: 8px; padding: 12px; }.paper-item { display: flex; align-items: flex-start; gap: 11px; padding: 12px; border: 1px solid #ececee; border-radius: 9px; color: inherit; text-decoration: none; background: #fff; transition: .15s; }.paper-item:hover { border-color: #d0ccdE; background: #fafafa; transform: none; box-shadow: none; }.paper-index { display: grid; place-items: center; flex: none; width: 28px; height: 28px; border-radius: 7px; color: #6254af; background: #f0eef8; font-size: 9px; font-weight: 600; }.paper-copy { flex: 1; min-width: 0; }.paper-copy strong { display: block; color: #37373b; font-size: 12px; line-height: 1.5; }.paper-meta { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 6px; color: #8e8e93; font-size: 9px; }.paper-meta span { display: flex; align-items: center; gap: 4px; }.paper-copy p { display: -webkit-box; overflow: hidden; margin: 8px 0 0; color: #707075; font-size: 10px; line-height: 1.55; -webkit-box-orient: vertical; -webkit-line-clamp: 3; }.external-icon { flex: none; margin-top: 5px; color: #99999e; }
.raw-output { overflow: auto; max-height: 420px; margin: 0; padding: 16px; color: #5c667a; background: #fbfcfe; font-size: 11px; line-height: 1.6; white-space: pre-wrap; }
</style>
