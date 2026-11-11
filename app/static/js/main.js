/* OpenLib Global Interactivity, Search Suggestions, Accessibility & Text-to-Speech */

(function () {
    'use strict';

    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    window.OpenLib = {
        getCsrfToken: getCsrfToken
    };

    // Live Search Suggestions
    document.querySelectorAll('[data-search-autocomplete]').forEach(function (input) {
        const wrapper = input.closest('.ol-search-wrapper');
        if (!wrapper) return;
        const box = wrapper.querySelector('.ol-search-suggestions');
        if (!box) return;

        let debounceTimer = null;
        let currentIndex = -1;

        input.addEventListener('input', function () {
            const q = input.value.trim();
            clearTimeout(debounceTimer);
            if (q.length < 2) {
                box.classList.remove('show');
                box.innerHTML = '';
                return;
            }
            debounceTimer = setTimeout(async function () {
                try {
                    const res = await fetch('/api/search/suggestions?q=' + encodeURIComponent(q));
                    if (!res.ok) return;
                    const items = await res.json();
                    currentIndex = -1;
                    if (!items.length) {
                        box.classList.remove('show');
                        box.innerHTML = '';
                        return;
                    }
                    box.innerHTML = items.map(function (item) {
                        return (
                            '<a href="' + item.url + '" class="ol-suggestion-item">' +
                            '<div><div class="fw-semibold">' + escapeHtml(item.title) + '</div>' +
                            '<small class="text-muted">' + escapeHtml(item.author) + '</small></div>' +
                            '<span class="badge bg-light text-dark border">' + escapeHtml(item.age_group) + '</span>' +
                            '</a>'
                        );
                    }).join('');
                    box.classList.add('show');
                } catch (err) {
                    console.debug('Suggestion error', err);
                }
            }, 220);
        });

        input.addEventListener('keydown', function (e) {
            const links = box.querySelectorAll('.ol-suggestion-item');
            if (!links.length) return;
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                currentIndex = Math.min(currentIndex + 1, links.length - 1);
                updateActive(links, currentIndex);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                currentIndex = Math.max(currentIndex - 1, -1);
                updateActive(links, currentIndex);
            } else if (e.key === 'Enter' && currentIndex >= 0) {
                e.preventDefault();
                window.location.href = links[currentIndex].getAttribute('href');
            } else if (e.key === 'Escape') {
                box.classList.remove('show');
            }
        });

        document.addEventListener('click', function (e) {
            if (!wrapper.contains(e.target)) {
                box.classList.remove('show');
            }
        });
    });

    function updateActive(links, idx) {
        links.forEach(function (el, i) {
            el.classList.toggle('active', i === idx);
        });
    }

    function escapeHtml(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    // Dynamic Category Filter on Search Page
    const ageFilter = document.getElementById('filterAgeGroup');
    const catFilter = document.getElementById('filterCategory');
    if (ageFilter && catFilter) {
        ageFilter.addEventListener('change', async function () {
            const agSlug = ageFilter.value;
            try {
                const res = await fetch('/api/categories?age_group=' + encodeURIComponent(agSlug));
                if (!res.ok) return;
                const cats = await res.json();
                const currentVal = catFilter.value;
                catFilter.innerHTML = '<option value="">All Categories</option>' +
                    cats.map(function (c) {
                        const sel = c.slug === currentVal ? ' selected' : '';
                        return '<option value="' + escapeHtml(c.slug) + '"' + sel + '>' +
                            escapeHtml(c.name) + ' (' + c.count + ')</option>';
                    }).join('');
            } catch (err) {
                console.debug('Category filter error', err);
            }
        });
    }

    // Global Accessibility Toggles (Large Text & High Contrast)
    async function toggleA11y(flagName, bodyClass) {
        const active = document.body.classList.toggle(bodyClass);
        try {
            localStorage.setItem('openlib_' + flagName, active ? '1' : '0');
            const payload = {};
            payload[flagName] = active;
            await fetch('/api/accessibility', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify(payload)
            });
        } catch (err) {
            console.debug('A11y sync error', err);
        }
    }

    document.querySelectorAll('[data-a11y-toggle="large_text"]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            toggleA11y('large_text', 'a11y-large-text');
        });
    });

    document.querySelectorAll('[data-a11y-toggle="high_contrast"]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            toggleA11y('high_contrast', 'a11y-high-contrast');
        });
    });

    // Apply stored guest preferences if body doesn't already have server class
    if (localStorage.getItem('openlib_large_text') === '1') {
        document.body.classList.add('a11y-large-text');
    }
    if (localStorage.getItem('openlib_high_contrast') === '1') {
        document.body.classList.add('a11y-high-contrast');
    }

    // Text-to-Speech (Web Speech API) helper for Seniors & Accessibility
    window.OpenLibTTS = {
        speak: function (text, rate) {
            if (!('speechSynthesis' in window)) {
                alert('Text-to-speech is not supported in this browser.');
                return;
            }
            window.speechSynthesis.cancel();
            const clean = String(text || '').trim();
            if (!clean) return;
            const utter = new SpeechSynthesisUtterance(clean.slice(0, 6000));
            utter.rate = rate || 0.95;
            window.speechSynthesis.speak(utter);
        },
        pause: function () {
            if ('speechSynthesis' in window) window.speechSynthesis.pause();
        },
        resume: function () {
            if ('speechSynthesis' in window) window.speechSynthesis.resume();
        },
        stop: function () {
            if ('speechSynthesis' in window) window.speechSynthesis.cancel();
        }
    };

    document.querySelectorAll('[data-tts-target]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const targetSel = btn.getAttribute('data-tts-target');
            const el = document.querySelector(targetSel);
            if (el) {
                window.OpenLibTTS.speak(el.innerText, 0.92);
            }
        });
    });

    document.querySelectorAll('[data-tts-stop]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            window.OpenLibTTS.stop();
        });
    });
})();

