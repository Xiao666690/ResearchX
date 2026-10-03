import api from '@/api/api'
import { type ChatRequest } from '@/types/type'

export const getLibraryInfo = async () => {
  // 向后端请求获取知识库信息
  try {
    let token = localStorage.getItem('token')
    if (token) {
      token = `Bearer ${token}`
    }
    const resp = await api.get('/knowledges/getLibraryInfo', {
      headers: {
        Authorization: token,
      },
    })
    return resp.data
  } catch (e: any) {
    throw new Error(e.response?.data?.msg || e.message || '读取论文库失败')
  }
}

export const getKnowledgeList = async () => {
  // 向后端请求获取知识列表
  try {
    let token = localStorage.getItem('token')
    if (token) {
      token = `Bearer ${token}`
    }
    const resp = await api.get('/knowledges/getKnowledgeList', {
      headers: {
        Authorization: token,
      },
    })
    return resp.data
  } catch (e: any) {
    throw new Error(e.response.data.msg)
  }
}

export const createKnowledge = async (
  knowledgeName: string,
  knowledgeDescription?: string,
) => {
  // 向后端请求创建知识
  try {
    let token = localStorage.getItem('token')
    if (token) {
      token = `Bearer ${token}`
    }
    const data = {
      knowledgeName: knowledgeName,
      knowledgeDescription: knowledgeDescription,
    }
    const resp = await api.post('/knowledges/createKnowledge', data, {
      headers: {
        Authorization: token,
      },
    })
    return resp.data
  } catch (e: any) {
    throw new Error(e.response.data.msg)
  }
}

export const editKnowledge = async (
  knowledgeID: string,
  knowledgeName: string,
  knowledgeDescription?: string,
) => {
  try {
    const token = localStorage.getItem('token')
    const resp = await api.post(
      '/knowledges/updateKnowledge',
      { knowledgeID, knowledgeName, knowledgeDescription },
      { headers: { Authorization: token ? `Bearer ${token}` : undefined } },
    )
    return resp.data
  } catch (e: any) {
    throw new Error(e.response?.data?.msg || e.message || '编辑知识失败')
  }
}

export const deleteKnowledge = async (knowledgeIDs: string[]) => {
  try {
    const token = localStorage.getItem('token')
    const resp = await api.post(
      '/knowledges/deleteKnowledge',
      { knowledgeIDs },
      { headers: { Authorization: token ? `Bearer ${token}` : undefined } },
    )
    return resp.data
  } catch (e: any) {
    throw new Error(e.response?.data?.msg || e.message || '删除知识失败')
  }
}

export const getDocumentList = async (knowledgeID: string) => {
  // 向后端请求获取文档列表
  try {
    let token = localStorage.getItem('token')
    if (token) {
      token = `Bearer ${token}`
    }
    const params = {
      knowledgeID: knowledgeID,
    }
    const resp = await api.get(`/document/getDocumentList`, {
      headers: {
        Authorization: token,
      },
      params: params,
    })
    return resp.data
  } catch (e: any) {
    throw new Error(e.response.data.msg)
  }
}

export const uploadDocument = async (knowledgeID: string, file: File) => {
  // 向后端请求上传文档
  try {
    let token = localStorage.getItem('token')
    if (token) {
      token = `Bearer ${token}`
    }
    const formData = new FormData()
    formData.append('knowledgeID', knowledgeID)
    formData.append('documentFile', file)
    const resp = await api.post('/document/upload', formData, {
      headers: {
        Authorization: token,
        'Content-Type': 'multipart/form-data',
      },
    })
    return resp.data
  } catch (e: any) {
    throw new Error(e.response.data.msg)
  }
}

// 获取单个文档状态
export const getDocumentInfo = async (
  knowledgeID: string,
  documentID: string,
) => {
  try {
    let token = localStorage.getItem('token')
    if (token) {
      token = `Bearer ${token}`
    }
    const params = {
      knowledgeID: knowledgeID,
      documentID: documentID,
    }
    const resp = await api.get('/document/Info', {
      headers: {
        Authorization: token,
      },
      params: params,
    })
    return resp.data
  } catch (e: any) {
    throw new Error(e.response.data.msg)
  }
}

// 获取文档pdf文件
export const getDocumentFile = async (
  knowledgeID: string,
  documentID: string,
) => {
  try {
    let token = localStorage.getItem('token')
    if (token) {
      token = `Bearer ${token}`
    }
    const params = {
      knowledgeID: knowledgeID,
      documentID: documentID,
    }
    const resp = await api.get('/document/getFile', {
      headers: {
        Authorization: token,
      },
      params: params,
    })
    return resp.data
  } catch (e: any) {
    throw new Error(e.response.data.msg)
  }
}

