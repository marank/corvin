import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

/**
 * The open tab of a page, kept in the URL (?tab=…) so links, reloads and back buttons
 * land on it. The default tab leaves the URL without the parameter; switching tabs
 * replaces the history entry instead of adding one per click.
 */
export function useTabQuery<T extends string>(defaultTab: T, tabs: readonly T[], param = 'tab') {
  const route = useRoute()
  const router = useRouter()
  return computed<T>({
    get: () => {
      const value = route.query[param]
      return typeof value === 'string' && (tabs as readonly string[]).includes(value)
        ? (value as T)
        : defaultTab
    },
    set: (value) => {
      void router.replace({
        query: { ...route.query, [param]: value === defaultTab ? undefined : value },
      })
    },
  })
}
