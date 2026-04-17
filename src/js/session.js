/**
 * BrandShift session helpers.
 *
 * The backend has a real SQL-backed Users table with PBKDF2 hashed passwords.
 * Once a user logs in we keep their profile in localStorage (no cookies on
 * file:// preview) and guard dashboard pages with requireAuth().
 */
(function initSession() {
    const KEY = "brandshift.session";

    function save(user) {
        if (!user) return;
        localStorage.setItem(KEY, JSON.stringify(user));
    }

    function get() {
        try {
            const raw = localStorage.getItem(KEY);
            return raw ? JSON.parse(raw) : null;
        } catch (_) {
            return null;
        }
    }

    function clear() {
        localStorage.removeItem(KEY);
    }

    function requireAuth() {
        const user = get();
        if (!user) {
            window.location.replace("index.html");
            return null;
        }
        return user;
    }

    window.BrandShiftSession = { save, get, clear, requireAuth };
})();
