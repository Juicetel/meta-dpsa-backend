<template>
  <UDashboardNavbar
    class="sticky lg:absolute top-0 inset-x-0 border-b-0 z-10 bg-default/75 backdrop-blur lg:bg-transparent lg:backdrop-blur-none pointer-events-none sm:px-4"
    :ui="{ left: 'pointer-events-auto', right: 'pointer-events-auto' }"
  >
    <template #left>
      <UDashboardSidebarCollapse />
    </template>

    <template #right>
      <UColorModeButton />

      <UModal
        title="How to use Batho Pele AI"
        close-icon="ic:sharp-cancel"
      >
        <UButton
          color="neutral"
          variant="ghost"
          icon="ic:outline-help-outline"
          aria-label="Help"
        />

        <template #body>
          <div class="space-y-5 text-sm text-zinc-700 dark:text-zinc-300">
            <section>
              <h3 class="font-semibold text-zinc-900 dark:text-zinc-100 mb-2">Getting started</h3>
              <ul class="list-disc pl-5 space-y-1.5">
                <li>Type your question into the chat box and press <span class="font-medium">Send</span>.</li>
                <li><span class="font-medium">Be clear and specific about what you are searching for</span> &mdash; the more focused your question, the better the answer.</li>
                <li>Use the <span class="font-medium">Quick Topics</span> or <span class="font-medium">FAQ</span> shortcuts on the home page to explore common subjects.</li>
                <li>Open the side panel to revisit past chats or start a new conversation.</li>
              </ul>
            </section>

            <section>
              <h3 class="font-semibold text-zinc-900 dark:text-zinc-100 mb-2">Tips for better results</h3>
              <ul class="list-disc pl-5 space-y-1.5">
                <li>Mention the policy, document, or topic name where possible.</li>
                <li>Ask one question at a time so the response stays focused.</li>
                <li>If a response isn&rsquo;t quite right, rephrase your question with more detail.</li>
              </ul>
            </section>

            <section class="rounded-md border border-[#006532]/30 bg-[#006532]/5 p-3">
              <h3 class="font-semibold text-[#006532] dark:text-[#3AD389] mb-1">Important notice</h3>
              <p>
                By using Batho Pele AI you agree to the <span class="font-medium">DPSA terms and services</span>. This chatbot is <span class="font-medium">not connected to the internet</span> and can only answer questions based on the information in its knowledge base and what is published on the DPSA website. Anything that is not on the website cannot be answered confidently.
              </p>
            </section>
          </div>
        </template>
      </UModal>

      <UButton
        color="neutral"
        variant="ghost"
        icon="i-lucide-plus"
        to="/"
        class="lg:hidden"
      />

    </template>
  </UDashboardNavbar>
</template>
