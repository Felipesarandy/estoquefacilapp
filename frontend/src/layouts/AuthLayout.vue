<template>
  <div class="flex min-h-screen items-center justify-center bg-slate-100 px-4 py-8">
    <div class="w-full max-w-md">
      <div class="mb-6 text-center">
        <h1 class="text-3xl font-bold text-emerald-700">EstoqueFácil</h1>
        <p class="mt-1 text-sm text-slate-600">Controle de estoque do haras</p>
      </div>
      <div class="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200 sm:p-8">
        <slot />
      </div>
    </div>
  </div>
</template>
