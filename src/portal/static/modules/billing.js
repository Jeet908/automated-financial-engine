/**
 * src/portal/static/modules/billing.js
 * Dual-Rail Global Billing (Stripe + Razorpay), ERP Mesh & Scoped API Keys.
 */

import { apiRequest, appState, csrfHeaders, showToast } from './api.js';
import { refreshAccount, showAuthPanel, setAuthFeedback } from './auth.js';
import { apiJobResult, markAllCompleted, renderLiveDashboard, setStep } from './valuation.js';

export function detectUserCurrency() {
    try {
        const timeZone = (Intl.DateTimeFormat().resolvedOptions().timeZone || '').toLowerCase();

        // 1. India & South Asian Region -> INR
        if (timeZone.includes('kolkata') || timeZone.includes('calcutta') || timeZone.includes('india') || timeZone.includes('asia/colombo') || timeZone.includes('asia/kathmandu')) {
            return { code: 'INR', symbol: '₹', region: 'India (Domestic Schedule III)' };
        }

        // 2. United Kingdom -> GBP
        if (timeZone.includes('london')) {
            return { code: 'GBP', symbol: '£', region: 'United Kingdom (Companies House)' };
        }

        // 3. Europe / Eurozone -> EUR
        const euroZones = [
            'paris', 'berlin', 'rome', 'madrid', 'amsterdam', 'brussels', 'vienna',
            'dublin', 'lisbon', 'helsinki', 'athens', 'warsaw', 'prague', 'stockholm',
            'copenhagen', 'oslo', 'zurich', 'europe'
        ];
        if (euroZones.some(city => timeZone.includes(city))) {
            return { code: 'EUR', symbol: '€', region: 'Europe (IFRS / Eurozone)' };
        }

        // 4. Secondary Browser Language Detection
        const navLang = (navigator.languages ? navigator.languages[0] : (navigator.language || '')).toLowerCase();
        if (navLang.includes('-in') || navLang.startsWith('hi')) {
            return { code: 'INR', symbol: '₹', region: 'India (Domestic Schedule III)' };
        }
        if (navLang.includes('-gb')) {
            return { code: 'GBP', symbol: '£', region: 'United Kingdom (Companies House)' };
        }
        if (['de', 'fr', 'es', 'it', 'nl', 'pt', 'el'].some(l => navLang.startsWith(l))) {
            return { code: 'EUR', symbol: '€', region: 'Europe (IFRS / Eurozone)' };
        }
    } catch {
        // Fallback safely
    }

    // Default to USD for Americas & Global Allocators
    return { code: 'USD', symbol: '$', region: 'Global / US (US GAAP)' };
}

const initialGeo = detectUserCurrency();
let activeCurrency = initialGeo.code;

export function getActiveCurrency() {
    return activeCurrency;
}

export function updateCurrencyBadge(label) {
    const badgeLabel = document.getElementById('detected-currency-label');
    if (badgeLabel) {
        badgeLabel.textContent = `📍 Localized Currency: ${label}`;
    }
}

export async function autoResolveRegionalCurrency() {
    // Immediate client-side zero-flicker resolution
    const clientGeo = detectUserCurrency();
    activeCurrency = clientGeo.code;
    appState.setState({ activeCurrency: clientGeo.code });
    updateCurrencyBadge(`${clientGeo.code} (${clientGeo.symbol}) · ${clientGeo.region}`);

    // Asynchronous background proxy header verification from edge
    try {
        const edgeGeo = await apiRequest('/api/v1/billing/geo-currency');
        if (edgeGeo && edgeGeo.currency && edgeGeo.currency !== activeCurrency) {
            activeCurrency = edgeGeo.currency;
            appState.setState({ activeCurrency: edgeGeo.currency });
            updateCurrencyBadge(`${edgeGeo.currency} (${edgeGeo.symbol}) · ${edgeGeo.region}`);
            renderPlans();
        } else if (edgeGeo && edgeGeo.region) {
            updateCurrencyBadge(`${edgeGeo.currency} (${edgeGeo.symbol}) · ${edgeGeo.region}`);
        }
    } catch {
        // Client-side detection already active
    }
}

export function openUpgradeModal(requiredPlan = 'pro') {
    const plansSec = document.querySelector('.plans-card') || document.getElementById('plans-heading');
    if (plansSec) {
        plansSec.scrollIntoView({ behavior: 'smooth', block: 'center' });
        plansSec.style.outline = '2px solid var(--accent-odd)';
        setTimeout(() => { plansSec.style.outline = ''; }, 3000);
    }
    showToast(`This feature requires a ${requiredPlan.toUpperCase()} subscription. Please choose a plan below.`, 'error');
}

// Global hook for apiRequest 403 fallback
window._openUpgradeModal = openUpgradeModal;

export function setPlanCurrency(curr) {
    activeCurrency = curr;
    appState.setState({ activeCurrency: curr });
    const syms = { USD: '$', INR: '₹', EUR: '€', GBP: '£' };
    updateCurrencyBadge(`${curr} (${syms[curr] || '$'}) · Auto-Resolved`);
    renderPlans();
}

export async function refreshPlans() {
    try {
        await autoResolveRegionalCurrency();
        const response = await apiRequest('/api/v1/billing/plans');
        appState.setState({ plans: response.plans || [] });
        window.marketLensPlans = response.plans || [];
        renderPlans();
    } catch {
        const grid = document.getElementById('plan-grid');
        if (grid) grid.textContent = 'Plans are temporarily unavailable.';
    }
}

