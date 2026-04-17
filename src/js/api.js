/**
 * BrandShift frontend API config.
 *
 * When the site is served by Azure Static Web Apps linked to the Function App,
 * the platform auto-proxies /api/* to the backend on the same origin. That is
 * the preferred path (no CORS, shorter URL, works on preview environments).
 *
 * When you open the HTML files locally (file:// or a plain static server) there
 * is no /api proxy, so we fall back to the fully-qualified Azure Functions URL.
 */
(function initApi() {
    const DIRECT_API = "https://brandshift-api-dhiren-ereffhe9cqcfhhe4.westus2-01.azurewebsites.net/api";

    const isHttp = typeof window !== "undefined" &&
                   window.location &&
                   /^https?:$/.test(window.location.protocol);

    // If we're on http(s) we assume the SWA /api proxy is available.
    // For file:// preview we reach directly to the deployed Functions host.
    const BASE = isHttp ? "/api" : DIRECT_API;

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

        const response = await fetch(target, init);
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
