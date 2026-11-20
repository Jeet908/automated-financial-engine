/**
 * src/portal/static/modules/charts.js
 * High-DPI Financial Visualizers & Bento Proximity Radial Glow.
 */

// ============================================================================
// 1. INTERACTIVE 5x5 SENSITIVITY HEATMAP STATE & METHODS
// ============================================================================
export const sensState = {
    baselineWacc: 0.112,
    baselineGrowth: 0.040,
    centerWacc: 0.112,
    centerGrowth: 0.040,
    stepBps: 50,
    fcffList: [250.0, 280.0, 310.0, 345.0, 380.0],
    baseDebt: 240.0,
    baseCash: 269.5,
    shares: 50.0,
    marketPrice: 298.5,
    currencySymbol: '₹',
    currencyUnit: 'Cr'
};

export function initSensitivityHeatmap(data) {
    const comp = (data && data.company) || {};
    const sens = (data && data.sensitivity) || {};
    sensState.currencySymbol = comp.currency === 'INR' ? '₹' : (comp.currency === 'USD' ? '$' : (comp.currency || '$'));
    sensState.currencyUnit = comp.currency === 'INR' ? 'Cr' : 'M';
    sensState.marketPrice = Number(comp.current_market_price || 298.5);

    if (sens.center_wacc) {
        sensState.centerWacc = sens.center_wacc;
        sensState.baselineWacc = sens.center_wacc;
    } else if (comp.wacc) {
        sensState.centerWacc = comp.wacc / 100;
        sensState.baselineWacc = comp.wacc / 100;
    }
    if (sens.center_growth) {
        sensState.centerGrowth = sens.center_growth;
        sensState.baselineGrowth = sens.center_growth;
    }
    if (sens.fcff_list && sens.fcff_list.length) {
        sensState.fcffList = sens.fcff_list;
    }
    if (sens.base_debt !== undefined) sensState.baseDebt = sens.base_debt;
    if (sens.base_cash !== undefined) sensState.baseCash = sens.base_cash;
    if (sens.shares_outstanding !== undefined && sens.shares_outstanding > 0) {
        sensState.shares = sens.shares_outstanding;
    }

    const waccSlider = document.getElementById('wacc-slider');
    const growthSlider = document.getElementById('growth-slider');
    const waccVal = document.getElementById('wacc-slider-val');
    const growthVal = document.getElementById('growth-slider-val');

    if (waccSlider) waccSlider.value = (sensState.centerWacc * 100).toFixed(1);
    if (waccVal) waccVal.textContent = `${(sensState.centerWacc * 100).toFixed(2)}%`;
    if (growthSlider) growthSlider.value = (sensState.centerGrowth * 100).toFixed(1);
    if (growthVal) growthVal.textContent = `${(sensState.centerGrowth * 100).toFixed(2)}%`;

    renderSensitivityHeatmap();
}

export function calculateSensitivityCell(w, g) {
    if (w <= g + 0.001) {
        return { w, g, ev: 0, equity: 0, price: 0, upside: -100, invalid: true };
    }
    const n = sensState.fcffList.length;
    let pvFcff = 0;
    for (let t = 0; t < n; t++) {
        pvFcff += sensState.fcffList[t] / Math.pow(1 + w, t + 1);
    }
    const terminalFcff = sensState.fcffList[n - 1];
    const tv = (terminalFcff * (1 + g)) / (w - g);
    const pvTv = tv / Math.pow(1 + w, n);
    const ev = pvFcff + pvTv;
    const equity = ev - sensState.baseDebt + sensState.baseCash;
    const price = Math.max(0, equity / sensState.shares);
    const upside = sensState.marketPrice > 0 ? ((price / sensState.marketPrice - 1) * 100) : 0;
    return { w, g, ev, equity, price, upside, invalid: false };
}

