import type { UIMessage } from 'ai'
import { createUIMessageStream, createUIMessageStreamResponse } from 'ai'
import { db, schema } from 'hub:db'
import { and, eq } from 'drizzle-orm'
import { z } from 'zod'

const LANGUAGE_NAMES: Record<string, string> = {
  en: 'English',
  zu: 'isiZulu',
  af: 'Afrikaans',
  xh: 'isiXhosa',
  nso: 'Sepedi',
  tn: 'Setswana',
  st: 'Sesotho',
  ts: 'Xitsonga',
  ss: 'siSwati'
}

// Visually distinguish downloadable content in the Sources block so users
// can identify resources at a glance instead of clicking each link to find
// out what it is. Inferred from the URL's file extension.
function inferFileKind(url: string): { icon: string; label: string } {
  const lower = url.toLowerCase()
  if (lower.endsWith('.pdf')) return { icon: '📄', label: 'PDF' }
  if (lower.endsWith('.doc') || lower.endsWith('.docx')) return { icon: '📘', label: 'Word' }
  if (lower.endsWith('.xls') || lower.endsWith('.xlsx') || lower.endsWith('.csv')) return { icon: '📊', label: 'Spreadsheet' }
  if (lower.endsWith('.ppt') || lower.endsWith('.pptx')) return { icon: '📑', label: 'Slides' }
  return { icon: '🔗', label: 'Link' }
}

defineRouteMeta({
  openAPI: {
    description: 'Chat with Batho Pele AI.',
    tags: ['ai']
  }
})

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const session = await getUserSession(event)

  const { id } = await getValidatedRouterParams(event, z.object({
    id: z.string()
  }).parse)

  const { messages } = await readValidatedBody(event, z.object({
    model: z.string().optional(),
    messages: z.array(z.custom<UIMessage>())
  }).parse)

  const chat = await db.query.chats.findFirst({
    where: () => and(
      eq(schema.chats.id, id as string),
      eq(schema.chats.userId, session.user?.id || session.id)
    ),
    with: {
      messages: true
    }
  })
  if (!chat) {
    throw createError({ statusCode: 404, statusMessage: 'Chat not found' })
  }

  // Extract user query text from last message
  const lastMessage = messages[messages.length - 1]
  const userQuery = lastMessage?.parts
    ?.filter((p: any) => p.type === 'text')
    ?.map((p: any) => p.text)
    ?.join(' ') ?? ''

  // File attachments disabled (R2 not configured)
  const enrichedQuery = userQuery

  // Generate title from first message if not set
  if (!chat.title) {
    const firstMessage = messages[0]
    const firstText = firstMessage?.parts
      ?.filter((p: any) => p.type === 'text')
      ?.map((p: any) => p.text)
      ?.join(' ') ?? 'New chat'
    const title = firstText.slice(0, 30).trim()
    await db.update(schema.chats).set({ title }).where(eq(schema.chats.id, id as string))
  }

  // Save incoming user message
  if (lastMessage?.role === 'user' && messages.length > 1) {
    await db.insert(schema.messages).values({
      chatId: id as string,
      role: 'user',
      parts: lastMessage.parts
    })
  }

  // Call DPSA Python pipeline
  let pipelineResult: any
  try {
    pipelineResult = await $fetch(`${config.public.apiBase}/chat`, {
      method: 'POST',
      body: {
        query: enrichedQuery,
        session_id: id,
        images: undefined
      }
    })
  }
  catch {
    throw createError({ statusCode: 502, statusMessage: 'DPSA pipeline unavailable. Ensure the Python API is running on port 8000.' })
  }

  // Build full response text
  const parts: string[] = [pipelineResult.response]

  if (pipelineResult.source_links?.length > 0) {
    parts.push('\n\n**Sources:**')
    for (const src of pipelineResult.source_links) {
      const kind = inferFileKind(src.url)
      parts.push(`- ${kind.icon} **${kind.label}** — [${src.title}](${src.url})`)
    }
  }

  if (pipelineResult.followups?.length > 0) {
    parts.push('\n\n**You might also ask:**')
    for (const q of pipelineResult.followups) {
      parts.push(`- ${q}`)
    }
  }

  // Verification footer: surface detected language. The Python pipeline
  // already refuses below 0.75 confidence (see LOW_CONFIDENCE_THRESHOLD in
  // demo/pipeline.py), so the confidence percentage is no longer shown --
  // any answer that reaches the user has already passed the threshold.
  const langCode = pipelineResult.language || 'en'
  const langName = LANGUAGE_NAMES[langCode] || langCode
  parts.push(`\n\n---\n*Detected language: ${langName}*`)

  const fullText = parts.join('\n')

  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
      const textId = crypto.randomUUID()
      writer.write({ type: 'text-start', id: textId })
      writer.write({ type: 'text-delta', id: textId, delta: fullText })
      writer.write({ type: 'text-end', id: textId })
    },
    onFinish: async ({ messages: finishedMessages }) => {
      await db.insert(schema.messages).values(finishedMessages.map(message => ({
        chatId: chat.id,
        role: message.role as 'user' | 'assistant',
        parts: message.parts
      })))
    }
  })

  return createUIMessageStreamResponse({ stream })
})
