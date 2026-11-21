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
    cancelSubscription
} from './modules/billing.js';

function wireInteractiveElements() {
    // Navigation Action Buttons
    const navAuth = document.getElementById('nav-auth-button');
    if (navAuth) navAuth.addEventListener('click', () => showAuthPanel('login'));

    const navTrial = document.getElementById('nav-trial-btn');
    if (navTrial) navTrial.addEventListener('click', () => showAuthPanel('register'));

    const navAudit = document.getElementById('nav-audit-btn');
    if (navAudit) navAudit.addEventListener('click', () => openAuditLedgerModal());

    // Hero Guest Action Buttons
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

async function bootstrap() {
    // 1. Initialize component controllers and listeners with independent fail-safes
    try { initAuth(); } catch (err) { console.error('[MarketLens Portal] initAuth error:', err); }
    try { initValuation(); } catch (err) { console.error('[MarketLens Portal] initValuation error:', err); }
    try { initBilling(); } catch (err) { console.error('[MarketLens Portal] initBilling error:', err); }
    try { initCharts(null); } catch (err) { console.error('[MarketLens Portal] initCharts error:', err); }
    try { wireInteractiveElements(); } catch (err) { console.error('[MarketLens Portal] wireInteractiveElements error:', err); }

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