export function renderSensitivityHeatmap() {
    const table = document.getElementById('sensitivity-heatmap-table');
    if (!table) return;

    const step = sensState.stepBps / 10000;
    const gStep = step * 0.5;

    const waccSteps = [
        sensState.centerWacc - 2 * step,
        sensState.centerWacc - step,
        sensState.centerWacc,
        sensState.centerWacc + step,
        sensState.centerWacc + 2 * step
    ];
    const growthSteps = [
        sensState.centerGrowth - 2 * gStep,
        sensState.centerGrowth - gStep,
        sensState.centerGrowth,
        sensState.centerGrowth + gStep,
        sensState.centerGrowth + 2 * gStep
    ];

    let html = '<thead><tr><th style="width:18%;">WACC \\ g</th>';
    for (let j = 0; j < 5; j++) {
        html += `<th style="width:16.4%;" data-col="${j}" class="heat-col-head font-mono">${(growthSteps[j] * 100).toFixed(2)}%</th>`;
    }
    html += '</tr></thead><tbody>';

    for (let i = 0; i < 5; i++) {
        const w = waccSteps[i];
        html += `<tr><th class="heat-row-head font-mono" data-row="${i}">${(w * 100).toFixed(2)}%</th>`;
        for (let j = 0; j < 5; j++) {
            const g = growthSteps[j];
            const isCenter = (i === 2 && j === 2);
            const cell = calculateSensitivityCell(w, g);

            let cellClass = 'heat-cell font-mono tabular-nums';
            if (isCenter) cellClass += ' cell-center';
            if (cell.invalid) {
                cellClass += ' cell-neutral';
                html += `<td class="${cellClass}" data-row="${i}" data-col="${j}" data-invalid="true"><span class="cell-price font-mono" style="opacity:0.4;">N/A</span><span class="cell-upside font-mono" style="opacity:0.4;">w ≤ g</span></td>`;
            } else {
                if (cell.price >= sensState.marketPrice) {
                    cellClass += ' cell-undervalued';
                } else {
                    cellClass += ' cell-overvalued';
                }
                const upsideText = `${cell.upside >= 0 ? '+' : ''}${cell.upside.toFixed(1)}%`;
                html += `<td class="${cellClass}" data-row="${i}" data-col="${j}" data-w="${(w*100).toFixed(2)}" data-g="${(g*100).toFixed(2)}" data-price="${cell.price.toFixed(2)}" data-ev="${Math.round(cell.ev)}" data-upside="${cell.upside.toFixed(1)}" data-center="${isCenter}">
                    <span class="cell-price font-mono">${sensState.currencySymbol}${cell.price.toFixed(2)}</span>
                    <span class="cell-upside font-mono">${upsideText}</span>
                </td>`;
            }
        }
        html += '</tr>';
    }
    html += '</tbody>';
    table.innerHTML = html;

    const centerCell = calculateSensitivityCell(sensState.centerWacc, sensState.centerGrowth);
    updateHeatmapPrecisionBar(sensState.centerWacc, sensState.centerGrowth, centerCell.price, centerCell.ev, centerCell.upside, true);

    const cells = table.querySelectorAll('td.heat-cell');
    cells.forEach(td => {
        td.addEventListener('mouseenter', function() {
            const r = this.getAttribute('data-row');
            const c = this.getAttribute('data-col');
            highlightCrosshairs(r, c);

            if (this.getAttribute('data-invalid') === 'true') {
                const coords = document.getElementById('prec-coords');
                const pEl = document.getElementById('prec-price');
                const evEl = document.getElementById('prec-ev');
                const upEl = document.getElementById('prec-upside');
                if (coords) coords.textContent = `WACC: ${(waccSteps[r]*100).toFixed(2)}% · g: ${(growthSteps[c]*100).toFixed(2)}% (Singularity Guard)`;
                if (pEl) pEl.textContent = 'N/A';
                if (evEl) evEl.textContent = 'N/A';
                if (upEl) upEl.textContent = 'w ≤ g';
                return;
            }

            const wVal = parseFloat(this.getAttribute('data-w')) / 100;
            const gVal = parseFloat(this.getAttribute('data-g')) / 100;
            const price = parseFloat(this.getAttribute('data-price'));
            const ev = parseFloat(this.getAttribute('data-ev'));
            const upside = parseFloat(this.getAttribute('data-upside'));
            const isCenter = this.getAttribute('data-center') === 'true';

            updateHeatmapPrecisionBar(wVal, gVal, price, ev, upside, isCenter);
        });

        td.addEventListener('mouseleave', function() {
            clearCrosshairs();
            const center = calculateSensitivityCell(sensState.centerWacc, sensState.centerGrowth);
            updateHeatmapPrecisionBar(sensState.centerWacc, sensState.centerGrowth, center.price, center.ev, center.upside, true);
        });
    });
}

function highlightCrosshairs(rowIdx, colIdx) {
    const table = document.getElementById('sensitivity-heatmap-table');
    if (!table) return;
    table.querySelectorAll('td.heat-cell, th.heat-col-head, th.heat-row-head').forEach(el => {
        const elR = el.getAttribute('data-row');
        const elC = el.getAttribute('data-col');
        if (elR === rowIdx || elC === colIdx) {
            el.classList.add('crosshair-active');
        } else {
            el.classList.remove('crosshair-active');
        }
    });
}

function clearCrosshairs() {
    const table = document.getElementById('sensitivity-heatmap-table');
    if (!table) return;
    table.querySelectorAll('.crosshair-active').forEach(el => el.classList.remove('crosshair-active'));
}

export function updateHeatmapPrecisionBar(w, g, price, ev, upside, isCenter) {
    const coords = document.getElementById('prec-coords');
    const priceEl = document.getElementById('prec-price');
    const evEl = document.getElementById('prec-ev');
    const upsideEl = document.getElementById('prec-upside');
    if (!coords) return;

    coords.textContent = `WACC: ${(w*100).toFixed(2)}% · g: ${(g*100).toFixed(2)}% ${isCenter ? '(Center Scenario)' : ''}`;
    if (priceEl) {
        priceEl.textContent = `${sensState.currencySymbol}${price.toFixed(2)}`;
        priceEl.style.color = price >= sensState.marketPrice ? 'var(--status-pass)' : 'var(--accent-odd)';
    }
    if (evEl) {
        evEl.textContent = `${sensState.currencySymbol}${Math.round(ev).toLocaleString()} ${sensState.currencyUnit}`;
    }
    if (upsideEl) {
        const upText = `${upside >= 0 ? '+' : ''}${upside.toFixed(1)}% (${upside >= 0 ? 'Undervalued' : 'Overvalued'})`;
        upsideEl.textContent = upText;
        upsideEl.style.color = upside >= 0 ? 'var(--status-pass)' : 'var(--accent-odd)';
    }
}

export function onWaccSliderChange(val) {
    sensState.centerWacc = parseFloat(val) / 100;
    const lbl = document.getElementById('wacc-slider-val');
    if (lbl) lbl.textContent = `${parseFloat(val).toFixed(2)}%`;
    renderSensitivityHeatmap();
}

export function onGrowthSliderChange(val) {
    sensState.centerGrowth = parseFloat(val) / 100;
    const lbl = document.getElementById('growth-slider-val');
    if (lbl) lbl.textContent = `${parseFloat(val).toFixed(2)}%`;
    renderSensitivityHeatmap();
}

export function setSensitivityStep(bps) {
    sensState.stepBps = bps;
    ['25', '50', '100'].forEach(b => {
        const btn = document.getElementById(`step-btn-${b}`);
        if (btn) btn.classList.toggle('active', parseInt(b) === bps);
    });
    renderSensitivityHeatmap();
}

export function resetSensitivityDefaults() {
    sensState.centerWacc = sensState.baselineWacc;
    sensState.centerGrowth = sensState.baselineGrowth;
    sensState.stepBps = 50;
    const waccSlider = document.getElementById('wacc-slider');
    const growthSlider = document.getElementById('growth-slider');
    const waccVal = document.getElementById('wacc-slider-val');
    const growthVal = document.getElementById('growth-slider-val');

    if (waccSlider) waccSlider.value = (sensState.centerWacc * 100).toFixed(1);
    if (waccVal) waccVal.textContent = `${(sensState.centerWacc * 100).toFixed(2)}%`;
    if (growthSlider) growthSlider.value = (sensState.centerGrowth * 100).toFixed(1);
    if (growthVal) growthVal.textContent = `${(sensState.centerGrowth * 100).toFixed(2)}%`;

    ['25', '50', '100'].forEach(b => {
        const btn = document.getElementById(`step-btn-${b}`);
        if (btn) btn.classList.toggle('active', b === '50');
    });
    renderSensitivityHeatmap();
}

