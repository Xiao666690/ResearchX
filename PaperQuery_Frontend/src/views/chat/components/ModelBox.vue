<template>
  <div class="model-box">
    <el-dropdown trigger="click" :hide-on-click="true" @command="handleSelect">
      <button type="button" class="model-trigger" aria-label="切换模型">
        <span class="model-dot" />
        <span>{{ currentLabel }}</span>
        <ChevronDown :size="15" />
      </button>

      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item
            v-for="model in modelStore.modelOptions"
            :key="model.value"
            :command="model.value"
            :class="{ 'is-current-model': model.value === modelStore.currentModel }"
          >
            <span>{{ model.label }}</span>
            <Check v-if="model.value === modelStore.currentModel" :size="14" />
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElNotification } from 'element-plus'
import { Check, ChevronDown } from 'lucide-vue-next'
import { useModelStore, type ModelType } from '@/stores/modelStore'
import { useMessageListStore } from '@/stores/messageList'

const modelStore = useModelStore()
const messageListStore = useMessageListStore()

const currentLabel = computed(() => {
  const option = modelStore.modelOptions.find(m => m.value === modelStore.currentModel)
  return option ? option.label : 'DeepSeek'
})

function handleSelect(model: ModelType | string) {
  if (!modelStore.modelOptions.some(item => item.value === model)) return
  const nextModel = model as ModelType
  if (nextModel === modelStore.currentModel) return

  const fromLabel = modelStore.getModelLabel(modelStore.currentModel)
  const toLabel = modelStore.getModelLabel(nextModel)
  messageListStore.compressContextForModelSwitch(fromLabel, toLabel)
  modelStore.setModel(nextModel)
  messageListStore.addSystemMessage(
    `已切换至 ${toLabel}。系统已压缩并保留当前上下文；切换模型无可避免可能导致回答准确率降低，请结合论文来源核对关键结论。`,
  )
  ElNotification({
    title: `已切换至 ${toLabel}`,
    message: '已压缩保留当前上下文。切换模型可能降低回答准确率，请注意核对。',
    type: 'warning',
    duration: 5000,
  })
}
</script>

<style scoped>
.model-trigger { display: inline-flex; height: 38px; align-items: center; gap: 8px; padding: 0 12px; border: 1px solid #e3e3e6; border-radius: 11px; color: #343438; background: rgba(255,255,255,.92); font-size: 13px; font-weight: 600; transition: border-color .18s ease, background .18s ease, box-shadow .18s ease; }
.model-trigger:hover { border-color: #d2cde4; background: #fff; box-shadow: 0 4px 14px rgba(32,32,36,.06); }
.model-trigger:focus-visible { outline: 3px solid rgba(109,91,208,.14); outline-offset: 1px; }
.model-dot { width: 7px; height: 7px; border-radius: 50%; background: #6d5bd0; box-shadow: 0 0 0 3px #eeebf8; }
:deep(.el-dropdown-menu__item) { display: flex; min-width: 132px; justify-content: space-between; gap: 20px; border-radius: 7px; color: #55555b; }
:deep(.el-dropdown-menu__item.is-current-model) { color: #51458f; background: #f3f1f8; font-weight: 600; }
</style>
