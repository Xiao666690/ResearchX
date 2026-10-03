import { LayoutDashboard, LibraryBig, MessagesSquare, FlaskConical, UsersRound } from 'lucide-vue-next'

interface SidebarItem {
  title: string
  icon: any
  link: string
}

// 基础导航（所有角色一致）
const baseItems: SidebarItem[] = [
  {
    title: '概览',
    icon: LayoutDashboard,
    link: '/home/dashboard',
  },
  {
    title: '论文库',
    link: '/home/library',
    icon: LibraryBig,
  },
  {
    title: '智能问答',
    link: '/home/chat',
    icon: MessagesSquare,
  },
  {
    title: '深度研究',
    link: '/home/research',
    icon: FlaskConical,
  },
  // 论坛模块已隐藏 - 恢复时取消此注释即可
  // {
  //   title: '论坛',
  //   link: '/home/forum/threads',
  //   icon: UsersRound,
  // },
]

// 管理员专属导航：团队管理
const adminItems: SidebarItem[] = [
  {
    title: '管理团队',
    link: '/home/team',
    icon: UsersRound,
  },
]

// 按角色动态生成侧边栏：仅 admin 显示「管理团队」，其余角色与改造前完全一致
export const getSidebarItems = (role?: string | null): SidebarItem[] => {
  if (role === 'admin') {
    return [...baseItems, ...adminItems]
  }
  return baseItems
}

export const sidebarItems = getSidebarItems()
