<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { useVModel } from '@vueuse/core'
import { cn } from '@/lib/utils'

const props = defineProps<{
  defaultValue?: string | number
  modelValue?: string | number
  class?: HTMLAttributes['class']
}>()

const emits = defineEmits<{
  (e: 'update:modelValue', payload: string | number): void
}>()

const modelValue = useVModel(props, 'modelValue', emits, {
  passive: true,
  defaultValue: props.defaultValue,
})
</script>

<template>
  <input v-model="modelValue" :class="cn('flex min-h-[46px] w-full rounded-[10px] border border-[#dce5ee] bg-white px-4 py-2.5 text-sm text-[#263b52] transition-[border-color,box-shadow] duration-200 file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-[#9aa9b9] focus-visible:border-[#8aaad0] focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-[#dbe9f8] disabled:cursor-not-allowed disabled:opacity-50', props.class)">
</template>
