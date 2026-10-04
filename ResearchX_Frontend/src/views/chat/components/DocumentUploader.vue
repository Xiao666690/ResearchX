<template>
  <div>
    <el-button circle class="upload-trigger" title="添加论文" @click="openDialog">
      <IconoirProvider
        :icon-props="{ color: '#ffffff', 'stroke-width': 2, width: '2em', height: '2em' }"
      >
        <PlusCircle />
      </IconoirProvider>
    </el-button>

    <el-dialog v-model="dialogVisible" title="添加对话论文" width="680px" append-to-body>
      <el-tabs v-model="sourceMode">
        <el-tab-pane label="从 Library 选择" name="library">
          <el-select
            v-model="selectedKnowledgeID"
            class="w-full"
            placeholder="请选择知识库"
            @change="loadDocuments"
          >
            <el-option
              v-for="knowledge in knowledgeList"
              :key="knowledge.knowledgeID"
              :label="`${knowledge.knowledgeName}（${knowledge.documentNum || 0} 篇）`"
              :value="knowledge.knowledgeID"
            />
          </el-select>

          <div v-loading="libraryLoading" class="mt-4 max-h-72 overflow-y-auto rounded-lg border border-gray-200 p-3">
            <el-empty
              v-if="!libraryLoading && libraryDocuments.length === 0"
              description="该知识库暂无论文"
              :image-size="64"
            />
            <el-checkbox-group v-else v-model="selectedDocumentIDs" class="flex flex-col gap-3">
              <el-checkbox
                v-for="document in libraryDocuments"
                :key="document.documentID"
                :value="document.documentID"
                :disabled="document.documentStatus !== 2"
              >
                <span class="font-medium">{{ document.documentName }}</span>
                <span v-if="document.documentStatus !== 2" class="ml-2 text-xs text-amber-600">
                  {{ document.documentStatus === 1 ? '处理中' : '等待处理' }}
                </span>
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </el-tab-pane>

        <el-tab-pane label="上传本地 PDF" name="upload">
          <input
            ref="fileInput"
            class="hidden"
            type="file"
            accept=".pdf,application/pdf"
            multiple
            @change="handleFileSelect"
          />
          <button
            class="flex w-full flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 px-5 py-8 text-gray-600 transition hover:border-gray-400 hover:bg-gray-50"
            type="button"
            @click="fileInput?.click()"
          >
            <span class="text-base font-medium">选择本地 PDF</span>
            <span class="mt-1 text-xs text-gray-400">支持一次选择多篇论文</span>
          </button>

          <div v-if="pendingFiles.length" class="mt-3 max-h-36 overflow-y-auto rounded-lg bg-gray-50 p-3 text-sm">
            <div v-for="file in pendingFiles" :key="`${file.name}-${file.size}`" class="truncate py-1">
              {{ file.name }}（{{ formatSize(file.size) }}）
            </div>
          </div>

          <div class="mt-5 flex items-center justify-between rounded-lg border border-gray-200 p-4">
            <div>
              <div class="text-sm font-medium text-gray-900">同时加入 Library</div>
              <div class="mt-1 text-xs text-gray-500">关闭时仅用于当前聊天，不进入长期论文库</div>
            </div>
            <el-switch v-model="addToLibrary" />
          </div>

          <el-select
            v-if="addToLibrary"
            v-model="uploadKnowledgeID"
            class="mt-3 w-full"
            placeholder="选择要加入的知识库"
          >
            <el-option
              v-for="knowledge in knowledgeList"
              :key="knowledge.knowledgeID"
              :label="knowledge.knowledgeName"
              :value="knowledge.knowledgeID"
            />
          </el-select>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="confirmSelection">
          添加到当前对话
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { IconoirProvider, PlusCircle } from '@iconoir/vue'
import { ElMessage, ElNotification } from 'element-plus'
import { ref } from 'vue'
import { getDocumentList, getKnowledgeList } from '@/api/data'
import { uploadFile } from '@/api/chat'
import { useDocumentListStore, type Document } from '@/stores/documentList'
import { formatSize } from '@/utils/format'

