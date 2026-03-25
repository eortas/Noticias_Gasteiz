document.addEventListener('DOMContentLoaded', () => {
    const mainView = document.getElementById('main-view');
    const detailView = document.getElementById('detail-view');
    const statsContainer = document.getElementById('stats-container');
    const newsGrid = document.getElementById('news-grid');
    const articleContent = document.getElementById('article-content');
    const backBtn = document.getElementById('back-btn');
    const liveUpdateBadge = document.getElementById('live-update-badge');

    let newsData = [];

    // Set today's date
    const today = new Date().toLocaleDateString('es-ES', { day: '2-digit', month: 'long' });
    liveUpdateBadge.innerHTML = `<span class="ping"></span><span class="dot"></span>Live Update • ${today}`;

    // Load Data
    fetch('data/news.json')
        .then(res => res.json())
        .then(data => {
            newsData = data;
            renderStats();
            renderNewsFeed();
        })
        .catch(err => {
            console.error('Error loading news:', err);
            newsGrid.innerHTML = '<p style="color:var(--text-muted); font-weight:300;">Error cargando las narrativas. Asegúrate de haber ejecutado el scraper.</p>';
        });

    function renderStats() {
        if (!newsData || newsData.length === 0) return;
        
        const total = newsData.length;
        const positivas = newsData.filter(n => n.sentiment === 'positiva').length;
        const negativas = newsData.filter(n => n.sentiment === 'negativa').length;
        const pctPositivas = total > 0 ? Math.round((positivas / total) * 100) : 0;

        statsContainer.innerHTML = `
            <div class="stat-item">
                <div class="stat-label">Volumen</div>
                <div class="stat-value">${total} <span style="font-size:1rem; font-weight:600; color:var(--text-muted); letter-spacing:0">News</span></div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
                <div class="stat-label">Vibe Positivo</div>
                <div class="stat-value text-emerald">${pctPositivas}%</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
                <div class="stat-label">Critical Alerta</div>
                <div class="stat-value text-rose">${negativas}</div>
            </div>
        `;
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

    function renderNewsFeed() {
        if (!newsData || newsData.length === 0) {
            newsGrid.innerHTML = '<p style="color:var(--text-muted); font-weight:300;">No hay noticias disponibles.</p>';
            return;
        }

        newsGrid.innerHTML = newsData.map(item => `
            <div class="card glass" data-id="${item.id}">
                <div class="card-img-wrap">
                    <img src="${item.image || ''}" alt="${item.title}" class="card-img" loading="lazy" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9IiMxZTI5M2IiLz48L3N2Zz4='">
                    <div class="img-overlay"></div>
                    <div class="card-source-badge">
                        <div class="sentiment-dot dot-${item.sentiment}"></div>
                        <span class="source-text">${item.source}</span>
                    </div>
                </div>
                <div class="card-content">
                    <div class="card-date">${formatDate(item.date)}</div>
                    <h2 class="card-title">${item.title}</h2>
                    <div class="card-footer">
                        <span class="read-more">Ver narrativa</span>
                        <div class="line"></div>
                    </div>
                </div>
            </div>
        `).join('');

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
                        <span class="badge-source">${item.source}</span>
                        <span class="badge-sentiment ${sentimentColorClass}"># ${item.sentiment}</span>
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
                    <div class="footer-note">Documento generado por IA vía ${item.source}</div>
                    <a href="${item.url}" target="_blank" class="source-link">
                        Ver fuente original
                        <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                        </svg>
                    </a>
                </div>
            </div>
        `;

        // Swap views
        mainView.classList.replace('view-active', 'view-hidden');
        detailView.classList.replace('view-hidden', 'view-active');
        window.scrollTo({ top: 0, behavior: 'instant' });
    }

    backBtn.addEventListener('click', () => {
        detailView.classList.replace('view-active', 'view-hidden');
        mainView.classList.replace('view-hidden', 'view-active');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
});
