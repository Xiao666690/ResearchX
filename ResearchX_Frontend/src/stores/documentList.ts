import { defineStore } from 'pinia'
import { reactive, computed } from 'vue'

export type Document = {
  isLoading: boolean
  documentID?: string
  documentName: string
  fileSize?: number
  documentFile?: File
  knowledgeID?: string
  source: 'library' | 'upload'
}

export const useDocumentListStore = defineStore('documentList', () => {
  const state = reactive({
    documentList: <Array<Document>>[],
    selectedDocumentIDs: <string[]>[],
  })

  const getDocumentList = computed(() => state.documentList)

  function appendDocument(document: Document) {
    if (
      document.documentID &&
      state.documentList.some(item => item.documentID === document.documentID)
    ) {
      return false
    }
    state.documentList.push(document)
    if (document.documentID) state.selectedDocumentIDs = [document.documentID]
    return true
  }

  function deleteDocument(index: number) {
    const removed = state.documentList.splice(index, 1)[0]
    if (removed?.documentID) state.selectedDocumentIDs = state.selectedDocumentIDs.filter(id => id !== removed.documentID)
  }

  // 按文档 ID 移除（用于知识库删除文档后，同步清理对话页绑定的残留文档）
  function deleteDocumentById(documentID: string) {
    const index = state.documentList.findIndex(item => item.documentID === documentID)
    if (index !== -1) {
      deleteDocument(index)
      return true
    }
    return false
  }

  function getDocumentIDs() {
    return state.selectedDocumentIDs.filter(id => state.documentList.some(item => item.documentID === id))
  }

  function toggleDocument(documentID: string) {
    state.selectedDocumentIDs = state.selectedDocumentIDs.includes(documentID)
      ? state.selectedDocumentIDs.filter(id => id !== documentID)
      : [...state.selectedDocumentIDs, documentID]
  }

  function getSelectedSnapshots() {
    return getDocumentSnapshots().filter(item => item.documentID && getDocumentIDs().includes(item.documentID))
  }

  function restoreDocuments(documents: Array<{ documentID?: string; documentName: string; knowledgeID?: string; source?: 'library' | 'upload' }>, selected?: string[]) {
    state.documentList = documents.filter(item => item.documentID).map(item => ({ ...item, source: item.source || 'library', isLoading: false }))
    const validIds = state.documentList.map(item => item.documentID!).filter(Boolean)
    state.selectedDocumentIDs = selected?.filter(id => validIds.includes(id)) || validIds.slice(-1)
  }

  function clearDocuments() { state.documentList = []; state.selectedDocumentIDs = [] }

  function getDocumentSnapshots() {
    return state.documentList.map((value) => {
      return {
        documentID: value.documentID?.toString(),
        documentName: value.documentName,
        knowledgeID: value.knowledgeID,
        source: value.source,
      }
    })
  }

  return {
    state,
    getDocumentIDs,
    getDocumentSnapshots,
    getDocumentList,
    appendDocument,
    deleteDocument,
    deleteDocumentById,
    toggleDocument,
    getSelectedSnapshots,
    restoreDocuments,
    clearDocuments,
  }
})
