/**
 * src/portal/static/modules/auth.js
 * Identity, Enterprise SSO, Trial Activation & Access Governance.
 */

import { apiRequest, appState, csrfHeaders, showToast } from './api.js';

export function setAuthFeedback(message, isError = false) {
    const feedback = document.getElementById('auth-feedback');
    if (feedback) {
        feedback.textContent = message;
        feedback.classList.toggle('error', isError);
    }
}

export function showAuthPanel(mode = 'register') {
    const panel = document.getElementById('auth-panel');
    if (panel) {
        panel.hidden = false;
        setAuthMode(mode);
        panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

export function setAuthMode(mode) {
    const authMode = mode === 'login' ? 'login' : 'register';
    appState.setState({ authMode });
    const isLogin = authMode === 'login';

    const regTab = document.getElementById('register-tab');
    const logTab = document.getElementById('login-tab');
    const termsLabel = document.getElementById('terms-label');
    const termsAccepted = document.getElementById('terms-accepted');
    const authPassword = document.getElementById('auth-password');
    const credSubmit = document.getElementById('credentials-submit');
    const forgotBtn = document.getElementById('forgot-password-button');
    const credForm = document.getElementById('credentials-form');
    const recForm = document.getElementById('recovery-form');
    const verResendForm = document.getElementById('verification-resend-form');
    const resetForm = document.getElementById('reset-form');
    const googleTerms = document.getElementById('google-terms-accepted');

    if (regTab) regTab.setAttribute('aria-pressed', String(!isLogin));
    if (logTab) logTab.setAttribute('aria-pressed', String(isLogin));
    if (termsLabel) termsLabel.hidden = isLogin;
    if (termsAccepted) {
        termsAccepted.disabled = isLogin;
        termsAccepted.required = !isLogin;
    }
    if (authPassword) authPassword.autocomplete = isLogin ? 'current-password' : 'new-password';
    if (credSubmit) credSubmit.textContent = isLogin ? 'Sign in' : 'Create account';
    if (forgotBtn) forgotBtn.hidden = !isLogin;
    if (credForm) credForm.hidden = false;
    if (recForm) recForm.hidden = true;
    if (verResendForm) verResendForm.hidden = true;
    if (resetForm) resetForm.hidden = true;
    if (googleTerms) googleTerms.checked = false;

    setAuthFeedback('');
}

export function setAccess(account) {
    const state = appState.getState();
    const user = account && account.user;
    const guestView = document.getElementById('guest-view');
    const accountView = document.getElementById('account-view');
    const navAuth = document.getElementById('nav-auth-button');
    const navTrial = document.getElementById('nav-trial-btn');
    const navLabel = document.getElementById('nav-account-label');

    if (guestView) guestView.hidden = Boolean(user);
    if (accountView) accountView.hidden = !user;
    if (navAuth) navAuth.hidden = Boolean(user);
    if (navTrial) navTrial.hidden = Boolean(user);
    if (navLabel) {
        navLabel.hidden = !user;
        navLabel.textContent = user ? user.email : '';
    }

    if (user) {
        const plan = account.plan || {};
        const welcome = document.getElementById('account-welcome');
        const usage = document.getElementById('account-usage');
        const subNote = document.getElementById('account-subscription');
        const cancelBtn = document.getElementById('cancel-subscription');

        if (welcome) welcome.textContent = `Welcome, ${user.email}`;
        if (usage) {
            usage.textContent = `${plan.name || 'Free'} plan · ${plan.used_this_month || 0} of ${plan.monthly_valuations || 1} valuations used this month`;
        }
        const subscription = account.subscription;
        if (subNote) {
            subNote.textContent =
                subscription && subscription.cancel_at_period_end
                    ? `Renewal cancelled. Access remains active until ${subscription.current_period_end || 'the billing period ends'}.`
                    : (plan.key === 'free' ? 'Upgrade any time; manage your subscription here.' : 'Your subscription is active.');
        }
        if (cancelBtn) {
            cancelBtn.hidden = !(subscription && ['active', 'trialing', 'authenticated'].includes(subscription.status) && !subscription.cancel_at_period_end);
        }
        if (typeof window._refreshJobHistory === 'function') {
            window._refreshJobHistory();
        }
    } else {
        const histList = document.getElementById('job-history-list');
        if (histList) histList.replaceChildren();
    }

    const isBusy = Boolean(state.analysisBusy);
    const guestUsed = document.cookie.includes('marketlens_guest_run=1') || localStorage.getItem('marketlens_guest_run') === '1';
    const limitReached = Boolean(account && account.plan && account.plan.remaining_this_month <= 0);

    const domainSelect = document.getElementById('domain-selector');
    const liveBtn = document.getElementById('btn-live-scrape');
    const fileIn = document.getElementById('file-input');
    const drop = document.getElementById('dropzone');
    const progMsg = document.getElementById('progress-message');

    // ONLY disable inputs while analysis computation is actively in progress
    if (domainSelect) domainSelect.disabled = isBusy;
    if (liveBtn) {
        liveBtn.disabled = isBusy;
        if (isBusy) {
            liveBtn.textContent = 'Running Valuation Pipeline...';
        } else {
            const tickerInput = document.getElementById('ticker-search-input');
            const ticker = tickerInput && tickerInput.value.trim() ? tickerInput.value.trim().toUpperCase() : '';
            if (ticker) {
                liveBtn.textContent = `Run Valuation for ${ticker}`;
            } else if (domainSelect && domainSelect.value && domainSelect.value !== 'Any Random Domain') {
                const shortDomain = domainSelect.value.split('&')[0].trim();
                liveBtn.textContent = `Run Valuation (${shortDomain})`;
            } else {
                liveBtn.textContent = 'Run Institutional Valuation';
            }
        }
    }
    if (fileIn) fileIn.disabled = isBusy;
    if (drop) {
        drop.setAttribute('aria-disabled', String(isBusy));
        drop.classList.toggle('locked', isBusy);
    }
    if (progMsg) {
        if (isBusy) {
            // Handled during execution
        } else if (user && limitReached) {
            progMsg.textContent = 'Monthly quota reached. Upgrade to Professional Advisory or Institutional Fund for expanded access.';
        } else if (!user && guestUsed) {
            progMsg.textContent = 'Guest preview completed. Request executive access to unlock full institutional models and downloads.';
        }
    }

    document.querySelectorAll('.plan-card').forEach(card => {
        card.classList.toggle('current', Boolean(account && card.dataset.planKey === (account.plan && account.plan.key)));
    });
}

export async function refreshAccount() {
    try {
        const account = await apiRequest('/api/v1/auth/me');
        const currentAccount = account.user ? account : null;
        const csrfToken = account.csrf_token || null;
        appState.setState({ currentAccount, csrfToken });
        setAccess(currentAccount);
        if (typeof window._renderPlans === 'function') {
            window._renderPlans();
        }
    } catch {
        appState.setState({ currentAccount: null, csrfToken: null });
        setAccess(null);
    }
}

export async function refreshFeatures() {
    try {
        const health = await apiRequest('/api/v1/health');
        const systemFeatures = health.features || {};
        appState.setState({ systemFeatures });

        const google = document.getElementById('google-signin');
        if (google && !systemFeatures.google_sign_in) {
            google.setAttribute('aria-disabled', 'true');
            google.title = 'Google sign-in is being configured.';
        }
        const billNote = document.getElementById('billing-note');
        if (billNote) {
            if (!systemFeatures.email_verification) {
                billNote.textContent = 'Account verification email is being configured. Subscription checkout is provided by Razorpay after setup.';
            }
            if (!systemFeatures.razorpay) {
                billNote.textContent = 'Paid checkout is disabled until Razorpay credentials, monthly plans, and the webhook are configured.';
            }
        }
    } catch {
        appState.setState({ systemFeatures: {} });
    }
}

export async function activateTrial() {
    const { currentAccount } = appState.getState();
    if (!currentAccount) {
        showAuthPanel('register');
        return;
    }
    try {
        const res = await apiRequest('/api/v1/auth/trial/activate', {
            method: 'POST',
            headers: csrfHeaders()
        });
        showToast(res.message || '14-Day Free Trial Activated!', 'success');
        await refreshAccount();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

export function showPasswordRecovery() {
    const credForm = document.getElementById('credentials-form');
    const recForm = document.getElementById('recovery-form');
    const verResendForm = document.getElementById('verification-resend-form');
    const resetForm = document.getElementById('reset-form');

    if (credForm) credForm.hidden = true;
    if (recForm) recForm.hidden = false;
    if (verResendForm) verResendForm.hidden = true;
    if (resetForm) resetForm.hidden = true;
    setAuthFeedback('Enter your account email and we will send a reset link.');
}

export async function logout() {
    try {
        await apiRequest('/api/v1/auth/logout', { method: 'POST', headers: csrfHeaders() });
    } catch (error) {
        showToast(error.message, 'error');
        return;
    }
    appState.setState({ currentAccount: null, csrfToken: null });
    setAccess(null);
    showAuthPanel('login');
}

export async function submitCredentials(event) {
    if (event) event.preventDefault();
    const emailEl = document.getElementById('auth-email');
    const passEl = document.getElementById('auth-password');
    const email = emailEl ? emailEl.value : '';
    const password = passEl ? passEl.value : '';
    const { authMode } = appState.getState();

    try {
        if (authMode === 'register') {
            const termsCheck = document.getElementById('terms-accepted');
            const res = await apiRequest('/api/v1/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email,
                    password,
                    accepted_terms: termsCheck ? termsCheck.checked : false
                })
            });
            if (res && res.user) {
                appState.setState({
                    currentAccount: res,
                    csrfToken: res.csrf_token
                });
                const authPanel = document.getElementById('auth-panel');
                if (authPanel) authPanel.hidden = true;
                setAccess(res);
                if (typeof window._renderPlans === 'function') {
                    window._renderPlans();
                }
                showToast('Account created and verified! Welcome to MarketLens.', 'success');
            } else {
                setAuthFeedback(res.message || 'Account created. Check your email to verify the address, then sign in.');
                setAuthMode('login');
            }
        } else {
            const account = await apiRequest('/api/v1/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            appState.setState({
                currentAccount: account,
                csrfToken: account.csrf_token
            });
            const authPanel = document.getElementById('auth-panel');
            if (authPanel) authPanel.hidden = true;
            setAccess(account);
            if (typeof window._renderPlans === 'function') {
                window._renderPlans();
            }
        }
    } catch (error) {
        setAuthFeedback(error.message, true);
        if (error.message.toLowerCase().includes('verify your email')) {
            const vEmail = document.getElementById('verification-email');
            const credForm = document.getElementById('credentials-form');
            const vResend = document.getElementById('verification-resend-form');
            if (vEmail) vEmail.value = email;
            if (credForm) credForm.hidden = true;
            if (vResend) vResend.hidden = false;
        }
    }
}