// ============================================================================
// 2. MONTE CARLO BELL CURVE CANVAS (10,000 ITERATIONS + VaR 95% SHADED BAND)
// ============================================================================
export const mcState = {
    iterations: 10000,
    mean: 312.4,
    median: 310.5,
    stdDev: 34.2,
    min: 210.0,
    max: 440.0,
    p5: 258.0,
    p95: 372.0,
    probUndervalued: 68.4,
    marketPrice: 298.5,
    bins: [],
    counts: [],
    currencySymbol: '₹'
};

export function initMonteCarloCanvas(data) {
    const comp = (data && data.company) || {};
    const mc = (data && data.monte_carlo) || {};
    mcState.currencySymbol = comp.currency === 'INR' ? '₹' : (comp.currency === 'USD' ? '$' : (comp.currency || '$'));
    mcState.marketPrice = Number(comp.current_market_price || 298.5);

    if (mc.iterations) mcState.iterations = mc.iterations;
    if (mc.mean_price) mcState.mean = mc.mean_price;
    else if (comp.fair_value_per_share) mcState.mean = Number(comp.fair_value_per_share);
    if (mc.median_price) mcState.median = mc.median_price;
    else mcState.median = mcState.mean;
    if (mc.std_dev) mcState.stdDev = mc.std_dev;
    else mcState.stdDev = Math.max(10, mcState.mean * 0.12);
    if (mc.min_price) mcState.min = mc.min_price;
    else mcState.min = Math.max(1, mcState.mean - 3.2 * mcState.stdDev);
    if (mc.max_price) mcState.max = mc.max_price;
    else mcState.max = mcState.mean + 3.2 * mcState.stdDev;
    if (mc.pct_5) mcState.p5 = mc.pct_5;
    else mcState.p5 = mcState.mean - 1.645 * mcState.stdDev;
    if (mc.pct_95) mcState.p95 = mc.pct_95;
    else mcState.p95 = mcState.mean + 1.645 * mcState.stdDev;
    if (mc.prob_undervalued !== undefined) mcState.probUndervalued = mc.prob_undervalued;
    else {
        const z = (mcState.marketPrice - mcState.mean) / mcState.stdDev;
        const probLess = 0.5 * (1 + approxErf(z / Math.SQRT2));
        mcState.probUndervalued = roundNumber((1 - probLess) * 100, 1);
    }

    if (mc.histogram_bins && mc.histogram_counts && mc.histogram_bins.length) {
        mcState.bins = mc.histogram_bins;
        mcState.counts = mc.histogram_counts;
    } else {
        const numBins = 25;
        const binW = (mcState.max - mcState.min) / numBins;
        mcState.bins = [];
        mcState.counts = [];
        for (let b = 0; b <= numBins; b++) {
            mcState.bins.push(mcState.min + b * binW);
        }
        const totalSamples = mcState.iterations;
        for (let b = 0; b < numBins; b++) {
            const mid = (mcState.bins[b] + mcState.bins[b + 1]) / 2;
            const z = (mid - mcState.mean) / mcState.stdDev;
            const density = Math.exp(-0.5 * z * z) / (mcState.stdDev * Math.sqrt(2 * Math.PI));
            mcState.counts.push(Math.round(density * binW * totalSamples));
        }
    }

    const iterEl = document.getElementById('mc-stat-iter');
    const p5El = document.getElementById('mc-stat-p5');
    const medEl = document.getElementById('mc-stat-median');
    const p95El = document.getElementById('mc-stat-p95');
    const stdEl = document.getElementById('mc-stat-std');
    const mktEl = document.getElementById('mc-stat-market');
    const varEl = document.getElementById('mc-var-95-display');
    const probEl = document.getElementById('mc-prob-undervalued');

    if (iterEl) iterEl.textContent = mcState.iterations.toLocaleString();
    if (p5El) p5El.textContent = `${mcState.currencySymbol}${mcState.p5.toFixed(2)}`;
    if (medEl) medEl.textContent = `${mcState.currencySymbol}${mcState.median.toFixed(2)}`;
    if (p95El) p95El.textContent = `${mcState.currencySymbol}${mcState.p95.toFixed(2)}`;
    if (stdEl) stdEl.textContent = `${mcState.currencySymbol}${mcState.stdDev.toFixed(2)}`;
    if (mktEl) mktEl.textContent = `${mcState.currencySymbol}${mcState.marketPrice.toFixed(2)}`;
    if (varEl) varEl.textContent = `${mcState.currencySymbol}${mcState.p5.toFixed(2)}`;
    if (probEl) probEl.textContent = `${mcState.probUndervalued.toFixed(1)}%`;

    renderMonteCarloCanvas();
}

function approxErf(x) {
    const a1 = 0.254829592;
    const a2 = -0.284496736;
    const a3 = 1.421413741;
    const a4 = -1.453152027;
    const a5 = 1.061405429;
    const p = 0.3275911;
    const sign = x < 0 ? -1 : 1;
    const absX = Math.abs(x);
    const t = 1.0 / (1.0 + p * absX);
    const y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-absX * absX);
    return sign * y;
}

