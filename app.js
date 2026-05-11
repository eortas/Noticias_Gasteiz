document.addEventListener('DOMContentLoaded', () => {
    const mainView = document.getElementById('main-view');
    const detailView = document.getElementById('detail-view');
    const statsContainer = document.getElementById('stats-container');
    const newsGrid = document.getElementById('news-grid');
    const articleContent = document.getElementById('article-content');
    const backNav = document.getElementById('nav-back');
    const backBtn = document.getElementById('back-btn');
    const liveUpdateBadge = document.getElementById('live-update-badge');

    let newsData = [];
    let moodHistoryData = [];
    let podcastData = null;
    let currentFilter = null;
        const READ_ARTICLES_KEY = 'vitoria_read_articles';

    // Apply initial lang state
        function formatLongDate(dateStr) {
                try {
            const date = new Date(dateStr);
            if (currentLang === 'eu') return getEuskaraDate(date, true);
            return date.toLocaleDateString(locales[currentLang] || 'es-ES', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
        } catch {
            return dateStr;
        }
    }

    function sortNewsByReadState() {
        const readIds = JSON.parse(localStorage.getItem(READ_ARTICLES_KEY) || '[]');
        newsData.sort((a, b) => {
            const aRead = readIds.includes(a.id);
            const bRead = readIds.includes(b.id);

            // Si uno está leído y el otro no, el leído va al final
            if (aRead && !bRead) return 1;
            if (!aRead && bRead) return -1;

            // Si ambos están en el mismo estado, mantener orden por fecha (descendente)
            return new Date(b.date) - new Date(a.date);
        });
    }

    let lastScrollPos = 0;

    function renderNewsFeed() {
        if (!newsData || newsData.length === 0) {
            newsGrid.innerHTML = '<p style="color:var(--text-muted); font-weight:300;">No hay noticias disponibles.</p>';
            return;
        }

        const readIds = JSON.parse(localStorage.getItem(READ_ARTICLES_KEY) || '[]');

        const filteredData = currentFilter
            ? newsData.filter(item => item.sentiment === currentFilter)
            : newsData;

        if (filteredData.length === 0) {
            newsGrid.innerHTML = '<p style="color:var(--text-muted); font-weight:300; padding: 2rem;">No hay noticias con este sentimiento hoy.</p>';
            return;
        }

        newsGrid.innerHTML = filteredData.map((item, index) => {
            const isRead = readIds.includes(item.id);
            let html = `
                <div class="card glass ${isRead ? 'card-read' : ''}" data-id="${item.id}" data-source="${item.source}">
                    <div class="card-img-wrap">
                        <img src="${item.image || ''}" alt="${item.title}" class="card-img" loading="lazy" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9IiMxZTI5M2IiLz48L3N2Zz4='">
                        <div class="img-overlay"></div>
                        <div class="card-top-badges">
                            <div class="card-source-badge">
                                <div class="sentiment-dot dot-${item.sentiment}" title="Sentimiento: ${item.sentiment}"></div>
                            </div>
                            ${item.category && item.category !== 'Otros' ? `<div class="badge-category cat-${item.category.toLowerCase().replace('í', 'i')}">${item.category}</div>` : ''}
                        </div>
                    </div>
                    <div class="card-content">
                        <div class="card-date">${formatDate(item.date)} ${isRead ? `<span class="read-tag">• ${'Leído'}</span>` : ''}</div>
                        <h2 class="card-title">${item.title}</h2>
                        <div class="card-footer">
                            <span class="read-more">${'Ver narrativa'}</span>
                            <div class="line"></div>
                        </div>
                    </div>
                </div>
            `;

            /* 
            // Insert Ad every 4 items
            if ((index + 1) % 4 === 0) {
                html += `
                    <div class="card-ad glass">
                        <span class="ad-label">${'PUBLICIDAD'}</span>
                        <div class="ad-placeholder">
                            <ins class="adsbygoogle"
                                 style="display:block"
                                 data-ad-format="fluid"
                                 data-ad-layout-key="-fb+5w+4e-db+86"
                                 data-ad-client="ca-pub-5020124346364113"
                                 data-ad-slot="auto"></ins>
                        </div>
                    </div>
                `;
                // Push AdSense
                setTimeout(() => {
                    (window.adsbygoogle = window.adsbygoogle || []).push({});
                }, 100);
            }
            */

            return html;
        }).join('');

        // Add click events to cards
        document.querySelectorAll('.card').forEach(card => {
            card.addEventListener('click', (e) => {
                lastScrollPos = window.scrollY; // Save scroll POS
                const id = e.currentTarget.getAttribute('data-id');
                showDetail(id);
            });
        });
    }

    function showDetail(id) {
        const item = newsData.find(n => n.id === id);
        if (!item) return;

        // Marcar como leído
        const readIds = JSON.parse(localStorage.getItem(READ_ARTICLES_KEY) || '[]');
        if (!readIds.includes(id)) {
            readIds.push(id);
            localStorage.setItem(READ_ARTICLES_KEY, JSON.stringify(readIds));
        }

        // Render Detail
        const sentimentColorClass = item.sentiment === 'positiva' ? 'text-emerald' : (item.sentiment === 'negativa' ? 'text-rose' : 'text-muted');

        const isEu = currentLang === 'eu';
        const isPl = currentLang === 'pl';
        const displayTitle = (isEu && item.title_eu) ? item.title_eu : (isPl && item.title_pl ? item.title_pl : item.title);
        const displayBody = (isEu && item.body_eu) ? item.body_eu : (isPl && item.body_pl ? item.body_pl : (item.body || ''));

        const paragraphs = displayBody ? displayBody.split('\n').filter(p => p.trim() !== '') : [];
        const bodyHtml = paragraphs.length > 0 
            ? paragraphs.map(p => `<p class="paragraph">${p}</p>`).join('')
            : `<p class="paragraph" style="color:var(--text-muted); font-style:italic;">${isEu ? 'Eduki osoa ez dago eskuragarri.' : (isPl ? 'Pełna treść nie jest dostępna.' : 'El contenido completo no está disponible.')}</p>`;

        articleContent.innerHTML = `
            <div class="hero-wrap">
                <img src="${item.image || ''}" alt="${displayTitle}" class="hero-img" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9IiMxZTI5M2IiLz48L3N2Zz4='">
                <div class="hero-overlay"></div>
                <div class="hero-content">
                    <div class="hero-badges">
                        <span class="badge-sentiment ${sentimentColorClass}"># ${item.sentiment}</span>
                        ${item.category ? `<span class="badge-source">${item.category}</span>` : ''}
                    </div>
                    <h1 class="hero-title">${displayTitle}</h1>
                </div>
            </div>
            
            <div class="article-body">
                <div class="meta-info">
                    <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    ${formatLongDate(item.date)}
                </div>
                
                <div class="prose-content">
                    ${bodyHtml}
                </div>
                
                <div class="article-footer">
                    <div class="footer-note">${isEu ? 'IA bitartez egiaztatutako eta aztertutako dokumentua' : (isPl ? 'Dokument zweryfikowany i przeanalizowany przez AI' : 'Documento verificado y analizado por IA')}</div>
                </div>
            </div>
        `;

        // Swap views
        mainView.classList.replace('view-active', 'view-hidden');
        detailView.classList.replace('view-hidden', 'view-active');
        backNav.classList.replace('view-hidden', 'view-active');
        window.scrollTo({ top: 0, behavior: 'instant' });
    }

    backBtn.addEventListener('click', () => {
        sortNewsByReadState();
        renderNewsFeed();
        detailView.classList.replace('view-active', 'view-hidden');
        backNav.classList.replace('view-active', 'view-hidden');
        mainView.classList.replace('view-hidden', 'view-active');
        // Restore scroll position
        window.scrollTo({ top: lastScrollPos, behavior: 'instant' });
    });

    // Handle language changes from the toggle buttons
    
    function renderMoodWidget(history) {
        const widget = document.getElementById('mood-widget-container');
        if (!widget) return;

        widget.style.display = 'block';

        const todayMood = history[history.length - 1];
        const score = todayMood.score;

        const moodTextEl = document.getElementById('mood-text');
        const moodMarkerEl = document.getElementById('mood-marker');

        let emoji = '😐';
        let text = 'Vitoria está neutral';

        if (score > 0.3) {
            emoji = '😄';
            text = 'Vitoria está de excelente humor';
        } else if (score > 0.05) {
            emoji = '🙂';
            text = 'Vitoria tiene un buen día';
        } else if (score < -0.3) {
            emoji = '😞';
            text = 'Vitoria tiene un día difícil';
        } else if (score < -0.05) {
            emoji = '😕';
            text = 'Vitoria está algo decaída';
        }

        moodTextEl.textContent = `${text} (Score: ${score > 0 ? '+' : ''}${score})`;
        moodMarkerEl.textContent = emoji;

        let percent = ((score + 1) / 2) * 100;
        percent = Math.max(5, Math.min(95, percent));

        setTimeout(() => {
            moodMarkerEl.style.left = `${percent}%`;
        }, 500);

        const chartEl = document.getElementById('mood-history-chart');
        const isMobile = window.innerWidth <= 480;
        const daysToShow = isMobile ? 5 : 7;
        const lastDays = history.slice(-daysToShow);

        chartEl.innerHTML = lastDays.map(day => {
            const dayScore = day.score;
            let barColor = 'var(--text-muted)';
            if (dayScore > 0.05) barColor = 'var(--emerald-400)';
            if (dayScore < -0.05) barColor = 'var(--rose-400)';

            const absScore = Math.abs(dayScore);
            const heightPct = Math.max(10, absScore * 100);

                        const date = new Date(day.date);
            let dStr = "";
            if (currentLang === 'eu') {
                dStr = getEuskaraDate(date);
            } else {
                dStr = date.toLocaleDateString(locales[currentLang] || 'es-ES', { day: 'numeric', month: 'short' }).replace('.', '');
            }

            return `
                <div class="history-bar-col" title="${day.date}: ${dayScore}">
                    <div class="history-bar" style="height: ${heightPct}%; background-color: ${barColor}"></div>
                    <div class="history-date">${dStr}</div>
                </div>
            `;
        }).join('');
    }

    function updatePodcastPlayer() {
        // Dejamos que el reproductor nativo de Spotify del HTML maneje el feed.
        // Spotify Show Embed se actualiza automáticamente con el último capítulo.
        /*
        const iframe = document.querySelector('.spotify-embed iframe');
        if (!iframe || !podcastData) return;

        // Seleccionamos el slug según el idioma
        let slug = podcastData.es_slug;
        if (currentLang === 'eu') slug = podcastData.eu_slug;
        if (currentLang === 'pl') slug = podcastData.pl_slug;

        if (slug) {
            // El formato de embed de Anchor es muy compatible y estable
            const newSrc = `https://anchor.fm/eduardo-armentia/embed/episodes/${slug}`;
            const currentSrc = iframe.getAttribute('src');
            if (!currentSrc || !currentSrc.includes(slug)) {
                iframe.setAttribute('src', newSrc);
                iframe.setAttribute('scrolling', 'no'); // Evitar scrollbar
            }
        }
        */
    }
});

// Global function so onclick in HTML can reach it
