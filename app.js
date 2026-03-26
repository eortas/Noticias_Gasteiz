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
    let currentFilter = null;
    let currentLang = localStorage.getItem('vitoria_lang') || 'es';
    const READ_ARTICLES_KEY = 'vitoria_read_articles';

    // Apply initial lang state
    function applyLangUI() {
        document.getElementById('btn-es').classList.toggle('active', currentLang === 'es');
        document.getElementById('btn-eu').classList.toggle('active', currentLang === 'eu');
        document.getElementById('btn-pl').classList.toggle('active', currentLang === 'pl');
        
        const subtitle = document.getElementById('subtitle-text');
        const moodTitle = document.getElementById('mood-title');
        const backBtnText = document.getElementById('back-btn-text');
        const footerCopyright = document.getElementById('footer-copyright');

        const locales = { es: 'es-ES', eu: 'eu-ES', pl: 'pl-PL' };
        const currentLocale = locales[currentLang] || 'es-ES';
        let todayStr = "";
        if (currentLang === 'eu') {
            todayStr = getEuskaraDate(new Date());
        } else {
            todayStr = new Date().toLocaleDateString(currentLocale, { day: '2-digit', month: 'long' });
        }
        
        if (liveUpdateBadge) {
            liveUpdateBadge.innerHTML = `<span class="ping"></span><span class="dot"></span>Live Update • ${todayStr.toUpperCase()}`;
        }

        if (subtitle) {
            if (currentLang === 'eu') {
                subtitle.innerHTML = 'Gasteiz-ko berrien ataria. Informazioaren fluxua <span class="italic">bisual-narratibetan</span> bihurtzen dugu, adimen artifizialarekin aztertuta.';
            } else if (currentLang === 'pl') {
                subtitle.innerHTML = 'Twój portal informacyjny Vitoria-Gasteiz. Przekształcamy przepływ informacji w <span class="italic">wizualne narracje</span> analizowane przez sztuczną inteligencję.';
            } else {
                subtitle.innerHTML = 'Tu portal de noticias de Vitoria-Gasteiz. Transformamos el flujo de información en <span class="italic">narrativas visuales</span> analizadas por inteligencia artificial.';
            }
        }

        if (moodTitle) {
            moodTitle.textContent = currentLang === 'eu' ? 'Gasteizko "Mood"-a' : (currentLang === 'pl' ? 'Atmosfera Vitoria' : 'El "Mood"');
        }

        if (backBtnText) {
            backBtnText.textContent = currentLang === 'eu' ? 'Atariara itzuli' : (currentLang === 'pl' ? 'Powrót do portalu' : 'Volver al portal');
        }

        if (footerCopyright) {
            footerCopyright.textContent = `© 2026 Vitoria Live • Powered by AI.`;
        }
    }
    applyLangUI();


    // Initial date will be set by applyLangUI()

    // Load Data
    Promise.all([
        fetch('data/news.json').then(res => res.json()).catch(() => []),
        fetch('data/mood_history.json').then(res => res.json()).catch(() => [])
    ]).then(([news, moodHistory]) => {
        newsData = news;
        moodHistoryData = moodHistory;
        if (newsData.length > 0) {
            sortNewsByReadState();
            renderStats();
            renderNewsFeed();
        } else {
            newsGrid.innerHTML = '<p style="color:var(--text-muted); font-weight:300;">Error cargando las narrativas. Asegúrate de haber ejecutado el scraper.</p>';
        }
        
        if (moodHistoryData && moodHistoryData.length > 0) {
            renderMoodWidget(moodHistoryData);
        }
    });

    function renderStats() {
        if (!newsData || newsData.length === 0) return;
        
        const total = newsData.length;
        const positivas = newsData.filter(n => n.sentiment === 'positiva').length;
        const negativas = newsData.filter(n => n.sentiment === 'negativa').length;
        const pctPositivas = total > 0 ? Math.round((positivas / total) * 100) : 0;

        const hasFilter = currentFilter !== null;

        const eu = currentLang === 'eu';
        const pl = currentLang === 'pl';
        statsContainer.innerHTML = `
            <div class="stat-item ${currentFilter === null ? 'stat-active' : ''}" id="stat-all" style="cursor:pointer">
                <div class="stat-label">${eu ? 'Bolumena' : (pl ? 'Wolumen' : 'Volumen')}</div>
                <div class="stat-value">${total} <span style="font-size:1rem; font-weight:600; color:var(--text-muted); letter-spacing:0">${eu ? 'Albisteak' : (pl ? 'Wiadomości' : 'Noticias')}</span> ${currentFilter === null ? '<span class="filter-dot"></span>' : ''}</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item ${currentFilter === 'positiva' ? 'stat-active' : ''}" id="stat-pos" style="cursor:pointer">
                <div class="stat-label">${eu ? 'Bibrazio Positiboa' : (pl ? 'Pozytywne Wibracje' : 'Vibe Positivo')}</div>
                <div class="stat-value text-emerald">${pctPositivas}% ${currentFilter === 'positiva' ? '<span class="filter-dot"></span>' : ''}</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item ${currentFilter === 'negativa' ? 'stat-active' : ''}" id="stat-neg" style="cursor:pointer">
                <div class="stat-label">${eu ? 'Bibrazio Negatiboa' : (pl ? 'Negatywne Wibracje' : 'Vibe Negativo')}</div>
                <div class="stat-value text-rose">${negativas} ${currentFilter === 'negativa' ? '<span class="filter-dot"></span>' : ''}</div>
            </div>
        `;

        // Listeners for stats
        document.getElementById('stat-all').onclick = () => setFilter(null);
        document.getElementById('stat-pos').onclick = () => setFilter('positiva');
        document.getElementById('stat-neg').onclick = () => setFilter('negativa');
    }

    function setFilter(sentiment) {
        currentFilter = sentiment;
        renderStats();
        renderNewsFeed();
    }

    function getEuskaraDate(date, long = false) {
        const months = ['urtarrilaren', 'otsailaren', 'martxoaren', 'apirilaren', 'maiatzaren', 'ekainaren', 'uztailaren', 'abuztuaren', 'irailaren', 'urriaren', 'azaroaren', 'abenduaren'];
        const weekdays = ['igandea', 'astelehena', 'asteartea', 'asteazkena', 'osteguna', 'ostirala', 'larunbata'];
        const d = date.getDate();
        const m = months[date.getMonth()];
        const y = date.getFullYear();
        if (long) {
            const w = weekdays[date.getDay()];
            return `${y}(e)ko ${m} ${d}a, ${w}`;
        }
        return `${m} ${d}a`;
    }

    function formatDate(dateStr) {
        const locales = { es: 'es-ES', eu: 'eu-ES', pl: 'pl-PL' };
        try {
            const date = new Date(dateStr);
            if (currentLang === 'eu') return getEuskaraDate(date);
            return date.toLocaleDateString(locales[currentLang] || 'es-ES', { day: '2-digit', month: 'short' });
        } catch {
            return currentLang === 'eu' ? 'Berria' : (currentLang === 'pl' ? 'Najnowsze' : 'Reciente');
        }
    }
    function formatLongDate(dateStr) {
        const locales = { es: 'es-ES', eu: 'eu-ES', pl: 'pl-PL' };
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

        newsGrid.innerHTML = filteredData.map(item => {
            const isRead = readIds.includes(item.id);
            return `
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
                        <div class="card-date">${formatDate(item.date)} ${isRead ? `<span class="read-tag">• ${currentLang === 'eu' ? 'Irakurrita' : (currentLang === 'pl' ? 'Przeczytane' : 'Leído')}</span>` : ''}</div>
                        <h2 class="card-title">${currentLang === 'eu' && item.title_eu ? item.title_eu : (currentLang === 'pl' && item.title_pl ? item.title_pl : item.title)}</h2>
                        <div class="card-footer">
                            <span class="read-more">${currentLang === 'eu' ? 'Irakurri' : (currentLang === 'pl' ? 'Czytaj więcej' : 'Ver narrativa')}</span>
                            <div class="line"></div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Add click events to cards
        document.querySelectorAll('.card').forEach(card => {
            card.addEventListener('click', (e) => {
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
        const displayBody = (isEu && item.body_eu) ? item.body_eu : (isPl && item.body_pl ? item.body_pl : item.body);

        const paragraphs = displayBody ? displayBody.split('\n').filter(p => p.trim() !== '') : [];
        const bodyHtml = paragraphs.map(p => `<p class="paragraph">${p}</p>`).join('');

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
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // Handle language changes from the toggle buttons
    document.getElementById('main-view').addEventListener('langchange', (e) => {
        currentLang = e.detail;
        localStorage.setItem('vitoria_lang', currentLang);
        applyLangUI();
        renderStats();
        renderNewsFeed();
        if (moodHistoryData && moodHistoryData.length > 0) {
            renderMoodWidget(moodHistoryData);
        }
    });

    function renderMoodWidget(history) {
        const widget = document.getElementById('mood-widget-container');
        if (!widget) return;
        
        widget.style.display = 'block';
        
        const todayMood = history[history.length - 1];
        const score = todayMood.score; 
        
        const moodTextEl = document.getElementById('mood-text');
        const moodMarkerEl = document.getElementById('mood-marker');
        
        let emoji = '😐';
        let text = currentLang === 'eu' ? 'Gasteiz neutroa da' : (currentLang === 'pl' ? 'Vitoria jest neutralna' : 'Vitoria está neutral');
        
        if (score > 0.3) {
            emoji = '😄';
            text = currentLang === 'eu' ? 'Gasteiz umore bikainean dago' : (currentLang === 'pl' ? 'Vitoria jest w doskonałym nastroju' : 'Vitoria está de excelente humor');
        } else if (score > 0.05) {
            emoji = '🙂';
            text = currentLang === 'eu' ? 'Gasteizko eguna ona da' : (currentLang === 'pl' ? 'Vitoria ma dobry dzień' : 'Vitoria tiene un buen día');
        } else if (score < -0.3) {
            emoji = '😞';
            text = currentLang === 'eu' ? 'Gasteizek egun zaila du' : (currentLang === 'pl' ? 'Vitoria ma trudny dzień' : 'Vitoria tiene un día difícil');
        } else if (score < -0.05) {
            emoji = '😕';
            text = currentLang === 'eu' ? 'Gasteiz zertxobait dekaitua dago' : (currentLang === 'pl' ? 'Vitoria jest nieco przygnębiona' : 'Vitoria está algo decaída');
        }
        
        moodTextEl.textContent = `${text} (Score: ${score > 0 ? '+' : ''}${score})`;
        moodMarkerEl.textContent = emoji;
        
        let percent = ((score + 1) / 2) * 100;
        percent = Math.max(5, Math.min(95, percent));
        
        setTimeout(() => {
            moodMarkerEl.style.left = `${percent}%`;
        }, 500);
        
        const chartEl = document.getElementById('mood-history-chart');
        const last7 = history.slice(-7);
        
        chartEl.innerHTML = last7.map(day => {
            const dayScore = day.score;
            let barColor = 'var(--text-muted)';
            if (dayScore > 0.05) barColor = 'var(--emerald-400)';
            if (dayScore < -0.05) barColor = 'var(--rose-400)';
            
            const absScore = Math.abs(dayScore);
            const heightPct = Math.max(10, absScore * 100);
            
            const locales = { es: 'es-ES', eu: 'eu-ES', pl: 'pl-PL' };
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
});

// Global function so onclick in HTML can reach it
function setLang(lang) {
    const app = document.getElementById('main-view');
    if (!app) return;
    // Dispatch a custom event so the DOMContentLoaded scope can handle it
    app.dispatchEvent(new CustomEvent('langchange', { detail: lang }));
}
