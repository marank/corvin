<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'

// A form split into its fields (#details) and one long text (#report, a Markdown editor).
// The text tab is as tall as the fields, so switching keeps the size of the dialog or page;
// the details are measured before they leave the page. #report gets `fill` once that height
// is known: the editor then fills it and scrolls inside. Both tabs are at least 18rem high,
// so a short form still leaves room to write.
defineProps<{
  reportLabel: string
  // In a dialog: pulled up to its title, whose padding already separates the two.
  dialog?: boolean
}>()
const { t } = useI18n()
const tab = ref<'details' | 'report'>('details')
const details = ref<HTMLElement>()
const height = ref<number>()
watch(
  tab,
  () => {
    if (details.value?.offsetHeight) height.value = details.value.offsetHeight
  },
  { flush: 'pre' },
)
</script>

<template>
  <Tabs v-model:value="tab" :class="{ '-mt-3': dialog }">
    <TabList>
      <Tab value="details" :class="{ 'pt-2!': dialog }">{{ t('common.details') }}</Tab>
      <Tab value="report" :class="{ 'pt-2!': dialog }">{{ reportLabel }}</Tab>
    </TabList>
    <TabPanels class="px-0! pb-0!">
      <TabPanel value="details">
        <div ref="details" class="min-h-72"><slot name="details" /></div>
      </TabPanel>
      <TabPanel value="report">
        <div :style="height ? { height: `${height}px` } : undefined">
          <slot name="report" :fill="!!height" />
        </div>
      </TabPanel>
    </TabPanels>
  </Tabs>
</template>
