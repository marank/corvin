import { computed, ref } from 'vue'
import { ApiError, type Page } from '../api/client'

export interface PaginationState {
  page: number
  pageSize: number
  field: string
  order: 1 | -1
}

export function usePagination(load: () => unknown, defaultOrdering = '') {
  const page = ref(1)
  const pageSize = ref(50)
  const totalRecords = ref(0)
  const loading = ref(false)
  const defaultField = defaultOrdering.replace(/^-/, '')
  const defaultOrder: 1 | -1 = defaultOrdering.startsWith('-') ? -1 : 1
  const sortField = ref(defaultField)
  const sortOrder = ref<1 | -1>(defaultOrder)
  const first = computed(() => (page.value - 1) * pageSize.value)
  const ordering = computed(() =>
    sortField.value ? `${sortOrder.value === -1 ? '-' : ''}${sortField.value}` : '',
  )
  let started = false
  let requestId = 0

  function addTo(params: URLSearchParams) {
    params.set('page', String(page.value))
    params.set('page_size', String(pageSize.value))
    if (ordering.value) params.set('ordering', ordering.value)
    return params
  }

  async function fetchPage<T>(
    request: (query: string) => Promise<Page<T>>,
    params: URLSearchParams = new URLSearchParams(),
  ): Promise<T[] | null> {
    const id = ++requestId
    loading.value = true
    try {
      let response: Page<T>
      try {
        response = await request(addTo(new URLSearchParams(params)).toString())
      } catch (error) {
        if (!(error instanceof ApiError && error.status === 404 && page.value > 1)) throw error
        page.value = 1
        response = await request(addTo(new URLSearchParams(params)).toString())
      }
      if (id !== requestId) return null
      totalRecords.value = response.count
      const lastPage = Math.max(1, Math.ceil(response.count / pageSize.value))
      if (page.value > lastPage) {
        page.value = lastPage
        return fetchPage(request, params)
      }
      return response.results
    } finally {
      if (id === requestId) loading.value = false
    }
  }

  function start() {
    started = true
    return load()
  }

  function onPage(value: { page: number; pageSize: number }) {
    page.value = value.pageSize === pageSize.value ? value.page : 1
    pageSize.value = value.pageSize
    load()
  }

  function onSort(value: { field: string; order: 1 | -1 }) {
    sortField.value = value.field
    sortOrder.value = value.order
    page.value = 1
    load()
  }

  function onRestore(value: PaginationState) {
    page.value = Math.max(1, value.page)
    pageSize.value = value.pageSize
    sortField.value = value.field || defaultField
    sortOrder.value = value.field ? value.order : defaultOrder
    if (started) load()
  }

  function refresh() {
    page.value = 1
    load()
  }

  return {
    page,
    pageSize,
    totalRecords,
    loading,
    sortField,
    sortOrder,
    first,
    ordering,
    fetchPage,
    start,
    onPage,
    onSort,
    onRestore,
    refresh,
  }
}
