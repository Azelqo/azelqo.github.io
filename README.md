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

The original hexo-admin 2.3.0 is tied to the legacy Hexo 3 API and Node.js versions below 8. It is isolated in `admin/`; the public blog itself is built with modern Hexo 8.

On Windows with nvm-windows, use a separate legacy Node runtime:

```powershell
nvm install 7.10.1
nvm use 7.10.1
npm run admin
```

Then open `http://localhost:4000/admin/` in your browser. The admin instance and public Hexo 8 generator share the same `source/` directory.

**Security note:** Node.js 7 is end-of-life. Use this only as a local editor on your own computer, never expose port 4000 to the internet, and switch back to a supported Node.js version before running the public Hexo 8 build. If you do not want to use an obsolete Node runtime, hexo-admin 2.3.0 is not a suitable editor; a modern CMS would be needed instead.

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