export function renderPlans() {
    const { plans: statePlans, currentAccount } = appState.getState();
    const plans = statePlans.length ? statePlans : (window.marketLensPlans || []);
    const grid = document.getElementById('plan-grid');
    if (!grid) return;

    grid.replaceChildren();
    const currSymbols = { USD: '$', INR: '₹', EUR: '€', GBP: '£' };
    const sym = currSymbols[activeCurrency] || '$';

    plans.forEach(plan => {
        const card = document.createElement('article');
        card.className = 'plan-card bento-cell';
        card.dataset.planKey = plan.key;
        if (plan.key === 'business') {
            card.classList.add('featured');
        } else if (plan.key === 'enterprise') {
            card.classList.add('enterprise-card');
        }

        // 1. CARD HEADER (Title, Category Badge, Tagline)
        const cardHeader = document.createElement('div');
        cardHeader.className = 'plan-card-header';

        const badgeRow = document.createElement('div');
        badgeRow.className = 'plan-badge-slot';
        if (plan.key === 'business') {
            badgeRow.innerHTML = '<span class="plan-badge-pill popular"><span class="pulse-dot"></span> MOST POPULAR</span>';
        } else if (plan.key === 'enterprise') {
            badgeRow.innerHTML = '<span class="plan-badge-pill enterprise">ENTERPRISE SLA</span>';
        } else {
            badgeRow.innerHTML = '<span class="plan-badge-pill standard">ADVISORY</span>';
        }
        cardHeader.appendChild(badgeRow);

        const heading = document.createElement('h3');
        heading.textContent = plan.name;
        cardHeader.appendChild(heading);

        const tagline = document.createElement('p');
        tagline.className = 'plan-tagline';
        if (plan.key === 'pro') {
            tagline.textContent = 'For boutique advisory teams & corporate finance desks.';
        } else if (plan.key === 'business') {
            tagline.textContent = 'For PE funds, investment offices & active M&A dealmakers.';
        } else if (plan.key === 'enterprise') {
            tagline.textContent = 'For multi-subsidiary conglomerates & sovereign institutions.';
        } else {
            tagline.textContent = 'Deterministic institutional valuation modeling.';
        }
        cardHeader.appendChild(tagline);
        card.appendChild(cardHeader);

        // 2. DEDICATED CONTAINED PRICING & DESCRIPTION WELL (ZERO OVERLAY / ZERO PROTRUSION)
        const pricingBox = document.createElement('div');
        pricingBox.className = 'plan-pricing-box';

        const priceRow = document.createElement('div');
        priceRow.className = 'price-row';

        const priceVal = plan.prices && plan.prices[activeCurrency] !== undefined
            ? plan.prices[activeCurrency]
            : (plan.price_paise === 0 ? 0 : Math.round(plan.price_paise / 100));

        const formattedPrice = typeof priceVal === 'number' ? priceVal.toLocaleString() : priceVal;
        if (plan.key === 'free') {
            priceRow.innerHTML = `<span class="price-val">${sym}0</span> <span class="price-period">/ evaluation</span>`;
        } else {
            priceRow.innerHTML = `<span class="price-val">${sym}${formattedPrice}</span> <span class="price-period">/ month</span>`;
        }
        pricingBox.appendChild(priceRow);

        const quotaNote = document.createElement('div');
        quotaNote.className = 'plan-quota-note';
        if (plan.key === 'free') {
            quotaNote.textContent = '1 full evaluation · SHA-256 Merkle root verification';
        } else if (plan.key === 'enterprise') {
            quotaNote.textContent = 'Unlimited institutional valuations · Dedicated single-tenant VPC';
        } else if (plan.key === 'business') {
            quotaNote.textContent = '100 institutional valuations & M&A roll-ups per month';
        } else if (plan.key === 'pro') {
            quotaNote.textContent = '25 institutional valuations per month';
        } else {
            quotaNote.textContent = `${plan.monthly_valuations} institutional valuations per month`;
        }
        pricingBox.appendChild(quotaNote);

        if (plan.key === 'enterprise') {
            const annualPriceText = activeCurrency === 'INR' ? '₹36,00,000 / yr' : (activeCurrency === 'EUR' ? '€42,000 / yr' : (activeCurrency === 'GBP' ? '£36,000 / yr' : '$45,000 / yr'));
            const annualNote = document.createElement('div');
            annualNote.className = 'enterprise-annual-subtext';
            annualNote.textContent = `or ${annualPriceText} via Corporate Invoicing / PO`;
            pricingBox.appendChild(annualNote);
        }
        card.appendChild(pricingBox);

        // 3. FEATURES LIST WRAPPER
        if (Array.isArray(plan.features) && plan.features.length) {
            const featuresWrapper = document.createElement('div');
            featuresWrapper.className = 'plan-features-wrapper';

            const featuresCap = document.createElement('div');
            featuresCap.className = 'plan-features-caption';
            featuresCap.textContent = 'INCLUDED CAPABILITIES';
            featuresWrapper.appendChild(featuresCap);

            const featuresList = document.createElement('ul');
            featuresList.className = 'plan-features-list';
            plan.features.forEach(feat => {
                const li = document.createElement('li');
                li.className = 'plan-feature-item';
                li.innerHTML = `<span class="plan-feature-bullet">✓</span> <span>${feat}</span>`;
                featuresList.appendChild(li);
            });
            featuresWrapper.appendChild(featuresList);
            card.appendChild(featuresWrapper);
        }

        // 4. ACTION DOCK
        const actions = document.createElement('div');
        actions.className = 'plan-actions';
        const activePlan = currentAccount && currentAccount.plan && currentAccount.plan.key === plan.key;

        const button = document.createElement('button');
        button.type = 'button';
        if (plan.key === 'business') {
            button.className = 'primary-button plan-cta-primary';
            button.textContent = activePlan ? 'Current Active Tier' : 'Request Fund Pilot Access';
            button.title = 'Start 14-day PE / Fund Pilot or direct onboarding';
            button.addEventListener('click', () => {
                const { currentAccount } = appState.getState();
                if (!currentAccount) {
                    showAuthPanel('register');
                    return;
                }
                openEnterpriseConciergeModal('fund');
            });
            actions.appendChild(button);

            const altLink = document.createElement('a');
            altLink.href = 'javascript:void(0)';
            altLink.className = 'plan-secondary-link';
            altLink.style.cssText = 'display:block; text-align:center; font-size:12px; color:var(--text-secondary); margin-top:12px; text-decoration:none; cursor:pointer; transition:color 0.15s ease;';
            altLink.textContent = 'or Instant Corporate Card Checkout →';
            altLink.addEventListener('mouseenter', () => { altLink.style.color = '#ffffff'; });
            altLink.addEventListener('mouseleave', () => { altLink.style.color = 'var(--text-secondary)'; });
            altLink.addEventListener('click', (e) => {
                e.preventDefault();
                startCheckout(plan.key);
            });
            actions.appendChild(altLink);
        } else if (plan.key === 'enterprise') {
            button.className = 'secondary-button plan-cta-secondary';
            button.textContent = activePlan ? 'Current Active Tier' : 'Request Sovereign Contract';
            button.title = 'Generate Formal Pro-Forma Invoice, Pilot Contract & Dedicated VPC Deployment';
            button.addEventListener('click', (e) => {
                e.preventDefault();
                openEnterpriseConciergeModal('enterprise');
            });
            actions.appendChild(button);
        } else {
            button.className = 'secondary-button plan-cta-secondary';
            button.textContent = activePlan ? 'Current Active Tier' : 'Choose Advisory Desk';
            button.disabled = Boolean(activePlan || (plan.key !== 'free' && !plan.checkout_available));
            button.addEventListener('click', () => startCheckout(plan.key));
            actions.appendChild(button);
        }
        if (plan.key !== 'free' && plan.key !== 'free_trial' && !plan.checkout_available) {
            const setup = document.createElement('p');
            setup.className = 'locked-note';
            setup.textContent = 'Checkout setup is in progress.';
            actions.appendChild(setup);
        }
        card.appendChild(actions);
        grid.appendChild(card);
    });

    document.querySelectorAll('.plan-card').forEach(card => {
        card.classList.toggle('current', Boolean(currentAccount && card.dataset.planKey === (currentAccount.plan && currentAccount.plan.key)));
    });
}

