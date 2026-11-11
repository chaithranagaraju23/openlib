/* OpenLib Integrated Online Book Reader (PDF.js + Text Reader + Bookmarks + Progress + TTS) */

(function () {
    'use strict';

    const configEl = document.getElementById('readerConfig');
    if (!configEl) return;

    const bookId = parseInt(configEl.dataset.bookId, 10);
    const readerMode = configEl.dataset.readerMode;
    const pdfUrl = configEl.dataset.pdfUrl;
    const initialPage = Math.max(1, parseInt(configEl.dataset.initialPage || '1', 10));
    const isAuthenticated = configEl.dataset.authenticated === 'true';
    const textEndpoint = configEl.dataset.textEndpoint;

    const shell = document.getElementById('readerShell');
    const stage = document.getElementById('readerStage');
    const canvas = document.getElementById('pdfCanvas');
    const ctx = canvas ? canvas.getContext('2d') : null;
    const pageNumInput = document.getElementById('pageNumInput');
    const totalPagesEl = document.getElementById('totalPagesSpan');
    const zoomLevelEl = document.getElementById('zoomLevelSpan');
    const progressBar = document.getElementById('readingProgressBar');
    const progressPctText = document.getElementById('readingProgressPct');
    const bookmarksListEl = document.getElementById('bookmarksList');
    const statusBanner = document.getElementById('readerStatusMsg');

    let pdfDoc = null;
    let currentPage = initialPage;
    let totalPages = 1;
    let currentScale = 1.25;
    let rendering = false;
    let pendingPage = null;
    let currentPageText = '';
    let currentFontSize = 18;
    let saveTimer = null;

    function getCsrf() {
        return window.OpenLib ? window.OpenLib.getCsrfToken() : '';
    }

    function showStatus(msg, type) {
        if (!statusBanner) return;
        statusBanner.textContent = msg;
        statusBanner.className = 'alert py-2 px-3 small mb-2 alert-' + (type || 'info');
        statusBanner.classList.remove('d-none');
    }

    function updateProgressUI(page, total) {
        totalPages = Math.max(1, total);
        currentPage = Math.min(Math.max(1, page), totalPages);
        if (pageNumInput) pageNumInput.value = currentPage;
        if (totalPagesEl) totalPagesEl.textContent = totalPages;

        const pct = Math.round((currentPage / totalPages) * 100);
        if (progressBar) {
            progressBar.style.width = pct + '%';
            progressBar.setAttribute('aria-valuenow', pct);
        }
        if (progressPctText) progressPctText.textContent = pct + '%';

        clearTimeout(saveTimer);
        saveTimer = setTimeout(function () {
            persistProgress(currentPage, totalPages);
        }, 450);
    }

    async function persistProgress(page, total) {
        try {
            localStorage.setItem('openlib_progress_' + bookId, JSON.stringify({ page: page, total: total }));
            if (!isAuthenticated) return;
            await fetch('/api/reading-progress', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrf()
                },
                body: JSON.stringify({
                    book_id: bookId,
                    current_page: page,
                    total_pages: total
                })
            });
        } catch (e) {
            console.debug('Progress save skipped', e);
        }
    }

    // PDF.js Rendering
    async function renderPdfPage(num) {
        if (!pdfDoc || !canvas || !ctx) return;
        rendering = true;
        try {
            const page = await pdfDoc.getPage(num);
            const viewport = page.getViewport({ scale: currentScale });
            canvas.height = viewport.height;
            canvas.width = viewport.width;

            await page.render({ canvasContext: ctx, viewport: viewport }).promise;

            // Extract text for optional Text-to-Speech
            try {
                const txt = await page.getTextContent();
                currentPageText = txt.items.map(function (i) { return i.str; }).join(' ');
            } catch (e) {
                currentPageText = '';
            }

            updateProgressUI(num, pdfDoc.numPages);
            if (zoomLevelEl) zoomLevelEl.textContent = Math.round(currentScale * 100) + '%';
        } finally {
            rendering = false;
            if (pendingPage !== null) {
                const next = pendingPage;
                pendingPage = null;
                renderPdfPage(next);
            }
        }
    }

    function queuePage(num) {
        if (!pdfDoc) return;
        const clamped = Math.min(Math.max(1, num), pdfDoc.numPages);
        if (rendering) {
            pendingPage = clamped;
        } else {
            renderPdfPage(clamped);
        }
    }

    async function initPdfJs() {
        if (!window.pdfjsLib || !pdfUrl) return;
        window.pdfjsLib.GlobalWorkerOptions.workerSrc = '/static/js/pdfjs/pdf.worker.min.js';
        try {
            showStatus('Loading document in PDF.js reader...', 'info');
            const loadingTask = window.pdfjsLib.getDocument(pdfUrl);
            pdfDoc = await loadingTask.promise;
            if (statusBanner) statusBanner.classList.add('d-none');

            const savedGuest = localStorage.getItem('openlib_progress_' + bookId);
            let startPage = initialPage;
            if (!isAuthenticated && savedGuest) {
                try {
                    startPage = JSON.parse(savedGuest).page || 1;
                } catch (e) {}
            }
            startPage = Math.min(Math.max(1, startPage), pdfDoc.numPages);
            await renderPdfPage(startPage);
        } catch (err) {
            console.error('PDF.js load error:', err);
            showStatus(
                'Unable to stream the remote PDF directly into the embedded canvas. Please use the Official Source Reader button below.',
                'warning'
            );
            const fallbackEl = document.getElementById('externalFallbackCard');
            if (fallbackEl) fallbackEl.classList.remove('d-none');
        }
    }

    // Text-Reader Mode (for Gutenberg plain-text public domain books)
    const textPaper = document.getElementById('textReaderPaper');
    const loadTextBtn = document.getElementById('loadTextPreviewBtn');
    let textPages = [];

    function renderTextPage(pageNum) {
        if (!textPaper || !textPages.length) return;
        const clamped = Math.min(Math.max(1, pageNum), textPages.length);
        textPaper.textContent = textPages[clamped - 1];
        currentPageText = textPages[clamped - 1];
        updateProgressUI(clamped, textPages.length);
        if (stage) stage.scrollTop = 0;
    }

    if (loadTextBtn && textEndpoint) {
        loadTextBtn.addEventListener('click', async function () {
            loadTextBtn.disabled = true;
            loadTextBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Loading Full Text...';
            try {
                const res = await fetch(textEndpoint);
                const data = await res.json();
                if (!data.available) {
                    showStatus(data.message || 'Text preview unavailable; use the official reading link.', 'warning');
                    return;
                }
                const chunkSize = 2600;
                const raw = data.text || '';
                textPages = [];
                for (let i = 0; i < raw.length; i += chunkSize) {
                    textPages.push(raw.slice(i, i + chunkSize));
                }
                if (!textPages.length) textPages.push(raw);
                if (textPaper) textPaper.classList.remove('d-none');
                const extCard = document.getElementById('externalFallbackCard');
                if (extCard) extCard.classList.add('d-none');
                renderTextPage(Math.min(initialPage, textPages.length));
            } catch (e) {
                showStatus('Error fetching text edition. Please try the official reading link.', 'warning');
            } finally {
                loadTextBtn.disabled = false;
                loadTextBtn.innerHTML = '<i class="bi bi-file-text me-1"></i> Reload Built-in Text Reader';
            }
        });
    }

    // Navigation Controls
    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');
    if (prevBtn) {
        prevBtn.addEventListener('click', function () {
            if (pdfDoc) queuePage(currentPage - 1);
            else if (textPages.length) renderTextPage(currentPage - 1);
        });
    }
    if (nextBtn) {
        nextBtn.addEventListener('click', function () {
            if (pdfDoc) queuePage(currentPage + 1);
            else if (textPages.length) renderTextPage(currentPage + 1);
        });
    }
    if (pageNumInput) {
        pageNumInput.addEventListener('change', function () {
            const p = parseInt(pageNumInput.value, 10) || 1;
            if (pdfDoc) queuePage(p);
            else if (textPages.length) renderTextPage(p);
        });
    }

    // Zoom Controls
    const zoomInBtn = document.getElementById('zoomInBtn');
    const zoomOutBtn = document.getElementById('zoomOutBtn');
    const zoomFitBtn = document.getElementById('zoomFitBtn');
    if (zoomInBtn) {
        zoomInBtn.addEventListener('click', function () {
            currentScale = Math.min(3.0, +(currentScale + 0.2).toFixed(2));
            if (pdfDoc) queuePage(currentPage);
        });
    }
    if (zoomOutBtn) {
        zoomOutBtn.addEventListener('click', function () {
            currentScale = Math.max(0.5, +(currentScale - 0.2).toFixed(2));
            if (pdfDoc) queuePage(currentPage);
        });
    }
    if (zoomFitBtn) {
        zoomFitBtn.addEventListener('click', async function () {
            if (!pdfDoc || !stage) return;
            const page = await pdfDoc.getPage(currentPage);
            const unscaled = page.getViewport({ scale: 1 });
            currentScale = Math.max(0.6, +((stage.clientWidth - 48) / unscaled.width).toFixed(2));
            queuePage(currentPage);
        });
    }

    // Font Size Controls (for Text Reader & Senior Comfort)
    const fontIncBtn = document.getElementById('fontIncreaseBtn');
    const fontDecBtn = document.getElementById('fontDecreaseBtn');
    if (fontIncBtn) {
        fontIncBtn.addEventListener('click', function () {
            currentFontSize = Math.min(30, currentFontSize + 2);
            if (textPaper) textPaper.style.fontSize = currentFontSize + 'px';
            if (pdfDoc && !textPages.length) {
                currentScale = Math.min(3.0, +(currentScale + 0.15).toFixed(2));
                queuePage(currentPage);
            }
        });
    }
    if (fontDecBtn) {
        fontDecBtn.addEventListener('click', function () {
            currentFontSize = Math.max(14, currentFontSize - 2);
            if (textPaper) textPaper.style.fontSize = currentFontSize + 'px';
            if (pdfDoc && !textPages.length) {
                currentScale = Math.max(0.6, +(currentScale - 0.15).toFixed(2));
                queuePage(currentPage);
            }
        });
    }

    // Night Mode & Fullscreen
    const nightBtn = document.getElementById('nightModeBtn');
    if (nightBtn && shell) {
        nightBtn.addEventListener('click', function () {
            const on = shell.classList.toggle('night-mode');
            nightBtn.classList.toggle('btn-dark', on);
            nightBtn.classList.toggle('btn-outline-secondary', !on);
        });
    }

    const fsBtn = document.getElementById('fullscreenBtn');
    if (fsBtn && shell) {
        fsBtn.addEventListener('click', function () {
            if (!document.fullscreenElement) {
                shell.requestFullscreen().catch(function () {});
            } else {
                document.exitFullscreen().catch(function () {});
            }
        });
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', function (e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        if (e.key === 'ArrowRight') {
            if (pdfDoc) queuePage(currentPage + 1);
            else if (textPages.length) renderTextPage(currentPage + 1);
        } else if (e.key === 'ArrowLeft') {
            if (pdfDoc) queuePage(currentPage - 1);
            else if (textPages.length) renderTextPage(currentPage - 1);
        }
    });

    // Bookmarks Panel
    const addBookmarkBtn = document.getElementById('addPageBookmarkBtn');
    if (addBookmarkBtn && isAuthenticated) {
        addBookmarkBtn.addEventListener('click', async function () {
            const noteInput = document.getElementById('bookmarkNoteInput');
            const note = noteInput ? noteInput.value.trim() : '';
            const res = await fetch('/api/reader-bookmarks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrf()
                },
                body: JSON.stringify({
                    book_id: bookId,
                    page_number: currentPage,
                    label: 'Page ' + currentPage,
                    note: note,
                    action: 'save'
                })
            });
            if (res.ok) {
                if (noteInput) noteInput.value = '';
                refreshBookmarks();
            }
        });
    }

    async function refreshBookmarks() {
        if (!isAuthenticated || !bookmarksListEl) return;
        const res = await fetch('/api/reader-bookmarks/' + bookId);
        if (!res.ok) return;
        const items = await res.json();
        if (!items.length) {
            bookmarksListEl.innerHTML = '<div class="text-muted small">No page bookmarks yet.</div>';
            return;
        }
        bookmarksListEl.innerHTML = items.map(function (bm) {
            return (
                '<div class="d-flex justify-content-between align-items-center border-bottom py-2">' +
                '<button type="button" class="btn btn-link btn-sm p-0 text-start fw-semibold jump-bm" data-page="' + bm.page_number + '">' +
                bm.label + (bm.note ? ' — <span class="text-muted fw-normal">' + bm.note + '</span>' : '') +
                '</button>' +
                '<button type="button" class="btn btn-sm btn-outline-danger py-0 px-1 del-bm" data-page="' + bm.page_number + '">&times;</button>' +
                '</div>'
            );
        }).join('');

        bookmarksListEl.querySelectorAll('.jump-bm').forEach(function (btn) {
            btn.addEventListener('click', function () {
                const p = parseInt(btn.dataset.page, 10);
                if (pdfDoc) queuePage(p);
                else if (textPages.length) renderTextPage(p);
            });
        });
        bookmarksListEl.querySelectorAll('.del-bm').forEach(function (btn) {
            btn.addEventListener('click', async function () {
                await fetch('/api/reader-bookmarks', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
                    body: JSON.stringify({
                        book_id: bookId,
                        page_number: parseInt(btn.dataset.page, 10),
                        action: 'delete'
                    })
                });
                refreshBookmarks();
            });
        });
    }

    // Text-to-Speech inside Reader
    const ttsPlayBtn = document.getElementById('readerTtsPlay');
    const ttsStopBtn = document.getElementById('readerTtsStop');
    if (ttsPlayBtn) {
        ttsPlayBtn.addEventListener('click', function () {
            const fallbackDesc = document.getElementById('readerBookSummary')?.innerText || '';
            const content = currentPageText || fallbackDesc;
            window.OpenLibTTS.speak(content, 0.95);
        });
    }
    if (ttsStopBtn) {
        ttsStopBtn.addEventListener('click', function () {
            window.OpenLibTTS.stop();
        });
    }

    // Initialize
    if (readerMode === 'pdfjs' && pdfUrl) {
        initPdfJs();
    }
    if (isAuthenticated) {
        refreshBookmarks();
    }
})();

