<script lang="ts" setup>
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { computed, ref } from 'vue'
import { ElMessageBox, ElNotification } from 'element-plus'
import { formatName } from '@/components/utils'
import { Label } from '@/components/ui/label'
import { useRouter } from 'vue-router'
import {
  getDocumentList,
  uploadDocument,
  getDocumentInfo,
  deleteDocument,
} from '@/api/data'
import { useRoute } from 'vue-router'
import { useDocumentListStore } from '@/stores/documentList'
import { type Document } from '@/types/type'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { ChevronsUpDown } from 'lucide-vue-next'
import moment from 'moment'

const search = ref('')

const router = useRouter()

const route = useRoute()

const knowledgeID = route.params.knowledgeID as string

// 开启关闭上传进度条
const uploadTaskStatus = ref(false)

const processTaskStatus = ref(false)

const progress = ref(0)

const uploadTaskQueue = ref<File[]>([])

// 正在处理的文档id列表
const processingDocList = ref<Document[]>([])

const taskNum = ref(0)

enum DocumentStatus {
  Queuing = 0,
  Processing = 1,
  Done = 2,
}

onMounted(async () => {
  // 向后端发送请求,获取知识内文档列表
  const route = useRoute()
  try {
    const knowledgeID = route.params.knowledgeID as string
    const resp = await getDocumentList(knowledgeID)
    if (resp) {
      tableData.value = resp.data
    }
  } catch (error: any) {
    ElNotification.error({
      title: 'Error',
      message: `获取文档列表失败：${error.message}`,
    })
  }
})

const filterTableData = computed(() =>
  // 需要对 tableData 的 documentName 和 tag进行搜索
  tableData.value.filter((data) => {
    const searchValue = search.value.toLowerCase()
    const nameMatches = data.documentName.toLowerCase().includes(searchValue)
    const tagMatches = (data.documentTags || []).some(
      (tag) => tag && tag.toLowerCase().includes(searchValue.toLowerCase()),
    )
    return !search.value || nameMatches || tagMatches
  }),
)
// const handleEdit = (index: number, row: Document) => {
//   // 编辑该行数据
//   console.log(index, row)
// }

const handleView = async (index: number, row: Document) => {
  // 在这里实现跳转到显示对应pdf的页面
  if (row) {
    // 向后端发送请求,获取对应的pdf文件
    router.push({
      name: 'pdfInfo',
      params: { knowledgeID: knowledgeID, documentID: row.documentID },
    })
  }
  // Todo: 跳转到显示对应pdf的页面
  // router.push(`/viewPdf/${row.documentName}`)
}

// 删除文档 处理函数
const handleDelete = async (index: number, row: Document) => {
  try {
    await ElMessageBox.confirm(`确认删除 ${row.documentName}？该论文及笔记将从论文库移除。`, '删除论文', { type: 'warning' })
    const resp = await deleteDocument(knowledgeID, row.documentID)
    if (resp) {
      ElNotification({
        title: 'Success',
        message: '文件删除成功',
        type: 'success',
      })
      // 删除该行数据
      tableData.value = tableData.value.filter(item => item.documentID !== row.documentID)
      // 同步移除对话页已绑定的该文档，避免残留 ID 仍在 Chat 会话中显示
      useDocumentListStore().deleteDocumentById(row.documentID)
    }
  } catch (error: any) {
    if (error === 'cancel' || error === 'close') return
    ElNotification({
      title: 'Error',
      message: `文件删除失败：${error.message}`,
      type: 'error',
    })
  }
}

// 整个表格数据
const tableData = ref<Document[]>([])

// 单个页面数据
// const pageData = ref<Document[]>([])

const fileInput = ref<HTMLInputElement | null>(null)
// const selectedFiles = ref<File[]>([])

const openFilePicker = () => {
  fileInput.value!.click()
}

// 上传文件的回调处理函数
const handleFileUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const files = target.files
  if (files) {
    // 更新上传队列
    uploadTaskQueue.value = Array.from(files)
    // 更新任务数量
    taskNum.value = uploadTaskQueue.value.length
    // 上传文件并显示进度条
    progress.value = 0
    uploadTaskStatus.value = true
    await processQueue(knowledgeID)
    target.value = ''
    // 关闭进度条显示
    uploadTaskStatus.value = false
    if (processingDocList.value.length === 0) {
      return
    }
    ElNotification({
      title: 'Success',
      message: '文件上传成功',
      type: 'success',
    })
    await new Promise((resolve) => setTimeout(resolve, 2000))
    ElNotification({
      title: 'Info',
      message: '文档处理中',
      type: 'info',
    })
    // 监听文档处理状态
    processTaskStatus.value = true
    progress.value = 20
    await checkDocumentStatus()
    processTaskStatus.value = false
  }
}

