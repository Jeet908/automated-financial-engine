---
name: lenis-smooth-scroll
description: >-
  Guides installation, configuration, and GSAP ScrollTrigger synchronization for Lenis
  smooth scrolling (lenis.dev). Use when adding inertial smooth scrolling via npm or CDN,
  preventing scroll hijacking inside modals/drawers, or syncing Lenis with GSAP.
---

# Lenis Smooth Scroll (`lenis.dev`)

Lenis provides hardware-friendly inertial smooth scrolling while preserving native browser scrollbars, sticky positioning, and accessibility. *(Note: `@studio-freight/lenis` is deprecated; always use `lenis`.)*

## 1. Installation

### Option A: NPM (Bundled Apps)
```bash
npm install lenis
```
Import both the library and recommended CSS:
```javascript
import Lenis from 'lenis';
import 'lenis/dist/lenis.css';
```

### Option B: CDN (Static / Server-Rendered HTML Portals)
```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/lenis@1.1.18/dist/lenis.css">
<script src="https://cdn.jsdelivr.net/npm/lenis@1.1.18/dist/lenis.min.js"></script>
```

## 2. Core Initialization & GSAP ScrollTrigger Sync

Always synchronize Lenis with GSAP's ticker when `ScrollTrigger` is active so scroll-linked animations stay frame-locked:

```javascript
const lenis = new Lenis({
  duration: 1.15,
  easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
  orientation: 'vertical',
  gestureOrientation: 'vertical',
  smoothWheel: true,
  wheelMultiplier: 1.0,
  touchMultiplier: 1.25,
});

if (window.gsap && window.ScrollTrigger) {
  window.gsap.registerPlugin(window.ScrollTrigger);
  lenis.on('scroll', window.ScrollTrigger.update);
  window.gsap.ticker.add((time) => {
    lenis.raf(time * 1000); // GSAP time is in seconds; Lenis expects ms
  });
  window.gsap.ticker.lagSmoothing(0);
} else {
  function raf(time) {
    lenis.raf(time);
    requestAnimationFrame(raf);
  }
  requestAnimationFrame(raf);
}
```

## 3. Essential Edge-Case Guardrails

- **Modals, Drawers, & Nested Scroll Containers:** Add `data-lenis-prevent` to any scrollable overlay (`.modal-card`, `.nav-drawer-body`, `.typeahead-dropdown`) so wheel events scroll the overlay instead of the page behind it.
- **Pause/Resume on Modal Open:** Call `lenis.stop()` when locking body scroll for a modal and `lenis.start()` when closing.
- **Reduced Motion:** Respect `window.matchMedia('(prefers-reduced-motion: reduce)').matches` by skipping Lenis initialization or setting `smoothWheel: false`.

## 4. Verification
- Confirm `lenis.css` is loaded (prevents `overflow` and `html.lenis-smooth` glitches).
- Verify scrolling over modals/dropdowns does not fight with page scroll.
- Check console for zero `Lenis` or `ScrollTrigger` ticker errors.
