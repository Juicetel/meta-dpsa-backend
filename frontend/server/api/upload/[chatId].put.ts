export default defineEventHandler(async () => {
  throw createError({
    statusCode: 503,
    statusMessage: 'File uploads are temporarily disabled'
  })
})
