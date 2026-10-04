import { defineStore } from 'pinia'
import { ref } from 'vue'

export type WorkspaceMode = 'ask' | 'research'

export const useWorkspaceModeStore = defineStore('workspaceMode', () => {
  const mode = ref<WorkspaceMode>('ask')

  function setMode(m: WorkspaceMode) {
    mode.value = m
  }

  return { mode, setMode }
})
