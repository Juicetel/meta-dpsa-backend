<script setup lang="ts">
import type { DefineComponent } from 'vue'
import { Chat } from '@ai-sdk/vue'
import { DefaultChatTransport } from 'ai'
import type { UIMessage } from 'ai'
import { useClipboard } from '@vueuse/core'
import { getTextFromMessage } from '@nuxt/ui/utils/ai'
import ProseStreamPre from '../../components/prose/PreStream.vue'
import ProseANewTab from '../../components/prose/A.vue'

const components = {
  pre: ProseStreamPre as unknown as DefineComponent,
  a: ProseANewTab as unknown as DefineComponent
}

const route = useRoute()
const toast = useToast()
const clipboard = useClipboard()
const api = useApi()

function getFileName(url: string): string {
  try {
    const urlObj = new URL(url)
    const pathname = urlObj.pathname
    const filename = pathname.split('/').pop() || 'file'
    return decodeURIComponent(filename)
  } catch {
    return 'file'
  }
}

const { data } = await useFetch(api(`/api/chats/${route.params.id}`), {
  cache: 'force-cache'
})
if (!data.value) {
  throw createError({ statusCode: 404, statusMessage: 'Chat not found' })
}

// Map message id -> initial rating state, so MessageRating can hydrate from
// the DB row (the UIMessage type used by @ai-sdk/vue strips these fields).
const initialRatings = computed(() => {
  const map: Record<string, { rating: 'up' | 'down' | null; ratingComment: string | null }> = {}
  for (const m of (data.value?.messages ?? []) as Array<{ id: string; rating?: 'up' | 'down' | null; ratingComment?: string | null }>) {
    map[m.id] = {
      rating: m.rating ?? null,
      ratingComment: m.ratingComment ?? null
    }
  }
  return map
})

const { data: modelInfo } = await useFetch<{ raw: string, label: string }>(api('/api/model'), {
  default: () => ({ raw: '', label: 'Loading model…' })
})

const input = ref('')

const { csrf, headerName } = useCsrf()

const chat = new Chat({
  id: data.value.id,
  messages: data.value.messages,
  transport: new DefaultChatTransport({
    api: api(`/api/chats/${data.value.id}`),
    headers: { [headerName]: csrf }
  }),
  onData: (dataPart) => {
    if (dataPart.type === 'data-chat-title') {
      refreshNuxtData('chats')
    }
  },
  onError(error) {
    const { message } = typeof error.message === 'string' && error.message[0] === '{' ? JSON.parse(error.message) : error
    toast.add({
      description: message,
      icon: 'i-lucide-alert-circle',
      color: 'error',
      duration: 0
    })
  }
})

async function handleSubmit(e: Event) {
  e.preventDefault()
  if (input.value.trim()) {
    chat.sendMessage({ text: input.value })
    input.value = ''
  }
}

const copied = ref(false)

function copy(e: MouseEvent, message: UIMessage) {
  clipboard.copy(getTextFromMessage(message))

  copied.value = true

  setTimeout(() => {
    copied.value = false
  }, 2000)
}

const speakingMessageId = ref<string | null>(null)

