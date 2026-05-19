<script setup lang="ts">
const input = ref('')
const loading = ref(false)
const chatId = crypto.randomUUID()

const { csrf, headerName } = useCsrf()
const api = useApi()

async function createChat(prompt: string) {
  input.value = prompt
  loading.value = true

  const chat = await $fetch(api('/api/chats'), {
    method: 'POST',
    headers: { [headerName]: csrf },
    body: {
      id: chatId,
      message: {
        role: 'user',
        parts: [{ type: 'text', text: prompt }]
      }
    }
  })

  refreshNuxtData('chats')
  navigateTo(`/chat/${chat?.id}`)
}

async function onSubmit() {
  await createChat(input.value)
}

const view = ref<'quick' | 'faq'>('quick')

const quickTopics = [
  {
    label: 'Home',
    description: 'Have natural conversations and get fast, smart answers for any topic.',
    image: '/images/Home.png',
    to: 'https://www.dpsa.gov.za/',
    prompt: 'Please tell me about the home page of the DPSA website'
  },
  {
    label: 'About Us',
    description: 'Learn more about the Department of Public Service and Administration.',
    image: '/images/About_us.png',
    to: 'https://www.dpsa.gov.za/about-us/',
    prompt: 'Please tell me about the Department of Public Service and Administration'
  },
  {
    label: 'Legislation',
    description: 'Browse legislation governing the South African public service.',
    image: '/images/Legislation.png',
    to: 'https://www.dpsa.gov.za/legislation/',
    prompt: 'Please tell me about the legislation governing the South African public service'
  },
  {
    label: 'PAIA',
    description: 'Access information under the Promotion of Access to Information Act.',
    image: '/images/PAIA.png',
    to: 'https://www.dpsa.gov.za/paia/',
    prompt: 'Please tell me about the Promotion of Access to Information Act (PAIA) and how to access information under it'
  },
  {
    label: 'Policy Updates',
    description: 'Stay current with revised policies and circulars.',
    image: '/images/Policy_updates.png',
    to: 'https://www.dpsa.gov.za/policy-updates/',
    prompt: 'Please tell me about the latest DPSA policy updates and circulars'
  },
  {
    label: 'Resource Centre',
    description: 'Centralized knowledge and tools for government employees.',
    image: '/images/Resource_centre.png',
    to: 'https://www.dpsa.gov.za/resource_centre/',
    prompt: 'Please tell me about the DPSA Resource Centre and the resources available for government employees'
  }
]

const quickChats = [
  {
    label: 'Pensions',
  },
  {
    label: 'Accommodation expenditure: Offical',
  },
  {
    label: 'Service bonus',
  },
  {
    label: 'Medical assistance',
  },
  {
    label: 'Government employees home scheme',
  },
  {
    label: 'Organisational functionality assessment',
  },
  {
    label: 'Corporate governance of ICT policy framework',
  },
  {
    label: 'Performance of other remunerative work outside an employee’s department',
  },
  {
    label: 'Discipline management',
  },
  {
    label: 'Doing business with the state',
  },
  {
    label: 'Special advisors',
  },
  {
    label: 'Acting allowances',
  }
]
</script>

<template>
  <UDashboardPanel
    id="home"
    class="min-h-0"
    :ui="{ body: 'p-0 sm:p-0' }"
  >

  
    <template #header>
      <DashboardNavbar />
    </template>

    <template #body>
      <div class="flex flex-1">
        <UContainer class="flex-1 flex flex-col justify-center gap-4 sm:gap-6 py-8">
          <div class="flex flex-row justify-center items-center">
            <div class="text-black dark:text-white font-normal rounded-full bg-[#3AD38914] border border-[#3AD3891F] lg:w-[50%] w-[80%] text-center text-[14px] p-2">
              Batho Pele - We Belong, We Care, We Serve
            </div>
          </div>
          <span class="flex flex-row justify-center items-center gap-4 sm:gap-6 py-8">
            <NuxtImg src="/images/coat_of_arms.svg" alt="Logo" width="40" height="40" />
            <h1 class="text-xl sm:text-2xl text-highlighted font-medium">
              What can <span class="text-[#006532]">Batho Pele AI</span> help you with today?
            </h1>
          </span>

          <UChatPrompt
            v-model="input"
            :status="loading ? 'streaming' : 'ready'"
            class="[view-transition-name:chat-prompt]"
            variant="subtle"
            :ui="{ base: 'px-1.5' }"
            @submit="onSubmit"
          >
            <template #footer>
              <div class="flex items-center gap-1" />

              <UChatPromptSubmit variant="solid" label="Send" size="sm" class="bg-[#00703E] hover:bg-[#005c33] text-white" />
            </template>
          </UChatPrompt>

          <div class="flex items-center gap-2">
            <UButton
              label="Quick Topics"
              size="sm"
              :variant="view === 'quick' ? 'solid' : 'ghost'"
              :class="view === 'quick' ? 'bg-[#006532] hover:bg-[#005c33] text-white' : 'text-[#006532] border border-[#006532] hover:bg-[#006532]/10'"
              @click="view = 'quick'"
            />
            <UButton
              label="FAQ"
              size="sm"
              :variant="view === 'faq' ? 'solid' : 'ghost'"
              :class="view === 'faq' ? 'bg-[#006532] hover:bg-[#005c33] text-white' : 'text-[#006532] border border-[#006532] hover:bg-[#006532]/10'"
              @click="view = 'faq'"
            />
          </div>

          <template v-if="view === 'quick'">
            <div class="flex items-center justify-between">
              <div>
                <h3 class="text-black dark:text-white font-semibold">Quick Topics</h3>
                <p class="text-xs text-muted">Get started with Quick Topics and explore below</p>
              </div>
              <NuxtLink to="https://www.dpsa.gov.za/" target="_blank" class="text-xs text-[#006532] hover:underline flex items-center gap-1">
                Browse all
                <UIcon name="i-lucide:arrow-right" class="w-3 h-3" />
              </NuxtLink>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <div
                v-for="topic in quickTopics"
                :key="topic.label"
                class="rounded-lg border border-default overflow-hidden flex flex-col bg-default"
              >
                <div class="h-32 w-full overflow-hidden bg-white dark:bg-gray-900">
                  <NuxtImg :src="topic.image" :alt="topic.label" class="w-full h-full object-cover" />
                </div>
                <div class="p-4 flex flex-col gap-3 flex-1">
                  <h4 class="font-semibold text-black dark:text-white">{{ topic.label }}</h4>
                  <p class="text-sm text-muted flex-1">{{ topic.description }}</p>
                  <UButton
                    label="Learn More"
                    size="sm"
                    color="neutral"
                    variant="outline"
                    block
                    @click="createChat(topic.prompt)"
                  />
                </div>
              </div>
            </div>
          </template>

          <template v-else>
            <div>
              <h3 class="text-black dark:text-white font-semibold">Frequently asked questions</h3>
              <p class="text-xs text-muted">Get started with Frequently asked questions and explore below</p>
            </div>
            <div class="flex flex-wrap gap-2">
              <UButton
                v-for="quickChat in quickChats"
                :key="quickChat.label"
                :label="quickChat.label"
                trailing-icon="i-lucide:arrow-right"
                size="sm"
                color="neutral"
                variant="outline"
                class=" lg:w-[49%] w-[48%] lg:text-md text-sm justify-between px-4 text-wrap text-left hover:bg-linear-to-r from-[#006532] to-[#007847] hover:text-white transition-all duration-200"
                @click="createChat(quickChat.label)"
              />
            </div>
          </template>
        </UContainer>
      </div>
    </template>
  </UDashboardPanel>
</template>
