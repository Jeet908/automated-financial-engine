/**
 * src/portal/static/modules/api.js
 * Shared Client, Reactive State Bus & Global Toast UI.
 */

class AppStore {
    constructor() {
        this._state = {
            currentAccount: null,
            csrfToken: null,
            authMode: 'register',
            resetToken: null,
            analysisBusy: false,
            systemFeatures: {},
            plans: [],
            activeCurrency: 'USD',
            lastValuationResult: null,
            currentJobId: null
        };
        this._listeners = new Set();
        this._keyListeners = new Map();
    }

    getState() {
        return { ...this._state };
    }

    setState(updates) {
        const prevState = { ...this._state };
        this._state = { ...this._state, ...updates };

        // Global listeners
        for (const listener of this._listeners) {
            try {
                listener(this._state, prevState);
            } catch (err) {
                console.error('[AppStore] Listener error:', err);
            }
        }

        // Key-specific listeners
        for (const [key, val] of Object.entries(updates)) {
            if (this._keyListeners.has(key) && prevState[key] !== val) {
                for (const kListener of this._keyListeners.get(key)) {
                    try {
                        kListener(val, prevState[key], this._state);
                    } catch (err) {
                        console.error(`[AppStore] Key listener error for '${key}':`, err);
                    }
                }
            }
        }
    }

    subscribe(listener) {
        this._listeners.add(listener);
        return () => this._listeners.delete(listener);
    }

    subscribeKey(key, listener) {
        if (!this._keyListeners.has(key)) {
            this._keyListeners.set(key, new Set());
        }
        this._keyListeners.get(key).add(listener);
        return () => {
            const set = this._keyListeners.get(key);
            if (set) set.delete(listener);
        };
    }
}

export const appState = new AppStore();

export function csrfHeaders(extra = {}) {
    const token = appState.getState().csrfToken;
    return {
        ...extra,
        ...(token ? { 'X-CSRF-Token': token } : {})
    };
}

export async function apiRequest(url, options = {}) {
    const headers = { ...(options.headers || {}) };
    const token = appState.getState().csrfToken;
    if (token && !headers['X-CSRF-Token']) {
        headers['X-CSRF-Token'] = token;
    }

    const response = await fetch(url, {
        credentials: 'same-origin',
        ...options,
        headers
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        if (
            response.status === 403 &&
            (data.error === 'plan_upgrade_required' ||
                (data.detail && data.detail.error === 'plan_upgrade_required'))
        ) {
            const reqPlan = (data.detail && data.detail.required_plan) || data.required_plan || 'pro';
            if (typeof window._openUpgradeModal === 'function') {
                window._openUpgradeModal(reqPlan);
            }
        }
        const errDetail =
            typeof data.detail === 'object'
                ? data.detail.message
                : data.detail || data.message || `Request failed (${response.status}).`;
        const err = new Error(errDetail);
        err.status = response.status;
        err.data = data;
        throw err;
    }

    return data;
}

export function showToast(message, type = 'info') {
    let toastContainer = document.getElementById('marketlens-toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'marketlens-toast-container';
        toastContainer.style.cssText =
            'position: fixed; bottom: 24px; right: 24px; z-index: 9999; display: flex; flex-direction: column; gap: 8px; pointer-events: none;';
        document.body.appendChild(toastContainer);
    }

    const toast = document.createElement('div');
    const isError = type === 'error';
    const isSuccess = type === 'success';

    toast.style.cssText = `
        pointer-events: auto;
        padding: 10px 16px;
        border-radius: 8px;
        font-size: 13px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-weight: 500;
        background: ${isError ? '#181111' : (isSuccess ? '#101b15' : '#18181c')};
        color: ${isError ? '#f87171' : (isSuccess ? '#34d399' : '#fafafa')};
        border: 1px solid ${isError ? 'rgba(239,68,68,0.4)' : (isSuccess ? 'rgba(16,185,129,0.4)' : 'rgba(255,255,255,0.12)')};
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        gap: 8px;
        transition: opacity 0.3s ease, transform 0.3s ease;
        opacity: 0;
        transform: translateY(10px);
    `;

    toast.innerHTML = `
        <span>${isError ? '⚠' : (isSuccess ? '✓' : 'ℹ')}</span>
        <span>${escapeHtml(message)}</span>
    `;

    toastContainer.appendChild(toast);
    requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    });

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

export function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
