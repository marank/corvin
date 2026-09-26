<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Column from 'primevue/column'
import AppPageHeader from '../../components/ui/AppPageHeader.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import Tag from 'primevue/tag'
import { templatesApi, type InvoiceTemplate } from '../../api'

const { t } = useI18n()
const router = useRouter()
const rows = ref<InvoiceTemplate[]>([])
const loading = ref(true)

onMounted(async () => {
  rows.value = (await templatesApi.list()).results
  loading.value = false
})
</script>

<template>
  <div>
    <AppPageHeader :title="t('nav.templates')" />
    <AppDataTable :rows="rows" :loading="loading" @row-click="(r: InvoiceTemplate) => router.push(`/templates/${r.id}`)">
      <Column field="name" :header="t('common.name')" />
      <Column field="page_size" :header="t('designer.pageSize')" />
      <Column :header="t('common.status')">
        <template #body="{ data }"><Tag v-if="data.is_default" value="default" severity="info" /></template>
      </Column>
    </AppDataTable>
  </div>
</template>
