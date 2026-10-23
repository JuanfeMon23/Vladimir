<script setup lang="ts">
definePageMeta({ layout: 'default', leo: { tag: SETTINGS_TAGS.view } })

const admin = useSettingsScreen()
</script>

<template>
  <UiSettingsPanel :admin="admin" />
</template>
