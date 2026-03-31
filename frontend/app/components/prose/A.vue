<script setup lang="ts">
const props = defineProps<{
  href?: string
}>()

const isExternal = computed(() =>
  !!props.href && (props.href.startsWith('http://') || props.href.startsWith('https://'))
)
</script>

<template>
  <a
    v-bind="$attrs"
    :href="props.href"
    :target="isExternal ? '_blank' : undefined"
    :rel="isExternal ? 'noopener noreferrer' : undefined"
  >
    <slot />
  </a>
</template>
