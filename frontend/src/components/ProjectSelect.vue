<script setup lang="ts">
import Select from 'primevue/select'
import { ref, watch } from 'vue'
import { projectsApi, type Project } from '../api'

const props = defineProps<{ customerId?: string | null; placeholder?: string }>()
const emit = defineEmits<{ select: [project: Project | null] }>()
const model = defineModel<string | null>()
const projects = ref<Project[]>([])

async function load() {
  const params = props.customerId ? `customer=${props.customerId}&` : ''
  projects.value = (await projectsApi.list(`${params}page_size=500`)).results
  // A project of another customer can't stay selected once the customer changes.
  if (model.value && !projects.value.some((project) => project.id === model.value)) model.value = null
}

function onChange(id: string | null) {
  emit('select', projects.value.find((project) => project.id === id) ?? null)
}

watch(() => props.customerId, load, { immediate: true })
</script>

<template>
  <Select
    v-model="model"
    :options="projects"
    option-label="name"
    option-value="id"
    :placeholder="placeholder"
    filter
    show-clear
    class="w-full"
    @update:model-value="onChange"
  />
</template>
