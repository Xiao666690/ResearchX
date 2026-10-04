import api from '@/api/api'

// 只创建持久化任务；研究在后端继续执行，通过查询接口读取进度。
export const createResearchTask = async (
  goal: string,
  mode = 'research',
  documentIds: string[] = [],
  parentTaskId?: string,
) => {
  const token = localStorage.getItem('token')
  const resp = await api.post(
    '/research/tasks',
    { goal, mode, document_ids: documentIds, parent_task_id: parentTaskId },
    {
      headers: { Authorization: `Bearer ${token}` },
      timeout: 20000,
    },
  )
  return resp.data
}

// 任务列表
export const listResearchTasks = async () => {
  const token = localStorage.getItem('token')
  const resp = await api.get('/research/tasks', {
    headers: { Authorization: `Bearer ${token}` },
  })
  return resp.data
}

// 任务详情
export const getResearchTask = async (taskId: string) => {
  const token = localStorage.getItem('token')
  const resp = await api.get(`/research/tasks/${taskId}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return resp.data
}
