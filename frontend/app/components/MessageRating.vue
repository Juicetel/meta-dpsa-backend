<script setup lang="ts">
const props = defineProps<{
  messageId: string
  initialRating?: 'up' | 'down' | null
  initialComment?: string | null
}>()

const toast = useToast()
const { csrf, headerName } = useCsrf()
const api = useApi()

const currentRating = ref<'up' | 'down' | null>(props.initialRating ?? null)
const showCommentBox = ref(false)
const comment = ref(props.initialComment ?? '')
const saving = ref(false)

async function persist(rating: 'up' | 'down', commentToSend: string | null) {
  saving.value = true
  try {
    await $fetch(api(`/api/messages/${props.messageId}/rating`), {
      method: 'PUT',
      headers: { [headerName]: csrf },
      body: { rating, comment: commentToSend ?? undefined }
    })
  } catch (err) {
    toast.add({
      title: 'Could not save your rating',
      icon: 'i-lucide-alert-circle',
      color: 'error',
      duration: 4000
    })
    throw err
  } finally {
    saving.value = false
  }
}

async function rate(rating: 'up' | 'down') {
  if (currentRating.value === rating) return
  const previous = currentRating.value
  currentRating.value = rating
  showCommentBox.value = true
  try {
    await persist(rating, comment.value.trim() || null)
  } catch {
    currentRating.value = previous
  }
}

async function saveComment() {
  if (!currentRating.value) return
  try {
    await persist(currentRating.value, comment.value.trim() || null)
    toast.add({
      title: 'Thanks for the feedback',
      icon: 'i-lucide-check',
      color: 'success',
      duration: 2000
    })
    showCommentBox.value = false
  } catch {
    // toast already shown by persist()
  }
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="flex items-center gap-1">
      <UButton
        icon="i-lucide-thumbs-up"
        size="sm"
        variant="ghost"
        :color="currentRating === 'up' ? 'success' : 'neutral'"
        :disabled="saving"
        aria-label="Helpful"
        @click="rate('up')"
      />
      <UButton
        icon="i-lucide-thumbs-down"
        size="sm"
        variant="ghost"
        :color="currentRating === 'down' ? 'error' : 'neutral'"
        :disabled="saving"
        aria-label="Not helpful"
        @click="rate('down')"
      />
    </div>

    <div v-if="showCommentBox" class="flex flex-col gap-2 max-w-md">
      <UTextarea
        v-model="comment"
        placeholder="Optional: tell us why"
        :rows="2"
        :maxlength="1000"
        size="sm"
        autoresize
      />
      <div class="flex items-center gap-2">
        <UButton
          size="xs"
          variant="solid"
          color="neutral"
          :loading="saving"
          @click="saveComment"
        >
          Save
        </UButton>
        <UButton
          size="xs"
          variant="ghost"
          color="neutral"
          :disabled="saving"
          @click="showCommentBox = false"
        >
          Skip
        </UButton>
      </div>
    </div>
  </div>
</template>