// 处理上传文档
const processQueue = async (knowledgeID: string) => {
  while (uploadTaskQueue.value.length > 0) {
    const file = uploadTaskQueue.value[0]
    try {
      const resp = await uploadDocument(knowledgeID, file)
      if (resp) {
        // 添加到表格数据
        const item = {
          documentID: resp.data.documentID,
          documentName: file.name,
          documentTags: [],
          documentStatus: DocumentStatus.Queuing,
          vectorNum: 0,
          createTime: resp.data.createTime,
        }
        tableData.value.push(item)
        processingDocList.value.push(item)
      }
    } catch (error: any) {
      console.error(`文件上传失败：${error.message}`)
      ElNotification.error({
        title: '上传失败',
        message: error.message || '文件上传失败，请重试',
      })
    } finally {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      uploadTaskQueue.value.shift()
      progress.value =
        100 - (uploadTaskQueue.value.length / taskNum.value) * 100
      await new Promise((resolve) => setTimeout(resolve, 1000))
    }
  }
}

// 检查文档处理状态
const checkDocumentStatus = async () => {
  while (true) {
    // 列表不为空时，执行回调函数
    let processDone = true
    for (let i = 0; i < processingDocList.value.length; i++) {
      if (processingDocList.value[i].documentStatus === DocumentStatus.Done) {
        continue
      }
      try {
        // 获取文档状态
        const resp = await getDocumentInfo(
          knowledgeID,
          processingDocList.value[i].documentID,
        )
        if (resp) {
          // 获取到当前文档的处理状态
          processingDocList.value[i].documentStatus = resp.data.documentStatus
          processingDocList.value[i].documentTags = resp.data.documentTags
          processingDocList.value[i].vectorNum = resp.data.vectorNum
          processingDocList.value[i].createTime = resp.data.createTime
          if (resp.data.documentStatus !== DocumentStatus.Done) {
            processDone = false
          }
        }
      } catch (error: any) {
        processDone = false
        ElNotification({
          title: 'Error',
          message: `获取文档状态失败：${error.message}`,
          type: 'error',
        })
      }
    }
    if (processDone) {
      break
    }
    // 等待一段时间后再次检查列表状态
    await new Promise((resolve) => setTimeout(resolve, 5000)) // 每5秒检查一次
    console.log('Checking document status...')
  }
}
// const totalItems = ref(100) // 总条目数
// const pageSize = ref(1) // 每页显示的条目数
// const currentPage = ref(1) // 当前页码

// const totalPages = computed(() => {
//   return Math.ceil(totalItems.value / pageSize.value)
// })

// const handlePageChange = (page: any) => {
//   currentPage.value = page
//   console.log(`Current page: ${page}`)
//   // 在这里执行分页数据的获取逻辑
//   // 切换数据
// }

// const onAddItem = () => {
//   tableData.value.push({
//     documentName: 'New Document' + rand(1, 100),
//     status: 'loading',
//     queryNumber: rand(100, 500),
//     documentSize: rand(100, 500),
//   })
// }

const formatterName = (row: Document) => {
  // 定义超过 5 个字符显示省略号
  const maxLength = 20
  // 去除文件名后缀
  return formatName(row.documentName.replace(/\.pdf$/i, ''), maxLength)
}

const formatterTime = (row: Document) => {
  // return row.createTime
  if (!row || !row.createTime) {
    return ''
  }
  const timestamp = row.createTime.toString().length === 10 ? Number(row.createTime) * 1000 : row.createTime
  const now = moment()
  const inputTime = moment(timestamp)
  const diffInHours = now.diff(inputTime, 'hours')

  if (diffInHours < 1) {
    const diffInMinutes = now.diff(inputTime, 'minutes')
    return `${diffInMinutes} 分钟前`
  } else if (diffInHours < 24) {
    return `${diffInHours} 小时前`
  } else {
    return inputTime.format('YYYY-MM-DD')
  }
}

const getTagType = (index: number) => {
  // 根据索引返回不同的类型
  const colors = ['success', 'info', 'warning', 'danger', 'primary']
  return colors[index % colors.length]
}

const isOpen = ref(true)
</script>

