<template>
  <section class="external-results" aria-label="外部学术搜索结果">
    <div class="results-heading">
      <strong>外部学术搜索 · 找到 {{ result.items.length }} 篇论文</strong>
      <span v-if="result.provider">{{ result.provider === 'arxiv' ? 'arXiv' : 'OpenAlex' }}</span>
    </div>
    <p v-if="result.keywords.length" class="search-terms">检索词：{{ result.keywords.join(' · ') }}</p>
    <p v-if="result.warning" class="search-note">{{ result.warning }}</p>
    <p class="search-note">以下为检索到的题目和摘要，尚未核查全文。可自行选择要阅读或加入 Library 的论文。</p>

    <div v-for="(paper, index) in result.items" :key="`${paper.title}-${index}`" class="paper-card">
      <div class="paper-title">{{ index + 1 }}. {{ paper.title }}</div>
      <div class="paper-meta">
        {{ paper.authors.slice(0, 3).join('、') || '作者信息暂缺' }}
        <span v-if="paper.published"> · {{ paper.published }}</span>
      </div>
      <p v-if="paper.summary" class="paper-summary">{{ paper.summary }}</p>
      <div class="paper-actions">
        <el-button size="small" :disabled="!paper.pdf_url" @click="openPaper(paper)">查看 / 下载原文</el-button>
        <el-button size="small" type="primary" plain :disabled="!paper.importable" @click="chooseLibrary(paper)">
          加入 Library
        </el-button>
        <span v-if="!paper.importable" class="import-hint">此来源请先下载 PDF，再手动上传</span>
      </div>
    </div>

    <el-dialog v-model="dialogVisible" title="将论文加入 Library" width="440px" append-to-body>
      <p class="dialog-title">{{ selectedPaper?.title }}</p>
      <el-select v-model="selectedKnowledgeID" class="w-full" placeholder="选择知识库" :loading="loadingLibraries">
        <el-option
          v-for="item in libraries"
          :key="item.knowledgeID"
          :label="item.knowledgeName"
          :value="item.knowledgeID"
        />
      </el-select>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" :disabled="!selectedKnowledgeID" @click="confirmImport">
          下载并加入
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getKnowledgeList } from '@/api/data'
import { importExternalPaper, type ExternalPaper, type ExternalPaperResult } from '@/api/qa'
import { useDocumentListStore } from '@/stores/documentList'

defineProps<{ result: ExternalPaperResult }>()

type LibraryItem = { knowledgeID: string; knowledgeName: string }
const dialogVisible = ref(false)
const selectedPaper = ref<ExternalPaper | null>(null)
const selectedKnowledgeID = ref('')
const libraries = ref<LibraryItem[]>([])
const loadingLibraries = ref(false)
const importing = ref(false)

function openPaper(paper: ExternalPaper) {
  if (!/^https?:\/\//i.test(paper.pdf_url)) return
  window.open(paper.pdf_url, '_blank', 'noopener,noreferrer')
}

async function chooseLibrary(paper: ExternalPaper) {
  selectedPaper.value = paper
  dialogVisible.value = true
  loadingLibraries.value = true
  try {
    const response = await getKnowledgeList()
    libraries.value = response.data?.knowledgeList || []
    selectedKnowledgeID.value = libraries.value[0]?.knowledgeID || ''
    if (!libraries.value.length) ElMessage.info('请先在 Library 创建一个知识库')
  } catch (error: any) {
    ElMessage.error(error?.message || '读取知识库失败')
  } finally {
    loadingLibraries.value = false
  }
}

async function confirmImport() {
  if (!selectedPaper.value?.pdf_url || !selectedKnowledgeID.value) return
  importing.value = true
  try {
    const data = await importExternalPaper(selectedPaper.value.pdf_url, selectedKnowledgeID.value, selectedPaper.value.title)
    useDocumentListStore().appendDocument({
      documentID: data.documentID,
      documentName: data.documentName,
      knowledgeID: data.knowledgeID,
      source: 'library',
      isLoading: false,
    })
    dialogVisible.value = false
    ElMessage.success('论文已加入 Library 和当前对话，可以继续提问')
  } catch (error: any) {
    ElMessage.error(error?.message || '导入失败')
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.external-results { margin-top: 18px; border-top: 1px solid #e5e7eb; padding-top: 14px; }
.results-heading { display: flex; justify-content: space-between; gap: 12px; color: #1f2937; font-size: 15px; }
.results-heading span, .paper-meta, .search-terms, .search-note { color: #6b7280; font-size: 12px; }
.search-terms, .search-note { margin: 6px 0; }
.paper-card { margin-top: 10px; border: 1px solid #e5e7eb; border-radius: 12px; padding: 12px 14px; background: #fafbff; }
.paper-title { color: #1f2937; font-size: 14px; font-weight: 600; line-height: 1.5; }
.paper-meta { margin-top: 4px; }
.paper-summary { margin: 8px 0; color: #4b5563; font-size: 12px; line-height: 1.55; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.paper-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.import-hint { color: #9ca3af; font-size: 11px; }
.dialog-title { margin-bottom: 14px; color: #374151; font-size: 13px; }
</style>
