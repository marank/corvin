<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  icon: string
  ariaLabel?: string
  severity?: 'primary' | 'danger' | 'secondary'
}>()

defineEmits<{ click: [e: MouseEvent] }>()

const el = ref<HTMLButtonElement>()
const { t } = useI18n()
// Most table buttons are bare icons; give the common ones a name for screen readers.
const label = computed(() => props.ariaLabel
  ?? (props.icon.includes('pi-trash') ? t('common.delete') : props.icon.includes('pi-pencil') ? t('common.edit') : undefined))

function ripple(e: MouseEvent) {
  const btn = el.value
  if (!btn) return
  const rect = btn.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  const span = document.createElement('span')
  span.className = 'icon-btn-ripple'
  span.style.left = `${x}px`
  span.style.top = `${y}px`
  btn.appendChild(span)
  span.addEventListener('animationend', () => span.remove())
}
</script>

<template>
  <button
    ref="el"
    type="button"
    class="icon-btn app-icon-btn"
    :class="severity === 'danger' ? 'icon-btn--danger' : ''"
    :aria-label="label"
    @click="(e: MouseEvent) => { ripple(e); $emit('click', e) }"
  >
    <i :class="icon" />
  </button>
</template>

<style scoped>
/* In a layer so utility classes (hidden, sm:hidden, ...) can override display. */
@layer components {
  .icon-btn {
    position: relative;
    overflow: hidden;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    border: none;
    border-radius: 4px;
    background: transparent;
    color: var(--p-text-color);
    font-size: 0.875rem;
    cursor: pointer;
    transition: transform 0.1s ease;
  }
  .icon-btn:hover {
    transform: scale(1.18);
  }
  .icon-btn:active {
    transform: scale(1.05);
  }
  .icon-btn--danger {
    color: var(--p-red-500);
  }
}
:deep(.icon-btn-ripple) {
  position: absolute;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.25;
  transform: scale(0);
  animation: icon-ripple 0.1s ease-out forwards;
  pointer-events: none;
}
@keyframes icon-ripple {
  to {
    transform: scale(18);
    opacity: 0;
  }
}
</style>
