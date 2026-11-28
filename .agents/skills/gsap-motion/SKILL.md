---
name: gsap-motion
description: >-
  Guides installation, animation architecture, ScrollTrigger parallax, and performance
  best practices for GSAP (gsap.com). Use when building hero entrances, scroll-driven
  animations, 3D card tilt physics, magnetic buttons, or syncing GSAP with Lenis/React.
---

# GSAP Motion Platform (`gsap.com`)

GSAP (GreenSock Animation Platform) is the industry-standard JavaScript animation engine for 60fps UI choreography, `ScrollTrigger` timelines, and interactive physics.

## 1. Installation

### Option A: NPM (React / Vite / Next.js)
```bash
npm install gsap
```
```javascript
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);
```

### Option B: CDN (Static / Server-Rendered HTML Portals)
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"></script>
```

## 2. Core Production Patterns

### A. Staggered Hero & Bento Entrance
```javascript
gsap.from('.hero-title', { opacity: 0, y: 32, duration: 0.9, ease: 'power4.out' });
gsap.from('.hero-cap-card', {
  opacity: 0,
  y: 20,
  duration: 0.75,
  stagger: 0.08,
  ease: 'power3.out',
});
```

### B. Interactive 3D Tilt & Magnetic Hover
Always scope pointer physics to desktop (`window.innerWidth > 768` and `(hover: hover)`):
```javascript
btn.addEventListener('mousemove', (e) => {
  const rect = btn.getBoundingClientRect();
  const x = e.clientX - rect.left - rect.width / 2;
  const y = e.clientY - rect.top - rect.height / 2;
  gsap.to(btn, { x: x * 0.2, y: y * 0.2, duration: 0.2, ease: 'power2.out' });
});
btn.addEventListener('mouseleave', () => {
  gsap.to(btn, { x: 0, y: 0, duration: 0.45, ease: 'elastic.out(1.1, 0.4)' });
});
```

### C. ScrollTrigger Parallax on Background Layers
```javascript
gsap.to('#bg-kinetic-grid', {
  y: 90,
  ease: 'none',
  scrollTrigger: {
    trigger: document.body,
    start: 'top top',
    end: 'bottom bottom',
    scrub: 1.2,
  },
});
```

### D. React Cleanup (`gsap.context()`)
When used inside React `useEffect`, wrap animations in `gsap.context()` and return `() => ctx.revert()` to prevent double-animation in React 18+ StrictMode.

## 3. Performance & Accessibility Rules
- Animate only GPU-composited properties (`transform` / `x`, `y`, `scale`, `rotation`, `opacity`). Avoid animating `top`, `left`, `width`, or `height`.
- Add `will-change: transform` sparingly to actively scrubbed background layers.
- Guard animations with `prefers-reduced-motion: reduce` checks so motion-sensitive users get instant state transitions.
