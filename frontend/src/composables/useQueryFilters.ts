import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { customersApi, projectsApi } from '../api'

/**
 * Customer/project filters preset from the URL (?customer=…&project=…), as the
 * "show all" links on customer and project overviews set them, plus their names
 * for the filter chips.
 */
export function useQueryFilters() {
  const query = useRoute().query
  const customer = typeof query.customer === 'string' ? query.customer : null
  const project = typeof query.project === 'string' ? query.project : null
  const names = ref({ customer: '', project: '' })
  if (customer) customersApi.get(customer).then((c) => { names.value.customer = c.name }).catch(() => {})
  if (project) projectsApi.get(project).then((p) => { names.value.project = p.name }).catch(() => {})
  return { customer, project, names }
}