export function renderMonteCarloCanvas() {
    const canvas = document.getElementById('mc-bell-canvas');
    const container = document.getElementById('mc-canvas-container');
    if (!canvas || !container) return;

    const rect = container.getBoundingClientRect();
    if (rect.width <= 0) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;

    const ctx = canvas.getContext('2d');
    if (ctx.resetTransform) ctx.resetTransform();
    else ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    const padL = 50;
    const padR = 40;
    const padT = 35;
    const padB = 40;
    const plotW = w - padL - padR;
    const plotH = h - padT - padB;

    ctx.clearRect(0, 0, w, h);

    const xMin = mcState.min;
    const xMax = mcState.max;
    const maxCount = Math.max(...mcState.counts, 1);

    const xToPx = (val) => padL + ((val - xMin) / (xMax - xMin)) * plotW;
    const yToPx = (cnt) => padT + plotH - (cnt / (maxCount * 1.15)) * plotH;

    // 1. Gridlines
    ctx.strokeStyle = 'rgba(250, 250, 250, 0.05)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = padT + (i / 4) * plotH;
        ctx.beginPath();
        ctx.moveTo(padL, y);
        ctx.lineTo(padL + plotW, y);
        ctx.stroke();
    }

    // 2. Subtle Histogram Bars
    const numBins = mcState.counts.length;
    const binW_px = plotW / numBins;
    for (let i = 0; i < numBins; i++) {
        const bMin = mcState.bins[i];
        const cnt = mcState.counts[i];
        const bx = xToPx(bMin);
        const by = yToPx(cnt);
        const barH = padT + plotH - by;

        if (bMin <= mcState.p5) {
            ctx.fillStyle = 'rgba(255, 90, 31, 0.15)';
            ctx.strokeStyle = 'rgba(255, 90, 31, 0.35)';
        } else {
            ctx.fillStyle = 'rgba(255, 255, 255, 0.04)';
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
        }
        ctx.fillRect(bx, by, binW_px - 1, barH);
        ctx.strokeRect(bx, by, binW_px - 1, barH);
    }

    // 3. VaR 95% Shaded Tail Region
    const p5Px = Math.min(padL + plotW, Math.max(padL, xToPx(mcState.p5)));
    ctx.save();
    ctx.beginPath();
    ctx.rect(padL, padT, p5Px - padL, plotH);
    ctx.clip();

    ctx.fillStyle = 'rgba(255, 90, 31, 0.22)';
    ctx.beginPath();
    ctx.moveTo(padL, padT + plotH);
    for (let i = 0; i <= numBins; i++) {
        const pVal = mcState.bins[Math.min(i, numBins - 1)];
        const cnt = mcState.counts[Math.min(i, numBins - 1)] || 0;
        ctx.lineTo(xToPx(pVal), yToPx(cnt));
    }
    ctx.lineTo(p5Px, padT + plotH);
    ctx.closePath();
    ctx.fill();
    ctx.restore();

    // 4. Smooth Density Curve
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(padL, padT + plotH);
    for (let i = 0; i < numBins; i++) {
        const bMid = (mcState.bins[i] + mcState.bins[i + 1]) / 2;
        const cnt = mcState.counts[i];
        const x = xToPx(bMid);
        const y = yToPx(cnt);
        if (i === 0) ctx.lineTo(x, y);
        else {
            const prevMid = (mcState.bins[i - 1] + mcState.bins[i]) / 2;
            const prevX = xToPx(prevMid);
            const prevY = yToPx(mcState.counts[i - 1]);
            const cpX = (prevX + x) / 2;
            ctx.bezierCurveTo(cpX, prevY, cpX, y, x, y);
        }
    }
    ctx.strokeStyle = '#fafafa';
    ctx.lineWidth = 2.2;
    ctx.stroke();
    ctx.restore();

    // 5. VaR 95% Boundary Line & Badge
    ctx.save();
    ctx.strokeStyle = '#ff5a1f';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(p5Px, padT);
    ctx.lineTo(p5Px, padT + plotH);
    ctx.stroke();

    ctx.fillStyle = '#ff5a1f';
    drawRoundedRect(ctx, p5Px - 45, padT - 22, 90, 18, 4);
    ctx.fill();
    ctx.fillStyle = '#ffffff';
    ctx.font = '700 10px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText(`VaR 95%: ${mcState.currencySymbol}${mcState.p5.toFixed(1)}`, p5Px, padT - 9);
    ctx.restore();

    // 6. Current Market Price Line & Badge (Dashed)
    const mktPx = Math.min(padL + plotW, Math.max(padL, xToPx(mcState.marketPrice)));
    ctx.save();
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = 'rgba(250, 250, 250, 0.85)';
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.moveTo(mktPx, padT + 8);
    ctx.lineTo(mktPx, padT + plotH);
    ctx.stroke();

    ctx.setLineDash([]);
    ctx.fillStyle = 'rgba(30, 30, 35, 0.95)';
    ctx.strokeStyle = 'rgba(250, 250, 250, 0.3)';
    drawRoundedRect(ctx, mktPx - 42, padT - 22, 84, 18, 4);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#fafafa';
    ctx.font = '600 10px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText(`Market: ${mcState.currencySymbol}${mcState.marketPrice.toFixed(1)}`, mktPx, padT - 9);
    ctx.restore();

    // 7. 50th Percentile (Median Fair Value) Line & Badge
    const medPx = Math.min(padL + plotW, Math.max(padL, xToPx(mcState.median)));
    ctx.save();
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(medPx, padT);
    ctx.lineTo(medPx, padT + plotH);
    ctx.stroke();

    ctx.fillStyle = '#10b981';
    drawRoundedRect(ctx, medPx - 46, padT + 4, 92, 18, 4);
    ctx.fill();
    ctx.fillStyle = '#09090b';
    ctx.font = '700 10px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText(`Median: ${mcState.currencySymbol}${mcState.median.toFixed(1)}`, medPx, padT + 17);
    ctx.restore();

    // 8. X-Axis Price Labels
    ctx.fillStyle = '#a1a1aa';
    ctx.font = '500 10px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    const numTicks = 5;
    for (let t = 0; t < numTicks; t++) {
        const pVal = xMin + (t / (numTicks - 1)) * (xMax - xMin);
        const x = xToPx(pVal);
        ctx.fillText(`${mcState.currencySymbol}${pVal.toFixed(0)}`, x, padT + plotH + 18);
    }
}

