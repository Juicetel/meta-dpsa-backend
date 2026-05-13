<script setup lang="ts">
const props = defineProps<{
  href?: string
}>()

const isExternal = computed(() =>
  !!props.href && (props.href.startsWith('http://') || props.href.startsWith('https://'))
)

const DOCUMENT_EXTENSIONS = [
  '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
  '.txt', '.csv', '.odt', '.ods', '.odp', '.rtf'
]

const isDocument = computed(() => {
  if (!props.href) return false
  try {
    const url = new URL(props.href, 'http://placeholder.local')
    const pathname = url.pathname.toLowerCase()
    return DOCUMENT_EXTENSIONS.some(ext => pathname.endsWith(ext))
  } catch {
    const lower = props.href.toLowerCase()
    return DOCUMENT_EXTENSIONS.some(ext => lower.includes(ext))
  }
})
</script>

<template>
  <a
    v-bind="$attrs"
    :href="props.href"
    :target="isExternal ? '_blank' : undefined"
    :rel="isExternal ? 'noopener noreferrer' : undefined"
    class="text-blue-600 dark:text-blue-400 underline hover:text-blue-800 dark:hover:text-blue-300 break-all"
  >
    <UIcon
      v-if="isDocument"
      name="material-symbols-light:document-search"
      class="inline-block align-text-bottom size-4 mr-1"
    />
    <slot />
  </a>
</template>
