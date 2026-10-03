<template>
  <div class="flex-col w-full p-8">
    <div class="flex items-center justify-between mb-8">
      <h1 class="text-2xl font-bold">管理团队</h1>
      <p class="text-sm text-gray-500">团队成员共享同一知识库与对话</p>
    </div>

    <!-- 团队信息 -->
    <Card class="mb-6">
      <CardHeader>
        <CardTitle>团队信息</CardTitle>
      </CardHeader>
      <CardContent v-if="teamInfo" class="text-sm space-y-1.5">
        <div class="flex flex-wrap items-center gap-2">
          <span>团队名称：</span>
          <template v-if="renaming">
            <input
              v-model="draftTeamName"
              aria-label="新团队名称"
              maxlength="50"
              class="h-9 min-w-48 rounded-md border border-gray-300 bg-white px-3 outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
              :disabled="savingName"
              @keyup.enter="saveTeamName"
              @keyup.esc="cancelRename"
            />
            <Button :disabled="savingName" @click="saveTeamName">{{ savingName ? '保存中…' : '保存' }}</Button>
            <Button variant="ghost" :disabled="savingName" @click="cancelRename">取消</Button>
          </template>
          <template v-else>
            <span class="font-medium">{{ teamInfo.team_name }}</span>
            <Button variant="outline" @click="startRename">重命名</Button>
          </template>
        </div>
        <p>管理员：<span class="font-medium">{{ teamInfo.owner_username }}</span></p>
        <p>成员数量：<span class="font-medium">{{ teamInfo.members.length }}</span></p>
      </CardContent>
    </Card>

    <!-- 加入申请（用户注册填团队名即提交，管理员审批） -->
    <Card class="mb-6">
      <CardHeader>
        <CardTitle>加入申请</CardTitle>
        <p class="text-sm text-gray-500">用户注册时填写团队名即提交申请，审批通过后共享团队知识库与对话</p>
      </CardHeader>
      <CardContent>
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-gray-500 border-b">
              <th class="py-2 pr-4">用户名</th>
              <th class="py-2 pr-4">申请时间</th>
              <th class="py-2 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in requests" :key="r.username" class="border-b last:border-0">
              <td class="py-2.5 pr-4 font-medium">{{ r.username }}</td>
              <td class="py-2.5 pr-4 text-gray-500">{{ r.created_at }}</td>
              <td class="py-2.5 text-right whitespace-nowrap">
                <Button class="mr-2" :disabled="approving === r.username" @click="approveRequest(r.username)">通过 ✓</Button>
                <Button variant="ghost" class="text-red-500 hover:text-red-600" :disabled="approving === r.username" @click="rejectRequest(r.username)">拒绝 ✗</Button>
              </td>
            </tr>
            <tr v-if="requests.length === 0">
              <td colspan="3" class="py-6 text-center text-gray-400">暂无待审批申请</td>
            </tr>
          </tbody>
        </table>
      </CardContent>
    </Card>

    <!-- 成员列表 -->
    <Card>
      <CardHeader>
        <CardTitle>成员列表</CardTitle>
      </CardHeader>
      <CardContent>
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-gray-500 border-b">
              <th class="py-2 pr-4">用户名</th>
              <th class="py-2 pr-4">加入时间</th>
              <th class="py-2 text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in members" :key="m.username" class="border-b last:border-0">
              <td class="py-2.5 pr-4 font-medium">{{ m.username }}</td>
              <td class="py-2.5 pr-4 text-gray-500">{{ m.joined_at }}</td>
              <td class="py-2.5 text-right">
                <Button variant="ghost" class="text-red-500 hover:text-red-600" @click="removeMember(m.username)">
                  移除
                </Button>
              </td>
            </tr>
            <tr v-if="members.length === 0">
              <td colspan="3" class="py-6 text-center text-gray-400">暂无成员，成员申请通过后自动加入</td>
            </tr>
          </tbody>
        </table>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

const base = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001'

interface Member {
  username: string
  joined_at: string
}
interface JoinRequest {
  username: string
  created_at: string
}
interface TeamInfo {
  team_id: string
  team_name: string
  owner_username: string
  members: Member[]
}

const teamInfo = ref<TeamInfo | null>(null)
const members = ref<Member[]>([])
const requests = ref<JoinRequest[]>([])
const approving = ref('') // 正在审批的用户名，避免重复点击
const renaming = ref(false)
const draftTeamName = ref('')
const savingName = ref(false)

const authHeader = () => ({ Authorization: `Bearer ${localStorage.getItem('token') || ''}` })

const startRename = () => {
  draftTeamName.value = teamInfo.value?.team_name || ''
  renaming.value = true
}

const cancelRename = () => {
  renaming.value = false
  draftTeamName.value = ''
}

const saveTeamName = async () => {
  const name = draftTeamName.value.trim()
  if (!name || name.length > 50) {
    ElMessage.warning('团队名称需为 1–50 个字符')
    return
  }
  if (name === teamInfo.value?.team_name) {
    cancelRename()
    return
  }
  savingName.value = true
  try {
    const { data } = await axios.post(`${base}/team/rename`, { team_name: name }, { headers: authHeader(), timeout: 10000 })
    if (teamInfo.value) teamInfo.value.team_name = data.data.team_name
    ElMessage.success('团队名称已更新')
    cancelRename()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '重命名失败')
  } finally {
    savingName.value = false
  }
}

const loadTeam = async () => {
  try {
    const { data } = await axios.get(`${base}/team/info`, { headers: authHeader(), timeout: 10000 })
    if (data?.data) {
      teamInfo.value = data.data
      members.value = data.data.members || []
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '获取团队信息失败')
  }
}

const loadRequests = async () => {
  try {
    const { data } = await axios.get(`${base}/team/requests`, { headers: authHeader(), timeout: 10000 })
    requests.value = data?.data || []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '获取加入申请失败')
  }
}

const approveRequest = async (username: string) => {
  if (approving.value) return
  approving.value = username
  try {
    const { data } = await axios.post(`${base}/team/approve`, { username }, { headers: authHeader(), timeout: 10000 })
    ElMessage.success(data?.msg || '已通过申请')
    await loadRequests()
    await loadTeam() // 刷新成员列表，显示新通过成员
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    approving.value = ''
  }
}

const rejectRequest = async (username: string) => {
  if (approving.value) return
  approving.value = username
  try {
    const { data } = await axios.post(`${base}/team/reject`, { username }, { headers: authHeader(), timeout: 10000 })
    ElMessage.success(data?.msg || '已拒绝申请')
    await loadRequests()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    approving.value = ''
  }
}

const removeMember = async (username: string) => {
  try {
    await ElMessageBox.confirm(
      `确定移除成员 ${username} 吗？移除后该用户将回到个人空间，团队内容不可见。`,
      '移除成员',
      { type: 'warning', confirmButtonText: '移除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const { data } = await axios.post(`${base}/team/remove`, { username }, { headers: authHeader(), timeout: 10000 })
    ElMessage.success(data?.msg || '移除成功')
    await loadTeam()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '移除失败')
  }
}

onMounted(() => {
  loadTeam()
  loadRequests()
})
</script>
