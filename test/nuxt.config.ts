export default defineNuxtConfig({
  compatibilityDate: '2026-11-17',
  modules: ['@nuxt/content', 'nuxt-studio'],
  css: ['~/assets/css/main.css'],
  content: { build: { markdown: { toc: { depth: 3, searchDepth: 3 } } } },
  studio: {
    route: '/admin',
    repository: { provider: 'github', owner: 'Azelqo', repo: 'azelqo.github.io', branch: 'main', rootDir: 'test', private: false }
  },
  nitro: { preset: 'cloudflare' },
  devtools: { enabled: false },
  app: { head: { title: 'Azelqo — Test', meta: [
    { name: 'description', content: 'Azelqoの新しいブログ基盤を試すためのプレビューサイト。' },
    { name: 'theme-color', content: '#111318' }
  ] } }
})
