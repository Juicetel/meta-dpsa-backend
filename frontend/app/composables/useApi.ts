/**
 * useApi — prefixes app.baseURL onto root-relative paths so client-side
 * $fetch and useFetch calls go through the IIS Application mount point
 * (e.g. /chatbot/api/...) rather than the parent CMS at /api/...
 *
 * Use:
 *   const api = useApi()
 *   const data = await $fetch(api('/api/chats'))
 */
export const useApi = () => {
  const { app } = useRuntimeConfig()
  const base = app.baseURL.replace(/\/+$/, '')
  return (path: string) => base + (path.startsWith('/') ? path : '/' + path)
}
