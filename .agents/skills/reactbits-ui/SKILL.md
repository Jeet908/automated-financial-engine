---
name: reactbits-ui
description: >-
  Guides installation, MCP setup, and component integration for React Bits (reactbits.dev).
  Use when adding animated React Bits components (text animations, backgrounds, cards, buttons)
  via shadcn/jsrepo CLI, configuring reactbits-dev-mcp-server, or porting React Bits motion
  effects to vanilla HTML/CSS/GSAP portals.
---

# React Bits UI (`reactbits.dev`)

React Bits is an open-source collection of animated, interactive React components (text effects, backgrounds, cards, micro-interactions). Components are installed as owned source code rather than a monolithic package.

## 1. CLI Installation (React / Next.js / Vite Projects)

Verify `package.json` and `react` exist in the workspace before running CLI commands.

### Via shadcn CLI (Recommended)
```bash
npx shadcn@latest add @react-bits/<ComponentName>-<LANG>-<STYLE>
```
Variants: `JS-CSS`, `JS-TW`, `TS-CSS`, `TS-TW` (e.g., `npx shadcn@latest add @react-bits/SplitText-TS-TW`).

### Via jsrepo CLI
```bash
npx jsrepo@latest add https://reactbits.dev/r/<ComponentName>-<LANG>-<STYLE>
```

### Common Peer Dependencies
Depending on the component, install required peer libraries:
- GSAP-powered components (`SplitText`, `ScrollReveal`, `Magnet`): `npm install gsap`
- WebGL / Shader backgrounds (`Aurora`, `Threads`, `Iridescence`, `Silk`): `npm install ogl` or `three`

## 2. MCP Server Setup (AI Agent Discovery)

To let AI assistants search and pull React Bits components directly, add `reactbits-dev-mcp-server` to your MCP config (`mcp_config.json` / `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "reactbits": {
      "command": "npx",
      "args": ["reactbits-dev-mcp-server"],
      "env": {
        "GITHUB_TOKEN": "your_github_token_here"
      }
    }
  }
}
```

## 3. Porting to Vanilla HTML / JS Portals (No `package.json`)

When working in a non-React backend portal (e.g., FastAPI + static HTML/JS):
1. Do **not** initialize an unused `node_modules` folder at the repo root unless a React build pipeline is requested.
2. Port the component's visual & motion architecture directly into CSS + GSAP:
   - **Aurora / Silk / Grid Backgrounds:** Implement with layered radial/linear gradients, `filter: blur(...)`, `will-change: transform`, and GSAP `ScrollTrigger` parallax.
   - **SpotlightCard:** Track `--mouse-x` and `--mouse-y` on `mousemove` and render a radial-gradient border/surface mask via `::before` and `::after`.
   - **Magnet:** Interpolate pointer offset (`x * 0.2`, `y * 0.2`) with `gsap.to(..., { ease: 'elastic.out(1.1, 0.4)' })`.
   - **ShinyText:** Animate `background-position` across a `linear-gradient` with `background-clip: text`.

## 4. Verification
- In React projects: confirm component file exists under `src/components/`, peer dependencies are listed in `package.json`, and build/typecheck passes.
- In vanilla portals: verify `prefers-reduced-motion: reduce` disables heavy transforms and pointer effects remain 60fps.
