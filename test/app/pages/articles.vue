<script setup lang="ts">
const { data: articles } = await useAsyncData('all-articles', () =>
  queryCollection('content').where('path', '!=', '/').order('date', 'DESC').all()
)
</script>
<template>
  <section class="page-heading"><p class="eyebrow">ARCHIVE</p><h1>記事一覧</h1><p>考えたことや、覚えておきたいこと。</p></section>
  <div class="article-list">
    <NuxtLink v-for="article in articles" :key="article.path" class="article-row" :to="article.path">
      <div><p class="article-date">{{ article.date || 'NOTE' }}</p><h2>{{ article.title }}</h2><p>{{ article.description }}</p></div><span class="arrow">↗</span>
    </NuxtLink>
  </div>
</template>
