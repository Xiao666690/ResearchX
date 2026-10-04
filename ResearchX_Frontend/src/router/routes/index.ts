import { RouteRecordRaw } from 'vue-router'

import pdfInfo from '@/views/pdf/pdfInfo.vue' // 静态导入

/**
 * 路由配置
 * @description 所有路由都在这里集中管理
 */
const routes: Array<RouteRecordRaw> = [
  // 首页
  {
    path: '/',
    redirect: '/login',
  },
  // 登录界面
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/login/login.vue'),
  },
  // 主页
  {
    name: 'home',
    path: '/home',
    component: () => import('@/views/home.vue'),
    meta: {
      requiresAuth: true,
    },
    children: [
      {
        path: '/home',
        redirect: '/home/dashboard',
      },
      // 控制台页面
      {
        path: 'dashboard',
        component: () => import('@/views/dashboard/dashboard.vue'),
      },
      // 知识库页面
      {
        path: 'library',
        component: () => import('@/views/library/library.vue'),
      },
      {
        path: 'library/notes',
        name: 'notesCollection',
        component: () => import('@/views/library/notesCollection.vue'),
      },
      // 知识页面
      {
        path: 'knowledge/:knowledgeID',
        name: 'knowledge',
        component: () => import('@/views/library/knowledge.vue'),
      },
      {
        path: 'pdfInfo/:knowledgeID/:documentID',
        name: 'pdfInfo',
        component: pdfInfo,
      },
      // 笔记全屏编辑：左论文右笔记分栏（与笔记内「全屏编辑」、笔记集卡片共用入口）
      {
        path: 'note/fullscreen/:knowledgeID/:documentID',
        name: 'noteFullscreen',
        component: () => import('@/views/note/NoteFullscreen.vue'),
      },
      {
        path: 'Chat',
        component: () => import('@/views/chat/chat.vue'),
      },
      {
        path: 'research',
        name: 'research',
        component: () => import('@/views/research/ResearchView.vue'),
      },
      // 团队管理：仅 admin 可进入（路由守卫见 router/index.ts）
      {
        path: 'team',
        name: 'team',
        component: () => import('@/views/team/TeamView.vue'),
        meta: { requiresAuth: true, role: 'admin' },
      },
      {
        path: 'Note',
        component: () => import('@/views/note/note.vue'),
      },
      // 论坛模块已隐藏 - 恢复时取消此注释即可
      // {
      //   path: 'Forum',
      //   name: 'forum',
      //   component: () => import('@/views/forum/forum.vue'),
      //   children: [
      //     {
      //       path: 'threadDetail/:postid',
      //       name: 'threadDetail',
      //       component: () => import('@/views/forum/components/threadDetail.vue'),
      //     },
      //     {
      //       path: 'threads',
      //       component: () => import('@/views/forum/components/threads.vue'),
      //     }
      //   ],
      // }
    ],
  },
  // 知识页面

  // 404页面
  // {
  //   path: '/:catchAll(.*)',
  //   name: 'NotFound',
  //   component: () => import('@/views/NotFound.vue'),
  // },
]

export default routes
