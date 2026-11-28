/**
 * src/portal/static/main.js
 * Sovereign Native ES-Module Main Entrypoint & DOM Bootstrap.
 */

import { appState } from './modules/api.js';
import {
    initAuth,
    refreshAccount,
    refreshFeatures,
    handleAccountLinks,
    showAuthPanel,
    setAuthMode,
    showPasswordRecovery,
    logout,
    setAccess
} from './modules/auth.js';
import {
    initValuation,
    openAuditLedgerModal
} from './modules/valuation.js';
import {
    initCharts,
    onWaccSliderChange,
    onGrowthSliderChange,
    setSensitivityStep,
    resetSensitivityDefaults
} from './modules/charts.js';
import {
    initBilling,
    refreshPlans,
    refreshERPProviders,
    refreshApiKeys,
    cancelSubscription,
    openEnterpriseConciergeModal
} from './modules/billing.js';

function wireInteractiveElements() {
    // Navigation Action Buttons
    const navAuth = document.getElementById('nav-auth-button');
    if (navAuth) navAuth.addEventListener('click', () => showAuthPanel('login'));

    const navTrial = document.getElementById('nav-trial-btn');
    if (navTrial) navTrial.addEventListener('click', () => showAuthPanel('register'));

    const navAudit = document.getElementById('nav-audit-btn');
    if (navAudit) navAudit.addEventListener('click', () => openAuditLedgerModal());

    const footerAudit = document.getElementById('footer-audit-link');
    if (footerAudit) footerAudit.addEventListener('click', () => openAuditLedgerModal());

    const navPricing = document.getElementById('nav-pricing-link');
    if (navPricing) {
        navPricing.addEventListener('click', (e) => {
            e.preventDefault();
            const pricingSec = document.getElementById('pricing');
            if (pricingSec) {
                pricingSec.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    }

    // Collapsible Institutional Navigation Drawer
    const navDrawer = document.getElementById('nav-drawer');
    const menuToggle = document.getElementById('nav-menu-toggle');
    const drawerClose = document.getElementById('nav-drawer-close');
    const drawerBackdrop = document.getElementById('nav-drawer-backdrop');

    function openDrawer() {
        if (!navDrawer) return;
        navDrawer.classList.remove('hidden');
        navDrawer.setAttribute('aria-hidden', 'false');
        if (menuToggle) menuToggle.setAttribute('aria-expanded', 'true');
    }

    function closeDrawer() {
        if (!navDrawer) return;
        navDrawer.classList.add('hidden');
        navDrawer.setAttribute('aria-hidden', 'true');
        if (menuToggle) menuToggle.setAttribute('aria-expanded', 'false');
    }

    if (menuToggle) menuToggle.addEventListener('click', openDrawer);
    if (drawerClose) drawerClose.addEventListener('click', closeDrawer);
    if (drawerBackdrop) drawerBackdrop.addEventListener('click', closeDrawer);

    // Smooth Horizontal Scroll Arrows for Quick Ticker Chips
    const tickerTrack = document.getElementById('quick-ticker-chips');
    const tickerLeft = document.getElementById('ticker-scroll-left');
    const tickerRight = document.getElementById('ticker-scroll-right');
    if (tickerTrack && tickerLeft && tickerRight) {
        tickerLeft.addEventListener('click', () => {
            tickerTrack.scrollBy({ left: -180, behavior: 'smooth' });
        });
        tickerRight.addEventListener('click', () => {
            tickerTrack.scrollBy({ left: 180, behavior: 'smooth' });
        });
    }

    const enterpriseWrapper = document.getElementById('enterprise-infrastructure-wrapper');
    const toggleEnterpriseBtn = document.getElementById('toggle-enterprise-suite');

    function revealEnterpriseSuite(targetId) {
        if (enterpriseWrapper) {
            enterpriseWrapper.classList.remove('hidden-enterprise-suite');
            if (toggleEnterpriseBtn) {
                toggleEnterpriseBtn.innerHTML = '🏛️ Collapse Enterprise Expansion Infrastructure ↑';
            }
        }
        if (targetId) {
            setTimeout(() => {
                const targetSec = document.getElementById(targetId);
                if (targetSec) targetSec.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 60);
        }
    }

    if (toggleEnterpriseBtn) {
        toggleEnterpriseBtn.addEventListener('click', () => {
            if (!enterpriseWrapper) return;
            const isHidden = enterpriseWrapper.classList.contains('hidden-enterprise-suite');
            if (isHidden) {
                revealEnterpriseSuite('enterprise');
            } else {
                enterpriseWrapper.classList.add('hidden-enterprise-suite');
                toggleEnterpriseBtn.innerHTML = '🏛️ Explore Enterprise Expansion Infrastructure (ERPs, API & Plans) ↓';
            }
        });
    }

    const drawerPricing = document.getElementById('drawer-pricing-link');
    if (drawerPricing) {
        drawerPricing.addEventListener('click', (e) => {
            e.preventDefault();
            closeDrawer();
            revealEnterpriseSuite('pricing');
        });
    }

    const drawerCohort = document.getElementById('drawer-cohort-link');
    if (drawerCohort) {
        drawerCohort.addEventListener('click', (e) => {
            e.preventDefault();
            closeDrawer();
            const cohortSec = document.getElementById('founding-cohort');
            if (cohortSec) cohortSec.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }

    const drawerAudit = document.getElementById('drawer-audit-link');
    if (drawerAudit) {
        drawerAudit.addEventListener('click', (e) => {
            e.preventDefault();
            closeDrawer();
            openAuditLedgerModal();
        });
    }

    const drawerPlatform = document.getElementById('drawer-platform-link');
    if (drawerPlatform) {
        drawerPlatform.addEventListener('click', (e) => {
            e.preventDefault();
            closeDrawer();
            const platSec = document.getElementById('platform');
            if (platSec) platSec.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }

    const drawerErp = document.getElementById('drawer-erp-link');
    if (drawerErp) {
        drawerErp.addEventListener('click', (e) => {
            e.preventDefault();
            closeDrawer();
            revealEnterpriseSuite('enterprise');
        });
    }

    const drawerApi = document.getElementById('drawer-api-link');
    if (drawerApi) {
        drawerApi.addEventListener('click', (e) => {
            e.preventDefault();
            closeDrawer();
            revealEnterpriseSuite('developer-api');
        });
    }

    const drawerTrial = document.getElementById('drawer-trial-btn');
    if (drawerTrial) {
        drawerTrial.addEventListener('click', (e) => {
            e.preventDefault();
            closeDrawer();
            openEnterpriseConciergeModal('fund');
        });
    }

    // Hero Guest Action Buttons
    const heroRun = document.getElementById('btn-hero-run');
    if (heroRun) {
        heroRun.addEventListener('click', () => {
            const liveBtn = document.getElementById('btn-live-scrape');
            const tickerInput = document.getElementById('ticker-search-input');
            const controlCard = document.querySelector('.live-control-card');
            if (controlCard) {
                controlCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                controlCard.style.borderColor = 'var(--accent-odd)';
                controlCard.style.boxShadow = '0 0 24px rgba(59, 130, 246, 0.45)';
                setTimeout(() => {
                    controlCard.style.borderColor = '';
                    controlCard.style.boxShadow = '';
                }, 1600);
            }
            if (tickerInput) tickerInput.focus();
            if (liveBtn) liveBtn.click();
        });
    }

    const inspectSampleBtn = document.getElementById('btn-inspect-sample');
    if (inspectSampleBtn) {
        inspectSampleBtn.addEventListener('click', () => {
            const tickerInput = document.getElementById('ticker-search-input');
            const liveBtn = document.getElementById('btn-live-scrape');
            if (tickerInput) tickerInput.value = 'NVDA';
            const controlCard = document.querySelector('.live-control-card');
            if (controlCard) controlCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
            if (liveBtn) liveBtn.click();
        });
    }

    const cohortBtn = document.getElementById('btn-join-cohort');
    if (cohortBtn) {
        cohortBtn.addEventListener('click', () => {
            openEnterpriseConciergeModal('fund');
        });
    }

    // Mobile Sticky Dock Action
    const mobileRun = document.getElementById('btn-mobile-run-valuation');
    if (mobileRun) {
        mobileRun.addEventListener('click', () => {
            const liveBtn = document.getElementById('btn-live-scrape');
            const tickerInput = document.getElementById('ticker-search-input');
            const controlCard = document.querySelector('.live-control-card');
            if (controlCard) {
                controlCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            if (tickerInput && !tickerInput.value.trim()) {
                tickerInput.focus();
            }
            if (liveBtn) liveBtn.click();
        });
    }

    // Scrolltide Fanned Scenario Deck Interaction
    const scrolltideCards = document.querySelectorAll('.scrolltide-card');
    scrolltideCards.forEach(card => {
        card.addEventListener('click', () => {
            scrolltideCards.forEach(c => c.classList.remove('active'));
            card.classList.add('active');
        });
    });

    const heroTrial = document.getElementById('btn-guest-trial');
    if (heroTrial) heroTrial.addEventListener('click', () => showAuthPanel('register'));

    const heroSignin = document.getElementById('btn-guest-signin');
    if (heroSignin) heroSignin.addEventListener('click', () => showAuthPanel('login'));

    // Account Actions
    const logoutBtn = document.getElementById('btn-logout');
    if (logoutBtn) logoutBtn.addEventListener('click', logout);

    const cancelSubBtn = document.getElementById('cancel-subscription');
    if (cancelSubBtn) cancelSubBtn.addEventListener('click', cancelSubscription);

    // Auth Panel Controls
    const regTab = document.getElementById('register-tab');
    if (regTab) regTab.addEventListener('click', () => setAuthMode('register'));

    const logTab = document.getElementById('login-tab');
    if (logTab) logTab.addEventListener('click', () => setAuthMode('login'));

    const forgotBtn = document.getElementById('forgot-password-button');
    if (forgotBtn) forgotBtn.addEventListener('click', showPasswordRecovery);

    // Sensitivity Heatmap Sliders & Buttons
    const resetSensBtn = document.getElementById('btn-reset-sens');
    if (resetSensBtn) resetSensBtn.addEventListener('click', resetSensitivityDefaults);

    const waccSlider = document.getElementById('wacc-slider');
    if (waccSlider) waccSlider.addEventListener('input', (e) => onWaccSliderChange(e.target.value));

    const growthSlider = document.getElementById('growth-slider');
    if (growthSlider) growthSlider.addEventListener('input', (e) => onGrowthSliderChange(e.target.value));

    const step25 = document.getElementById('step-btn-25');
    if (step25) step25.addEventListener('click', () => setSensitivityStep(25));

    const step50 = document.getElementById('step-btn-50');
    if (step50) step50.addEventListener('click', () => setSensitivityStep(50));

    const step100 = document.getElementById('step-btn-100');
    if (step100) step100.addEventListener('click', () => setSensitivityStep(100));
}

function initGlassSpotlight() {
    let ticking = false;
    document.addEventListener('mousemove', (e) => {
        if (!ticking) {
            window.requestAnimationFrame(() => {
                const cards = document.querySelectorAll('.bento-cell, .plan-card');
                cards.forEach(card => {
                    const rect = card.getBoundingClientRect();
                    const x = e.clientX - rect.left;
                    const y = e.clientY - rect.top;
                    if (x >= -250 && x <= rect.width + 250 && y >= -250 && y <= rect.height + 250) {
                        card.style.setProperty('--mouse-x', `${x}px`);
                        card.style.setProperty('--mouse-y', `${y}px`);
                    }
                });
                ticking = false;
            });
            ticking = true;
        }
    }, { passive: true });
}

function initLenisAndGSAP() {
    const prefersReducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) return;

    // 1. Initialize Lenis Smooth Inertial Scroll
    if (typeof window.Lenis !== 'undefined') {
        try {
            const lenis = new window.Lenis({
                duration: 1.15,
                easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
                orientation: 'vertical',
                gestureOrientation: 'vertical',
                smoothWheel: true,
                wheelMultiplier: 1.0,
                touchMultiplier: 1.25,
            });
            window.__lenis = lenis;

            function raf(time) {
                lenis.raf(time);
                requestAnimationFrame(raf);
            }
            requestAnimationFrame(raf);

            // Synchronize Lenis with GSAP ScrollTrigger
            if (typeof window.gsap !== 'undefined' && typeof window.ScrollTrigger !== 'undefined') {
                window.gsap.registerPlugin(window.ScrollTrigger);
                lenis.on('scroll', window.ScrollTrigger.update);
                window.gsap.ticker.add((time) => {
                    lenis.raf(time * 1000);
                });
                window.gsap.ticker.lagSmoothing(0);
            }
        } catch (lenisErr) {
            console.warn('[MarketLens Portal] Lenis initialization notice:', lenisErr);
        }
    }

    // 2. Initialize GSAP Kinetic Animations & 3D Physics
    if (typeof window.gsap !== 'undefined') {
        try {
            const gsap = window.gsap;

            // Staggered Hero Entrance
            gsap.from('.hero-badge', { opacity: 0, y: -18, duration: 0.75, ease: 'power3.out' });
            gsap.from('.hero-title', { opacity: 0, y: 32, duration: 0.95, delay: 0.1, ease: 'power4.out' });
            gsap.from('.hero-desc', { opacity: 0, y: 22, duration: 0.85, delay: 0.22, ease: 'power3.out' });
            gsap.from('.hero-capabilities-grid .hero-cap-card', {
                opacity: 0,
                y: 20,
                duration: 0.75,
                stagger: 0.08,
                delay: 0.32,
                ease: 'power3.out'
            });
            gsap.from('.scrolltide-deck-wrapper', {
                opacity: 0,
                scale: 0.96,
                y: 25,
                duration: 1.0,
                delay: 0.42,
                ease: 'back.out(1.2)'
            });
            gsap.from('.bento-hero-right', {
                opacity: 0,
                x: 35,
                duration: 0.95,
                delay: 0.3,
                ease: 'power3.out'
            });

            // Interactive 3D Cursor Physics on the Fanned Scenario Deck
            const deckWrapper = document.querySelector('.scrolltide-deck-wrapper');
            const fannedContainer = document.getElementById('scrolltide-deck');
            if (deckWrapper && fannedContainer && window.innerWidth > 768) {
                deckWrapper.addEventListener('mousemove', (e) => {
                    const rect = deckWrapper.getBoundingClientRect();
                    const x = e.clientX - rect.left - rect.width / 2;
                    const y = e.clientY - rect.top - rect.height / 2;
                    const rotX = -(y / (rect.height / 2)) * 6.5;
                    const rotY = (x / (rect.width / 2)) * 8.5;
                    gsap.to(fannedContainer, {
                        rotateX: rotX,
                        rotateY: rotY,
                        duration: 0.35,
                        ease: 'power2.out',
                        transformPerspective: 1100
                    });
                });
                deckWrapper.addEventListener('mouseleave', () => {
                    gsap.to(fannedContainer, {
                        rotateX: 0,
                        rotateY: 0,
                        duration: 0.65,
                        ease: 'power3.out'
                    });
                });
            }

            // Mark scrollable overlays with data-lenis-prevent so wheel scroll stays inside modals/drawers
            document.querySelectorAll('.nav-drawer-body, .modal-card, .typeahead-dropdown').forEach(el => {
                el.setAttribute('data-lenis-prevent', '');
            });

            // Tactile Magnetic Hover & Single-Color ClickSpark for Action Buttons
            const magnetics = document.querySelectorAll('.primary-button, .btn-live-scrape, .btn-pill-trial');
            magnetics.forEach(btn => {
                btn.addEventListener('mousemove', (e) => {
                    const rect = btn.getBoundingClientRect();
                    const x = e.clientX - rect.left - rect.width / 2;
                    const y = e.clientY - rect.top - rect.height / 2;
                    gsap.to(btn, { x: x * 0.2, y: y * 0.2, duration: 0.2, ease: 'power2.out' });
                });
                btn.addEventListener('mouseleave', () => {
                    gsap.to(btn, { x: 0, y: 0, duration: 0.45, ease: 'elastic.out(1.1, 0.4)' });
                });
                btn.addEventListener('click', (e) => {
                    const colors = ['#059669', '#10B981'];
                    for (let i = 0; i < 8; i++) {
                        const spark = document.createElement('span');
                        const angle = (Math.PI * 2 * i) / 8;
                        spark.style.cssText = `position:fixed;left:${e.clientX}px;top:${e.clientY}px;width:4px;height:4px;border-radius:50%;pointer-events:none;z-index:9999;background:${colors[i % colors.length]};box-shadow:0 0 6px ${colors[i % colors.length]};`;
                        document.body.appendChild(spark);
                        gsap.to(spark, {
                            x: Math.cos(angle) * 26,
                            y: Math.sin(angle) * 26,
                            opacity: 0,
                            scale: 0.2,
                            duration: 0.4,
                            ease: 'power2.out',
                            onComplete: () => spark.remove()
                        });
                    }
                });
            });

            // Kinetic Multi-Layer Background Animations (Scrolltide + Lenis + GSAP)
            const motes = gsap.utils.toArray('.kinetic-mote');
            motes.forEach((mote, idx) => {
                gsap.to(mote, {
                    y: (idx % 2 === 0 ? -45 : 45),
                    x: (idx % 3 === 0 ? 35 : -30),
                    opacity: 0.9,
                    scale: 1.4,
                    duration: 4.5 + (idx % 4) * 1.4,
                    repeat: -1,
                    yoyo: true,
                    ease: 'sine.inOut',
                    delay: idx * 0.35
                });
            });

            if (typeof window.ScrollTrigger !== 'undefined') {
                const bgGrid = document.getElementById('bg-kinetic-grid');
                if (bgGrid) {
                    gsap.to(bgGrid, {
                        y: 90,
                        ease: 'none',
                        scrollTrigger: {
                            trigger: document.body,
                            start: 'top top',
                            end: 'bottom bottom',
                            scrub: 1.2
                        }
                    });
                }
                const auroraRibbon = document.getElementById('bg-aurora-ribbon');
                if (auroraRibbon) {
                    gsap.to(auroraRibbon, {
                        y: 120,
                        rotation: -2,
                        ease: 'none',
                        scrollTrigger: {
                            trigger: document.body,
                            start: 'top top',
                            end: 'bottom bottom',
                            scrub: 1.5
                        }
                    });
                }
            }

            // Smooth ScrollTrigger on Bento Panels
            if (typeof window.ScrollTrigger !== 'undefined') {
                gsap.utils.toArray('.bento-panel').forEach(panel => {
                    gsap.from(panel, {
                        scrollTrigger: {
                            trigger: panel,
                            start: 'top 88%',
                            toggleActions: 'play none none none'
                        },
                        opacity: 0,
                        y: 35,
                        duration: 0.85,
                        ease: 'power3.out'
                    });
                });
            }
        } catch (gsapErr) {
            console.warn('[MarketLens Portal] GSAP animation notice:', gsapErr);
        }
    }
}

async function bootstrap() {
    // 1. Initialize component controllers and listeners with independent fail-safes
    try { initAuth(); } catch (err) { console.error('[MarketLens Portal] initAuth error:', err); }
    try { initValuation(); } catch (err) { console.error('[MarketLens Portal] initValuation error:', err); }
    try { initBilling(); } catch (err) { console.error('[MarketLens Portal] initBilling error:', err); }
    try { initCharts(null); } catch (err) { console.error('[MarketLens Portal] initCharts error:', err); }
    try { wireInteractiveElements(); } catch (err) { console.error('[MarketLens Portal] wireInteractiveElements error:', err); }
    try { initGlassSpotlight(); } catch (err) { console.error('[MarketLens Portal] initGlassSpotlight error:', err); }
    try { initLenisAndGSAP(); } catch (err) { console.error('[MarketLens Portal] initLenisAndGSAP error:', err); }

    // 2. Set default UI states
    try {
        setAuthMode('register');
        setAccess(null);
    } catch (err) {
        console.error('[MarketLens Portal] Default state error:', err);
    }

    // 3. Parallel fetch core portal features and session
    try {
        await Promise.all([
            refreshFeatures(),
            refreshPlans(),
            refreshAccount(),
            refreshERPProviders(),
            refreshApiKeys(),
            handleAccountLinks()
        ]);
    } catch (err) {
        console.error('[MarketLens Portal] Bootstrap initialization notice:', err);
    }

    console.log('[MarketLens Analytics] Terminal interactive controllers armed and ready.');
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrap);
} else {
    bootstrap();
}
