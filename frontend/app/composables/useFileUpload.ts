// File uploads temporarily disabled (R2 not configured)
export function useFileUploadWithStatus(_chatId: string) {
  const files = ref<FileWithStatus[]>([])
  const dropzoneRef = ref<HTMLElement | null>(null)

  return {
    dropzoneRef,
    isDragging: ref(false),
    open: () => {},
    files,
    isUploading: computed(() => false),
    uploadedFiles: computed(() => [] as Array<{ type: 'file', mediaType: string, url: string }>),
    addFiles: async (_newFiles: File[]) => {},
    removeFile: (_id: string) => {},
    clearFiles: () => {}
  }
}
