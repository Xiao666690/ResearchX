<script setup lang="ts">
import { type HTMLAttributes, computed } from 'vue'
import {
  DialogClose,
  DialogContent,
  type DialogContentEmits,
  type DialogContentProps,
  DialogOverlay,
  DialogPortal,
  useForwardPropsEmits,
} from 'radix-vue'
import { X } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

const props = defineProps<DialogContentProps & { class?: HTMLAttributes['class'] }>()
const emits = defineEmits<DialogContentEmits>()

const delegatedProps = computed(() => {
  const { class: _, ...delegated } = props

  return delegated
})

const forwarded = useForwardPropsEmits(delegatedProps, emits)
</script>

<template>
  <DialogPortal>
    <DialogOverlay
      class="fixed inset-0 z-50 bg-[#162943]/40 backdrop-blur-[3px] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 motion-reduce:animate-none"
    />
    <DialogContent
      v-bind="forwarded"
      :class="
        cn(
          'fixed left-1/2 top-1/2 z-50 grid w-[calc(100vw-32px)] max-w-[640px] max-h-[88vh] -translate-x-1/2 -translate-y-1/2 gap-5 overflow-y-auto rounded-[18px] border border-[#e0e7ef] bg-white p-6 text-[#263b52] shadow-[0_28px_72px_rgba(22,43,73,.18),0_4px_14px_rgba(22,43,73,.06)] duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 sm:p-8 motion-reduce:animate-none',
          props.class,
        )"
    >
      <slot />

      <DialogClose
        class="absolute right-5 top-5 grid h-9 w-9 place-items-center rounded-[9px] text-[#8191a4] transition-colors hover:bg-[#eef3f8] hover:text-[#315f9d] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#86a9d4] disabled:pointer-events-none"
      >
        <X class="w-4 h-4" />
        <span class="sr-only">关闭弹窗</span>
      </DialogClose>
    </DialogContent>
  </DialogPortal>
</template>
