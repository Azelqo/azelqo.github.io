# Azelqo Nuxt Studio test

Isolated Nuxt 4 + Nuxt Content + Nuxt Studio experiment. The existing Hexo/Materialis homepage and Hugo archive are not modified by this app.

## Preview deployment

The GitHub Actions workflow deploys this app to Cloudflare Workers as azelqo-test when the required repository secrets are configured:

- CLOUDFLARE_API_TOKEN — Cloudflare API token with Workers Scripts edit permission
- CLOUDFLARE_ACCOUNT_ID — Cloudflare account ID

After deployment, the preview is available at the Worker URL shown in the Actions deployment output.

## Studio

The editor route is /admin. Production publishing uses GitHub OAuth and commits Markdown content to test/content/ in this repository. Configure these Worker secrets before using the editor:

- STUDIO_GITHUB_CLIENT_ID
- STUDIO_GITHUB_CLIENT_SECRET

Register the GitHub OAuth callback URL using the Nuxt Studio provider documentation for the deployed preview origin.

The app uses Nuxt Studio's official Git integration and authentication, not a third-party CMS.

## Local validation

Run npm install and npm run build from this directory.
