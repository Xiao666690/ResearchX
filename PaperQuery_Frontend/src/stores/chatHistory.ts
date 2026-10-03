import { computed, reactive } from 'vue'
import { defineStore } from 'pinia'
import type { Message } from './messageList'

export type ChatDocumentSnapshot = {
  documentID?: string
  documentName: string
  knowledgeID?: string
  source?: 'library' | 'upload'
}

export type ChatSession = {
  id: string
  title: string
  updatedAt: number
  model: string
  modelLabel: string
  memory: string
  summary?: string
  isTitleCustomized?: boolean
  documents: ChatDocumentSnapshot[]
  selectedDocumentIDs?: string[]
  messages: Message[]
}

function getStorageKey() {
  const username = localStorage.getItem('username') || 'guest'
  return `paperquery:chat-history:${username}`
}

function createSessionId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export const useChatHistoryStore = defineStore('chatHistory', () => {
  const state = reactive({
    sessions: <ChatSession[]>[],
    currentSessionId: '',
  })

  function loadFromStorage() {
    try {
      const raw = localStorage.getItem(getStorageKey())
      const saved = raw ? JSON.parse(raw) : []
      state.sessions = Array.isArray(saved)
        ? saved.map((session: ChatSession) => ({
            ...session,
            summary: session.summary || session.memory || '',
            isTitleCustomized: Boolean(session.isTitleCustomized),
          }))
        : []
    } catch (error) {
      console.error('Load chat history failed:', error)
      state.sessions = []
    }
  }

  function persist() {
    localStorage.setItem(getStorageKey(), JSON.stringify(state.sessions))
  }

  function saveSnapshot(snapshot: Omit<ChatSession, 'id' | 'updatedAt'>) {
    if (snapshot.messages.length === 0) return

    if (!state.currentSessionId) {
      state.currentSessionId = createSessionId()
    }

    const index = state.sessions.findIndex(item => item.id === state.currentSessionId)
    const previous = index >= 0 ? state.sessions[index] : undefined
    const session: ChatSession = {
      ...snapshot,
      id: state.currentSessionId,
      updatedAt: Date.now(),
      title: previous?.isTitleCustomized ? previous.title : snapshot.title,
      summary: snapshot.summary || snapshot.memory || previous?.summary || '',
      isTitleCustomized: previous?.isTitleCustomized || false,
    }
    if (index >= 0) {
      state.sessions[index] = session
    } else {
      state.sessions.unshift(session)
    }
    state.sessions.sort((a, b) => b.updatedAt - a.updatedAt)
    state.sessions = state.sessions.slice(0, 30)
    persist()
  }

  function startNewSession() {
    state.currentSessionId = createSessionId()
  }

  function useSession(sessionId: string) {
    state.currentSessionId = sessionId
  }

  function removeSession(sessionId: string) {
    state.sessions = state.sessions.filter(item => item.id !== sessionId)
    if (state.currentSessionId === sessionId) {
      state.currentSessionId = ''
    }
    persist()
  }

  function renameSession(sessionId: string, title: string) {
    const session = state.sessions.find(item => item.id === sessionId)
    const normalized = title.trim().slice(0, 60)
    if (!session || !normalized) return false
    session.title = normalized
    session.isTitleCustomized = true
    session.updatedAt = Date.now()
    persist()
    return true
  }

  function updateSessionSummary(sessionId: string, summary: string) {
    const session = state.sessions.find(item => item.id === sessionId)
    const normalized = summary.trim()
    if (!session || !normalized) return false
    session.summary = normalized
    session.memory = normalized
    session.updatedAt = Date.now()
    persist()
    return true
  }

  const sessionList = computed(() => state.sessions)

  loadFromStorage()

  return {
    state,
    sessionList,
    loadFromStorage,
    saveSnapshot,
    startNewSession,
    useSession,
    removeSession,
    renameSession,
    updateSessionSummary,
  }
})
