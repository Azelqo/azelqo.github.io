# Azelqo

Azelqo is a personal notebook for things worth remembering: what I learn, investigate, test, and think about.

## Public site

- Main blog (Hexo + Materialis): https://azelqo.github.io/
- Previous Hugo blog, preserved as an archive: https://azelqo.github.io/original/

## Stack

- **Hexo 8** — main static blog generator
- **Materialis** — Material Design 3 Expressive theme by [Can1425](https://github.com/Can1425/Hexo-Theme-Materialis)
- **hexo-admin 2.3.0** — local-only writing dashboard
- **Hugo + Stack** — preserved legacy site under `/original/`
- GitHub Pages + GitHub Actions

## Write and edit posts

The main blog's Markdown files are stored in `source/_posts/`.

### Open the admin dashboard

From the repository root:

```bash
npm run admin
```

Open `http://localhost:4000/admin/` in your browser.

The admin environment is intentionally separate: hexo-admin 2.3.0 uses the legacy Hexo 3 API, while the public site is generated with Hexo 8. Both use the same `source/` content directory. The dashboard is local-only and must never be exposed to the public internet.

After editing, stop the admin server and run:

```bash
npm install
npm run build
```

The local public preview can be started with:

```bash
npm run server
```

## Legacy Hugo archive

The original Hugo source, theme configuration, and posts are retained. The deploy workflow builds Hugo separately into `public/original/`, so the former site remains available at `/original/` without mixing its content into the new Hexo blog.

To preview the old Hugo site locally:

```bash
hugo server --baseURL http://localhost:1313/original/ --appendPort=false
```

## Deployment

Every push to `main` builds the Hexo homepage at `/`, builds the retained Hugo site at `/original/`, verifies both outputs, and deploys the combined Pages artifact.
