<script setup lang="ts">
import AppNumberDisplay from './AppNumberDisplay.vue'

defineProps<{ amount: number | string | null; currency?: string }>()
</script>

<template>
  <AppNumberDisplay :value="amount" mode="currency" :currency="currency" :minimum-fraction-digits="2" :maximum-fraction-digits="2" />
</template>