// Global hook for auth module
window._renderPlans = renderPlans;

export async function startCheckout(planKey) {
    const { currentAccount } = appState.getState();
    if (!currentAccount) {
        showAuthPanel('register');
        return;
    }
    try {
        if (activeCurrency !== 'INR') {
            // Global rail: Stripe Checkout for USD, EUR, GBP
            const data = await apiRequest('/api/v1/billing/stripe/checkout', {
                method: 'POST',
                headers: csrfHeaders({ 'Content-Type': 'application/json' }),
                body: JSON.stringify({ plan_key: planKey, currency: activeCurrency.toLowerCase() })
            });

            if (data.checkout_url && data.checkout_url.includes('mock_stripe_checkout=1')) {
                // Instant seamless sandbox activation for global currency
                const activated = await apiRequest('/api/v1/billing/sandbox/activate', {
                    method: 'POST',
                    headers: csrfHeaders({ 'Content-Type': 'application/json' }),
                    body: JSON.stringify({ plan_key: planKey })
                });
                showToast(activated.message || `Upgraded to ${planKey.toUpperCase()} tier!`, 'success');
                await refreshAccount();
                renderPlans();
                return;
            }

            if (data.checkout_url) {
                window.location.href = data.checkout_url;
                return;
            }
        }

        // Indian rail: Razorpay Subscriptions for INR
        const data = await apiRequest('/api/v1/billing/checkout', {
            method: 'POST',
            headers: csrfHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ plan_key: planKey })
        });

        // Fail-safe sandbox activation
        if (data.mode === 'demo_active' || (data.status === 'active' && !data.subscription_id)) {
            showToast(data.message || 'Subscription activated successfully!', 'success');
            await refreshAccount();
            renderPlans();
            return;
        }

        if (!window.Razorpay) {
            await new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = 'https://checkout.razorpay.com/v1/checkout.js';
                script.onload = resolve;
                script.onerror = () => reject(new Error('Could not load the secure payment checkout.'));
                document.head.appendChild(script);
            });
        }
        const checkout = new window.Razorpay({
            key: data.key_id,
            subscription_id: data.subscription_id,
            name: data.name,
            description: data.description,
            prefill: { email: data.email },
            theme: { color: '#ff5a1f' },
            handler: async payment => {
                try {
                    await apiRequest('/api/v1/billing/verify', {
                        method: 'POST',
                        headers: csrfHeaders({ 'Content-Type': 'application/json' }),
                        body: JSON.stringify({
                            razorpay_subscription_id: payment.razorpay_subscription_id,
                            razorpay_payment_id: payment.razorpay_payment_id,
                            razorpay_signature: payment.razorpay_signature
                        })
                    });
                    setAuthFeedback('Payment received. Subscription status is syncing.');
                    showToast('Subscription activated successfully!', 'success');
                    await refreshAccount();
                    renderPlans();
                } catch (error) {
                    showToast(error.message, 'error');
                }
            }
        });
        checkout.on('payment.failed', event => showToast(event.error.description || 'Payment was not completed.', 'error'));
        checkout.open();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

