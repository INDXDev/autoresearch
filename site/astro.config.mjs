// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// Where the site is served decides the `base` path baked into every asset URL:
//   * PUBLIC project pages  -> https://<owner>.github.io/<repo>/  (base "/<repo>/")
//   * PRIVATE pages         -> https://<id>.pages.github.io/      (base "/", ROOT)
// A private repo's Pages live at a random subdomain ROOT, so the repo-derived
// "/<repo>/" base 404s its CSS/JS there. Allow an explicit SITE_BASE override
// (set the repo Variable SITE_BASE=/ for private Pages); otherwise fall back to
// the repo slug for the common public case. SITE_URL optionally overrides the
// canonical origin (used for sitemap/canonical only).
const [owner = '', repo = ''] = (process.env.GITHUB_REPOSITORY || '').split('/');

/** Normalise a base override to a leading+trailing-slashed path, or null. */
function normalizeBase(value) {
  if (value == null || value.trim() === '') return null;
  const trimmed = value.trim();
  if (trimmed === '/') return '/';
  return `/${trimmed.replace(/^\/+|\/+$/g, '')}/`;
}
const base = normalizeBase(process.env.SITE_BASE) ?? (repo ? `/${repo}/` : '/');
const site = process.env.SITE_URL?.trim() || (owner ? `https://${owner}.github.io` : undefined);

// Mirror the content language chosen for the Issues (OUTPUT_LANGUAGE).
const lang = (process.env.OUTPUT_LANGUAGE || 'en').toLowerCase().startsWith('ja') ? 'ja' : 'en';
const title = process.env.SITE_TITLE || 'Auto Research';

const social = repo
  ? [{ icon: 'github', label: 'GitHub', href: `https://github.com/${owner}/${repo}` }]
  : [];

export default defineConfig({
  site,
  base,
  trailingSlash: 'always',
  integrations: [
    starlight({
      title,
      defaultLocale: 'root',
      locales: { root: { label: lang === 'ja' ? '日本語' : 'English', lang } },
      social,
      // theme.css is loaded AFTER custom.css so the AI-designed brand colour
      // (regenerated from site_config.json at build time) overrides the default.
      customCss: ['./src/styles/custom.css', './src/styles/theme.css'],
      // Inject the optional giscus comment box after the page footer.
      components: { Footer: './src/components/Footer.astro' },
      // `items/` is intentionally NOT a sidebar group — those per-item detail
      // pages are reached by clicking a card title, not browsed in the nav.
      sidebar: [
        { label: lang === 'ja' ? 'セクション' : 'Sections', autogenerate: { directory: 'sections' } },
        { label: lang === 'ja' ? '実行' : 'Runs', autogenerate: { directory: 'runs' } },
        { label: lang === 'ja' ? 'リアクション' : 'Reactions', autogenerate: { directory: 'reactions' } },
        { label: lang === 'ja' ? 'タグ' : 'Tags', autogenerate: { directory: 'tags' } },
      ],
    }),
  ],
});
