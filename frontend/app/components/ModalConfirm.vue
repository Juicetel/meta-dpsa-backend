<script setup lang="ts">
defineProps<{
  title: string
  description: string
}>()

const emit = defineEmits<{ close: [boolean] }>()
</script>

<template>
  <UModal
    :title="title"
    :description="description"
    :ui="{
      footer: 'flex-row-reverse justify-start'
    }"
    :close="false"
    :dismissible="false"
  >
    <template #footer>
      <UButton
        label="Delete"
        class="bg-[#006532] text-white border border-[#006532] hover:bg-[#005c33] focus:bg-transparent focus:text-[#006532] focus:outline-none focus-visible:bg-transparent focus-visible:text-[#006532] focus-visible:outline-none active:bg-transparent active:text-[#006532]"
        @click="emit('close', true)"
      />
      <UButton
        color="neutral"
        variant="ghost"
        label="Cancel"
        @click="emit('close', false)"
      />
    </template>
  </UModal>
</template>
