import { consumeSSE } from './sse'

export interface CitationItem {
  id: string
  documentID: string
  knowledgeID?: string
  page: number
  chunk_id: string
}

export interface ExternalPaper {
  title: string
  authors: string[]
  summary: string
  published: string
  pdf_url: string
  doi: string
  provider: string
  importable: boolean
}

export interface ExternalPaperResult {
  items: ExternalPaper[]
  keywords: string[]
  provider: string
  warning?: string
}

export interface SearchProgress {
  state: 'preparing' | 'searching' | 'answering' | 'done'
  text: string
}

export async function importExternalPaper(pdfUrl: string, knowledgeID: string, title: string) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL
  const res = await fetch(`${baseUrl}/document/import_external`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('token')}`,
    },
    body: JSON.stringify({ pdf_url: pdfUrl, knowledgeID, title }),
  })
  const data = await res.json()
  if (!res.ok || data.status_code !== 200) {
    throw new Error(data.detail || data.msg || `导入失败：HTTP ${res.status}`)
  }
  return data.data as { documentID: string; documentName: string; knowledgeID: string }
}

// 走 V2 /qa/stream（带 citations），回调 delta 与 citations
export async function askQuestionStream(
  question: string,
  documentIds: string[],
  model: string,
  conversationContext: string,
  onDelta: (text: string) => void,
  onCitations: (citations: CitationItem[]) => void,
  onSearchStatus: (progress: SearchProgress) => void,
  onExternalPapers: (result: ExternalPaperResult) => void,
): Promise<void> {
  const token = localStorage.getItem('token')
  const baseUrl = import.meta.env.VITE_API_BASE_URL
  const res = await fetch(`${baseUrl}/qa/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      question,
      document_ids: documentIds,
      model,
      mode: 'ask',
      conversation_context: conversationContext,
    }),
  })
  if (!res.ok) {
    throw new Error(`请求失败：HTTP ${res.status}`)
  }
  await consumeSSE(res, (evt) => {
    if (evt.event === 'delta') {
      onDelta(evt.data?.text || '')
    } else if (evt.event === 'citations') {
      onCitations(evt.data?.items || [])
    } else if (evt.event === 'search_status') {
      onSearchStatus({ state: evt.data?.state || 'searching', text: evt.data?.text || '' })
    } else if (evt.event === 'external_papers') {
      onExternalPapers({
        items: evt.data?.items || [],
        keywords: evt.data?.keywords || [],
        provider: evt.data?.provider || '',
        warning: evt.data?.warning || '',
      })
    }
  })
}