function speak(message: UIMessage) {
  if (typeof window === 'undefined' || !window.speechSynthesis) return

  if (speakingMessageId.value === message.id) {
    window.speechSynthesis.cancel()
    speakingMessageId.value = null
    return
  }

  window.speechSynthesis.cancel()

  const text = getTextFromMessage(message)
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/[*_`#>]/g, '')
    .replace(/---+/g, '')
    .replace(/\n+/g, '. ')
    .trim()
  if (!text) return

  const utterance = new SpeechSynthesisUtterance(text)
  utterance.rate = 1
  utterance.pitch = 1
  utterance.onend = () => {
    if (speakingMessageId.value === message.id) speakingMessageId.value = null
  }
  utterance.onerror = () => {
    if (speakingMessageId.value === message.id) speakingMessageId.value = null
  }

  speakingMessageId.value = message.id
  window.speechSynthesis.speak(utterance)
}

onBeforeUnmount(() => {
  if (typeof window !== 'undefined' && window.speechSynthesis) {
    window.speechSynthesis.cancel()
  }
})

// Timestamp handling — use server createdAt when available, otherwise stabilize
// per-message so the value doesn't flicker across re-renders.
const messageTimes = new Map<string, Date>()
function formatTime(message: UIMessage): string {
  const createdAt = (message as unknown as { createdAt?: string | Date }).createdAt
  let date: Date
  if (createdAt) {
    date = new Date(createdAt)
  } else if (messageTimes.has(message.id)) {
    date = messageTimes.get(message.id)!
  } else {
    date = new Date()
    messageTimes.set(message.id, date)
  }
  return date
    .toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
    .toLowerCase()
}

onMounted(() => {
  if (data.value?.messages.length === 1) {
    chat.regenerate()
  }
})
</script>

<template>
  <UDashboardPanel
    id="chat"
    class="relative min-h-0"
    :ui="{ body: 'p-0 sm:p-0 overscroll-none' }"
  >
    <template #header>
      <DashboardNavbar />
    </template>

    <template #body>
      <div class="flex flex-1">
        <UContainer class="flex-1 flex flex-col gap-4 sm:gap-6 max-w-[80%]">
          <UChatMessages
            should-auto-scroll
            :messages="chat.messages"
            :status="chat.status"
            :user="{ side: 'left', variant: 'naked', ui: { container: 'gap-0 pb-0' } }"
            :assistant="{ side: 'left', variant: 'naked', ui: { container: 'gap-0 pb-0' } }"
            :spacing-offset="160"
            :ui="{
              root: 'w-full flex flex-col gap-4 flex-1 px-0',
              indicator: 'h-6 flex items-center gap-1 px-5 py-3 *:size-2 *:rounded-full *:bg-zinc-300 dark:*:bg-zinc-600 [&>*:nth-child(1)]:animate-[bounce_1s_infinite] [&>*:nth-child(2)]:animate-[bounce_1s_0.15s_infinite] [&>*:nth-child(3)]:animate-[bounce_1s_0.3s_infinite]'
            }"
            class="lg:pt-(--ui-header-height) pb-4 sm:pb-6"
          >
            <template #content="{ message }">
              <div
                class="w-full rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4 sm:p-5"
              >
                <!-- Header: avatar + role label | timestamp -->
                <div class="flex items-center justify-between mb-3">
                  <div class="flex items-center gap-3">
                    <div
                      v-if="message.role === 'user'"
                      class="size-6 rounded-full bg-violet-200 dark:bg-violet-400/60 shrink-0"
                    />
                    <div
                      v-else
                      class="size-7 rounded-md bg-[#00703E] flex items-center justify-center shrink-0"
                    >
                      <UIcon name="i-lucide-bot" class="size-4 text-white" />
                    </div>
                    <span class="font-semibold text-zinc-900 dark:text-zinc-100">
                      {{ message.role === 'user' ? 'You' : 'Results' }}
                    </span>
                  </div>
                  <span class="text-xs text-zinc-500 dark:text-zinc-400 shrink-0">
                    {{ formatTime(message) }}
                  </span>
                </div>

                <!-- Content -->
                <div class="pl-10 text-sm sm:text-[15px] text-zinc-800 dark:text-zinc-200">
                  <template v-for="(part, index) in message.parts" :key="`${message.id}-${part.type}-${index}${'state' in part ? `-${part.state}` : ''}`">
                    <Reasoning
                      v-if="part.type === 'reasoning'"
                      :text="part.text"
                      :is-streaming="part.state !== 'done'"
                    />
                    <!-- Only render markdown for assistant messages to prevent XSS from user input -->
                    <MDCCached
                      v-else-if="part.type === 'text' && message.role === 'assistant'"
                      :value="part.text"
                      :cache-key="`${message.id}-${index}`"
                      :components="components"
                      :parser-options="{ highlight: false }"
                      class="*:first:mt-0 *:last:mb-0"
                    />
                    <!-- User messages are rendered as plain text (safely escaped by Vue) -->
                    <p v-else-if="part.type === 'text' && message.role === 'user'" class="whitespace-pre-wrap text-left">
                      &ldquo;{{ part.text }}&rdquo;
                    </p>
                    <ToolWeather
                      v-else-if="part.type === 'tool-weather'"
                      :invocation="(part as WeatherUIToolInvocation)"
                    />
                    <ToolChart
                      v-else-if="part.type === 'tool-chart'"
                      :invocation="(part as ChartUIToolInvocation)"
                    />
                    <FileAvatar
                      v-else-if="part.type === 'file'"
                      :name="getFileName(part.url)"
                      :type="part.mediaType"
                      :preview-url="part.url"
                      class="inline-flex"
                    />
                  </template>
                </div>

                <!-- Actions (assistant only) -->
                <div
                  v-if="message.role === 'assistant' && chat.status !== 'streaming'"
                  class="flex flex-col gap-2 mt-3 pl-8"
                >
                  <div class="flex items-center gap-1">
                    <UButton
                      :icon="speakingMessageId === message.id ? 'i-lucide-volume-x' : 'i-lucide-volume-2'"
                      size="sm"
                      variant="ghost"
                      color="neutral"
                      :aria-label="speakingMessageId === message.id ? 'Stop reading' : 'Read aloud'"
                      @click="speak(message)"
                    />
                    <UButton
                      :icon="copied ? 'i-lucide-copy-check' : 'i-lucide-copy'"
                      size="sm"
                      variant="ghost"
                      color="neutral"
                      aria-label="Copy"
                      @click="copy($event, message)"
                    />
                  </div>
                  <MessageRating
                    :message-id="message.id"
                    :initial-rating="initialRatings[message.id]?.rating"
                    :initial-comment="initialRatings[message.id]?.ratingComment"
                  />
                </div>
              </div>
            </template>
          </UChatMessages>

          <UChatPrompt
            v-model="input"
            :error="chat.error"
            variant="naked"
            class="sticky bottom-4 [view-transition-name:chat-prompt] z-10 rounded-xl bg-white dark:bg-zinc-900 shadow-md hover:shadow-lg focus-within:shadow-xl focus-within:ring-2 focus-within:ring-[#00703E]/30 focus-within:-translate-y-0.5 transition-all duration-200 mb-4"
            :ui="{ base: 'px-1.5' }"
            @submit="handleSubmit"
            @keydown.enter.exact.prevent="handleSubmit"
          >
            <template #footer>
              <div class="flex items-center gap-1">
                <span class="text-xs text-muted px-1" :title="modelInfo?.raw">{{ modelInfo?.label }}</span>
              </div>

              <UChatPromptSubmit
                :status="chat.status"
                color="neutral"
                size="sm"
                @stop="chat.stop()"
                @reload="chat.regenerate()"
                class="bg-[#00703E] hover:bg-[#005c33] text-white"
                label="Send"
              />
            </template>
          </UChatPrompt>
        </UContainer>
      </div>
    </template>
  </UDashboardPanel>
</template>