export async function handleAccountLinks() {
    const params = new URLSearchParams(window.location.search);
    const verificationToken = params.get('verify_email');
    const incomingResetToken = params.get('reset_password');

    if (verificationToken) {
        history.replaceState(null, '', window.location.pathname);
        showAuthPanel('login');
        try {
            const result = await apiRequest('/api/v1/auth/verify-email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: verificationToken })
            });
            setAuthFeedback(result.message);
        } catch (error) {
            setAuthFeedback(error.message, true);
        }
    }

    if (incomingResetToken) {
        history.replaceState(null, '', window.location.pathname);
        appState.setState({ resetToken: incomingResetToken });
        const authPanel = document.getElementById('auth-panel');
        const credForm = document.getElementById('credentials-form');
        const recForm = document.getElementById('recovery-form');
        const vResend = document.getElementById('verification-resend-form');
        const resetForm = document.getElementById('reset-form');

        if (authPanel) authPanel.hidden = false;
        if (credForm) credForm.hidden = true;
        if (recForm) recForm.hidden = true;
        if (vResend) vResend.hidden = true;
        if (resetForm) resetForm.hidden = false;
        setAuthFeedback('Choose a new password for your account.');
    }
}

export function redirectToSAML(orgSlug) {
    if (!orgSlug) return;
    window.location.href = `/api/v1/auth/saml/${encodeURIComponent(orgSlug)}/login`;
}