<template>
  <div class="document-list-page w-full p-6">
    <h1 class="text-2xl font-bold mb-5">论文文档</h1>
    <div class="flex-col">
      <div class="flex gap-3 mb-4 w-full">
        <Input v-model="search" type="text" placeholder="搜索论文名称或标签" class="w-full max-w-xl" />
        <input
          ref="fileInput"
          type="file"
          style="display: none"
          accept=".pdf"
          multiple="true"
          @change="handleFileUpload"
        />
        <Button
          variant="default"
          class="text-sm mr-2"
          :disabled="processTaskStatus || uploadTaskStatus"
          @click="openFilePicker"
        >
          上传文件
        </Button>
      </div>
      <el-table :data="filterTableData" class="document-table w-full" max-height="calc(100vh - 190px)">
        <el-table-column
          fixed
          :formatter="formatterName"
          label="论文名称"
          prop="documentName"
        />
        <el-table-column label="标签" prop="documentTags" min-width="300">
          <template #default="{ row }">
            <div class="document-tags" :title="(row.documentTags || []).join('、')">
              <el-tag
                v-for="(tag, index) in (row.documentTags || []).slice(0, 3)"
                :key="index"
                :type="getTagType(index)"
                size="small"
              >
                {{ tag }}
              </el-tag>
              <el-tag v-if="(row.documentTags || []).length > 3" size="small" type="info">
                +{{ row.documentTags.length - 3 }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" prop="documentStatus">
          <template #default="{ row }">
            <div>
              <el-tag
                v-if="row.documentStatus === DocumentStatus.Queuing"
                type="info"
              >
                排队中
              </el-tag>
              <el-tag
                v-else-if="row.documentStatus === DocumentStatus.Processing"
                type="warning"
              >
                处理中
              </el-tag>
              <el-tag
                v-else-if="row.documentStatus === DocumentStatus.Done"
                type="success"
              >
                完成
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="索引块数" prop="vectorNum" />
        <el-table-column
          label="创建时间"
          prop="createTime"
          :formatter="formatterTime"
        />
        <el-table-column align="right">
          <template #default="scope: { $index: number; row: Document }">
            <el-button
              class="text-sm"
              :disabled="
                processTaskStatus ||
                uploadTaskStatus ||
                scope.row.documentStatus !== DocumentStatus.Done
              "
              @click="handleView(scope.$index, scope.row)"
            >
              阅读
            </el-button>
            <el-button
              class="text-sm"
              :disabled="
                processTaskStatus ||
                uploadTaskStatus ||
                scope.row.documentStatus !== DocumentStatus.Done
              "
              @click="handleDelete(scope.$index, scope.row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <transition name="slide">
      <el-card v-show="uploadTaskStatus" class="fixed-card w-1/4">
        <Progress v-model="progress" class="w-full" />
      </el-card>
    </transition>
    <transition name="slide">
      <Collapsible
        v-show="processTaskStatus"
        v-model:open="isOpen"
        class="fixed-card w-1/4"
      >
        <CollapsibleTrigger class="w-full"
          ><Button variant="ghost" size="sm" class="w-full p-0">
            <ChevronsUpDown class="h-4 w-4" /> </Button
        ></CollapsibleTrigger>
        <CollapsibleContent>
          <el-card class="w-full">
            <div class="flex flex-col w-full mb-4">
              <Label
                >已处理文档：{{
                  processingDocList.filter(
                    (doc) => doc.documentStatus === DocumentStatus.Done,
                  ).length
                }}</Label
              >
              <Separator class="my-4" />
              <Label
                >待处理文档：{{
                  processingDocList.filter(
                    (doc) => doc.documentStatus !== DocumentStatus.Done,
                  ).length
                }}</Label
              >
            </div>
            <Progress v-model="progress" class="w-full" />
          </el-card>
        </CollapsibleContent>
      </Collapsible>
    </transition>
  </div>
</template>

<style scoped>
.document-list-page { min-width: 0; }
.document-tags { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; min-width: 0; }
.document-tags .el-tag { max-width: 100%; }
.document-table :deep(.el-table__cell) { padding: 7px 0; }
.document-table :deep(.el-table__cell .cell) { line-height: 1.35; }
/* 添加所需的自定义样式 */
.ellipsis {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: keep-all;
}
.fixed-card {
  position: fixed;
  bottom: 20px; /* 距离底部的距离，可以根据需要调整 */
  right: 20px; /* 距离右侧的距离，可以根据需要调整 */
  z-index: 1000; /* 确保卡片在其他元素之上显示 */
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 0.5s;
}
.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}
.loading-container {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 1001; /* 确保在其他元素之上 */
}
</style>
