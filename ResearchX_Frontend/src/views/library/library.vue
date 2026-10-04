<template>
  <div class="library-page flex-col w-full">
    <div class="library-toolbar flex items-center justify-between mb-8">
      <h1 class="library-title">论文库</h1>
      <div class="library-actions flex gap-2">
        <Button @click="openAddPaper"><Plus class="h-4 w-4" />添加论文</Button>
        <Button variant="outline" @click="router.push('/home/library/notes')">笔记集</Button>
        <Button variant="outline" @click="toggleSelectMode">
          {{ selectMode ? '取消选择' : '删除知识' }}
        </Button>
      </div>
    </div>
    <Dialog v-model:open="addPaperOpen">
      <DialogContent class="sm:max-w-[720px]">
        <DialogHeader>
          <p class="modal-eyebrow">LIBRARY / IMPORT</p>
          <DialogTitle>添加论文</DialogTitle>
          <DialogDescription>选择知识库并导入 PDF，我们会先检查文档结构和扫描文字。</DialogDescription>
        </DialogHeader>
        <template v-if="knowCardList?.length">
          <div class="upload-fields">
            <div>
              <label class="upload-label" for="paper-knowledge">保存到</label>
              <select id="paper-knowledge" v-model="selectedKnowledgeID" class="upload-select">
                <option v-for="card in knowCardList" :key="card.knowledgeID" :value="card.knowledgeID">
                  {{ card.knowledgeName }}
                </option>
              </select>
            </div>
            <div>
              <span class="upload-label">论文文件</span>
              <input id="paper-files" ref="paperFileInput" type="file" accept=".pdf,application/pdf" multiple class="upload-file-input" @change="selectPaperFiles" />
              <label class="upload-dropzone" for="paper-files">
                <FileUp class="h-5 w-5" />
                <strong>点击选择 PDF 文件</strong>
                <span>可一次添加多篇 · 单篇不超过 25 MB</span>
              </label>
            </div>
          </div>
          <div v-if="paperEntries.length" class="upload-results-head">
            <span>待添加的论文</span><span>{{ paperEntries.length }} 份</span>
          </div>
          <div v-for="(entry, index) in paperEntries" :key="index" class="paper-check">
            <div class="paper-check-top">
              <strong :title="entry.file.name">{{ entry.file.name }}</strong>
              <button type="button" :disabled="uploadingPapers" @click="removePaper(index)">移除</button>
            </div>
            <p v-if="entry.status === 'checking'" class="paper-check-note">正在识别 PDF 结构与扫描文字…</p>
            <p v-else-if="entry.status === 'error'" class="paper-check-bad">{{ entry.error }}</p>
            <template v-else-if="entry.assessment">
              <p :class="entry.assessment.verdict === 'likely_paper' ? 'paper-check-good' : 'paper-check-warn'">
                {{ verdictLabel(entry.assessment.verdict) }} · {{ entry.assessment.reason }}
              </p>
              <p class="paper-check-note">
                共 {{ entry.assessment.page_count }} 页；{{ entry.assessment.scanned ? `扫描版，已 OCR 识别第 ${entry.assessment.ocr_pages.join('、')} 页` : '可直接提取文字' }}
                <span v-if="entry.assessment.signals.length">；特征：{{ entry.assessment.signals.join('、') }}</span>
              </p>
              <label v-if="entry.assessment.verdict === 'review' || entry.assessment.verdict === 'not_paper'" class="paper-confirm">
                <input v-model="entry.approved" type="checkbox" /> 我已核对原文，仍要添加这份 PDF
              </label>
            </template>
          </div>
        </template>
        <p v-else class="upload-empty">{{ knowCardList === null ? '正在读取知识库，请稍后重试。' : '请先创建一个知识库，再将论文添加到其中。' }}</p>
        <p class="upload-disclaimer">OCR 只辅助识别文字和论文结构，无法核验论文是否真实发表。</p>
        <DialogFooter>
          <Button variant="outline" @click="addPaperOpen = false">取消</Button>
          <Button :disabled="!canUploadPapers" @click="submitPapers">
            {{ uploadingPapers ? '上传中…' : '上传论文' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
    <div v-if="loadError" class="library-error" role="alert">
      <span>{{ loadError }}</span>
      <Button variant="outline" @click="loadKnowledgeList">重试</Button>
    </div>
    <div v-if="knowCardList" class="library-filters flex gap-3 mb-6">
      <Input v-model="searchTerm" type="text" placeholder="搜索知识库名称或描述" class="w-full md:max-w-[440px]" />
      <Popover v-model:open="open">
        <PopoverTrigger as-child>
          <Button
            variant="outline"
            role="combobox"
            :aria-expanded="open"
            class="w-[200px] justify-between"
          >
            {{
              value || '全部知识库'
            }}
            <ChevronsUpDown class="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent class="w-[200px] p-0">
          <Command>
            <CommandInput class="h-9" placeholder="选择知识库" />
            <CommandEmpty>没有匹配的知识库</CommandEmpty>
            <CommandList>
              <CommandGroup>
                <CommandItem value="全部知识库" @select="value = ''; open = false">全部知识库</CommandItem>
                <CommandItem
                  v-for="card in knowCardList"
                  :key="card.knowledgeName"
                    :value="card.knowledgeName"
                  @select="
                    (ev) => {
                      value = card.knowledgeName
                      open = false
                    }
                  "
                >
                  {{ card.knowledgeDescription }}
                  <Check
                    :class="
                      cn(
                        'ml-auto h-4 w-4',
                        value === card.knowledgeName
                          ? 'opacity-100'
                          : 'opacity-0',
                      )
                    "
                  />
                </CommandItem>
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
    <!-- 知识库卡片 -->
    <div
      v-if="knowCardList !== null"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    >
      <!-- 显示创建卡片 -->
      <Card class="library-card flex justify-center items-center w-full">
        <Dialog v-model:open="createDialogOpen">
          <DialogTrigger as-child>
            <Button variant="ghost" class="w-full h-full text-base">
              <Plus class="h-5 w-5" />新建知识库
            </Button>
          </DialogTrigger>
          <DialogContent class="sm:max-w-[590px]">
            <DialogHeader>
              <p class="modal-eyebrow">LIBRARY / NEW</p>
              <DialogTitle>新建知识库</DialogTitle>
              <DialogDescription>为论文建立一个清晰的主题空间，之后可以继续添加文献。</DialogDescription>
            </DialogHeader>
            <div class="modal-form">
              <div><Label for="new-lib-name">知识库名称</Label><Input id="new-lib-name" v-model="newCard.knowledgeName" placeholder="例如：多模态检索研究" autocomplete="off" /></div>
              <div><Label for="new-lib-description">简要描述</Label><Input id="new-lib-description" v-model="newCard.knowledgeDescription" placeholder="写下这个知识库的研究方向（选填）" autocomplete="off" /></div>
            </div>
            <DialogFooter>
              <Button variant="outline" @click="createDialogOpen = false">取消</Button>
              <Button @click="SaveEvent">创建知识库</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </Card>
      <Card
        v-for="card in filteredCardList"
        :key="card.knowledgeName"
        class="library-card flex-col relative"
      >
        <CardHeader>
          <CardTitle>{{ card.knowledgeName }}</CardTitle>
          <!-- 删除模式下右上角的勾选圆圈 -->
          <button
            v-if="selectMode"
            type="button"
            class="absolute top-3 right-3 h-6 w-6 rounded-full border-2 flex items-center justify-center transition-colors"
            :class="
              selectedIds.has(card.knowledgeID)
                ? 'bg-red-500 border-red-500'
                : 'bg-white border-gray-300 hover:border-gray-400'
            "
            @click.stop="toggleSelect(card.knowledgeID)"
          >
            <Check
              v-if="selectedIds.has(card.knowledgeID)"
              class="h-4 w-4 text-white"
            />
          </button>
          <!-- <CardDescription>
            <label class="text-1xl">描述</label>
          </CardDescription> -->
        </CardHeader>
        <CardContent>
          <p class="text-sm text-gray-500">
            {{ card.knowledgeDescription }}
          </p>
        </CardContent>
        <!-- 横向布局 -->
        <CardFooter>
          <div class="library-card-actions flex w-full">
            <!-- 点击打开按钮 跳转到 knowledge 页面 -->
            <Button
              variant="outline"
              @click="router_knowledge(card.knowledgeID)"
              >打开</Button
            >
            <Button
              variant="outline"
              @click="router_chat(card)"
              >对话</Button
            >
            <Dialog :open="editingKnowledgeID === card.knowledgeID" @update:open="setEditDialogOpen(card.knowledgeID, $event)">
              <Button variant="outline" class="mr-2" @click="openEditDialog(card)">编辑</Button>
              <DialogContent class="sm:max-w-[590px]">
                <DialogHeader>
                  <p class="modal-eyebrow">LIBRARY / EDIT</p>
                  <DialogTitle>编辑知识库</DialogTitle>
                  <DialogDescription>调整名称和描述，已添加的论文会继续保留。</DialogDescription>
                </DialogHeader>
                <div class="modal-form">
                  <div><Label :for="`edit-lib-name-${card.knowledgeID}`">知识库名称</Label><Input :id="`edit-lib-name-${card.knowledgeID}`" v-model="tempCard.knowledgeName" /></div>
                  <div><Label :for="`edit-lib-description-${card.knowledgeID}`">简要描述</Label><Input :id="`edit-lib-description-${card.knowledgeID}`" v-model="tempCard.knowledgeDescription" /></div>
                </div>
                <DialogFooter>
                  <Button variant="outline" @click="editingKnowledgeID = ''">取消</Button>
                  <Button @click="EditEvent(card.knowledgeID, tempCard.knowledgeName, tempCard.knowledgeDescription)">保存修改</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardFooter>
      </Card>
    </div>
    <div
      v-else-if="knowCardList === null"
      class="grid w-full grid-cols-3 space-x-5 h-64"
    >
      <div class="space-y-2">
        <Skeleton class="h-2/3 w-full rounded-xl" />
        <Skeleton class="h-1/8 w-2/3" />
        <Skeleton class="h-1/8 w-1/3" />
      </div>
      <div class="space-y-2">
        <Skeleton class="h-2/3 w-full rounded-xl" />
        <Skeleton class="h-1/8 w-2/3" />
        <Skeleton class="h-1/8 w-1/3" />
      </div>
      <div class="space-y-2">
        <Skeleton class="h-2/3 w-full rounded-xl" />
        <Skeleton class="h-1/8 w-2/3" />
        <Skeleton class="h-1/8 w-1/3" />
      </div>
    </div>
  </div>
  <!-- 删除模式底部操作条 -->
  <div
    v-if="selectMode"
    class="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-4 rounded-lg border bg-white px-6 py-3 shadow-xl"
  >
    <span class="text-sm font-medium text-gray-700 mr-2">
      已选 {{ selectedIds.size }} 项
    </span>
    <Button
      variant="outline"
      class="px-4"
      @click="selectAll"
      :disabled="!knowCardList || knowCardList.length === 0"
    >
      全选
    </Button>
    <Button
      variant="outline"
      class="px-4"
      @click="cancelSelect"
      :disabled="selectedIds.size === 0"
    >
      取消已选
    </Button>
    <Button
      class="px-4 bg-red-500 hover:bg-red-600 text-white"
      @click="confirmDelete"
      :disabled="selectedIds.size === 0"
    >
      确认删除
    </Button>
  </div>
  <!-- <router-view /> -->
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Check, ChevronsUpDown, FileUp, Plus } from 'lucide-vue-next'
import { cn } from '@/components/utils'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { useRouter } from 'vue-router'
import {
  deleteKnowledge,
  getKnowledgeList,
  createKnowledge,
  editKnowledge,
  getDocumentList,
  uploadDocument,
  inspectDocument,
  type PaperInspection,
} from '@/api/data'
import { useDocumentListStore } from '@/stores/documentList'
import {
  type Knowledge,
  type KnowledgeListResponse,
  type KnowledgeResponse,
} from '@/types/type'

import { ElMessageBox, ElNotification } from 'element-plus'

const router = useRouter()

const knowCardList = ref<Knowledge[] | null>(null)
const loadError = ref('')
const addPaperOpen = ref(false)
const createDialogOpen = ref(false)
const editingKnowledgeID = ref('')
const selectedKnowledgeID = ref('')
type PaperEntry = { file: File; status: 'checking' | 'ready' | 'error'; assessment?: PaperInspection; error?: string; approved: boolean }
const paperEntries = ref<PaperEntry[]>([])
const paperFileInput = ref<HTMLInputElement | null>(null)
const uploadingPapers = ref(false)
const canUploadPapers = computed(() => !uploadingPapers.value && !!selectedKnowledgeID.value && paperEntries.value.length > 0 && paperEntries.value.every((entry) =>
  entry.status === 'ready' && entry.assessment?.verdict !== 'unreadable' &&
  (entry.assessment?.verdict === 'likely_paper' || entry.approved),
))
const searchTerm = ref('')
const filteredCardList = computed(() => (knowCardList.value || []).filter((card) => {
  const matchesSelected = !value.value || card.knowledgeName === value.value
  const needle = searchTerm.value.trim().toLowerCase()
  const matchesSearch = !needle || `${card.knowledgeName} ${card.knowledgeDescription || ''}`.toLowerCase().includes(needle)
  return matchesSelected && matchesSearch
}))

const newCard = ref({
  knowledgeName: '',
  knowledgeDescription: '',
})

const tempCard = reactive({
  knowledgeName: '',
  knowledgeDescription: '',
})

const openEditDialog = (card: Knowledge) => {
  tempCard.knowledgeName = card.knowledgeName
  tempCard.knowledgeDescription = card.knowledgeDescription
  editingKnowledgeID.value = card.knowledgeID
}

const setEditDialogOpen = (knowledgeID: string, isOpen: boolean) => {
  editingKnowledgeID.value = isOpen ? knowledgeID : ''
}

const loadKnowledgeList = async () => {
  knowCardList.value = null
  loadError.value = ''
  try {
    const libResp = (await getKnowledgeList()) as KnowledgeListResponse
    if (libResp.status_code !== 200 || !Array.isArray(libResp.data?.knowledgeList)) {
      throw new Error(libResp.msg || '论文库返回的数据无效')
    }
    knowCardList.value = libResp.data.knowledgeList
    if (!knowCardList.value.some((card) => card.knowledgeID === selectedKnowledgeID.value)) {
      selectedKnowledgeID.value = knowCardList.value[0]?.knowledgeID || ''
    }
  } catch (error: any) {
    loadError.value = error?.message || '读取论文库失败，请重试。'
    knowCardList.value = []
  }
}

onMounted(async () => {
  const token = localStorage.getItem('token')
  if (!token) {
    router.push('/login')
    return
  }
  await loadKnowledgeList()
})

const openAddPaper = () => {
  if (!selectedKnowledgeID.value) {
    selectedKnowledgeID.value = knowCardList.value?.[0]?.knowledgeID || ''
  }
  addPaperOpen.value = true
}

const verdictLabel = (verdict: PaperInspection['verdict']) => ({
  likely_paper: '符合论文结构',
  review: '需要人工确认',
  not_paper: '疑似非论文',
  unreadable: '无法识别',
})[verdict]

const selectPaperFiles = async (event: Event) => {
  const files = Array.from((event.target as HTMLInputElement).files || [])
  if (files.some((file) => !file.name.toLowerCase().endsWith('.pdf'))) {
    ElNotification.error('只能上传 PDF 论文')
    return
  }
  const entries = files.map((file): PaperEntry => reactive({ file, status: 'checking' as const, approved: false }))
  paperEntries.value.push(...entries)
  if (paperFileInput.value) paperFileInput.value.value = ''
  for (const entry of entries) {
    try {
      entry.assessment = await inspectDocument(entry.file)
      entry.status = 'ready'
    } catch (error: any) {
      entry.error = error?.message || '识别失败，请重新选择文件'
      entry.status = 'error'
    }
  }
}

const removePaper = (index: number) => paperEntries.value.splice(index, 1)

const submitPapers = async () => {
  if (!canUploadPapers.value) return
  uploadingPapers.value = true
  const failed: PaperEntry[] = []
  let uploaded = 0
  for (const entry of paperEntries.value) {
    try {
      const response = await uploadDocument(selectedKnowledgeID.value, entry.file)
      if (response?.status_code !== 200) throw new Error(response?.msg || '上传失败')
      uploaded += 1
    } catch (error: any) {
      failed.push(entry)
      ElNotification.error({ title: `《${entry.file.name}》上传失败`, message: error?.message || '请稍后重试' })
    }
  }
  uploadingPapers.value = false
  paperEntries.value = failed
  if (uploaded > 0) ElNotification.success(`已添加 ${uploaded} 篇论文，后台正在处理`)
  if (failed.length === 0 && uploaded > 0) {
    addPaperOpen.value = false
    router_knowledge(selectedKnowledgeID.value)
  }
}
const open = ref(false)
const value = ref('')

// 删除模式：多选状态与操作
const selectMode = ref(false)
const selectedIds = ref<Set<string>>(new Set())

// 进入/退出删除模式，退出时清空选中
const toggleSelectMode = () => {
  selectMode.value = !selectMode.value
  selectedIds.value = new Set()
}

// 勾选/取消勾选单个知识
const toggleSelect = (knowledgeID: string) => {
  const next = new Set(selectedIds.value)
  if (next.has(knowledgeID)) next.delete(knowledgeID)
  else next.add(knowledgeID)
  selectedIds.value = next
}

// 全选当前列表
const selectAll = () => {
  selectedIds.value = new Set(
    (knowCardList.value ?? []).map((c) => c.knowledgeID),
  )
}

// 取消所有已选
const cancelSelect = () => {
  selectedIds.value = new Set()
}

// 确认删除选中知识
const confirmDelete = async () => {
  const ids = [...selectedIds.value]
  if (ids.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${ids.length} 个知识库？其下全部文档、向量与源文件将一并删除，且不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  } catch {
    return
  }
  try {
    await deleteKnowledge(ids)
    // 从列表中移除已删除的知识
    knowCardList.value = (knowCardList.value ?? []).filter(
      (c) => !selectedIds.value.has(c.knowledgeID),
    )
    ElNotification.success(`已删除 ${ids.length} 个知识库`)
  } catch (error: any) {
    ElNotification.error(error.message || '删除失败')
  } finally {
    selectedIds.value = new Set()
    selectMode.value = false
  }
}

const router_knowledge = (knowledgeID: string) => {
  router.push({ name: 'knowledge', params: { knowledgeID: knowledgeID } })
}

// 点击「对话」：把该知识库内已处理完成的文档绑定到 Chat 的多文件对话，并跳转
const router_chat = async (card: Knowledge) => {
  try {
    const resp = (await getDocumentList(card.knowledgeID)) as any
    const docs = resp?.data || []
    const store = useDocumentListStore()
    let bound = 0
    docs.forEach((doc: any) => {
      // 只有处理完成(状态 2)的文档才有向量，能被 RAG 检索
      if (doc.documentStatus === 2) {
        store.appendDocument({
          isLoading: false,
          documentID: doc.documentID,
          documentName: doc.documentName,
          knowledgeID: card.knowledgeID,
          source: 'library',
        })
        bound += 1
      }
    })
    if (bound === 0) {
      ElNotification.warning({
        title: '暂无可用文档',
        message: '该知识库还没有处理完成的文档，无法进行对话',
      })
      return
    }
    router.push('/home/Chat')
  } catch (error: any) {
    ElNotification.error({
      title: '错误',
      message: error.message || '获取文档列表失败',
    })
  }
}

// 保存新创建的知识卡片
const SaveEvent = async () => {
  const knowledgeName = newCard.value.knowledgeName.trim()
  const knowledgeDescription = newCard.value.knowledgeDescription.trim()
  // 知识名不能为空
  if (knowledgeName === '') {
    ElNotification.error('知识名称不能为空')
    return
  }
  try {
    const knowResp = (await createKnowledge(
      knowledgeName,
      knowledgeDescription,
    )) as KnowledgeResponse

    if (knowResp.status_code === 200 && knowResp.data) {
      // 添加新创建的知识卡片到列表头
      knowCardList.value?.unshift(knowResp.data)
      selectedKnowledgeID.value ||= knowResp.data.knowledgeID
      newCard.value.knowledgeName = ''
      newCard.value.knowledgeDescription = ''
      createDialogOpen.value = false
      ElNotification.success('知识创建成功')
    } else {
      ElNotification.error(knowResp.status_code === 409 ? '知识名称重复' : knowResp.msg || '知识创建失败')
    }
  } catch (error: any) {
    ElNotification.error(error?.message || '知识创建失败')
  }
}

// 编辑知识卡片
const EditEvent = async (
  knowledgeID: string,
  knowledgeName: string,
  knowledgeDescription: string,
) => {
  // 先检测知识名是否为空或重复
  if (!knowledgeName.trim()) {
    ElNotification.error('知识名不能为空')
    return
  }
  try {
    const knowledgeResp = (await editKnowledge(
      knowledgeID,
      knowledgeName.trim(),
      knowledgeDescription.trim(),
    )) as KnowledgeResponse
    if (knowledgeResp.status_code === 200 && knowledgeResp.data) {
      const index = knowCardList.value?.findIndex((card) => card.knowledgeID === knowledgeID)
      if (index !== undefined && index !== -1) knowCardList.value?.splice(index, 1, knowledgeResp.data)
      editingKnowledgeID.value = ''
      ElNotification.success('知识编辑成功')
    } else {
      ElNotification.error(knowledgeResp.status_code === 409 ? '知识名重复' : knowledgeResp.msg || '知识编辑失败')
    }
  } catch (error: any) {
    ElNotification.error(error?.message || '知识编辑失败')
  }
}
</script>

<style scoped>
.library-page { min-height: calc(100vh - 72px); padding: 36px clamp(22px, 3.8vw, 60px) 70px; color: #263b52; background: #f7f9fc; }
.library-title { color: #263b52; font-size: 27px; font-weight: 650; letter-spacing: -.035em; }
.library-actions { flex-wrap: wrap; justify-content: flex-end; }
.library-filters { flex-wrap: wrap; }
.library-card-actions { flex-wrap: wrap; gap: 8px; }
.library-card { border-color: #e3e9f0; border-radius: 11px; background: #fff; transition: border-color .2s, box-shadow .2s, transform .2s; }
.library-card:hover { border-color: #bacde3; box-shadow: 0 9px 23px rgba(44, 79, 123, .06); transform: translateY(-2px); }
.modal-eyebrow { margin-bottom: 3px; color: #7f93aa; font-size: 11px; font-weight: 700; letter-spacing: .13em; }
.modal-form { display: grid; gap: 22px; padding: 4px 0 8px; }
.modal-form :deep(label) { display: block; margin-bottom: 9px; color: #344b63; font-size: 13px; font-weight: 650; }
.upload-fields { display: grid; gap: 22px; padding: 4px 0 2px; }
.upload-label { display: block; margin-bottom: 9px; color: #344b63; font-size: 13px; font-weight: 650; }
.upload-select { width: 100%; height: 48px; border: 1px solid #dce5ef; border-radius: 11px; padding: 0 15px; background: #fff; color: #263b52; font-size: 14px; transition: border-color .2s, box-shadow .2s; }
.upload-select:focus-visible { outline: none; border-color: #8aaad0; box-shadow: 0 0 0 3px #dbe9f8; }
.upload-file-input { position: absolute; width: 1px; height: 1px; opacity: 0; overflow: hidden; }
.upload-dropzone { display: flex; min-height: 118px; flex-direction: column; align-items: center; justify-content: center; gap: 7px; border: 1px dashed #b8cbe0; border-radius: 12px; background: #f8fbfe; color: #315f9d; cursor: pointer; transition: background .2s, border-color .2s, transform .2s; }
.upload-dropzone:hover { border-color: #739cca; background: #f1f7fd; transform: translateY(-1px); }
.upload-file-input:focus-visible + .upload-dropzone { outline: 3px solid #dbe9f8; outline-offset: 2px; }
.upload-dropzone strong { color: #365674; font-size: 14px; font-weight: 650; }
.upload-dropzone span { color: #8496a9; font-size: 12px; }
.upload-results-head { display: flex; justify-content: space-between; border-top: 1px solid #e8edf3; padding-top: 16px; color: #566d84; font-size: 13px; font-weight: 650; }
.upload-results-head span:last-child { color: #92a1b0; font-weight: 500; }
.upload-disclaimer { color: #91a0af; font-size: 12px; line-height: 1.6; }
.upload-empty { border-radius: 11px; padding: 20px; background: #f3f6fa; color: #63778f; font-size: 14px; }
.paper-check { border: 1px solid #e0e8f0; border-radius: 11px; padding: 15px 17px; background: #fbfcfe; }
.paper-check-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; font-size: 14px; }
.paper-check-top strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.paper-check-top button { flex: none; min-height: 32px; padding: 0 8px; border-radius: 7px; color: #58769a; font-size: 12px; cursor: pointer; }
.paper-check-top button:hover { background: #edf3fa; }
.paper-check-note, .paper-check-good, .paper-check-warn, .paper-check-bad { margin-top: 7px; font-size: 13px; line-height: 1.55; }
.paper-check-note { color: #718398; }
.paper-check-good { color: #267b61; }
.paper-check-warn { color: #9d6832; }
.paper-check-bad { color: #b4544a; }
.paper-confirm { display: flex; align-items: center; gap: 9px; margin-top: 12px; color: #526982; font-size: 13px; cursor: pointer; }
.paper-confirm input { width: 16px; height: 16px; accent-color: #315f9d; }
.library-error { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 20px; border: 1px solid #f0d9d5; border-radius: 10px; padding: 10px 14px; background: #fff8f6; color: #a1493c; font-size: 14px; }
@media (max-width: 680px) { .library-page { padding: 23px 16px 80px; } .library-toolbar { align-items: flex-start; flex-direction: column; gap: 16px; } .library-actions { width: 100%; justify-content: flex-start; } .library-actions :deep(button) { flex: 1; min-width: 104px; } .upload-dropzone { min-height: 108px; } }
@media (prefers-reduced-motion: reduce) { .library-card, .upload-dropzone { transition: none; } .upload-dropzone:hover { transform: none; } }
</style>
