<template>
  <div class="flex-col w-full p-8">
    <div class="flex items-center justify-between mb-8">
      <h1 class="text-2xl font-bold">论文库</h1>
      <div class="flex gap-2">
        <Button variant="outline" class="px-4 py-2" @click="router.push('/home/library/notes')">笔记集</Button>
        <Button variant="outline" class="px-4 py-2" @click="toggleSelectMode">
          {{ selectMode ? '取消选择' : '删除知识' }}
        </Button>
      </div>
    </div>
    <div v-if="knowCardList" class="flex space-x-4 mb-6">
      <Input v-model="searchTerm" type="text" placeholder="搜索知识库名称或描述" class="w-1/2" />
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
      <Card class="flex justify-center items-center w-full">
        <Dialog>
          <DialogTrigger as-child>
            <Button variant="ghost" class="w-full h-full text-xl">
              创建知识
            </Button>
          </DialogTrigger>
          <div>
            <DialogContent class="sm:max-w-[425px]">
              <DialogHeader>
                <DialogTitle>知识创建</DialogTitle>
              </DialogHeader>
              <div class="grid gap-4 py-4">
                <div class="grid grid-cols-4 items-center gap-4">
                  <Label for="libName" class="text-right"> 知识名称 </Label>
                  <Input
                    id="libName"
                    v-model="newCard.knowledgeName"
                    class="col-span-3"
                    required
                    autocomplete="off"
                  />
                </div>
                <div class="grid grid-cols-4 items-center gap-4">
                  <Label for="libDes" class="text-right"> 知识描述 </Label>
                  <Input
                    id="libDes"
                    v-model="newCard.knowledgeDescription"
                    class="col-span-3"
                    autocomplete="off"
                  />
                </div>
              </div>
              <div class="flex justify-center gap-4">
                <DialogTrigger>
                  <Button variant="outline">取消</Button>
                </DialogTrigger>
                <DialogTrigger>
                  <Button @click="SaveEvent">确认</Button>
                </DialogTrigger>
              </div>
            </DialogContent>
          </div>
        </Dialog>
      </Card>
      <Card
        v-for="card in filteredCardList"
        :key="card.knowledgeName"
        class="flex-col relative"
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
          <div class="flex justify-left w-full">
            <!-- 点击打开按钮 跳转到 knowledge 页面 -->
            <Button
              variant="outline"
              class="text-1xl mr-2"
              @click="router_knowledge(card.knowledgeID)"
              >打开</Button
            >
            <Button
              variant="outline"
              class="text-1xl mr-2"
              @click="router_chat(card)"
              >对话</Button
            >
            <Dialog>
              <DialogTrigger as-child>
                <Button
                  variant="outline"
                  class="text-1xl mr-2"
                  @click="openEditDialog(card)"
                >
                  编辑
                </Button>
              </DialogTrigger>
              <DialogContent class="sm:max-w-[425px]">
                <DialogHeader>
                  <DialogTitle>知识编辑</DialogTitle>
                </DialogHeader>
                <div class="grid gap-4 py-4">
                  <div class="grid grid-cols-4 items-center gap-4">
                    <Label for="libName" class="text-right"> 知识名称 </Label>
                    <Input
                      id="libName"
                      v-model="tempCard.knowledgeName"
                      class="col-span-3"
                    />
                  </div>
                  <div class="grid grid-cols-4 items-center gap-4">
                    <Label for="libDes" class="text-right"> 知识描述 </Label>
                    <Input
                      id="libDes"
                      v-model="tempCard.knowledgeDescription"
                      class="col-span-3"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <DialogTrigger as-child>
                    <Button
                      variant="outline"
                      class="text-1xl"
                      @click="
                        EditEvent(
                          card.knowledgeID,
                          tempCard.knowledgeName,
                          tempCard.knowledgeDescription,
                        )
                      "
                    >
                      保存
                    </Button>
                  </DialogTrigger>
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
import { ref } from 'vue'
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
import { Check, ChevronsUpDown } from 'lucide-vue-next'
import { cn } from '@/components/utils'
import {
  Dialog,
  DialogContent,
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

const tempCard = {
  knowledgeName: '',
  knowledgeDescription: '',
}

const openEditDialog = (card: Knowledge) => {
  tempCard.knowledgeName = card.knowledgeName
  tempCard.knowledgeDescription = card.knowledgeDescription
}

onMounted(async () => {
  const router = useRouter()
  const token = localStorage.getItem('token')
  if (!token) {
    router.push('/login')
    return
  }

  try {
    const libResp = (await getKnowledgeList()) as KnowledgeListResponse
    if (libResp) {
      knowCardList.value = libResp.data.knowledgeList
    }
  } catch (error: any) {
    console.error(error.message)
  }
})
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
  newCard.value.knowledgeName = ''
  newCard.value.knowledgeDescription = ''
  // 知识名不能为空
  if (knowledgeName === '') {
    ElNotification.error('知识名称不能为空')
    return
  }
  // TODO: 处理服务器500错误
  try {
    const knowResp = (await createKnowledge(
      knowledgeName,
      knowledgeDescription,
    )) as KnowledgeResponse

    if (knowResp) {
      // 添加新创建的知识卡片到列表头
      knowCardList.value?.unshift(knowResp.data)
      ElNotification.success('知识创建成功')
    }
  } catch (error: any) {
    if (error.message == '401') {
      const router = useRouter()
      ElNotification.error('Token过期，请重新登录')
      router.push('/login')
    } else if (error.message == '409') {
      ElNotification.error('知识名称重复')
    }
  }
}

// 编辑知识卡片
// TODO: 编辑知识卡片
const EditEvent = async (
  knowledgeID: string,
  knowledgeName: string,
  knowledgeDescription: string,
) => {
  // 先检测知识名是否为空或重复
  if (knowledgeName === '') {
    ElNotification.error('知识名不能为空')
    return
  }
  const knowledgeResp = (await editKnowledge(
    knowledgeID,
    knowledgeName,
    knowledgeDescription,
  )) as KnowledgeResponse
  if (knowledgeResp.status_code == 401) {
    ElNotification.error('Token过期，请重新登录')
    return
  }
  if (knowledgeResp.status_code == 409) {
    ElNotification.error('知识名重复')
    return
  }
  if (knowledgeResp.status_code === 200) {
    // 更新知识卡片
    const index = knowCardList.value?.findIndex(
      (card) => card.knowledgeID === knowledgeID,
    )
    if (index !== undefined && index !== -1) {
      knowCardList.value?.splice(index, 1, knowledgeResp.data)
      ElNotification.success('知识编辑成功')
    }
  } else {
    console.error('Failed to edit knowledge', knowledgeResp.msg)
  }
  console.log(
    `knowledgeID: ${knowledgeID}, knowledgeName: ${knowledgeName}, knowledgeDescription: ${knowledgeDescription}`,
  )
}
</script>

<style scoped>
/* 添加所需的自定义样式 */
</style>
