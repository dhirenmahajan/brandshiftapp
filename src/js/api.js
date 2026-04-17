/**
 * BrandShift frontend API config.
 *
 * The backend is deployed as a standalone Azure Function App
 * (brandshift-api-dhiren-*.azurewebsites.net), NOT as Static Web Apps
 * Managed Functions. That means the SWA origin does not proxy /api/* to
 * the Function App, so we always call the Function App host directly.
 *
 * You can override the backend host at runtime by setting
 * window.BRANDSHIFT_API_BASE BEFORE api.js loads (e.g. in a <script>
 * tag above this one), which is handy for local `func start` on
 * http://localhost:7071/api.
 *
 * IMPORTANT: The Function App must allow the SWA origin under
 *   Azure Portal → Function App → CORS
 * (add https://nice-sky-0f57ad11e.2.azurestaticapps.net and any preview
 *  domains you use). '*' works too but blocks credentials.
 */
(function initApi() {
    const DEFAULT_API = "https://brandshift-api-dhiren-ereffhe9cqcfhhe4.westus2-01.azurewebsites.net/api";

    // Respect a page-level override, then fall back to the deployed Function App.
    const BASE = (typeof window !== "undefined" && window.BRANDSHIFT_API_BASE)
        ? String(window.BRANDSHIFT_API_BASE).replace(/\/+$/, "")
        : DEFAULT_API;

    function url(path) {
        const clean = String(path || "").replace(/^\/+/, "");
        return `${BASE}/${clean}`;
    }

    async function request(path, { method = "GET", params, body, headers } = {}) {
        let target = url(path);
        if (params) {
            const qs = new URLSearchParams();
            Object.entries(params).forEach(([k, v]) => {
                if (v === undefined || v === null || v === "") return;
                qs.append(k, String(v));
            });
            const q = qs.toString();
            if (q) target += `?${q}`;
        }

        const init = {
            method,
            headers: {
                ...(body && !(body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
                ...(headers || {}),
            },
        };

        if (body instanceof FormData) init.body = body;
        else if (body !== undefined) init.body = JSON.stringify(body);

        let response;
        try {
            response = await fetch(target, init);
        } catch (netErr) {
            // CORS failures and DNS / connectivity issues land here with
            // TypeError: Failed to fetch – give the developer a hint.
            const err = new Error(
                `Network error contacting ${target}. ` +
                "Check that the Function App is running and that its CORS " +
                "configuration allows this origin. " +
                `(${netErr.message || netErr})`
            );
            err.cause = netErr;
            throw err;
        }

        if (!response.ok) {
            let msg = `Request failed (${response.status})`;
            try {
                const errJson = await response.clone().json();
                if (errJson && errJson.error) msg = errJson.error;
            } catch (_) {
                try { msg = (await response.text()) || msg; } catch (_) { /* ignore */ }
            }
            const err = new Error(msg);
            err.status = response.status;
            throw err;
        }
        const ct = response.headers.get("content-type") || "";
        if (ct.includes("application/json")) return response.json();
        return response.text();
    }

    window.BrandShiftAPI = {
        BASE,
        url,
        request,
        get: (path, params) => request(path, { method: "GET", params }),
        post: (path, body) => request(path, { method: "POST", body }),
    };
})();
