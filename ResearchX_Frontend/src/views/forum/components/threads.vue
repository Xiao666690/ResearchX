<template>
  <div class="flex p-4 w-[750px] overflow-hidden">
    <div
      class="flex-1 flex flex-col bg-white rounded-lg shadow overflow-hidden"
    >
      <div class="flex justify-start p-2">
        <div v-for="button in buttonList" :key="button" class="m-1">
          <Button :variant="selectedCategory === button ? 'default' : 'outline'" @click="selectedCategory = button">
            {{ button }}
          </Button>
        </div>
      </div>
      <ul class="flex-1 flex flex-col overflow-auto">
        <li
          v-for="post in filteredPosts"
          :key="post.postid"
          @click="
            () => {
              console.log(post.postid)
              router.push({
                name: 'threadDetail',
                params: { postid: post.postid },
              })
            }
          "
        >
          <div class="flex hover:bg-gray-100 p-4 rounded border items-center">
            <Avatar username="" class="h-10 w-10 rounded-sm bg-black mr-4" />
            <div>
              <h3 class="text-lg font-bold">{{ post.title }}</h3>
              <p class="text-gray-600 text-sm">
                {{ post.category || '技术' }} · {{ post.username }} ·
                {{ formatterTime(post.publishtime_timestamp.toString()) }}
              </p>
            </div>
          </div>
        </li>
        <li v-if="!filteredPosts.length" class="p-8 text-center text-gray-500">这个分类还没有帖子</li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { getForumPosts } from '@/api/forum'
import { formatterTime } from '@/components/utils'
import { Button } from '@/components/ui/button'
import Avatar from './avatar.vue'

// 定义post 结构体
interface Post {
  postid: string
  title: string
  content: string
  publishtime_timestamp: number
  updatetime_timestamp: number
  lid: string
  username: string
  category?: string
}

// 列表：存储所有帖子
const posts = ref<Post[]>([])
const selectedCategory = ref('全部')
const filteredPosts = computed(() => selectedCategory.value === '全部' ? posts.value : posts.value.filter(post => (post.category || '技术') === selectedCategory.value))

const router = useRouter()

const buttonList = [
  '全部',
  '技术',
  '生活',
  '学习',
  '创意',
  '好玩',
  '问与答',
  '城市',
  '其他',
]

let timeoutId: number | null = null // 明确指定类型

onMounted(() => {
  // 获取所有帖子
  getForumPosts().then((res) => {
    posts.value = res.data
  })

  // 定时获取全部帖子
  const fetchData = async () => {
    // console.log('开始请求数据...')
    try {
      const response = await getForumPosts()
      const res = await response.data
      posts.value = res
    } catch (error) {
      console.error('请求出错', error)
    }

    // 在异步操作完成后，再开始下一个定时器
    timeoutId = window.setTimeout(fetchData, 30000)
  }

  fetchData()
})

onUnmounted(() => {
  if (timeoutId) {
    clearTimeout(timeoutId)
  }
})
</script>

<style scoped>
/* 定义进入和离开的滑动效果 */
.slide-enter-active,
.slide-leave-active {
  transition:
    transform 1s ease,
    opacity 1s ease;
}
.slide-enter,
.slide-leave-to {
  transform: translateX(100%);
  opacity: 0;
}
.slide-enter-to,
.slide-leave {
  transform: translateX(0);
  opacity: 1;
}
</style>
