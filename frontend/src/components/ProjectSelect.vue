<script setup lang="ts">
import Select from 'primevue/select'
import { ref, watch } from 'vue'
import { projectsApi, type Project } from '../api'

const props = defineProps<{ customerId?: number | null }>()
const model = defineModel<number | null>()
const projects = ref<Project[]>([])

async function load() {
  const params = props.customerId ? `customer=${props.customerId}&` : ''
  projects.value = (await projectsApi.list(`${params}page_size=500`)).results
}

watch(() => props.customerId, load, { immediate: true })
</script>

<template>
  <Select
    v-model="model"
    :options="projects"
    option-label="name"
    option-value="id"
    filter
    class="w-full"
  />
</template>
