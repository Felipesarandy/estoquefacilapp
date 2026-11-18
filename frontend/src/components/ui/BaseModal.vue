<script setup>
import { nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  title: { type: String, required: true },
  size: { type: String, default: 'md' }, // sm | md | lg
  closeOnBackdrop: { type: Boolean, default: true },
})
const emit = defineEmits(['update:modelValue', 'close'])

const panel = ref(null)
const titleId = useId()
let previouslyFocused = null

function close() {
  emit('update:modelValue', false)
  emit('close')
}

function onBackdrop() {
  if (props.closeOnBackdrop) close()
}

// Mantém o Tab dentro do diálogo.
function trapFocus(event) {
  const items = panel.value?.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
  )
  if (!items?.length) return
  const first = items[0]
  const last = items[items.length - 1]
  if (event.shiftKey && (document.activeElement === first || document.activeElement === panel.value)) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

watch(
  () => props.modelValue,
  async (open) => {
    if (open) {
      previouslyFocused = document.activeElement
      document.body.style.overflow = 'hidden'
      await nextTick()
      panel.value?.focus()
    } else {
      document.body.style.overflow = ''
      previouslyFocused?.focus?.()
      previouslyFocused = null
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (props.modelValue) document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="fixed inset-0 z-50 flex items-end justify-center overflow-y-auto bg-slate-900/50 p-4 sm:items-center"
      @click.self="onBackdrop"
      @keydown.esc.stop="close"
      @keydown.tab="trapFocus"
    >
      <div
        ref="panel"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        tabindex="-1"
        class="w-full rounded-xl bg-white shadow-xl focus:outline-none"
        :class="{ 'max-w-sm': size === 'sm', 'max-w-lg': size === 'md', 'max-w-2xl': size === 'lg' }"
      >
        <div class="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <h2 :id="titleId" class="text-lg font-semibold text-slate-800">{{ title }}</h2>
          <button
            type="button"
            class="rounded p-1 text-slate-500 hover:text-slate-800 focus-visible:outline-2 focus-visible:outline-emerald-600"
            aria-label="Fechar"
            @click="close"
          >
            <svg class="size-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M5.3 4.3 10 9l4.7-4.7 1 1L11 10l4.7 4.7-1 1L10 11l-4.7 4.7-1-1L9 10 4.3 5.3z" />
            </svg>
          </button>
        </div>
        <div class="px-5 py-4"><slot /></div>
        <div v-if="$slots.footer" class="flex justify-end gap-2 border-t border-slate-200 px-5 py-3">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </Teleport>
</template>
