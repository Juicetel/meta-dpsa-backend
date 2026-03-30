<script setup lang="ts">
// const { loggedIn } = useUserSession()

</script>

<template>
  <UTooltip
    :content="{
      side: 'top'
    }"
  >
  <!-- :text="!loggedIn ? 'You need to be logged in to upload files' : ''" -->
  <UButton
  icon="i-lucide:mic"
  variant="ghost"
  color="neutral"
  size="sm"
  
  />
</UTooltip>
    <!-- :disabled="!loggedIn" -->
</template>
