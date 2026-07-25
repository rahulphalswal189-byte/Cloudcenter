/* ==========================================================================
   script.js
   ---------
   Global site behaviour shared by every page:
     1. Mobile sidebar open/close toggle
     2. Dark / Light theme switch (feature #20), persisted server-side
     3. Django flash messages rendered as animated Bootstrap toasts
     4. AOS scroll-animation initialisation
     5. Animated counters for dashboard stat cards (data-counter attr)
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    /* ---- 1. Sidebar toggle (mobile) ---- */
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => sidebar.classList.toggle('show'));
    }

    /* ---- 2. Dark / Light theme toggle ---- */
    const themeToggle = document.getElementById('themeToggle');
    const htmlEl = document.documentElement;

    function getCookie(name) {
        const match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
        return match ? match.pop() : '';
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', function () {
            const current = htmlEl.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            htmlEl.setAttribute('data-theme', next); // instant visual feedback

            const toggleUrl = themeToggle.dataset.toggleUrl;
            if (toggleUrl) {
                fetch(toggleUrl, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                }).catch(() => { /* fail silently - theme still applied client-side */ });
            }
        });
    }

    /* ---- 3. Flash messages -> toast notifications ---- */
    const messagesRoot = document.getElementById('djangoMessages');
    const toastContainer = document.getElementById('toastContainer');
    if (messagesRoot && toastContainer) {
        const tagToStyle = {
            success: { icon: 'bi-check-circle-fill', color: '#10B981' },
            error: { icon: 'bi-x-circle-fill', color: '#EF4444' },
            warning: { icon: 'bi-exclamation-triangle-fill', color: '#F59E0B' },
            info: { icon: 'bi-info-circle-fill', color: '#06B6D4' },
        };
        messagesRoot.querySelectorAll('.django-message').forEach(function (msgEl) {
            const tag = msgEl.dataset.tag || 'info';
            const style = tagToStyle[tag] || tagToStyle.info;
            const toast = document.createElement('div');
            toast.className = 'toast glass-toast align-items-center border-0 show mb-2';
            toast.setAttribute('role', 'alert');
            toast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="bi ${style.icon}" style="color:${style.color};"></i>
                        ${msgEl.textContent}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>`;
            toastContainer.appendChild(toast);
            setTimeout(() => { toast.classList.add('toast-fade-out'); setTimeout(() => toast.remove(), 400); }, 5000);
        });
    }

    /* ---- 4. AOS scroll animations ---- */
    if (window.AOS) {
        AOS.init({ duration: 600, once: true, offset: 40 });
    }

    /* ---- 5. Animated counters (usage: <span data-counter="1234">0</span>) ---- */
    document.querySelectorAll('[data-counter]').forEach(function (el) {
        const target = parseFloat(el.dataset.counter);
        if (isNaN(target)) return;
        const duration = 900;
        const start = performance.now();
        function tick(now) {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
            const value = target * eased;
            el.textContent = Number.isInteger(target) ? Math.round(value) : value.toFixed(1);
            if (progress < 1) requestAnimationFrame(tick);
            else el.textContent = Number.isInteger(target) ? target : target.toFixed(1);
        }
        requestAnimationFrame(tick);
    });
});