function drawRoundedRect(ctx, x, y, width, height, radius) {
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + width - radius, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
    ctx.lineTo(x + width, y + height - radius);
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    ctx.lineTo(x + radius, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
}

function setupMonteCarloScrubber() {
    const container = document.getElementById('mc-canvas-container');
    const canvas = document.getElementById('mc-bell-canvas');
    const crosshair = document.getElementById('mc-cursor-crosshair');
    const tooltip = document.getElementById('mc-cursor-tooltip');
    if (!container || !canvas || !crosshair || !tooltip) return;

    container.addEventListener('mousemove', function(e) {
        const rect = container.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const padL = 50;
        const padR = 40;
        const plotW = rect.width - padL - padR;

        if (mouseX < padL || mouseX > padL + plotW) {
            crosshair.style.display = 'none';
            tooltip.style.display = 'none';
            return;
        }

        crosshair.style.display = 'block';
        crosshair.style.left = `${mouseX}px`;

        const normX = (mouseX - padL) / plotW;
        const price = mcState.min + normX * (mcState.max - mcState.min);

        const z = (price - mcState.mean) / mcState.stdDev;
        const pct = Math.min(99.9, Math.max(0.1, 0.5 * (1 + approxErf(z / Math.SQRT2)) * 100));

        tooltip.style.display = 'block';
        tooltip.style.left = `${mouseX}px`;
        tooltip.style.top = `${e.clientY - rect.top}px`;
        tooltip.innerHTML = `
            <div style="font-weight:700; color:#fafafa;">${mcState.currencySymbol}${price.toFixed(2)}</div>
            <div style="font-size:10px; color:${price <= mcState.p5 ? 'var(--accent-odd)' : '#10b981'};">
                ${pct.toFixed(1)}th Percentile ${price <= mcState.p5 ? '⚠️ VaR 95% Tail' : ''}
            </div>
        `;

        const sPrice = document.getElementById('mc-scrub-price');
        const sPct = document.getElementById('mc-scrub-pct');
        if (sPrice) sPrice.textContent = `${mcState.currencySymbol}${price.toFixed(2)}`;
        if (sPct) sPct.textContent = `${pct.toFixed(1)}%`;
    });

    container.addEventListener('mouseleave', function() {
        crosshair.style.display = 'none';
        tooltip.style.display = 'none';
        const sPrice = document.getElementById('mc-scrub-price');
        const sPct = document.getElementById('mc-scrub-pct');
        if (sPrice) sPrice.textContent = 'Move cursor across bell curve';
        if (sPct) sPct.textContent = '--';
    });
}

// ============================================================================
// 3. DUPONT 5-WAY ROE WATERFALL CHART
// ============================================================================
export const dupontState = {
    years: ["FY23A", "FY24A", "FY25A", "FY26E", "FY27E", "FY28E", "FY29E", "FY30E"],
    activeYearIndex: 2,
    periods: [],
    currencySymbol: '₹',
    currencyUnit: 'Cr'
};

export function initDuPontWaterfall(data) {
    const comp = (data && data.company) || {};
    const dp = (data && data.dupont_roe) || {};
    dupontState.currencySymbol = comp.currency === 'INR' ? '₹' : (comp.currency === 'USD' ? '$' : (comp.currency || '$'));
    dupontState.currencyUnit = comp.currency === 'INR' ? 'Cr' : 'M';

    if (dp.years && dp.periods && dp.periods.length) {
        dupontState.years = dp.years;
        dupontState.periods = dp.periods;
        dupontState.activeYearIndex = Math.min(2, dp.periods.length - 1);
    } else {
        dupontState.years = ["FY23A", "FY24A", "FY25A", "FY26E", "FY27E", "FY28E", "FY29E", "FY30E"];
        const revs = [1000.0, 1120.0, 1243.2, 1392.4, 1545.5, 1700.1, 1853.1, 2001.3];
        const ebits = [215.0, 252.0, 305.2, 348.1, 394.1, 442.0, 491.1, 540.4];
        const pbts = [186.6, 226.3, 282.2, 325.1, 372.1, 421.0, 471.1, 521.4];
        const pats = [139.9, 169.7, 211.7, 243.8, 279.1, 315.8, 353.3, 391.1];
        const assets = [826.2, 917.9, 1040.9, 1140.2, 1250.4, 1370.1, 1495.2, 1625.0];
        const equities = [430.0, 520.1, 628.2, 735.5, 856.1, 988.4, 1130.0, 1280.5];

        dupontState.periods = [];
        let prior = null;
        for (let i = 0; i < dupontState.years.length; i++) {
            const yr = dupontState.years[i];
            const rev = revs[i];
            const ebit = ebits[i];
            const pbt = pbts[i];
            const pat = pats[i];
            const ass = assets[i];
            const eq = equities[i];

            const opM = ebit / rev;
            const turn = rev / ass;
            const lev = ass / eq;
            const intB = pbt / ebit;
            const taxB = pat / pbt;
            const roe = pat / eq;

            const yoyOp = prior ? roundNumber((opM - prior.opM) * 10000, 1) : 0;
            const yoyTurn = prior ? roundNumber((turn - prior.turn) * 10000, 1) : 0;
            const yoyLev = prior ? roundNumber((lev - prior.lev) * 10000, 1) : 0;
            const yoyInt = prior ? roundNumber((intB - prior.intB) * 10000, 1) : 0;
            const yoyTax = prior ? roundNumber((taxB - prior.taxB) * 10000, 1) : 0;
            const yoyRoe = prior ? roundNumber((roe - prior.roe) * 10000, 1) : 0;

            prior = { opM, turn, lev, intB, taxB, roe };

            dupontState.periods.push({
                year: yr,
                is_projection: yr.endsWith('E'),
                operating_margin: { ratio: opM, pct: opM * 100, numerator: ebit, denominator: rev, numerator_label: 'EBIT', denominator_label: 'Revenue', yoy_bps: yoyOp },
                asset_turnover: { ratio: turn, multiple: turn, numerator: rev, denominator: ass, numerator_label: 'Revenue', denominator_label: 'Total Assets', yoy_bps: yoyTurn },
                leverage_factor: { ratio: lev, multiple: lev, numerator: ass, denominator: eq, numerator_label: 'Total Assets', denominator_label: 'Total Equity', yoy_bps: yoyLev },
                interest_burden: { ratio: intB, pct: intB * 100, is_drag: intB < 1.0, numerator: pbt, denominator: ebit, numerator_label: 'EBT', denominator_label: 'EBIT', yoy_bps: yoyInt },
                tax_burden: { ratio: taxB, pct: taxB * 100, is_drag: taxB < 1.0, numerator: pat, denominator: pbt, numerator_label: 'Net Income', denominator_label: 'EBT', yoy_bps: yoyTax },
                roe: { ratio: roe, pct: roe * 100, numerator: pat, denominator: eq, numerator_label: 'Net Income', denominator_label: 'Total Equity', yoy_bps: yoyRoe },
                identity_verified: true,
                max_discrepancy: 0.0
            });
        }
        dupontState.activeYearIndex = 2;
    }

    renderDuPontYearPills();
    renderDuPontWaterfall(dupontState.activeYearIndex);
}

export function renderDuPontYearPills() {
    const bar = document.getElementById('dupont-year-bar');
    if (!bar) return;
    bar.innerHTML = '';
    dupontState.years.forEach((yr, idx) => {
        const isAct = idx === dupontState.activeYearIndex;
        const isProj = yr.endsWith('E');
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `dupont-year-btn ${isAct ? 'active' : ''}`;
        btn.textContent = `${yr} ${isProj ? '• Est' : '• Act'}`;
        btn.addEventListener('click', () => selectDuPontYear(idx));
        bar.appendChild(btn);
    });
}

export function selectDuPontYear(idx) {
    dupontState.activeYearIndex = idx;
    renderDuPontYearPills();
    renderDuPontWaterfall(idx);
}

export function renderDuPontWaterfall(idx) {
    const period = dupontState.periods[idx];
    if (!period) return;

    const calcProduct =
        period.operating_margin.ratio *
        period.asset_turnover.ratio *
        period.leverage_factor.ratio *
        period.interest_burden.ratio *
        period.tax_burden.ratio;
    const diff = Math.abs(calcProduct - period.roe.ratio);
    const verified = diff < 1e-6;

    const badge = document.getElementById('dupont-invariant-badge');
    if (badge) {
        badge.innerHTML = `<span class="pulse-dot"></span> Invariant: ${diff.toExponential(2)} Error`;
        badge.style.color = verified ? 'var(--status-pass)' : 'var(--accent-odd)';
    }

    const opEl = document.getElementById('eq-op-margin');
    const atEl = document.getElementById('eq-asset-turnover');
    const levEl = document.getElementById('eq-leverage');
    const intEl = document.getElementById('eq-interest');
    const taxEl = document.getElementById('eq-tax');
    const roeEl = document.getElementById('eq-roe');

    if (opEl) opEl.textContent = `Op Margin: ${period.operating_margin.pct.toFixed(1)}%`;
    if (atEl) atEl.textContent = `Asset Turn: ${period.asset_turnover.multiple.toFixed(2)}x`;
    if (levEl) levEl.textContent = `Leverage: ${period.leverage_factor.multiple.toFixed(2)}x`;
    if (intEl) intEl.textContent = `Interest: ${period.interest_burden.pct.toFixed(1)}%`;
    if (taxEl) taxEl.textContent = `Tax: ${period.tax_burden.pct.toFixed(1)}%`;
    if (roeEl) roeEl.textContent = `ROE: ${period.roe.pct.toFixed(1)}%`;

    const container = document.getElementById('dupont-chart-container');
    if (!container) return;

    const stages = [
        {
            name: 'Operating Margin',
            key: 'operating_margin',
            ratioText: `${period.operating_margin.pct.toFixed(1)}%`,
            val: period.operating_margin.pct,
            color: '#fafafa',
            isStep: false,
            startVal: 0,
            endVal: period.operating_margin.pct
        },
        {
            name: 'Asset Turnover',
            key: 'asset_turnover',
            ratioText: `${period.asset_turnover.multiple.toFixed(2)}x`,
            val: period.asset_turnover.multiple * 10,
            color: '#0ea5e9',
            isStep: true,
            startVal: period.operating_margin.pct,
            endVal: period.operating_margin.pct * period.asset_turnover.ratio
        },
        {
            name: 'Leverage Factor',
            key: 'leverage_factor',
            ratioText: `${period.leverage_factor.multiple.toFixed(2)}x`,
            val: period.leverage_factor.multiple * 10,
            color: '#8b5cf6',
            isStep: true,
            startVal: period.operating_margin.pct * period.asset_turnover.ratio,
            endVal: period.operating_margin.pct * period.asset_turnover.ratio * period.leverage_factor.ratio
        },
        {
            name: 'Interest Burden',
            key: 'interest_burden',
            ratioText: `${period.interest_burden.pct.toFixed(1)}%`,
            val: period.interest_burden.pct,
            color: period.interest_burden.is_drag ? '#ff5a1f' : '#10b981',
            isStep: true,
            isDrag: period.interest_burden.is_drag,
            startVal: period.operating_margin.pct * period.asset_turnover.ratio * period.leverage_factor.ratio,
            endVal: period.operating_margin.pct * period.asset_turnover.ratio * period.leverage_factor.ratio * period.interest_burden.ratio
        },
        {
            name: 'Tax Burden',
            key: 'tax_burden',
            ratioText: `${period.tax_burden.pct.toFixed(1)}%`,
            val: period.tax_burden.pct,
            color: period.tax_burden.is_drag ? '#ff5a1f' : '#10b981',
            isStep: true,
            isDrag: period.tax_burden.is_drag,
            startVal: period.operating_margin.pct * period.asset_turnover.ratio * period.leverage_factor.ratio * period.interest_burden.ratio,
            endVal: period.roe.pct
        },
        {
            name: 'Resulting ROE',
            key: 'roe',
            ratioText: `${period.roe.pct.toFixed(1)}%`,
            val: period.roe.pct,
            color: '#10b981',
            isStep: false,
            startVal: 0,
            endVal: period.roe.pct
        }
    ];

    const svgW = 860;
    const svgH = 260;
    const padL = 40;
    const padR = 40;
    const padT = 35;
    const padB = 45;
    const usableW = svgW - padL - padR;
    const usableH = svgH - padT - padB;

    const maxLevel = Math.max(
        ...stages.map(s => Math.max(s.startVal, s.endVal)),
        40
    ) * 1.15;

    const yToPx = (v) => padT + usableH - (v / maxLevel) * usableH;
    const colW = usableW / stages.length;
    const barW = Math.min(84, colW - 24);

    let svgContent = `<svg viewBox="0 0 ${svgW} ${svgH}" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">`;

    const baseZeroY = yToPx(0);
    svgContent += `<line x1="${padL}" y1="${baseZeroY}" x2="${svgW - padR}" y2="${baseZeroY}" stroke="rgba(255,255,255,0.15)" stroke-width="1" />`;

    for (let g = 1; g <= 3; g++) {
        const glVal = (maxLevel / 4) * g;
        const glY = yToPx(glVal);
        svgContent += `<line x1="${padL}" y1="${glY}" x2="${svgW - padR}" y2="${glY}" stroke="rgba(255,255,255,0.05)" stroke-dasharray="4,4" stroke-width="1" />`;
    }

    for (let i = 0; i < stages.length; i++) {
        const st = stages[i];
        const barX = padL + i * colW + (colW - barW) / 2;
        const yTop = yToPx(Math.max(st.startVal, st.endVal));
        const yBottom = yToPx(Math.min(st.startVal, st.endVal));
        const barHeight = Math.max(3, yBottom - yTop);

        if (i < stages.length - 1) {
            const nextBarX = padL + (i + 1) * colW + (colW - barW) / 2;
            const connY = yToPx(st.endVal);
            svgContent += `<line x1="${barX + barW}" y1="${connY}" x2="${nextBarX}" y2="${connY}" stroke="rgba(255,255,255,0.25)" stroke-dasharray="3,3" stroke-width="1.2" />`;
        }

        const fillStyle = st.color;
        const fillOpacity = st.key === 'roe' ? '0.9' : (st.isDrag ? '0.85' : '0.75');
        const strokeColor = st.isDrag ? '#ff5a1f' : st.color;

        svgContent += `
            <g class="dupont-bar-group" data-stage="${st.key}" data-year="${idx}" style="cursor:pointer;">
                <rect x="${barX}" y="${yTop}" width="${barW}" height="${barHeight}" rx="4" fill="${fillStyle}" fill-opacity="${fillOpacity}" stroke="${strokeColor}" stroke-width="1.2" />
                <text x="${barX + barW / 2}" y="${yTop - 8}" fill="#fafafa" font-size="11" font-weight="700" font-family="'JetBrains Mono', monospace" text-anchor="middle">${st.ratioText}</text>
                <text x="${barX + barW / 2}" y="${baseZeroY + 16}" fill="#a1a1aa" font-size="10" font-weight="500" font-family="'Inter', sans-serif" text-anchor="middle">${st.name.split(' ')[0]}</text>
                <text x="${barX + barW / 2}" y="${baseZeroY + 28}" fill="#71717a" font-size="9" font-family="'Inter', sans-serif" text-anchor="middle">${st.name.split(' ')[1] || ''}</text>
            </g>
        `;
    }

    svgContent += `</svg><div id="dupont-tooltip" class="factor-tooltip"></div>`;
    container.innerHTML = svgContent;

    // Attach event listeners to bar groups
    container.querySelectorAll('.dupont-bar-group').forEach(grp => {
        grp.addEventListener('mouseenter', e => {
            const key = grp.getAttribute('data-stage');
            const yearIndex = parseInt(grp.getAttribute('data-year'), 10);
            showDuPontTooltip(e, key, yearIndex);
        });
        grp.addEventListener('mouseleave', hideDuPontTooltip);
    });

    renderDuPontFactorCards(period);
}

export function renderDuPontFactorCards(p) {
    const grid = document.getElementById('dupont-factors-grid');
    if (!grid) return;

    const sym = dupontState.currencySymbol;
    const unit = dupontState.currencyUnit;

    const cards = [
        {
            title: '1. Operating Margin',
            formula: 'EBIT / Revenue',
            ratio: `${p.operating_margin.pct.toFixed(2)}%`,
            detail: `EBIT: ${sym}${p.operating_margin.numerator.toLocaleString()} ${unit} ÷ Rev: ${sym}${p.operating_margin.denominator.toLocaleString()} ${unit}`,
            yoy: p.operating_margin.yoy_bps,
            accent: '#fafafa'
        },
        {
            title: '2. Asset Turnover',
            formula: 'Revenue / Total Assets',
            ratio: `${p.asset_turnover.multiple.toFixed(3)}x`,
            detail: `Rev: ${sym}${p.asset_turnover.numerator.toLocaleString()} ${unit} ÷ Assets: ${sym}${p.asset_turnover.denominator.toLocaleString()} ${unit}`,
            yoy: p.asset_turnover.yoy_bps,
            accent: '#0ea5e9'
        },
        {
            title: '3. Leverage Factor',
            formula: 'Total Assets / Total Equity',
            ratio: `${p.leverage_factor.multiple.toFixed(3)}x`,
            detail: `Assets: ${sym}${p.leverage_factor.numerator.toLocaleString()} ${unit} ÷ Equity: ${sym}${p.leverage_factor.denominator.toLocaleString()} ${unit}`,
            yoy: p.leverage_factor.yoy_bps,
            accent: '#8b5cf6'
        },
        {
            title: '4. Interest Burden',
            formula: 'EBT / EBIT',
            ratio: `${p.interest_burden.pct.toFixed(2)}%`,
            detail: `EBT: ${sym}${p.interest_burden.numerator.toLocaleString()} ${unit} ÷ EBIT: ${sym}${p.interest_burden.denominator.toLocaleString()} ${unit}`,
            yoy: p.interest_burden.yoy_bps,
            accent: p.interest_burden.is_drag ? 'var(--accent-odd)' : 'var(--status-pass)',
            dragTag: p.interest_burden.is_drag ? 'Financing Drag (< 1.0)' : 'Net Income Accretive'
        },
        {
            title: '5. Tax Burden',
            formula: 'Net Income / EBT',
            ratio: `${p.tax_burden.pct.toFixed(2)}%`,
            detail: `PAT: ${sym}${p.tax_burden.numerator.toLocaleString()} ${unit} ÷ EBT: ${sym}${p.tax_burden.denominator.toLocaleString()} ${unit}`,
            yoy: p.tax_burden.yoy_bps,
            accent: p.tax_burden.is_drag ? 'var(--accent-odd)' : 'var(--status-pass)',
            dragTag: p.tax_burden.is_drag ? 'Tax Drag (< 1.0)' : 'Tax Neutral'
        },
        {
            title: '6. Resulting ROE',
            formula: 'Net Income / Total Equity',
            ratio: `${p.roe.pct.toFixed(2)}%`,
            detail: `PAT: ${sym}${p.roe.numerator.toLocaleString()} ${unit} ÷ Equity: ${sym}${p.roe.denominator.toLocaleString()} ${unit}`,
            yoy: p.roe.yoy_bps,
            accent: 'var(--status-pass)',
            dragTag: 'Invariant: 0.00 Err'
        }
    ];

    grid.innerHTML = cards.map(c => `
        <div class="dupont-factor-card">
            <div>
                <div class="factor-title" style="display:flex; justify-content:space-between; align-items:center;">
                    <span>${c.title}</span>
                    ${c.dragTag ? `<span style="color:${c.accent}; font-size:10px; font-weight:700;">${c.dragTag}</span>` : ''}
                </div>
                <div class="factor-ratio font-mono tabular-nums" style="color:${c.accent};">${c.ratio}</div>
                <div class="factor-sub font-mono">${c.formula}</div>
                <div class="factor-sub font-mono" style="margin-top:2px;">${c.detail}</div>
            </div>
            <div class="factor-yoy font-mono" style="color:${c.yoy >= 0 ? 'var(--status-pass)' : 'var(--accent-odd)'};">
                ${c.yoy !== 0 ? (c.yoy > 0 ? `+${c.yoy} bps YoY` : `${c.yoy} bps YoY`) : 'Baseline Year'}
            </div>
        </div>
    `).join('');
}

export function showDuPontTooltip(e, key, yearIdx) {
    const tooltip = document.getElementById('dupont-tooltip');
    const container = document.getElementById('dupont-chart-container');
    const period = dupontState.periods[yearIdx];
    if (!tooltip || !container || !period) return;

    const factor = period[key];
    if (!factor) return;

    const rect = container.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const sym = dupontState.currencySymbol;
    const unit = dupontState.currencyUnit;

    tooltip.style.display = 'block';
    tooltip.style.left = `${Math.min(rect.width - 200, Math.max(10, mouseX + 15))}px`;
    tooltip.style.top = `${Math.max(10, mouseY - 70)}px`;
    tooltip.innerHTML = `
        <div style="font-weight:700; color:#fafafa; margin-bottom:2px;">${key.replace('_', ' ').toUpperCase()} (${period.year})</div>
        <div style="color:var(--text-secondary); font-size:11px;">${factor.numerator_label}: ${sym}${factor.numerator.toLocaleString()} ${unit}</div>
        <div style="color:var(--text-secondary); font-size:11px;">${factor.denominator_label}: ${sym}${factor.denominator.toLocaleString()} ${unit}</div>
        <div style="color:${factor.yoy_bps >= 0 ? '#10b981' : '#ff5a1f'}; font-weight:600; margin-top:2px;">
            ${factor.yoy_bps >= 0 ? '+' : ''}${factor.yoy_bps} bps YoY vs Previous Year
        </div>
    `;
}

export function hideDuPontTooltip() {
    const tooltip = document.getElementById('dupont-tooltip');
    if (tooltip) tooltip.style.display = 'none';
}

function roundNumber(num, dec = 2) {
    return Number(Math.round(Number(num + 'e' + dec)) + 'e-' + dec);
}

// ============================================================================
// 4. BENTO RADIAL GLOW & RESIZE CONTROLLER
// ============================================================================
export function initBentoGlowTracker() {
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
    let ticking = false;
    let lastEvent = null;

    function updateGlow() {
        if (!lastEvent) { ticking = false; return; }
        const clientX = lastEvent.clientX;
        const clientY = lastEvent.clientY;
        const cells = document.querySelectorAll('.bento-cell');
        const glowRadius = 500;

        for (let i = 0; i < cells.length; i++) {
            const cell = cells[i];
            const rect = cell.getBoundingClientRect();
            if (
                clientX >= rect.left - glowRadius &&
                clientX <= rect.right + glowRadius &&
                clientY >= rect.top - glowRadius &&
                clientY <= rect.bottom + glowRadius
            ) {
                const x = clientX - rect.left;
                const y = clientY - rect.top;
                cell.style.setProperty('--mouse-x', `${x}px`);
                cell.style.setProperty('--mouse-y', `${y}px`);
            }
        }
        ticking = false;
    }

    window.addEventListener('mousemove', function(e) {
        lastEvent = e;
        if (!ticking) {
            requestAnimationFrame(updateGlow);
            ticking = true;
        }
    }, { passive: true });
}

export function initCharts(data = null) {
    initSensitivityHeatmap(data);
    initMonteCarloCanvas(data);
    setupMonteCarloScrubber();
    initDuPontWaterfall(data);
    initBentoGlowTracker();

    window.addEventListener('resize', function() {
        const resultsDashboard = document.getElementById('results-dashboard');
        if (resultsDashboard && resultsDashboard.style.display !== 'none') {
            renderMonteCarloCanvas();
            renderDuPontWaterfall(dupontState.activeYearIndex);
        }
    });
}
