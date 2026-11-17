<script setup lang="ts">
const route = useRoute()
const { data: article } = await useAsyncData(route.path, () =>
  queryCollection('content').path(route.path).first()
)
if (!article.value) throw createError({ statusCode: 404, statusMessage: '記事が見つかりません' })
</script>
<template>
  <article class="prose">
    <NuxtLink to="/articles" class="back-link">← 記事一覧へ</NuxtLink>
    <p class="eyebrow">{{ article.date || 'AZELQO NOTE' }}</p>
    <h1>{{ article.title }}</h1>
    <p class="lead">{{ article.description }}</p>
    <ContentRenderer v-if="article" :value="article" />
  </article>
</template>
