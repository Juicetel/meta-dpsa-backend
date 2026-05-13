<script setup lang="ts">

import { LazyModalConfirm } from '#components'
import type { NavigationMenuItem } from '@nuxt/ui'

const items2: NavigationMenuItem[][] = [[{
  label: 'Home',
  icon: 'i-solar:chat-round-dots-linear',
  to: 'https://www.dpsa.gov.za/',
  target: '_blank',
},
{
  label: 'About Us',
  icon: 'i-material-symbols-light:inbox-text-outline',
  to: 'https://www.dpsa.gov.za/about-us/',
  target: '_blank',
},
{
  label: 'Legislation',
  icon: 'i-lineicons:books-2',
  to: 'https://www.dpsa.gov.za/legislation/',
  target: '_blank',
},
{
  label: 'PAIA',
  icon: 'i-lineicons:books-2',
  to: 'https://www.dpsa.gov.za/paia/',
  target: '_blank',
},
{
  label: 'Policy Updates',
  icon: 'i-lineicons:books-2',
  to: 'https://www.dpsa.gov.za/policy-updates/',
  target: '_blank',
},
{
  label: 'Resource Center',
  icon: 'i-material-symbols-light:inbox-text-outline',
  to: 'https://www.dpsa.gov.za/resource_centre/',
  target: '_blank',
},
{
  label: 'Newsroom',
  icon: 'i-lineicons:books-2',
  to: 'https://www.dpsa.gov.za/newsroom/',
  target: '_blank',
},
{
  label: 'Contact Us',
  icon: 'i-lineicons:books-2',
  to: 'https://www.dpsa.gov.za/contact-us/',
  target: '_blank',
},
{
  label: 'FAQ',
  icon: 'i-lineicons:books-2',
  to: 'https://www.dpsa.gov.za/faq/',
  target: '_blank',
}
]]




const route = useRoute()
const toast = useToast()
const overlay = useOverlay()
const { loggedIn, openInPopup } = useUserSession()
const { csrf, headerName } = useCsrf()

const open = ref(false)

const deleteModal = overlay.create(LazyModalConfirm, {
  props: {
    title: 'Delete chat',
    description: 'Are you sure you want to delete this chat? This cannot be undone.'
  }
})

const { data: chats, refresh: refreshChats } = await useFetch('/api/chats', {
  key: 'chats',
  transform: data => data.map(chat => ({
    id: chat.id,
    label: chat.title || 'Untitled',
    to: `/chat/${chat.id}`,
    icon: 'i-lucide-message-circle',
    createdAt: chat.createdAt
  }))
})

onNuxtReady(async () => {
  const first10 = (chats.value || []).slice(0, 10)
  for (const chat of first10) {
    // prefetch the chat and let the browser cache it
    await $fetch(`/api/chats/${chat.id}`)
  }
})

watch(loggedIn, () => {
  refreshChats()

  open.value = false
})

const { groups } = useChats(chats)

const items = computed(() => groups.value?.flatMap((group) => {
  return [{
    label: group.label,
    type: 'label' as const
  }, ...group.items.map(item => ({
    ...item,
    slot: 'chat' as const,
    icon: undefined,
    class: item.label === 'Untitled' ? 'text-muted' : ''
  }))]
}))

async function deleteChat(id: string) {
  const instance = deleteModal.open()
  const result = await instance.result
  if (!result) {
    return
  }

  await $fetch(`/api/chats/${id}`, {
    method: 'DELETE',
    headers: { [headerName]: csrf }
  })

  toast.add({
    title: 'Chat deleted',
    description: 'Your chat has been deleted',
    icon: 'i-lucide-trash',
    ui: { icon: 'text-[#006532]' },
    progress: { ui: { indicator: 'bg-[#006532]' } }
  })

  refreshChats()

  if (route.params.id === id) {
    navigateTo('/')
  }
}

defineShortcuts({
  c: () => {
    navigateTo('/')
  }
})
</script>

<template>
  <UDashboardGroup unit="rem">
    <UDashboardSidebar
      id="default"
      v-model:open="open"
      :min-size="16"
      :default-size="25"
      collapsible
      resizable
      class="border-r-0 py-4"
    >
      <template #header="{ collapsed }">
        <NuxtLink to="/" class="flex items-end gap-0.5">
          <Logo class="h-8 w-auto shrink-0" />
          <span v-if="!collapsed" class="text-xl font-bold text-highlighted pl-2">BATHO PELE AI</span>
        </NuxtLink>

        <div v-if="!collapsed" class="flex items-center gap-1.5 ms-auto">
          <UDashboardSearchButton collapsed />
        </div>
      </template>

      <template #default="{ collapsed }">
        <div class="flex flex-col gap-1.5">
          <UButton
            v-bind="collapsed ? { icon: 'i-lucide-plus' } : { label: 'New chat' }"
            block
            to="/"
            @click="open = false"
            class="bg-[#006532] text-white border border-[#006532] hover:bg-[#005c33] focus:bg-transparent focus:text-[#006532] focus:outline-none focus-visible:bg-transparent focus-visible:text-[#006532] focus-visible:outline-none active:bg-transparent active:text-[#006532]"
          />

          <template v-if="collapsed">
            <UDashboardSearchButton collapsed />
          </template>
        </div>

        <UNavigationMenu
          v-if="!collapsed"
          :items="items"
          :collapsed="collapsed"
          orientation="vertical"
          :ui="{ link: 'overflow-hidden' }"
        >
          <template #chat-trailing="{ item }">
            <div class="flex -mr-1.25 translate-x-full group-hover:translate-x-0 transition-transform">
              <UButton
                icon="i-lucide-x"
                color="neutral"
                variant="ghost"
                size="xs"
                class="text-muted hover:text-primary hover:bg-accented/50 focus-visible:bg-accented/50 p-0.5"
                tabindex="-1"
                @click.stop.prevent="deleteChat((item as any).id)"
              />
            </div>
          </template>
        </UNavigationMenu>
        
        <h5 v-if="!collapsed" class="text-black dark:text-white">Features</h5>
        <UNavigationMenu
        :collapsed="collapsed"
        :items="items2"
        orientation="vertical"
        />

      </template>

     
    </UDashboardSidebar>

    <UDashboardSearch
      placeholder="Search chats..."
      :groups="[{
        id: 'links',
        items: [{
          label: 'New chat',
          to: '/',
          icon: 'i-lucide-square-pen'
        }]
      }, ...groups]"
    />

    <div class="flex-1 flex m-4 lg:ml-0 rounded-lg ring ring-default bg-default/75 shadow min-w-0">
      <slot />
    </div>
  </UDashboardGroup>
</template>
