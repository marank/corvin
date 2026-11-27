<script setup lang="ts" generic="T">
import { nextTick, onBeforeUnmount, onMounted, ref, useTemplateRef, watch } from 'vue'
import SelectButton from 'primevue/selectbutton'

// Segmented control: a SelectButton framed like an input, its selection sliding between the
// options. Always one option selected.
const props = defineProps<{
  modelValue: T
  options: { label: string; value: T }[]
  size?: 'small' | 'large'
  fluid?: boolean
}>()
const emit = defineEmits<{ 'update:modelValue': [value: T] }>()

const root = useTemplateRef<{ $el: HTMLElement }>('root')
const indicator = ref<{ left: string; width: string } | null>(null)
// Only a change of selection slides; a resize moves the indicator at once.
const sliding = ref(false)
let slideTimer: ReturnType<typeof setTimeout> | undefined

// Places the indicator over the selected option's content.
function place() {
  const el = root.value?.$el
  const content = el?.querySelector('.p-togglebutton-checked .p-togglebutton-content')
  if (!el || !content) return
  const box = el.getBoundingClientRect()
  const rect = content.getBoundingClientRect()
  indicator.value = {
    left: `${rect.left - box.left - el.clientLeft}px`,
    width: `${rect.width}px`,
  }
}

function slide() {
  sliding.value = true
  clearTimeout(slideTimer)
  slideTimer = setTimeout(() => (sliding.value = false), 250)
  void nextTick(place)
}

function select(value: T) {
  emit('update:modelValue', value)
  slide()
}

watch(() => props.modelValue, slide)
watch(
  () => props.options,
  () => void nextTick(place),
  { deep: true },
)
let observer: ResizeObserver | undefined
onMounted(() => {
  place()
  observer = new ResizeObserver(place)
  if (root.value) observer.observe(root.value.$el)
})
onBeforeUnmount(() => {
  observer?.disconnect()
  clearTimeout(slideTimer)
})
</script>

<template>
  <SelectButton
    ref="root"
    :model-value="modelValue"
    :options="options"
    option-label="label"
    option-value="value"
    :allow-empty="false"
    :size="size"
    :fluid="fluid"
    class="app-segmented"
    :class="{ 'app-segmented-sliding': sliding }"
    :style="indicator ? { '--seg-left': indicator.left, '--seg-width': indicator.width } : {}"
    @update:model-value="select"
  />
</template>

<style scoped>
.app-segmented {
  position: relative;
  isolation: isolate;
  border: 1px solid var(--p-inputtext-border-color);
  background: var(--p-togglebutton-background);
}
.app-segmented::before {
  content: '';
  position: absolute;
  z-index: 0;
  inset-block: var(--p-togglebutton-padding);
  left: var(--seg-left, 0);
  width: var(--seg-width, 0);
  background: var(--p-togglebutton-content-checked-background);
  border: 1px solid var(--p-surface-200);
  box-shadow: var(--p-togglebutton-content-checked-shadow);
}
.app-segmented-sliding::before {
  transition:
    left 0.2s ease,
    width 0.2s ease;
}
.app-segmented :deep(.p-togglebutton) {
  z-index: 1;
  padding-block: calc(var(--p-togglebutton-padding) - 1px);
  background: transparent;
  border-color: transparent;
}
.app-segmented :deep(.p-togglebutton-content) {
  background: transparent !important;
  box-shadow: none !important;
}
:global(.dark) .app-segmented::before {
  border-color: var(--p-surface-600);
}
</style>