export function initAuth() {
    const credForm = document.getElementById('credentials-form');
    if (credForm) credForm.addEventListener('submit', submitCredentials);

    const googleBtn = document.getElementById('google-signin');
    if (googleBtn) {
        googleBtn.addEventListener('click', event => {
            const { systemFeatures } = appState.getState();
            if (!systemFeatures.google_sign_in) {
                event.preventDefault();
                setAuthFeedback('Google sign-in is being configured.', true);
                return;
            }
            const googleTerms = document.getElementById('google-terms-accepted');
            if (!googleTerms || !googleTerms.checked) {
                event.preventDefault();
                setAuthFeedback('Accept the Terms and Privacy Notice before continuing with Google.', true);
                return;
            }
            googleBtn.href = '/api/v1/auth/google/start?terms_accepted=true';
        });
    }

    const recForm = document.getElementById('recovery-form');
    if (recForm) {
        recForm.addEventListener('submit', async event => {
            event.preventDefault();
            const recEmail = document.getElementById('recovery-email');
            try {
                const result = await apiRequest('/api/v1/auth/password/forgot', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: recEmail ? recEmail.value : '' })
                });
                setAuthFeedback(result.message);
            } catch (error) {
                setAuthFeedback(error.message, true);
            }
        });
    }

    const vResend = document.getElementById('verification-resend-form');
    if (vResend) {
        vResend.addEventListener('submit', async event => {
            event.preventDefault();
            const vEmail = document.getElementById('verification-email');
            try {
                const result = await apiRequest('/api/v1/auth/verification/resend', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: vEmail ? vEmail.value : '' })
                });
                setAuthFeedback(result.message);
            } catch (error) {
                setAuthFeedback(error.message, true);
            }
        });
    }

    const resetForm = document.getElementById('reset-form');
    if (resetForm) {
        resetForm.addEventListener('submit', async event => {
            event.preventDefault();
            const { resetToken } = appState.getState();
            const passEl = document.getElementById('reset-password');
            try {
                const result = await apiRequest('/api/v1/auth/password/reset', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        token: resetToken,
                        password: passEl ? passEl.value : ''
                    })
                });
                appState.setState({ resetToken: null });
                setAuthMode('login');
                setAuthFeedback(result.message);
            } catch (error) {
                setAuthFeedback(error.message, true);
            }
        });
    }
}
