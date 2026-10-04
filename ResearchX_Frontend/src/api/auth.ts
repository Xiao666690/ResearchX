// import axios from 'axios'
import { LoginResponse } from '@/types/type'
// import api from '@/api/api'
import axios from 'axios'

export const register = async (
  url: string,
  user: { username: string; password: string; teamName?: string },
) => {
  try {
    const response = await axios.post(
      `${url}/register`,
      { username: user.username, password: user.password, team_name: user.teamName ?? '' },
      { timeout: 10000 },
    )
    return response.data
  } catch (error: any) {
    throw new Error(error?.response?.data?.detail || error?.response?.data?.msg || '注册失败，请稍后重试')
  }
}

export const login = async (url: string, user: any): Promise<LoginResponse> => {
  const api = axios.create({
    baseURL: url,
    timeout: 10000,
  })
  try {
    const response = await api.post<LoginResponse>(`/login`, user)
    // 添加header
    const resp = response.data
    if (resp) {
      localStorage.setItem('token', resp.data.access_token)
      localStorage.setItem('username', user.username)
      // 角色与工作空间：决定侧边栏「管理团队」入口与共享知识库
      if (resp.data.role) localStorage.setItem('role', resp.data.role)
      if (resp.data.workspace_lid) localStorage.setItem('workspaceLid', resp.data.workspace_lid)
    }
    return response.data
  } catch (e: any) {
    throw new Error(e?.response?.data?.msg || e?.response?.data?.detail || '登录失败，请检查服务器连接')
  }
}