// 删除文档 API接口
export const deleteDocument = async (
  knowledgeID: string,
  documentID: string,
) => {
  try {
    let token = localStorage.getItem('token')
    if (token) {
      token = `Bearer ${token}`
    }
    const data = {
      knowledgeID: knowledgeID,
      documentID: documentID,
    }
    const resp = await api.post('/document/delete', data, {
      headers: {
        Authorization: token,
      },
    })
    return resp.data
  } catch (e: any) {
    throw new Error(e.response.data.msg)
  }
}

// 翻译 API接口
export const translateText = async (text: string) => {
  try {
    let token = localStorage.getItem('token')
    if (token) {
      token = `Bearer ${token}`
    }
    const data = { text: text }
    const resp = await api.post('/translate', data, {
      headers: {
        Authorization: token,
      },
      timeout: 90000,
    })
    return resp.data
  } catch (e: any) {
    throw new Error(e.response?.data?.detail || e.response?.data?.msg || e.message || '翻译失败')
  }
}

// 发送消息 API接口
export const askQuestion = async (req: ChatRequest) => {
  try {
    let token = localStorage.getItem('token')
    if (token) {
      token = `Bearer ${token}`
    }
    const data = req
    const resp = await api.post('/chat/generate', data, {
      headers: {
        Authorization: token,
      },
    })
    return resp.data
  } catch (e: any) {
    throw new Error(e.response.data.msg)
  }
}

// 获取gpt流式消息 API接口
export const askQuestionStream = async (req: ChatRequest, store: any) => {
  let messageIndex = -1
  try {
    let token = localStorage.getItem('token')
    if (token) {
      token = `Bearer ${token}`
    }
    const url = import.meta.env.VITE_API_BASE_URL
    const response = await fetch(`${url}/chat/generate_flow`, {
      method: 'POST',
      body: JSON.stringify(req),
      headers: {
        'Content-Type': 'application/json',
        Authorization: token as string,
      },
    })

    if (!response.body) {
      throw new Error('Network response was not ok')
    }

    if (!response.ok) {
      throw new Error(`请求失败：${response.status}`)
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder('utf-8')
    let result = ''
    const message = { text: '', sender: 'bot' }
    store.commit('addMessage', message)
    messageIndex = store.state.messageList.length - 1
    let buffer = ''
    while (true) {
      const { done, value } = await reader!.read()
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true })
      const parsed = parsePack(buffer)
      buffer = parsed.rest
      result += parsed.text
      if (parsed.text) {
        // 不断更新消息到消息列表
        store.commit('appendMessageByIndex', {
          index: messageIndex,
          text: parsed.text,
        })
      }
      if (done) break
    }
    return result
  } catch (e: any) {
    if (messageIndex >= 0) {
      store.commit('appendMessageByIndex', {
        index: messageIndex,
        text: `\n\n问答助手调用失败：${e.message || 'Error fetching stream'}`,
      })
    }
    throw new Error(e.message || 'Error fetching stream')
  }
}

// 解析消息格式
const parsePack = (str: string) => {
  const dataList: string[] = []
  const events = str.split('\n\n')
  const rest = events.pop() || ''

  for (const event of events) {
    const dataLine = event
      .split('\n')
      .find((line) => line.startsWith('data:'))
    if (!dataLine) continue
    try {
      const json = JSON.parse(dataLine.replace(/^data:\s*/, ''))
      if (json.data) {
        dataList.push(json.data)
      }
    } catch (e) {
      console.log('JSON parse error: ', e)
    }
  }

  return {
    text: dataList.join(''),
    rest,
  }
}

// 获取记忆力上下文 API接口
export const getMemoryContext = async (
  question: string,
  context: string,
  answer: string,
) => {
  try {
    let token = localStorage.getItem('token')
    if (token) {
      token = `Bearer ${token}`
    }
    const data = {
      question: question,
      context: context,
      answer: answer,
    }
    const resp = await api.post('chat/summarize', data, {
      headers: {
        Authorization: token,
      },
    })
    return resp.data
  } catch (e: any) {
    throw new Error(e.response.data.msg)
  }
}

// 获取文档总结 API接口
export const getDocumentSummary = async (
  knowledgeID: string,
  documentID: string,
) => {
  try {
    let token = localStorage.getItem('token')
    if (token) {
      token = `Bearer ${token}`
    }
    const params = {
      knowledgeID: knowledgeID,
      documentID: documentID,
    }
    const resp = await api.get('/document/summarize', {
      headers: {
        Authorization: token,
      },
      params: params,
    })
    return resp.data
  } catch (e: any) {
    throw new Error(e.response.data.msg)
  }
}
