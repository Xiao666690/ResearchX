<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps<{ class?: HTMLAttributes['class'] }>()
</script>

<template>
  <div
    :class="
      cn(
        'flex flex-col-reverse gap-2 border-t border-[#e8edf3] pt-5 sm:flex-row sm:justify-end sm:gap-3',
        props.class,
      )
    "
  >
    <slot />
  </div>
</template>
