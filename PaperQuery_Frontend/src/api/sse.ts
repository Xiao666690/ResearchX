// 统一 SSE 流式事件解析器

export interface SSEEvent {
  event: string
  data: any
}

// 把缓冲区分割为完整事件帧，返回已解析事件与剩余未完成缓冲区
export function parseSSEFrames(buffer: string): {
  events: SSEEvent[]
  rest: string
} {
  const events: SSEEvent[] = []
  const frames = buffer.split('\n\n')
  const rest = frames.pop() || ''

  for (const frame of frames) {
    let event = 'message'
    let dataStr = ''
    for (const line of frame.split('\n')) {
      if (line.startsWith('event:')) {
        event = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        dataStr += line.slice(5).trim()
      }
    }
    let data: any = dataStr
    try {
      data = JSON.parse(dataStr)
    } catch {
      // 保留原始字符串
    }
    events.push({ event, data })
  }
  return { events, rest }
}

// 消费一个 SSE Response，逐事件回调
export async function consumeSSE(
  response: Response,
  onEvent: (evt: SSEEvent) => void,
): Promise<void> {
  if (!response.body) {
    throw new Error('响应体为空')
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const { events, rest } = parseSSEFrames(buffer)
    buffer = rest
    events.forEach(onEvent)
  }
  // 处理末尾残留
  if (buffer.trim()) {
    const { events } = parseSSEFrames(buffer + '\n\n')
    events.forEach(onEvent)
  }
}
