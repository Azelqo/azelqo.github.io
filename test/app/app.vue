<template>
  <div class="site-shell">
    <header class="topbar">
      <NuxtLink class="brand" to="/">A<span>.</span></NuxtLink>
      <nav>
        <NuxtLink to="/">ホーム</NuxtLink>
        <NuxtLink to="/articles">記事</NuxtLink>
        <a href="/admin">編集画面</a>
        <a href="https://azelqo.github.io/original/">旧ブログ</a>
      </nav>
    </header>
    <main><NuxtPage /></main>
    <footer><span>AZELQO / NOTES & IDEAS</span><span>© Azelqo</span></footer>
  </div>
</template>
