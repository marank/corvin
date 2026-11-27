import { computed, ref } from 'vue'
import { visitsApi, type Visit } from '../../api'

export const tripKey = (visitId: string) => `travel:${visitId}`

// The trips an invoice bills (one line each), and those "Positionen holen" offers: the
// customer's open ones not on the invoice yet, ticked when offered.
export function useInvoiceTrips() {
  const billed = ref<Visit[]>([])
  const open = ref<Visit[]>([])
  const picked = ref(new Set<string>())
  const billedIds = computed(() => billed.value.map((visit) => visit.id))
  const offered = computed(() => open.value.filter((visit) => !billedIds.value.includes(visit.id)))

  let request = 0
  async function load(filters: {
    customer: string
    project: string | null
    dateFrom: string | null
    dateTo: string | null
    invoice: string | null
  }) {
    const current = ++request
    const params = new URLSearchParams({ customer: filters.customer })
    if (filters.project) params.set('project', filters.project)
    if (filters.dateFrom) params.set('date_from', filters.dateFrom)
    if (filters.dateTo) params.set('date_to', filters.dateTo)
    if (filters.invoice) params.set('invoice', filters.invoice)
    const found = await visitsApi.billableTravel(params.toString())
    if (current !== request) return
    open.value = found
    picked.value = new Set(offered.value.map((visit) => visit.id))
  }

  function toggle(visit: Visit) {
    const next = new Set(picked.value)
    if (!next.delete(visit.id)) next.add(visit.id)
    picked.value = next
  }

  function takeOver() {
    billed.value = [...billed.value, ...offered.value.filter((v) => picked.value.has(v.id))]
  }

  function remove(visitId: string) {
    billed.value = billed.value.filter((visit) => visit.id !== visitId)
  }

  // The request's trips, with the user's texts by line key.
  function specs(texts: Record<string, string>) {
    return billed.value.map((visit) => ({
      visit_id: visit.id,
      description: texts[tripKey(visit.id)] ?? null,
    }))
  }

  return { billed, billedIds, offered, picked, load, toggle, takeOver, remove, specs }
}
