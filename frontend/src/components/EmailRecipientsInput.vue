<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Chip from 'primevue/chip'
import InputText from 'primevue/inputtext'

// Several e-mail addresses as chips: typed ones are added on Enter, comma or leaving the
// field; the suggestions (e.g. the customer's contacts) are added with a click.
const props = defineProps<{
  suggestions?: { label: string; email: string }[]
  inputId?: string
}>()
const model = defineModel<string[]>({ required: true })
const { t } = useI18n()
const text = ref('')
const invalid = ref(false)

const offered = computed(() =>
  (props.suggestions ?? []).filter(
    (suggestion) =>
      suggestion.email &&
      !model.value.some((address) => address.toLowerCase() === suggestion.email.toLowerCase()),
  ),
)

function add(address: string) {
  const value = address.trim()
  if (!value) return true
  // A plain check; the server validates for real.
  if (!/^[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+$/.test(value)) return false
  if (!model.value.some((existing) => existing.toLowerCase() === value.toLowerCase()))
    model.value = [...model.value, value]
  return true
}

// Typed or pasted addresses become chips; what is no address stays, as typed if nothing was.
function commit() {
  const parts = text.value.split(/[,;\s]+/).filter(Boolean)
  const rest = parts.filter((part) => !add(part))
  if (rest.length < parts.length) text.value = rest.join(', ')
  invalid.value = !!text.value.trim()
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' || event.key === ',' || event.key === ';') {
    event.preventDefault()
    commit()
  } else if (event.key === 'Backspace' && !text.value && model.value.length) {
    model.value = model.value.slice(0, -1)
  }
}

function remove(address: string) {
  model.value = model.value.filter((existing) => existing !== address)
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <div
      class="flex flex-wrap items-center gap-1 p-1 border rounded-md border-surface-300 dark:border-surface-700"
      :class="{ 'border-red-500!': invalid }"
    >
      <Chip
        v-for="address in model"
        :key="address"
        :label="address"
        removable
        :pt="{
          removeIcon: { role: 'button', 'aria-label': t('common.remove', { name: address }) },
        }"
        @remove="remove(address)"
      />
      <InputText
        :id="inputId"
        v-model="text"
        class="flex-1 min-w-48 border-0! shadow-none!"
        :invalid="invalid"
        :aria-label="t('invoices.recipients')"
        @keydown="onKeydown"
        @blur="commit"
      />
    </div>
    <div v-if="offered.length" class="flex flex-wrap gap-2 text-sm">
      <button
        v-for="suggestion in offered"
        :key="suggestion.email"
        type="button"
        class="text-primary hover:underline"
        @click="add(suggestion.email)"
      >
        + {{ suggestion.label }}
      </button>
    </div>
  </div>
</template>
