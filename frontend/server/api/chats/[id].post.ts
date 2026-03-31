import type { UIMessage } from 'ai'
import { createUIMessageStream, createUIMessageStreamResponse } from 'ai'
import { db, schema } from 'hub:db'
import { blob } from 'hub:blob'
import { and, eq } from 'drizzle-orm'
import { z } from 'zod'
import { createRequire } from 'node:module'
const _require = createRequire(import.meta.url)
const pdfParse = _require('pdf-parse') as (buffer: Buffer) => Promise<{ text: string }>

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

defineRouteMeta({
  openAPI: {
    description: 'Chat with Batho Pele AI.',
    tags: ['ai']
  }
})

/**
 * Read a file from NuxtHub blob storage.
 * Handles both local dev (/_hub/blob/{pathname}) and production (full HTTPS URL).
 */
async function readBlobAsBuffer(fileUrl: string): Promise<Buffer | null> {
  try {
    // Local dev: /_hub/blob/{pathname}
    if (fileUrl.startsWith('/_hub/blob/')) {
      const pathname = fileUrl.slice('/_hub/blob/'.length)
      const blobData = await blob.get(pathname)
      if (blobData) {
        return Buffer.from(await blobData.arrayBuffer())
      }
    }
    // Production or fallback: fetch via HTTP
    const arrayBuffer = await $fetch<ArrayBuffer>(fileUrl, { responseType: 'arrayBuffer' })
    return Buffer.from(arrayBuffer)
  }
  catch {
    return null
  }
}

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

  // ── Extract file content from attachments ──────────────────────────────────
  const fileParts = (lastMessage?.parts ?? []).filter((p: any) => p.type === 'file')
  const textContexts: string[] = []
  const imageAttachments: Array<{ base64: string, media_type: string }> = []

  for (const part of fileParts) {
    const fileUrl: string = (part as any).url ?? ''
    const mediaType: string = (part as any).mediaType ?? ''
    if (!fileUrl) continue

    const buffer = await readBlobAsBuffer(fileUrl)
    if (!buffer) continue

    if (mediaType === 'application/pdf') {
      try {
        const pdf = await pdfParse(buffer)
        const text = pdf.text.replace(/\s+/g, ' ').trim().slice(0, 8000)
        if (text) textContexts.push(`[Attached PDF content]:\n${text}`)
      }
      catch {
        textContexts.push('[Attached PDF — could not extract text]')
      }
    }
    else if (mediaType === 'text/csv' || mediaType === 'text/plain') {
      const text = buffer.toString('utf-8').slice(0, 4000)
      if (text) textContexts.push(`[Attached document]:\n${text}`)
    }
    else if (mediaType.startsWith('image/')) {
      imageAttachments.push({
        base64: buffer.toString('base64'),
        media_type: mediaType
      })
    }
  }

  // Build enriched query (PDF/text content appended as context)
  const enrichedQuery = textContexts.length > 0
    ? `${userQuery}\n\n${textContexts.join('\n\n')}`
    : userQuery
  // ──────────────────────────────────────────────────────────────────────────

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
    pipelineResult = await $fetch(`${config.dpsaApiUrl}/chat`, {
      method: 'POST',
      body: {
        query: enrichedQuery,
        session_id: id,
        images: imageAttachments.length > 0 ? imageAttachments : undefined
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
      const safeUrl = src.url.replace(/ /g, '%20')
      parts.push(`- [${src.title}](${safeUrl})`)
    }
  }

  if (pipelineResult.followups?.length > 0) {
    parts.push('\n\n**You might also ask:**')
    for (const q of pipelineResult.followups) {
      parts.push(`- ${q}`)
    }
  }

  const langCode = pipelineResult.language || 'en'
  const langName = LANGUAGE_NAMES[langCode] || langCode
  const confidence = Math.round((pipelineResult.confidence || 0) * 100)
  parts.push(`\n\n---\n*Detected language: ${langName} · Confidence: ${confidence}%*`)

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
