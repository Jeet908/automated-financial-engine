/**
 * src/portal/static/modules/billing.js
 * Dual-Rail Global Billing (Stripe + Razorpay), ERP Mesh & Scoped API Keys.
 */

import { apiRequest, appState, csrfHeaders, showToast } from './api.js';
import { refreshAccount, showAuthPanel, setAuthFeedback } from './auth.js';

let activeCurrency = 'USD';

export function getActiveCurrency() {
    return activeCurrency;
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
    ['USD', 'INR', 'EUR', 'GBP'].forEach(c => {
        const btn = document.getElementById(`curr-btn-${c}`);
        if (btn) {
            btn.classList.toggle('active', c === curr);
        }
    });
    renderPlans();
}

export async function refreshPlans() {
    try {
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
        if (plan.key === 'free_trial' || plan.key === 'pro') {
            card.classList.add('featured');
        }

        const heading = document.createElement('h3');
        heading.textContent = plan.name;

        const price = document.createElement('div');
        price.className = 'plan-price';

        const priceVal = plan.prices && plan.prices[activeCurrency] !== undefined
            ? plan.prices[activeCurrency]
            : (plan.price_paise === 0 ? 0 : Math.round(plan.price_paise / 100));

        if (plan.key === 'free_trial') {
            price.innerHTML = `<span class="price-val" style="color:var(--accent-odd);">${sym}0</span> <span class="price-period">/ 14 days</span>`;
        } else if (plan.key === 'free') {
            price.innerHTML = `<span class="price-val">${sym}0</span> <span class="price-period">/ month</span>`;
        } else {
            price.innerHTML = `<span class="price-val">${sym}${priceVal}</span> <span class="price-period">/ month</span>`;
        }

        const note = document.createElement('p');
        note.className = 'plan-note';
        note.textContent = plan.key === 'free_trial'
            ? 'Instant 14-day full access. No credit card required.'
            : `${plan.monthly_valuations} valuation${plan.monthly_valuations === 1 ? '' : 's'} per month`;

        const actions = document.createElement('div');
        actions.className = 'plan-actions';
        const button = document.createElement('button');
        const isTrial = plan.key === 'free_trial';
        button.className = isTrial || plan.key === 'pro' ? 'primary-button' : 'secondary-button';

        const activePlan = currentAccount && currentAccount.plan && currentAccount.plan.key === plan.key;
        button.textContent = activePlan ? 'Current plan' : (isTrial ? 'Start 14-Day Free Trial' : (plan.key === 'free' ? 'Get started' : `Choose ${plan.name}`));
        button.disabled = Boolean(activePlan || (plan.key !== 'free' && plan.key !== 'free_trial' && !plan.checkout_available));

        button.addEventListener('click', async () => {
            if (isTrial) {
                if (!currentAccount) {
                    showAuthPanel('register');
                } else {
                    try {
                        const res = await apiRequest('/api/v1/auth/trial/activate', { method: 'POST', headers: csrfHeaders() });
                        showToast(res.message, 'success');
                        await refreshAccount();
                    } catch (err) {
                        showToast(err.message, 'error');
                    }
                }
            } else if (plan.key === 'free') {
                showAuthPanel('register');
            } else {
                startCheckout(plan.key);
            }
        });

        actions.appendChild(button);
        if (plan.key !== 'free' && plan.key !== 'free_trial' && !plan.checkout_available) {
            const setup = document.createElement('p');
            setup.className = 'locked-note';
            setup.textContent = 'Checkout setup is in progress.';
            actions.appendChild(setup);
        }
        card.append(heading, price, note, actions);
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
                const connBtn = document.createElement('button');
                connBtn.className = 'secondary-button';
                connBtn.textContent = `Connect ${p.name.split(' ')[0]} (Read-Only)`;
                connBtn.style.fontSize = '0.75rem';
                connBtn.style.padding = '0.4rem 0.75rem';
                connBtn.style.width = '100%';
                connBtn.addEventListener('click', () => connectERP(p.provider));
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
        const connBtn = document.createElement('button');
        connBtn.className = 'secondary-button';
        connBtn.style.fontSize = '0.75rem';
        connBtn.style.padding = '0.4rem 0.75rem';
        connBtn.style.width = '100%';
        connBtn.textContent = 'Connect (Read-Only)';
        connBtn.addEventListener('click', () => connectERP(e.prov));
        card.appendChild(connBtn);
        grid.appendChild(card);
    });
}

export async function connectERP(provider) {
    const { currentAccount } = appState.getState();
    if (!currentAccount) {
        showAuthPanel('login');
        setAuthFeedback('Please sign in or create an account to connect ERP integrations.', true);
        return;
    }
    try {
        const res = await apiRequest(`/api/v1/erp/${provider}/connect`);
        if (res.authorize_url) {
            window.location.href = res.authorize_url;
        }
    } catch (err) {
        showToast(err.message || 'Could not initiate ERP connection.', 'error');
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

# 2. Poll Decision & Alpha Prescriptions
diag = requests.get(
    f"{BASE_URL}/api/v1/diagnostics/{job_id}",
    headers={"X-API-Key": API_KEY}
).json()
print("Health Score:", diag["overall_health_score"])
print("Alpha Prescriptions:", diag["pain_points"])`;
    } else {
        code = el.textContent;
    }
    navigator.clipboard.writeText(code).then(() => {
        showToast('Integration code snippet copied to clipboard!', 'success');
    }).catch(() => {
        prompt('Copy snippet:', code);
    });
}

export function initBilling() {
    ['USD', 'INR', 'EUR', 'GBP'].forEach(curr => {
        const btn = document.getElementById(`curr-btn-${curr}`);
        if (btn) btn.addEventListener('click', () => setPlanCurrency(curr));
    });

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
}
