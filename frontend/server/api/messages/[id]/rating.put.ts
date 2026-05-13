import { db, schema } from 'hub:db'
import { eq } from 'drizzle-orm'
import { z } from 'zod'

export default defineEventHandler(async (event) => {
  const session = await getUserSession(event)
  const config = useRuntimeConfig()

  const { id: messageId } = await getValidatedRouterParams(event, z.object({
    id: z.string()
  }).parse)

  const { rating, comment } = await readValidatedBody(event, z.object({
    rating: z.enum(['up', 'down']),
    comment: z.string().max(1000).optional()
  }).parse)

  const message = await db.query.messages.findFirst({
    where: () => eq(schema.messages.id, messageId),
    with: { chat: true }
  })

  if (!message) {
    throw createError({ statusCode: 404, statusMessage: 'Message not found' })
  }
  if (message.role !== 'assistant') {
    throw createError({ statusCode: 400, statusMessage: 'Only assistant messages can be rated' })
  }
  if (message.chat.userId !== (session.user?.id || session.id)) {
    throw createError({ statusCode: 403, statusMessage: 'Forbidden' })
  }

  const trimmedComment = comment?.trim() || null

  await db.update(schema.messages)
    .set({ rating, ratingComment: trimmedComment })
    .where(eq(schema.messages.id, messageId))

  // Mirror to backend NDJSON log for observability. Best-effort -- the
  // frontend SQLite write above is the source of truth; if the Python API
  // is unreachable, the user's rating still sticks.
  try {
    await $fetch(`${config.public.apiBase}/feedback`, {
      method: 'POST',
      body: {
        message_id: messageId,
        session_id: message.chatId,
        rating,
        comment: trimmedComment
      }
    })
  } catch {
    // backend unavailable -- swallow so the user-facing rating still succeeds
  }

  return { ok: true, rating, comment: trimmedComment }
})
