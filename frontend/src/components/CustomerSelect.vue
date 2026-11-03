<script setup lang="ts">
import Select from 'primevue/select'
import { onMounted, ref } from 'vue'
import { customersApi, type Customer } from '../api'

defineProps<{ placeholder?: string }>()
const model = defineModel<string | null>()
const customers = ref<Customer[]>([])

onMounted(async () => {
  customers.value = (await customersApi.list('page_size=500')).results
})
</script>

<template>
  <Select
    v-model="model"
    :options="customers"
    option-label="name"
    option-value="id"
    :placeholder="placeholder"
    filter
    show-clear
    class="w-full"
  />
</template>
