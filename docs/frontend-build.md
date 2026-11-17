# Frontend build

`npm ci --prefix frontend` installs the pinned build dependencies.
`npm run build --prefix frontend` runs TypeScript checks and bundles the SPA
with esbuild. Hashed JavaScript/CSS and public PWA assets are written to
`frontend/dist`, which the existing Python backend serves unchanged.

Development: run the backend as usual, then `npm run dev --prefix frontend`.
This watches source files and rebuilds `dist`; open the backend on port 8000
and reload the page after edits. It replaces the Vite port-5173 proxy and React
fast refresh. Restart the watcher after changing `public` or `index.html`.
The production build and CI continue to check TypeScript separately.

## Why the build tool changed

On 2026-11-17, GHSA-fc5q-39xc-vjpf affected all published picomatch releases
through 4.0.7, including the dependency chain of Vite 6.4.5 and current Vite
8.3.8. No patched release was published. The application does not require
glob imports or Vite-specific APIs, so the limited SPA build now uses esbuild
directly. The vulnerable dependency chain is removed, not exempted from audit.
`npm audit --prefix frontend` remains unchanged in CI.

References:
- https://github.com/advisories/GHSA-fc5q-39xc-vjpf
- https://github.com/micromatch/picomatch/issues/234
- https://esbuild.github.io/api/
