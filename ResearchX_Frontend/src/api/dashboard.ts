import api from '@/api/api'

export interface NoteEntry {
  knowledgeID: string
  knowledgeName: string
  documentID: string
  documentName: string
  preview: string
}

export interface DailyOverview {
  date: string
  stats: { libraries: number; documents: number; vectors: number; askCount: number; researchCount: number; uploadCount: number; readingMinutes: number }
  researchGoals: Array<{ taskID: string; goal: string; status: string }>
  myPosts: Array<{ postID: string; title: string; published: number }>
  newPosts: Array<{ postID: string; title: string; author: string; published: number }>
  uploadedPapers: Array<{ knowledgeID: string; knowledgeName: string; documentID: string; documentName: string; topic: string }>
  readings: Array<{ knowledgeID: string; knowledgeName: string; documentID: string; documentName: string; seconds: number; hasNote: boolean }>
}

function auth() {
  return { headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` } }
}

export async function getDailyOverview(): Promise<DailyOverview> {
  const response = await api.get('/dashboard/overview', auth())
  return response.data.data
}

export async function getNoteCollection(): Promise<NoteEntry[]> {
  const response = await api.get('/notes/collection', auth())
  return response.data.data
}

export async function deleteNote(knowledgeID: string, documentID: string): Promise<void> {
  await api.delete(`/note/${encodeURIComponent(knowledgeID)}/${encodeURIComponent(documentID)}`, auth())
}

export async function recordReading(knowledgeID: string, documentID: string, seconds: number) {
  await api.post('/dashboard/reading', { knowledgeID, documentID, seconds }, auth())
}
