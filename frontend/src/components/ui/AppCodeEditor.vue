<script setup lang="ts">
import { basicSetup } from 'codemirror'
import { css } from '@codemirror/lang-css'
import { html } from '@codemirror/lang-html'
import { oneDark } from '@codemirror/theme-one-dark'
import { EditorState, StateEffect } from '@codemirror/state'
import { EditorView } from '@codemirror/view'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: string
  language?: 'html' | 'css'
}>(), { language: 'html' })
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const host = ref<HTMLElement>()
let view: EditorView | undefined
let themeObserver: MutationObserver | undefined

function extensions() {
  return [
    basicSetup,
    props.language === 'css' ? css() : html(),
    EditorView.lineWrapping,
    EditorView.theme({
      '&': { height: '100%', fontSize: '13px' },
      '.cm-scroller': { overflow: 'auto', fontFamily: 'ui-monospace, monospace' },
      '.cm-content': { minHeight: '100%' },
    }),
    ...(document.documentElement.classList.contains('dark') ? [oneDark] : []),
    EditorView.updateListener.of((update) => {
      if (update.docChanged) emit('update:modelValue', update.state.doc.toString())
    }),
  ]
}

function rebuild() {
  if (!view) return
  view.dispatch({ effects: StateEffect.reconfigure.of(extensions()) })
}

onMounted(() => {
  view = new EditorView({
    state: EditorState.create({ doc: props.modelValue, extensions: extensions() }),
    parent: host.value,
  })
  themeObserver = new MutationObserver(rebuild)
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
})

watch(() => props.modelValue, (value) => {
  if (!view || value === view.state.doc.toString()) return
  view.dispatch({
    changes: { from: 0, to: view.state.doc.length, insert: value },
  })
})

function insert(value: string) {
  if (!view) return
  const selection = view.state.selection.main
  view.dispatch({
    changes: { from: selection.from, to: selection.to, insert: value },
    selection: { anchor: selection.from + value.length },
  })
  view.focus()
}

defineExpose({ insert })

onBeforeUnmount(() => {
  themeObserver?.disconnect()
  view?.destroy()
})
</script>

<template><div ref="host" class="min-h-0 h-full overflow-hidden" /></template>