type Knowledge = {
  knowledgeID: string
  knowledgeName: string
  documentNum?: number
}

type LibraryDocument = {
  documentID: string
  documentName: string
  documentStatus: number
  vectorNum?: number
}

const dialogVisible = ref(false)
const sourceMode = ref<'library' | 'upload'>('library')
const knowledgeList = ref<Knowledge[]>([])
const selectedKnowledgeID = ref('')
const libraryDocuments = ref<LibraryDocument[]>([])
const selectedDocumentIDs = ref<string[]>([])
const libraryLoading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const pendingFiles = ref<File[]>([])
const addToLibrary = ref(false)
const uploadKnowledgeID = ref('')
const submitting = ref(false)

async function openDialog() {
  dialogVisible.value = true
  try {
    const response = await getKnowledgeList()
    knowledgeList.value = response.data?.knowledgeList || []
    if (!selectedKnowledgeID.value && knowledgeList.value.length) {
      selectedKnowledgeID.value = knowledgeList.value[0].knowledgeID
      await loadDocuments()
    }
  } catch (error: any) {
    ElMessage.error(error?.message || '读取 Library 失败')
  }
}

async function loadDocuments() {
  selectedDocumentIDs.value = []
  libraryDocuments.value = []
  if (!selectedKnowledgeID.value) return
  libraryLoading.value = true
  try {
    const response = await getDocumentList(selectedKnowledgeID.value)
    libraryDocuments.value = response.data || []
  } catch (error: any) {
    ElMessage.error(error?.message || '读取论文列表失败')
  } finally {
    libraryLoading.value = false
  }
}

function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  pendingFiles.value = Array.from(input.files || [])
}

async function confirmSelection() {
  const store = useDocumentListStore()

  if (sourceMode.value === 'library') {
    if (!selectedDocumentIDs.value.length) {
      ElMessage.warning('请至少选择一篇已处理完成的论文')
      return
    }
    let added = 0
    for (const documentID of selectedDocumentIDs.value) {
      const item = libraryDocuments.value.find(document => document.documentID === documentID)
      if (!item) continue
      const document: Document = {
        documentID: item.documentID,
        documentName: item.documentName,
        knowledgeID: selectedKnowledgeID.value,
        source: 'library',
        isLoading: false,
      }
      if (store.appendDocument(document)) added += 1
    }
    dialogVisible.value = false
    ElMessage.success(added ? `已从 Library 添加 ${added} 篇论文` : '所选论文已在当前对话中')
    return
  }

  if (!pendingFiles.value.length) {
    ElMessage.warning('请先选择本地 PDF')
    return
  }
  if (addToLibrary.value && !uploadKnowledgeID.value) {
    ElMessage.warning('请选择要加入的知识库')
    return
  }

  submitting.value = true
  try {
    let added = 0
    for (const file of pendingFiles.value) {
      const data = await uploadFile(file, {
        addToLibrary: addToLibrary.value,
        knowledgeID: addToLibrary.value ? uploadKnowledgeID.value : undefined,
      })
      const document: Document = {
        documentID: data.documentID,
        documentName: data.documentName || file.name,
        documentFile: file,
        fileSize: file.size,
        knowledgeID: data.knowledgeID || undefined,
        source: 'upload',
        isLoading: false,
      }
      if (store.appendDocument(document)) added += 1
    }
    dialogVisible.value = false
    pendingFiles.value = []
    if (fileInput.value) fileInput.value.value = ''
    ElNotification.success(
      addToLibrary.value
        ? `已上传并加入 Library，共 ${added} 篇`
        : `已上传到当前对话，共 ${added} 篇`,
    )
  } catch (error: any) {
    ElMessage.error(error?.message || '上传失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style lang="less" scoped>
.el-button {
  --el-button-hover-border-color: #5e4bc2;
}
.upload-trigger { width: 44px; height: 44px; border: 1px solid #315fa7; background: #315fa7; box-shadow: 0 2px 8px rgba(49,95,167,.12); }
.upload-trigger:hover { background: #5744bf; box-shadow: 0 3px 12px rgba(109,91,208,.38); }
</style>
