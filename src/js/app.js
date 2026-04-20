/**
 * BrandShift front-end controller.
 *
 * Binds each page in /src to the Azure Functions API:
 *   - index.html / register.html : Login / Register against /auth/login & /auth/register
 *   - search.html                : /api/SearchData?hshd_num=...  + demo pull /api/GetHousehold10
 *   - upload.html                : Multi-file CSV upload to /api/UploadData
 *   - dashboard.html             : KPI cards + 4 charts + 2 tables, all hitting live endpoints
 *
 * All requests go through window.BrandShiftAPI so we can use the SWA /api proxy
 * on production and fall back to the direct Functions URL on file:// previews.
 */
document.addEventListener("DOMContentLoaded", () => {
    const api = window.BrandShiftAPI;
    const session = window.BrandShiftSession;

    // Dashboard state. Declared up top so every dashboard helper that
    // references them is past the temporal dead zone when invoked.
    const chartRegistry = {};
    let currentFilters = {};

    // ------------------------------------------------------------------
    // Authentication pages
    // ------------------------------------------------------------------
    bindLogin();
    bindRegister();

    // Logout link (any page with [data-action="logout"])
    document.querySelectorAll('[data-action="logout"]').forEach((el) => {
        el.addEventListener("click", (e) => {
            e.preventDefault();
            session.clear();
            window.location.href = "index.html";
        });
    });

    // Reflect logged-in user on pages that show them
    const userLabel = document.getElementById("session-user");
    if (userLabel) {
        const u = session.get();
        if (u) userLabel.textContent = u.username || u.email || "Analyst";
    }

    // ------------------------------------------------------------------
    // Search page
    // ------------------------------------------------------------------
    bindSearch();

    // ------------------------------------------------------------------
    // Upload page
    // ------------------------------------------------------------------
    bindUpload();

    // ------------------------------------------------------------------
    // Dashboard page
    // ------------------------------------------------------------------
    if (document.getElementById("dashboard-root")) {
        guardDashboardPages();
        initDashboard();
    } else if (document.getElementById("search-root") || document.getElementById("upload-root")) {
        guardDashboardPages();
    }

    // ------------------------------------------------------------------
    // Login / Register
    // ------------------------------------------------------------------
    function bindLogin() {
        const form = document.getElementById("login-form");
        if (!form) return;
        const status = document.getElementById("auth-status");
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            setStatus(status, "Signing you in...", "muted");
            const data = Object.fromEntries(new FormData(form).entries());
            try {
                const user = await api.post("auth/login", {
                    username: data.username,
                    email: data.email,
                    password: data.password,
                });
                session.save(user);
                setStatus(status, "Success, redirecting...", "success");
                window.location.href = "dashboard.html";
            } catch (err) {
                setStatus(status, err.message || "Login failed.", "danger");
            }
        });
    }

    function bindRegister() {
        const form = document.getElementById("register-form");
        if (!form) return;
        const status = document.getElementById("auth-status");
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            setStatus(status, "Creating your account...", "muted");
            const data = Object.fromEntries(new FormData(form).entries());
            if ((data.password || "").length < 6) {
                setStatus(status, "Password must be at least 6 characters.", "danger");
                return;
            }
            try {
                const user = await api.post("auth/register", {
                    username: data.username,
                    email: data.email,
                    password: data.password,
                });
                session.save(user);
                setStatus(status, "Welcome! Redirecting...", "success");
                window.location.href = "dashboard.html";
            } catch (err) {
                setStatus(status, err.message || "Registration failed.", "danger");
            }
        });
    }

    function guardDashboardPages() {
        // Only guard pages that are not the login / register page.
        if (document.getElementById("login-form") || document.getElementById("register-form")) return;
        session.requireAuth();
    }

    // ------------------------------------------------------------------
    // Search page
    // ------------------------------------------------------------------
    function bindSearch() {
        const form = document.getElementById("search-form");
        if (!form) return;

        const resultsDiv = document.getElementById("results");
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const hshdNum = document.getElementById("hshd_num").value.trim();
            resultsDiv.innerHTML = loadingBlock(`Fetching live transactions for Household <strong>${hshdNum}</strong>...`);
            try {
                const payload = await api.get("SearchData", { hshd_num: hshdNum });
                renderSearchResults(resultsDiv, payload);
            } catch (err) {
                resultsDiv.innerHTML = errorBlock(err.message);
            }
        });

        const hh10 = document.getElementById("hh10-btn");
        if (hh10) {
            hh10.addEventListener("click", async () => {
                resultsDiv.innerHTML = loadingBlock("Fetching demo pull for Household 10...");
                try {
                    const rows = await api.get("GetHousehold10");
                    renderSearchResults(resultsDiv, { hshd_num: 10, household: null, transactions: rows || [], count: (rows || []).length });
                } catch (err) {
                    resultsDiv.innerHTML = errorBlock(err.message);
                }
            });
        }
    }

    function renderSearchResults(container, payload) {
        const hshd = payload.hshd_num;
        const demographics = payload.household;
        const rows = payload.transactions || [];

        if (!rows.length) {
            container.innerHTML = errorBlock(`No transactions found for Household ${hshd}.`);
            return;
        }

        const demoHtml = demographics ? `
            <div class="glass-panel" style="margin-bottom: 20px; padding: 20px;">
                <h3 style="margin-bottom: 12px;">Household #${hshd} Demographics</h3>
                <div class="demo-grid">
                    ${demoStat("Loyalty", demographics.Loyalty_flag)}
                    ${demoStat("Age Range", demographics.Age_range)}
                    ${demoStat("Marital", demographics.Marital_status)}
                    ${demoStat("Income", demographics.Income_range)}
                    ${demoStat("Homeowner", demographics.Homeowner_desc)}
                    ${demoStat("Composition", demographics.Hshd_composition)}
                    ${demoStat("HH Size", demographics.Hshd_size)}
                    ${demoStat("Children", demographics.Children)}
                </div>
            </div>` : "";

        const tableRows = rows.map((r) => `
            <tr>
                <td>${safe(r.Hshd_num)}</td>
                <td>${safe(r.Basket_num)}</td>
                <td>${formatDate(r.Date)}</td>
                <td>${safe(r.Product_num)}</td>
                <td>${safe(r.Department)}</td>
                <td>${safe(r.Commodity)}</td>
                <td>${safe(r.Brand_type)}</td>
                <td class="num">$${formatMoney(r.Spend)}</td>
                <td class="num">${safe(r.Units)}</td>
            </tr>`).join("");

        container.innerHTML = `
            ${demoHtml}
            <div class="glass-panel" style="padding: 0;">
                <div style="padding: 16px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-glass);">
                    <h3>Transaction Pull (${rows.length} rows)</h3>
                    <span class="badge badge-info">Sorted by Basket, Date, Product</span>
                </div>
                <div class="data-table-container" style="border: none; border-radius: 0 0 16px 16px;">
                    <table class="brand-table">
                        <thead>
                            <tr>
                                <th>HSHD_NUM</th>
                                <th>Basket</th>
                                <th>Date</th>
                                <th>Product</th>
                                <th>Department</th>
                                <th>Commodity</th>
                                <th>Brand</th>
                                <th class="num">Spend</th>
                                <th class="num">Units</th>
                            </tr>
                        </thead>
                        <tbody>${tableRows}</tbody>
                    </table>
                </div>
            </div>`;
    }

    function demoStat(label, value) {
        return `
            <div class="demo-stat">
                <span class="demo-label">${label}</span>
                <span class="demo-value">${safe(value) || "—"}</span>
            </div>`;
    }

    // ------------------------------------------------------------------
    // Upload
    // ------------------------------------------------------------------
    function bindUpload() {
        const uploadArea = document.getElementById("upload-area");
        const fileInput = document.getElementById("csv-file");
        const browseBtn = document.getElementById("browse-btn");
        const status = document.getElementById("upload-status");
        if (!uploadArea || !fileInput) return;

        // Single source of truth for opening the OS file picker. The <button>
        // and the <div> both point here so we never fire .click() twice in the
        // same tick (Safari drops the dialog when that happens).
        let pickerOpening = false;
        function openPicker() {
            if (pickerOpening) return;
            pickerOpening = true;
            fileInput.value = "";
            fileInput.click();
            setTimeout(() => { pickerOpening = false; }, 400);
        }

        if (browseBtn) {
            browseBtn.addEventListener("click", (e) => {
                e.preventDefault();
                e.stopPropagation();
                openPicker();
            });
        }
        uploadArea.addEventListener("click", (e) => {
            if (e.target.closest("#browse-btn")) return;
            openPicker();
        });
        uploadArea.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openPicker();
            }
        });

        uploadArea.addEventListener("dragover", (e) => {
            e.preventDefault();
            uploadArea.classList.add("dragover");
        });
        uploadArea.addEventListener("dragleave", () => uploadArea.classList.remove("dragover"));
        uploadArea.addEventListener("drop", (e) => {
            e.preventDefault();
            uploadArea.classList.remove("dragover");
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                handleUpload(e.dataTransfer.files);
            }
        });
        fileInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files.length > 0) {
                handleUpload(e.target.files);
            }
        });

        function renderRow(file, state, message) {
            const row = document.createElement("div");
            row.className = `upload-row ${state}`;
            row.dataset.file = file.name;
            row.innerHTML = `<strong>${escapeHtml(file.name)}</strong> — ${escapeHtml(message)}`;
            return row;
        }
        function updateRow(row, state, message) {
            row.className = `upload-row ${state}`;
            row.innerHTML = `<strong>${escapeHtml(row.dataset.file)}</strong> — ${escapeHtml(message)}`;
        }

        async function handleUpload(files) {
            uploadArea.classList.add("busy");
            for (const file of files) {
                const row = renderRow(file, "pending", "uploading…");
                status.appendChild(row);
                const form = new FormData();
                form.append("file", file);
                try {
                    const data = await api.post("UploadData", form);
                    updateRow(row, "success", data && data.message
                        ? data.message
                        : "loaded");
                } catch (err) {
                    updateRow(row, "error", (err && err.message) || "Upload failed.");
                }
            }
            uploadArea.classList.remove("busy");
            // Allow re-uploading the exact same file immediately.
            fileInput.value = "";
        }
    }

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    // ------------------------------------------------------------------
    // Dashboard
    // ------------------------------------------------------------------
    function initDashboard() {
        if (typeof Chart === "undefined") {
            console.error("Chart.js not loaded.");
            return;
        }
        // Global Chart.js defaults for the dark theme
        Chart.defaults.color = "#9CA3AF";
        Chart.defaults.borderColor = "rgba(255,255,255,0.06)";
        Chart.defaults.font.family = "Inter, system-ui, sans-serif";

        // Filter form wiring
        const filterForm = document.getElementById("filter-form");
        if (filterForm) {
            filterForm.addEventListener("submit", (e) => {
                e.preventDefault();
                currentFilters = Object.fromEntries(
                    Array.from(new FormData(filterForm).entries()).filter(([, v]) => v && v !== "all")
                );
                refreshAll();
            });

            const resetBtn = document.getElementById("filter-reset");
            if (resetBtn) {
                resetBtn.addEventListener("click", () => {
                    filterForm.reset();
                    currentFilters = {};
                    refreshAll();
                });
            }
        }

        refreshAll();
    }

    function refreshAll() {
        loadKpis();
        loadSpendTrends();
        loadChurn();
        loadBasket();
        loadDemographics();
        loadSeasonal();
    }

    // ----- KPIs -----
    async function loadKpis() {
        const host = document.getElementById("kpi-grid");
        if (!host) return;
        host.setAttribute("aria-busy", "true");
        try {
            const k = await api.get("analytics/kpis", currentFilters);
            host.innerHTML = [
                kpi("Total Processed Spend", money(k.total_spend), "YTD revenue across all filtered households"),
                kpi("Active Households", formatInt(k.active_households), "Distinct households buying in window"),
                kpi("Avg Basket Spend", money(k.avg_basket_spend), `${formatInt(k.total_baskets)} baskets`),
                kpi("Private Label Share", `${k.private_label_pct}%`, "Share of $ on private brands"),
                kpi("Loyalty Share of Spend", `${k.loyalty_spend_pct}%`, "Portion from loyalty households"),
                kpi("Total Units Sold", formatInt(k.total_units), "Units in the filtered set"),
            ].join("");
        } catch (err) {
            host.innerHTML = `<div class="glass-panel metric-card error">KPIs unavailable: ${err.message}</div>`;
        }
        host.removeAttribute("aria-busy");
    }

    function kpi(title, value, hint) {
        return `
            <div class="glass-panel metric-card">
                <span class="metric-title">${title}</span>
                <span class="metric-value">${value}</span>
                <span class="metric-hint">${hint}</span>
            </div>`;
    }

    // ----- Spend trends -----
    async function loadSpendTrends() {
        const canvas = document.getElementById("spendShiftChart");
        if (!canvas) return;
        try {
            const rows = await api.get("analytics/spend-trends");
            const labels = rows.map((r) => r.label);
            upsertChart("spend", canvas, {
                type: "line",
                data: {
                    labels,
                    datasets: [
                        dataset("National Brand", rows.map((r) => r.national_spend), "#9CA3AF", true),
                        dataset("Private Label", rows.map((r) => r.private_spend), "#00F0FF", true),
                        dataset("Organic / Natural", rows.map((r) => r.organic_spend), "#A78BFA", true),
                    ],
                },
                options: chartOpts({ stacked: false, currency: true }),
            });
        } catch (err) {
            toastChartError(canvas, err);
        }
    }

    // ----- Churn -----
    async function loadChurn() {
        const canvas = document.getElementById("churnChart");
        const tableBody = document.getElementById("churn-table-body");
        const countHost = document.getElementById("churn-counts");
        if (!canvas && !tableBody) return;
        try {
            const payload = await api.get("analytics/churn");
            if (countHost) {
                countHost.innerHTML = `
                    ${countChip("Healthy", payload.counts.healthy, "success")}
                    ${countChip("Stagnant", payload.counts.stagnant, "warn")}
                    ${countChip("At Risk", payload.counts.at_risk, "danger")}
                    ${countChip("Inactive", payload.counts.inactive || 0, "muted")}`;
            }
            if (canvas) {
                const series = payload.monthly || [];
                upsertChart("churn", canvas, {
                    type: "bar",
                    data: {
                        labels: series.map((s) => s.label),
                        datasets: [
                            {
                                label: "Active Households",
                                data: series.map((s) => s.active_households),
                                backgroundColor: "rgba(16,185,129,0.75)",
                                borderRadius: 6,
                            },
                        ],
                    },
                    options: chartOpts({ stacked: true }),
                });
            }
            if (tableBody) {
                const rows = (payload.top_risk || []).slice(0, 12);
                tableBody.innerHTML = rows.map((r) => `
                    <tr>
                        <td style="font-weight: 600;">${String(r.hshd_num).padStart(4, "0")}</td>
                        <td>${safe(r.income_range)} · ${safe(r.age_range)} · Kids: ${safe(r.children)}</td>
                        <td><span style="color: var(--status-danger);">${r.pct_change}% (slope ${r.slope})</span></td>
                        <td>${recommendCrossSell(r)}</td>
                        <td><button class="btn-secondary small">Send Coupon</button></td>
                    </tr>`).join("") || `<tr><td colspan="5" style="text-align:center; color: var(--text-muted);">No at-risk households detected in the current filter.</td></tr>`;
            }
        } catch (err) {
            if (canvas) toastChartError(canvas, err);
            if (tableBody) tableBody.innerHTML = `<tr><td colspan="5" class="error">${err.message}</td></tr>`;
        }
    }

    function recommendCrossSell(r) {
        if ((r.income_range || "").toLowerCase().includes("35") || (r.income_range || "").toLowerCase().includes("under")) {
            return `<span style="color: var(--accent-cyan);">Private Label Staples</span>`;
        }
        if ((r.children || "").trim() !== "" && r.children !== "null") {
            return `<span style="color: var(--accent-cyan);">Family Snack Bundles</span>`;
        }
        return `<span style="color: var(--accent-cyan);">Organic Produce / Premium Grocery</span>`;
    }

    // ----- Basket analysis -----
    async function loadBasket() {
        const body = document.getElementById("basket-body");
        if (!body) return;
        try {
            const rows = await api.get("analytics/basket");
            if (!rows.length) {
                body.innerHTML = `<tr><td colspan="5" style="text-align:center; color: var(--text-muted);">No basket pairs yet. Upload transactions and rerun.</td></tr>`;
                return;
            }
            body.innerHTML = rows.map((r) => `
                <tr>
                    <td>${safe(r.commodity_a)}</td>
                    <td>${safe(r.commodity_b)}</td>
                    <td class="num">${formatInt(r.baskets_together)}</td>
                    <td class="num">${r.lift}×</td>
                    <td class="num">${r.confidence}%</td>
                </tr>`).join("");
        } catch (err) {
            body.innerHTML = `<tr><td colspan="5" class="error">${err.message}</td></tr>`;
        }
    }

    // ----- Demographics -----
    async function loadDemographics() {
        const canvas = document.getElementById("demographicsChart");
        if (!canvas) return;
        try {
            const payload = await api.get("analytics/demographics", currentFilters);
            const income = payload.by_income || [];
            upsertChart("demographics", canvas, {
                type: "bar",
                data: {
                    labels: income.map((r) => r.bucket || "Unknown"),
                    datasets: [
                        {
                            label: "Avg Spend per Household",
                            data: income.map((r) => r.avg_spend_per_hshd),
                            backgroundColor: "rgba(0,240,255,0.7)",
                            borderRadius: 6,
                        },
                    ],
                },
                options: chartOpts({ currency: true }),
            });
            const sizeHost = document.getElementById("demographics-size");
            if (sizeHost) {
                sizeHost.innerHTML = (payload.by_size || []).map((r) => `
                    <div class="demo-row">
                        <span>${safe(r.bucket)} member${r.bucket == 1 ? "" : "s"}</span>
                        <strong>${money(r.avg_spend_per_hshd)}</strong>
                    </div>`).join("");
            }
        } catch (err) {
            toastChartError(canvas, err);
        }
    }

    // ----- Seasonal -----
    async function loadSeasonal() {
        const canvas = document.getElementById("seasonalChart");
        if (!canvas) return;
        try {
            const rows = await api.get("analytics/seasonal");
            upsertChart("seasonal", canvas, {
                type: "line",
                data: {
                    labels: rows.map((r) => r.month_name),
                    datasets: [
                        {
                            label: "Avg Weekly Spend",
                            data: rows.map((r) => r.avg_weekly_spend),
                            borderColor: "#14B8A6",
                            backgroundColor: "rgba(20,184,166,0.12)",
                            tension: 0.35,
                            fill: true,
                        },
                    ],
                },
                options: chartOpts({ currency: true }),
            });
        } catch (err) {
            toastChartError(canvas, err);
        }
    }

    // ------------------------------------------------------------------
    // Chart helpers
    // ------------------------------------------------------------------
    function upsertChart(id, canvas, config) {
        if (chartRegistry[id]) chartRegistry[id].destroy();
        chartRegistry[id] = new Chart(canvas.getContext("2d"), config);
    }

    function dataset(label, data, color, fill) {
        return {
            label,
            data,
            borderColor: color,
            backgroundColor: fill ? hexToRgba(color, 0.12) : color,
            tension: 0.35,
            fill: !!fill,
            pointRadius: 2,
        };
    }

    function chartOpts({ stacked = false, currency = false } = {}) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: "#F3F4F6" } },
                tooltip: {
                    callbacks: currency ? {
                        label: (ctx) => `${ctx.dataset.label}: $${formatMoney(ctx.parsed.y)}`,
                    } : undefined,
                },
            },
            scales: {
                x: { stacked, ticks: { color: "#9CA3AF" }, grid: { color: "rgba(255,255,255,0.05)" } },
                y: {
                    stacked,
                    ticks: {
                        color: "#9CA3AF",
                        callback: currency ? (v) => `$${compactNum(v)}` : undefined,
                    },
                    grid: { color: "rgba(255,255,255,0.05)" },
                },
            },
        };
    }

    function toastChartError(canvas, err) {
        const parent = canvas.parentElement;
        if (parent) parent.innerHTML = `<div class="error" style="padding: 24px;">Chart data unavailable: ${err.message}</div>`;
    }

    function countChip(label, n, tone) {
        return `<div class="count-chip tone-${tone}"><span>${label}</span><strong>${formatInt(n)}</strong></div>`;
    }

    // ------------------------------------------------------------------
    // Primitives
    // ------------------------------------------------------------------
    function setStatus(el, text, tone) {
        if (!el) return;
        const colorMap = { muted: "var(--text-muted)", success: "var(--status-success)", danger: "var(--status-danger)" };
        el.style.color = colorMap[tone] || "var(--text-muted)";
        el.textContent = text || "";
    }

    function loadingBlock(msg) {
        return `<div class="glass-panel" style="padding:32px; text-align:center; color: var(--text-muted);">${msg}</div>`;
    }
    function errorBlock(msg) {
        return `<div class="glass-panel" style="padding:24px; border-color: rgba(239,68,68,0.4); color: var(--status-danger);">${msg}</div>`;
    }

    function safe(v) {
        if (v === null || v === undefined) return "";
        return String(v).trim();
    }
    function formatDate(v) {
        if (!v) return "";
        const d = new Date(v);
        if (Number.isNaN(d.getTime())) return safe(v);
        return d.toISOString().slice(0, 10);
    }
    function formatMoney(v) {
        const n = Number(v) || 0;
        return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    function money(v) { return `$${formatMoney(v)}`; }
    function formatInt(v) {
        return (Number(v) || 0).toLocaleString();
    }
    function compactNum(v) {
        const n = Number(v) || 0;
        if (Math.abs(n) >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
        if (Math.abs(n) >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
        return n.toFixed(0);
    }
    function hexToRgba(hex, alpha) {
        const m = hex.replace("#", "").match(/.{1,2}/g);
        if (!m || m.length < 3) return hex;
        const [r, g, b] = m.map((c) => parseInt(c, 16));
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
});
