<script setup lang="ts">
const { data: articles } = await useAsyncData('home-articles', () =>
  queryCollection('content').where('path', '!=', '/').order('date', 'DESC').limit(5).all()
)
</script>
<template>
  <div>
    <section class="hero">
      <p class="eyebrow">PERSONAL JOURNAL / 2026</p>
      <h1>考えたことを、<br><em>かたちに残す。</em></h1>
      <p class="intro">学んだこと、試したこと、気になったこと。<br>あとから読み返せるように記録する場所。</p>
      <NuxtLink class="text-link" to="/articles">記事を読む <span>↗</span></NuxtLink>
    </section>
    <section class="latest">
      <div class="section-heading"><p class="eyebrow">LATEST NOTES</p><h2>最近の記録</h2></div>
      <div v-if="articles?.length" class="article-list">
        <NuxtLink v-for="article in articles" :key="article.path" class="article-row" :to="article.path">
          <div><p class="article-date">{{ article.date || 'NOTE' }}</p><h3>{{ article.title }}</h3><p>{{ article.description }}</p></div><span class="arrow">↗</span>
        </NuxtLink>
      </div>
      <div v-else class="empty-state">記事はまだありません。管理画面から最初の記事を作成できます。</div>
    </section>
    <section class="editor-callout"><div><p class="eyebrow">CONTENT STUDIO</p><h2>書くことに集中する。</h2><p>管理画面から記事の作成・編集を試せます。</p></div><a href="/admin" class="button">管理画面を開く ↗</a></section>
  </div>
</template>
