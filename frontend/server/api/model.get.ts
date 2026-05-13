defineRouteMeta({
  openAPI: {
    description: 'Returns the AI model currently running in the DPSA Python pipeline.',
    tags: ['ai']
  }
})

function formatModel(raw: string): string {
  const name = (raw.split('/').pop() || raw).toLowerCase()
  const match = name.match(/^llama-?(\d+(?:\.\d+)?)-?(.*)$/)
  if (!match) return raw
  const version = match[1]
  const rest = match[2]
  const size = rest.match(/(\d+)b\b/)?.[1]
  const variant = rest.split('-').find(p => p && !/^\d+b$/.test(p) && !/^\d+e$/.test(p) && p !== 'instruct' && p !== 'versatile' && p !== 'instant')
  const variantLabel = variant ? ` ${variant.charAt(0).toUpperCase() + variant.slice(1)}` : ''
  return size ? `Llama ${version}${variantLabel} ${size}B` : `Llama ${version}${variantLabel}`
}

export default defineCachedEventHandler(async () => {
  const config = useRuntimeConfig()
  try {
    const health = await $fetch<{ text_model?: string }>(`${config.public.apiBase}/health`)
    const raw = health.text_model || ''
    return { raw, label: raw ? formatModel(raw) : 'Unknown model' }
  }
  catch {
    return { raw: '', label: 'Model unavailable' }
  }
}, { maxAge: 60, swr: true })