export async function cancelSubscription() {
    if (!confirm('Schedule cancellation at the end of the current billing period?')) return;
    try {
        const response = await apiRequest('/api/v1/billing/cancel', {
            method: 'POST',
            headers: csrfHeaders()
        });
        setAuthFeedback(response.message);
        showToast(response.message, 'info');
        await refreshAccount();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// ============================================================================
// ERP MESH INTEGRATIONS
// ============================================================================
export async function refreshERPProviders() {
    const grid = document.getElementById('erp-provider-grid');
    if (!grid) return;
    try {
        const res = await apiRequest('/api/v1/erp/providers');
        const providers = res.providers || [];
        grid.replaceChildren();

        providers.forEach(p => {
            const card = document.createElement('div');
            card.className = 'bento-cell';
            card.style.padding = '1rem';
            card.style.display = 'flex';
            card.style.flexDirection = 'column';
            card.style.justifyContent = 'space-between';
            card.style.border = p.connected ? '1px solid rgba(16,185,129,0.3)' : '1px solid var(--border-hairline)';
            card.style.background = p.connected ? 'rgba(16,185,129,0.03)' : 'var(--bg-elevated)';

            const top = document.createElement('div');
            const titleRow = document.createElement('div');
            titleRow.style.display = 'flex';
            titleRow.style.justifyContent = 'space-between';
            titleRow.style.alignItems = 'center';
            titleRow.style.marginBottom = '0.4rem';

            const name = document.createElement('strong');
            name.textContent = p.name;
            name.style.fontSize = '0.88rem';
            name.style.color = 'var(--text-primary)';

            const badge = document.createElement('span');
            badge.style.fontSize = '0.7rem';
            badge.style.fontWeight = '600';
            badge.style.padding = '0.15rem 0.45rem';
            badge.style.borderRadius = '9999px';
            if (p.connected) {
                badge.textContent = 'CONNECTED';
                badge.style.color = 'var(--status-pass)';
                badge.style.background = 'rgba(16,185,129,0.15)';
            } else {
                badge.textContent = 'READ-ONLY';
                badge.style.color = 'var(--text-dim)';
                badge.style.background = 'rgba(255,255,255,0.05)';
            }
            titleRow.appendChild(name);
            titleRow.appendChild(badge);
            top.appendChild(titleRow);

            const desc = document.createElement('p');
            desc.textContent = p.description;
            desc.style.fontSize = '0.75rem';
            desc.style.color = 'var(--text-secondary)';
            desc.style.margin = '0 0 0.85rem 0';
            top.appendChild(desc);

            const actions = document.createElement('div');
            actions.style.display = 'flex';
            actions.style.gap = '0.4rem';

            if (p.connected) {
                const syncBtn = document.createElement('button');
                syncBtn.className = 'primary-button';
                syncBtn.textContent = 'Sync Now';
                syncBtn.style.fontSize = '0.75rem';
                syncBtn.style.padding = '0.4rem 0.75rem';
                syncBtn.addEventListener('click', () => syncERP(p.connection_id));

                const discBtn = document.createElement('button');
                discBtn.className = 'secondary-button';
                discBtn.textContent = 'Disconnect';
                discBtn.style.fontSize = '0.75rem';
                discBtn.style.padding = '0.4rem 0.6rem';
                discBtn.addEventListener('click', () => disconnectERP(p.connection_id));

                actions.appendChild(syncBtn);
                actions.appendChild(discBtn);
            } else {
                const demoBtn = document.createElement('button');
                demoBtn.className = 'primary-button';
                demoBtn.textContent = '⚡ Sample Demo';
                demoBtn.style.fontSize = '0.72rem';
                demoBtn.style.padding = '0.4rem 0.6rem';
                demoBtn.style.flex = '1';
                demoBtn.addEventListener('click', () => runERPSampleDemo(p.provider));

                const connBtn = document.createElement('button');
                connBtn.className = 'secondary-button';
                connBtn.textContent = 'Connect';
                connBtn.style.fontSize = '0.72rem';
                connBtn.style.padding = '0.4rem 0.6rem';
                connBtn.style.flex = '1';
                connBtn.addEventListener('click', () => connectERP(p.provider));

                actions.appendChild(demoBtn);
                actions.appendChild(connBtn);
            }

            card.appendChild(top);
            card.appendChild(actions);
            grid.appendChild(card);
        });
    } catch {
        renderOfflineERPProviders();
    }
}

function renderOfflineERPProviders() {
    const grid = document.getElementById('erp-provider-grid');
    if (!grid) return;
    const erps = [
        { name: 'TallyPrime', prov: 'tally', desc: 'Read-only XML relay for Indian Schedule III ledgers.' },
        { name: 'Zoho Books', prov: 'zoho', desc: 'Multi-DC OAuth 2.0 reports (.in, .com, .eu).' },
        { name: 'QuickBooks', prov: 'quickbooks', desc: 'Intuit OAuth 2.0 read-only Trial Balance.' },
        { name: 'Xero', prov: 'xero', desc: 'Read-only financial statements & balance sheets.' },
        { name: 'NetSuite', prov: 'netsuite', desc: 'SuiteQL read-only subsidiary trial balances.' },
    ];
    grid.replaceChildren();
    erps.forEach(e => {
        const card = document.createElement('div');
        card.className = 'bento-cell';
        card.style.padding = '1rem';
        card.style.display = 'flex';
        card.style.flexDirection = 'column';
        card.style.justifyContent = 'space-between';
        card.style.background = 'var(--bg-elevated)';

        card.innerHTML = `
            <div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
                    <strong style="color:var(--text-primary); font-size:0.88rem;">${e.name}</strong>
                    <span style="font-size:0.7rem; color:var(--text-dim); background:rgba(255,255,255,0.05); padding:0.15rem 0.45rem; border-radius:9999px;">READ-ONLY</span>
                </div>
                <p style="font-size:0.75rem; color:var(--text-secondary); margin:0 0 0.85rem 0;">${e.desc}</p>
            </div>
        `;
        const actions = document.createElement('div');
        actions.style.display = 'flex';
        actions.style.gap = '0.4rem';

        const demoBtn = document.createElement('button');
        demoBtn.className = 'primary-button';
        demoBtn.style.fontSize = '0.72rem';
        demoBtn.style.padding = '0.4rem 0.6rem';
        demoBtn.style.flex = '1';
        demoBtn.textContent = '⚡ Sample Demo';
        demoBtn.addEventListener('click', () => runERPSampleDemo(e.prov));

        const connBtn = document.createElement('button');
        connBtn.className = 'secondary-button';
        connBtn.style.fontSize = '0.72rem';
        connBtn.style.padding = '0.4rem 0.6rem';
        connBtn.style.flex = '1';
        connBtn.textContent = 'Connect';
        connBtn.addEventListener('click', () => connectERP(e.prov));

        actions.appendChild(demoBtn);
        actions.appendChild(connBtn);
        card.appendChild(actions);
        grid.appendChild(card);
    });
}

export function openERPRelayModal(provider) {
    const modal = document.getElementById('erp-relay-modal');
    if (!modal) return;
    const provName = provider.charAt(0).toUpperCase() + provider.slice(1);
    const badge = document.getElementById('erp-modal-prov-badge');
    if (badge) badge.textContent = provName;

    const sampleBtn = document.getElementById('btn-erp-modal-sample');
    if (sampleBtn) {
        sampleBtn.onclick = () => {
            closeERPRelayModal();
            runERPSampleDemo(provider);
        };
    }

    const dlBtn = document.getElementById('btn-erp-modal-sample-dl');
    if (dlBtn) {
        dlBtn.onclick = () => {
            const isTally = provider.toLowerCase() === 'tally';
            const sampleUrl = isTally ? '/static/templates/sample_tally_tb.xml' : '/static/templates/sample_trial_balance.csv';
            const a = document.createElement('a');
            a.href = sampleUrl;
            a.download = `${provider}_sample_ledger.${isTally ? 'xml' : 'csv'}`;
            a.click();
            showToast(`Downloaded sample ${provName} ledger template.`, 'success');
        };
    }

    modal.hidden = false;
    modal.classList.remove('hidden');
    modal.style.display = 'flex';
}

export function closeERPRelayModal() {
    const modal = document.getElementById('erp-relay-modal');
    if (modal) {
        modal.hidden = true;
        modal.classList.add('hidden');
        modal.style.display = 'none';
    }
}

export async function runERPSampleDemo(provider) {
    const provName = provider.charAt(0).toUpperCase() + provider.slice(1);
    const processFlow = document.getElementById('process-flow');
    const resultsDashboard = document.getElementById('results-dashboard');
    if (processFlow) processFlow.style.display = 'block';
    if (resultsDashboard) resultsDashboard.style.display = 'none';

    const stepLabel1 = document.getElementById('step-label-1');
    if (stepLabel1) stepLabel1.textContent = `Extracting ${provName} Trial Balance ledger`;
    const progMsg = document.getElementById('progress-message');
    if (progMsg) progMsg.textContent = `Initializing read-only ${provName} sync...`;
    setStep(1);

    appState.setState({ analysisBusy: true });
    showToast(`Simulating read-only ${provName} Trial Balance pull...`, 'info');

    try {
        const headers = csrfHeaders({ 'Content-Type': 'application/json' });
        const res = await apiRequest(`/api/v1/erp/${provider}/sample-demo`, {
            method: 'POST',
            headers
        });

        appState.setState({ currentJobId: res.job_id });
        window._currentJobId = res.job_id;

        const result = await apiJobResult(res.job_id);
        markAllCompleted();
        renderLiveDashboard(result);
        showToast(`${provName} Board Pack compiled successfully!`, 'success');
    } catch (err) {
        showToast(err.message || `Failed to run ${provName} sample demo.`, 'error');
        if (processFlow) processFlow.style.display = 'none';
    } finally {
        appState.setState({ analysisBusy: false });
    }
}

export async function connectERP(provider) {
    const { currentAccount } = appState.getState();
    if (!currentAccount) {
        openERPRelayModal(provider);
        return;
    }
    try {
        const res = await apiRequest(`/api/v1/erp/${provider}/connect`);
        if (res.authorize_url) {
            window.location.href = res.authorize_url;
            return;
        }
        openERPRelayModal(provider);
    } catch (err) {
        openERPRelayModal(provider);
    }
}

export async function syncERP(connectionId) {
    try {
        setAuthFeedback('Initiating read-only ERP ledger sync & Board Pack compilation...');
        await apiRequest(`/api/v1/erp/${connectionId}/sync`, {
            method: 'POST',
            headers: csrfHeaders()
        });
        showToast('ERP Synchronization Completed! Monthly Board Pack compiled and verified.', 'success');
        if (typeof window._refreshJobHistory === 'function') {
            window._refreshJobHistory();
        }
        await refreshERPProviders();
    } catch (err) {
        showToast(err.message || 'ERP sync failed.', 'error');
    }
}

export async function disconnectERP(connectionId) {
    if (!confirm('Disconnect this ERP integration and revoke encrypted tokens?')) return;
    try {
        await apiRequest(`/api/v1/erp/${connectionId}`, {
            method: 'DELETE',
            headers: csrfHeaders()
        });
        await refreshERPProviders();
        showToast('ERP integration disconnected.', 'info');
    } catch (err) {
        showToast(err.message || 'Could not disconnect ERP.', 'error');
    }
}

// ============================================================================
// DEVELOPER & UNDERWRITING API KEYS
// ============================================================================
export async function refreshApiKeys() {
    const table = document.getElementById('api-keys-table-body');
    if (!table) return;
    try {
        const data = await apiRequest('/api/v1/keys');
        const usage = await apiRequest('/api/v1/keys/usage').catch(() => ({}));

        const unitsEl = document.getElementById('api-metric-units');
        const quotaEl = document.getElementById('api-metric-quota');
        const keysEl = document.getElementById('api-metric-active-keys');
        const latEl = document.getElementById('api-metric-latency');

        const totalUnits = (usage.usage_summary && usage.usage_summary.total_billable_units) || 0;
        if (unitsEl) unitsEl.textContent = totalUnits;
        if (quotaEl) quotaEl.textContent = `Remaining Quota: ${usage.remaining_quota !== undefined ? usage.remaining_quota : '--'}`;
        const activeKeys = (data.keys || []).filter(k => k.status === 'active');
        if (keysEl) keysEl.textContent = activeKeys.length;
        if (latEl) latEl.textContent = `${(usage.usage_summary && usage.usage_summary.average_compute_ms) || 12.5} ms`;

        if (!data.keys || data.keys.length === 0) {
            table.innerHTML = '<div style="padding:0.5rem 0; color:var(--text-dim);">No active API keys found. Generate a scoped key above.</div>';
            return;
        }

        table.innerHTML = '';
        const listDiv = document.createElement('div');
        listDiv.style.cssText = 'display:flex; flex-direction:column; gap:8px;';

        data.keys.forEach(k => {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex; justify-content:space-between; align-items:center; padding:0.6rem 0.75rem; background:var(--bg-surface); border:1px solid var(--border-hairline); border-radius:6px; flex-wrap:wrap; gap:8px;';

            row.innerHTML = `
                <div>
                    <div style="display:flex; align-items:center; gap:0.5rem;">
                        <strong style="color:var(--text-primary); font-size:0.85rem;">${k.name}</strong>
                        <code style="font-family:'JetBrains Mono', monospace; font-size:0.75rem; background:rgba(255,255,255,0.06); padding:0.1rem 0.35rem; border-radius:4px; color:var(--text-secondary);">${k.key_prefix}••••••••</code>
                        <span style="font-size:0.68rem; font-weight:700; text-transform:uppercase; padding:0.1rem 0.4rem; border-radius:4px; background:${k.status === 'active' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}; color:${k.status === 'active' ? 'var(--status-pass)' : '#ef4444'};">${k.status}</span>
                    </div>
                    <div style="font-size:0.72rem; color:var(--text-dim); margin-top:0.25rem;">
                        Scopes: ${k.scopes.join(', ')} · Rate: ${k.rate_limit_per_min} req/min · Created: ${new Date(k.created_at).toLocaleDateString()}
                    </div>
                </div>
            `;

            const actionDiv = document.createElement('div');
            if (k.status === 'active') {
                const revokeBtn = document.createElement('button');
                revokeBtn.className = 'secondary-button';
                revokeBtn.style.cssText = 'font-size:0.72rem; padding:0.3rem 0.65rem; color:#ef4444; border-color:rgba(239,68,68,0.3);';
                revokeBtn.textContent = 'Revoke Key';
                revokeBtn.addEventListener('click', () => revokeApiKey(k.id));
                actionDiv.appendChild(revokeBtn);
            } else {
                actionDiv.innerHTML = '<span style="font-size:0.72rem; color:var(--text-dim);">Revoked</span>';
            }
            row.appendChild(actionDiv);
            listDiv.appendChild(row);
        });

        table.appendChild(listDiv);
    } catch {
        table.innerHTML = '<div style="padding:0.5rem 0; color:var(--text-dim);">Sign in to manage scoped institutional API keys.</div>';
    }
}

export async function promptCreateApiKey() {
    const { currentAccount } = appState.getState();
    if (!currentAccount) {
        showAuthPanel('login');
        setAuthFeedback('Please sign in or create an account to generate API keys.', true);
        return;
    }
    const keyName = prompt('Enter a label for this API key (e.g. Underwriting Bot, Valuation Pipeline):', 'VC Underwriting Pipeline');
    if (!keyName || !keyName.trim()) return;

    try {
        const res = await apiRequest('/api/v1/keys', {
            method: 'POST',
            headers: csrfHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({
                name: keyName.trim(),
                scopes: ['model:write', 'diagnostics:read', 'audit:read'],
                rate_limit_per_min: 60
            })
        });

        prompt(
            '⚡ INSTITUTIONAL SCOPED API KEY CREATED!\n\n' +
            'Copy and store this secret key in your secure vault now. You will NEVER be able to see it again:\n\n',
            res.secret_key
        );

        await refreshApiKeys();
    } catch (err) {
        showToast(err.message || 'Could not create API key.', 'error');
    }
}

export async function revokeApiKey(keyId) {
    if (!confirm('Immediately revoke this API key? External automated requests using it will be blocked.')) return;
    try {
        await apiRequest(`/api/v1/keys/${keyId}`, {
            method: 'DELETE',
            headers: csrfHeaders()
        });
        showToast('API key revoked.', 'info');
        await refreshApiKeys();
    } catch (err) {
        showToast(err.message || 'Could not revoke API key.', 'error');
    }
}

export function copyApiSnippet(kind) {
    const el = document.getElementById('api-snippet-display');
    if (!el) return;
    let code = '';
    if (kind === 'python') {
        code = `import requests

API_KEY = "ml_live_YOUR_SECRET_KEY"
BASE_URL = "https://automated-financial-engine-production.up.railway.app"

# 1. Submit Financial Ingestion Pack
with open("financials.xlsx", "rb") as f:
    resp = requests.post(
        f"{BASE_URL}/api/v1/model/generate-pack",
        headers={"X-API-Key": API_KEY},
        files={"file": f}
    )
job_id = resp.json()["job_id"]

# 2. Poll Decision & Sensitivity Diagnostics
diag = requests.get(
    f"{BASE_URL}/api/v1/diagnostics/{job_id}",
    headers={"X-API-Key": API_KEY}
).json()
print("Health Score:", diag["overall_health_score"])
print("Value Prescriptions:", diag["pain_points"])`;
    } else {
        code = el.textContent;
    }
    navigator.clipboard.writeText(code).then(() => {
        showToast('Integration code snippet copied to clipboard!', 'success');
    }).catch(() => {
        prompt('Copy snippet:', code);
    });
}

export function openEnterpriseConciergeModal(tier = 'fund') {
    const modal = document.getElementById('enterprise-concierge-modal');
    if (!modal) return;

    modal.dataset.tier = tier;
    const badgeText = document.getElementById('concierge-badge-text');
    const pricePill = document.getElementById('concierge-price-pill');
    const title = document.getElementById('concierge-title');
    const desc = document.getElementById('concierge-desc');
    const submitBtn = document.getElementById('btn-ent-quote-submit');

    if (tier === 'enterprise') {
        if (badgeText) badgeText.textContent = 'ANNUAL MASTER CONTRACT';
        if (pricePill) pricePill.textContent = activeCurrency === 'INR' ? '₹36,00,000 / yr' : '$45,000 / yr';
        if (title) title.textContent = 'Enterprise Sovereign Pilot & Corporate Invoicing';
        if (desc) desc.textContent = 'Tailored for conglomerates, multi-subsidiary holdings, and sovereign allocators requiring single-tenant VPC, Net-30 purchase orders, and Big-4 Merkle provenance attestation.';
        if (submitBtn) submitBtn.textContent = 'Generate Formal Pro-Forma Invoice & Pilot Contract';
    } else {
        if (badgeText) badgeText.textContent = 'Q1 FOUNDING COHORT · 5 SEATS';
        if (pricePill) pricePill.textContent = '14-Day Full Executive Pilot · Zero Commitment';
        if (title) title.textContent = 'Private Equity & Fund Desk · Executive Pilot';
        if (desc) desc.textContent = 'Fast-track institutional onboarding for investment committees and private equity deal teams. Includes 14 days of full platform access, custom sector peer comps, and a dedicated Quant Slack/Teams bridge.';
        if (submitBtn) submitBtn.textContent = 'Confirm 14-Day Fund Pilot & Access Pass';
    }

    modal.hidden = false;
    modal.classList.remove('hidden');
    modal.style.display = 'flex';
}

export function closeEnterpriseConciergeModal() {
    const modal = document.getElementById('enterprise-concierge-modal');
    if (modal) {
        modal.hidden = true;
        modal.classList.add('hidden');
        modal.style.display = 'none';
    }
}

export async function submitEnterpriseQuote(e) {
    if (e) e.preventDefault();
    const modal = document.getElementById('enterprise-concierge-modal');
    const isEnterprise = modal && modal.dataset.tier === 'enterprise';

    const companyInput = document.getElementById('ent-company-name');
    const emailInput = document.getElementById('ent-contact-email');
    const seatsInput = document.getElementById('ent-seats-count');
    const erpInput = document.getElementById('ent-erp-system');
    const submitBtn = document.getElementById('btn-ent-quote-submit');
    const resultBox = document.getElementById('ent-quote-result');

    if (!companyInput || !emailInput) return;
    const company_name = companyInput.value.trim();
    const contact_email = emailInput.value.trim();
    const seats = seatsInput ? parseInt(seatsInput.value, 10) || 5 : 5;
    const erp_system = erpInput ? erpInput.value : 'Oracle NetSuite & SAP';

    if (!company_name || !contact_email) {
        showToast('Please provide your company name and work email.', 'error');
        return;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = isEnterprise ? 'Generating Institutional Contract...' : 'Provisioning Fund Pilot Pass...';
    }

    try {
        const quote = await apiRequest('/api/v1/billing/enterprise/quote', {
            method: 'POST',
            headers: csrfHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({
                company_name,
                contact_email,
                seats,
                erp_system,
                custom_invariants: true,
                dedicated_vpc: isEnterprise
            })
        });

        if (resultBox) {
            resultBox.style.display = 'block';
            if (isEnterprise) {
                resultBox.innerHTML = `
                    <div style="background:rgba(16,185,129,0.06); border:1px solid rgba(16,185,129,0.3); border-radius:8px; padding:var(--space-3); margin-top:var(--space-3);">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                            <span style="font-weight:700; color:var(--status-pass); font-size:var(--font-xs);">${quote.quote_id} · OFFICIAL PRO-FORMA INVOICE</span>
                            <span style="font-family:'JetBrains Mono', monospace; font-size:var(--font-xs); color:var(--text-primary); font-weight:700;">$45,000 / yr</span>
                        </div>
                        <div style="font-size:var(--font-xs); color:var(--text-secondary); line-height:1.5; margin-bottom:8px;">
                            Prepared for: <strong style="color:var(--text-primary);">${quote.company_name}</strong> (${quote.contact_email})<br>
                            Scope: ${quote.seats} Seats · ${quote.erp_system} Sync · Net-30 Corporate Invoicing &amp; Dedicated VPC
                        </div>
                        <button type="button" class="secondary-button" id="btn-copy-quote-cert" style="width:100%; justify-content:center; font-size:var(--font-xs);">
                            Copy Formal Pro-Forma Invoice &amp; Wiring Instructions
                        </button>
                    </div>
                `;
            } else {
                resultBox.innerHTML = `
                    <div style="background:rgba(16,185,129,0.06); border:1px solid rgba(16,185,129,0.3); border-radius:8px; padding:var(--space-3); margin-top:var(--space-3);">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                            <span style="font-weight:700; color:var(--status-pass); font-size:var(--font-xs);">${quote.quote_id} · 14-DAY PILOT PASS APPROVED</span>
                            <span style="font-family:'JetBrains Mono', monospace; font-size:var(--font-xs); color:var(--text-primary); font-weight:700;">Zero Commitment · Full Quota</span>
                        </div>
                        <div style="font-size:var(--font-xs); color:var(--text-secondary); line-height:1.5; margin-bottom:8px;">
                            Partner: <strong style="color:var(--text-primary);">${quote.company_name}</strong> (${quote.contact_email})<br>
                            Scope: 14-Day Full PE Runway · ${quote.seats} Deal Team Seats · Dedicated Quant Slack Bridge
                        </div>
                        <button type="button" class="secondary-button" id="btn-copy-quote-cert" style="width:100%; justify-content:center; font-size:var(--font-xs);">
                            Copy Formal Pilot Pass &amp; Dedicated Slack Bridge Access
                        </button>
                    </div>
                `;
            }
            const copyBtn = document.getElementById('btn-copy-quote-cert');
            if (copyBtn) {
                copyBtn.onclick = () => {
                    navigator.clipboard.writeText(JSON.stringify(quote, null, 2));
                    showToast('Credentials & Access instructions copied to clipboard!', 'success');
                };
            }
        }
        showToast(isEnterprise ? 'Enterprise Sovereign Pro-Forma Invoice generated!' : 'Executive Fund Pilot activated! Check inbox for direct Slack invite.', 'success');
    } catch (err) {
        showToast(err.message || 'Could not generate quote.', 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = isEnterprise ? 'Generate Formal Pro-Forma Invoice & Pilot Contract' : 'Confirm 14-Day Fund Pilot & Access Pass';
        }
    }
}

export function initBilling() {
    autoResolveRegionalCurrency();

    const refreshErpBtn = document.getElementById('btn-refresh-erp');
    if (refreshErpBtn) refreshErpBtn.addEventListener('click', refreshERPProviders);

    const createKeyBtn = document.getElementById('btn-create-api-key');
    if (createKeyBtn) createKeyBtn.addEventListener('click', promptCreateApiKey);

    const refreshKeysBtn = document.getElementById('btn-refresh-api-keys');
    if (refreshKeysBtn) refreshKeysBtn.addEventListener('click', refreshApiKeys);

    const copyCurlBtn = document.getElementById('btn-copy-curl');
    if (copyCurlBtn) copyCurlBtn.addEventListener('click', () => copyApiSnippet('curl'));

    const copyPyBtn = document.getElementById('btn-copy-python');
    if (copyPyBtn) copyPyBtn.addEventListener('click', () => copyApiSnippet('python'));

    const erpCloseBtn = document.getElementById('erp-modal-close');
    if (erpCloseBtn) erpCloseBtn.addEventListener('click', closeERPRelayModal);

    const erpModal = document.getElementById('erp-relay-modal');
    if (erpModal) {
        erpModal.addEventListener('click', (e) => {
            if (e.target === erpModal) closeERPRelayModal();
        });
    }

    // Enterprise Sovereign Concierge Modal triggers
    const openConciergeBtn = document.getElementById('btn-open-concierge');
    if (openConciergeBtn) openConciergeBtn.addEventListener('click', openEnterpriseConciergeModal);

    const closeConciergeBtn = document.getElementById('ent-concierge-close');
    if (closeConciergeBtn) closeConciergeBtn.addEventListener('click', closeEnterpriseConciergeModal);

    const conciergeModal = document.getElementById('enterprise-concierge-modal');
    if (conciergeModal) {
        conciergeModal.addEventListener('click', (e) => {
            if (e.target === conciergeModal) closeEnterpriseConciergeModal();
        });
    }

    const entForm = document.getElementById('ent-quote-form');
    if (entForm) entForm.addEventListener('submit', submitEnterpriseQuote);
}
