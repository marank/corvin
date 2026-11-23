<script setup lang="ts">
import Select from 'primevue/select'
import { onMounted, ref } from 'vue'
import { customersApi, type Customer } from '../api'

defineProps<{ placeholder?: string }>()
const emit = defineEmits<{ select: [customer: Customer | null] }>()
const model = defineModel<string | null>()
const customers = ref<Customer[]>([])

onMounted(async () => {
  customers.value = (await customersApi.list('page_size=500')).results
})

function onChange(id: string | null) {
  emit('select', customers.value.find((customer) => customer.id === id) ?? null)
}
</script>

<template>
  <!-- eslint-disable-next-line vuejs-accessibility/form-control-has-label -- a wrapper: the caller labels it (AppFormField or an aria-label that falls through to the Select). -->
  <Select
    v-model="model"
    :options="customers"
    option-label="name"
    option-value="id"
    :placeholder="placeholder"
    filter
    show-clear
    class="w-full"
    @update:model-value="onChange"
  />
</template>
