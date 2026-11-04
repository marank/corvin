import { onMounted, ref } from 'vue'

/** Runs a detail page's load on mount; the returned flag turns true when it throws. */
export function useLoadFailed(load: () => Promise<unknown>) {
  const failed = ref(false)
  onMounted(async () => {
    try {
      await load()
    } catch {
      failed.value = true
    }
  })
  return failed
}
