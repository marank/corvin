<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

// Document preview. HTML previews (by `url` or as `html`) are zoomed out to the frame's
// width, so a whole page is visible instead of being cut off on the right.
const props = defineProps<{ url?: string; html?: string; mode?: 'html' | 'pdf' }>()
const { t } = useI18n()
const frame = ref<HTMLIFrameElement>()

function fit() {
  const root = frame.value?.contentDocument?.documentElement
  if (!root || props.mode === 'pdf') return
  root.style.zoom = ''
  // The space left of the content (body padding) is assumed on the right as well.
  const left = root.ownerDocument.body.firstElementChild?.getBoundingClientRect().left ?? 0
  const scale = root.clientWidth / (root.scrollWidth + Math.max(0, left))
  if (scale < 1) root.style.zoom = String(scale)
}

const observer = new ResizeObserver(fit)
onMounted(() => { if (frame.value) observer.observe(frame.value) })
onBeforeUnmount(() => observer.disconnect())
</script>

<template>
  <iframe
    v-if="mode !== 'pdf'"
    ref="frame"
    :src="html === undefined ? url : undefined"
    :srcdoc="html"
    class="w-full h-full border-0 bg-surface-200 dark:bg-surface-800"
    :title="t('designer.preview')"
    @load="fit"
  />
  <iframe v-else :src="url" class="w-full h-full border-0 bg-surface-200 dark:bg-surface-800" :title="t('designer.preview')" />
</template>
