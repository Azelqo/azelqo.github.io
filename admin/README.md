# Azelqo Admin

This is a local-only editing environment for `hexo-admin`. It uses the same Markdown source directory as the public Hexo 8 site.

## Start

From the repository root:

```bash
npm run admin
```

Then open:

```
http://localhost:4000/admin/
```

Posts and pages are written to the shared `../source` directory. After editing, stop the admin server and run `npm run build` from the repository root to preview the public Materialis site.

## Important

- Do not expose this server to the public internet.
- GitHub Pages only hosts static files; it cannot run the Hexo Admin server.
- The editor runs with the legacy Hexo 3 API required by hexo-admin 2.3.0, separately from the public Hexo 8 generator.
