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
    let currentFilter = null;
    const READ_ARTICLES_KEY = 'vitoria_read_articles';

    // Set today's date
    const today = new Date().toLocaleDateString('es-ES', { day: '2-digit', month: 'long' });
    liveUpdateBadge.innerHTML = `<span class="ping"></span><span class="dot"></span>Live Update • ${today}`;

    // Load Data
    Promise.all([
        fetch('data/news.json').then(res => res.json()).catch(() => []),
        fetch('data/mood_history.json').then(res => res.json()).catch(() => [])
    ]).then(([news, moodHistory]) => {
        newsData = news;
        if (newsData.length > 0) {
            sortNewsByReadState();
            renderStats();
            renderNewsFeed();
        } else {
            newsGrid.innerHTML = '<p style="color:var(--text-muted); font-weight:300;">Error cargando las narrativas. Asegúrate de haber ejecutado el scraper.</p>';
        }
        
        if (moodHistory && moodHistory.length > 0) {
            renderMoodWidget(moodHistory);
        }
    });

    function renderStats() {
        if (!newsData || newsData.length === 0) return;
        
        const total = newsData.length;
        const positivas = newsData.filter(n => n.sentiment === 'positiva').length;
        const negativas = newsData.filter(n => n.sentiment === 'negativa').length;
        const pctPositivas = total > 0 ? Math.round((positivas / total) * 100) : 0;

        const hasFilter = currentFilter !== null;

        statsContainer.innerHTML = `
            <div class="stat-item ${currentFilter === null ? 'stat-active' : ''}" id="stat-all" style="cursor:pointer">
                <div class="stat-label">Volumen</div>
                <div class="stat-value">${total} <span style="font-size:1rem; font-weight:600; color:var(--text-muted); letter-spacing:0">Noticias</span> ${currentFilter === null ? '<span class="filter-dot"></span>' : ''}</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item ${currentFilter === 'positiva' ? 'stat-active' : ''}" id="stat-pos" style="cursor:pointer">
                <div class="stat-label">Vibe Positivo</div>
                <div class="stat-value text-emerald">${pctPositivas}% ${currentFilter === 'positiva' ? '<span class="filter-dot"></span>' : ''}</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item ${currentFilter === 'negativa' ? 'stat-active' : ''}" id="stat-neg" style="cursor:pointer">
                <div class="stat-label">Vibe Negativo</div>
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

    function formatDate(dateStr) {
        try {
            return new Date(dateStr).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
        } catch {
            return 'Reciente';
        }
    }
    function formatLongDate(dateStr) {
        try {
            return new Date(dateStr).toLocaleDateString('es-ES', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
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
                        <div class="card-date">${formatDate(item.date)} ${isRead ? '<span class="read-tag">• Leído</span>' : ''}</div>
                        <h2 class="card-title">${item.title}</h2>
                        <div class="card-footer">
                            <span class="read-more">Ver narrativa</span>
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
        
        const paragraphs = item.body ? item.body.split('\n').filter(p => p.trim() !== '') : [];
        const bodyHtml = paragraphs.map(p => `<p class="paragraph">${p}</p>`).join('');

        articleContent.innerHTML = `
            <div class="hero-wrap">
                <img src="${item.image || ''}" alt="${item.title}" class="hero-img" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9IiMxZTI5M2IiLz48L3N2Zz4='">
                <div class="hero-overlay"></div>
                <div class="hero-content">
                    <div class="hero-badges">
                        <span class="badge-sentiment ${sentimentColorClass}"># ${item.sentiment}</span>
                        ${item.category ? `<span class="badge-source">${item.category}</span>` : ''}
                    </div>
                    <h1 class="hero-title">${item.title}</h1>
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
                    <div class="footer-note">Documento verificado y analizado por IA</div>
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
        const last7 = history.slice(-7);
        
        chartEl.innerHTML = last7.map(day => {
            const dayScore = day.score;
            let barColor = 'var(--text-muted)';
            if (dayScore > 0.05) barColor = 'var(--emerald-400)';
            if (dayScore < -0.05) barColor = 'var(--rose-400)';
            
            const absScore = Math.abs(dayScore);
            const heightPct = Math.max(10, absScore * 100);
            
            const dStr = new Date(day.date).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' }).replace('.', '');
            
            return `
                <div class="history-bar-col" title="${day.date}: ${dayScore}">
                    <div class="history-bar" style="height: ${heightPct}%; background-color: ${barColor}"></div>
                    <div class="history-date">${dStr}</div>
                </div>
            `;
        }).join('');
    }
});
