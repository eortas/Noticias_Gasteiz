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
    let currentCategory = null;
    const READ_ARTICLES_KEY = 'vitoria_read_articles';

    function formatDate(dateStr) {
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('es-ES', { month: 'short', day: 'numeric' });
        } catch {
            return dateStr;
        }
    }

    function formatLongDate(dateStr) {
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('es-ES', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
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

    function tokenize(text) {
        if (!text) return new Set();
        const stopwords = new Set([
            'de', 'la', 'el', 'en', 'y', 'a', 'los', 'un', 'una', 'con', 'para', 'este', 'esta', 'por', 'del', 
            'al', 'se', 'las', 'su', 'sus', 'o', 'u', 'como', 'para', 'que', 'en', 'del', 'lo', 'lo', 'los', 'un', 
            'una', 'uno', 'unas', 'unos', 'al', 'del', 'los', 'las', 'correo', 'gasteiz', 'hoy', 'noticias', 
            'alava', 'vitoria', 'diario'
        ]);
        const words = text.toLowerCase()
            .replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?"'']/g, "")
            .split(/\s+/);
        const tokens = new Set();
        for (const w of words) {
            if (w.length > 2 && !stopwords.has(w)) {
                tokens.add(w);
            }
        }
        return tokens;
    }

    function jaccardSimilarity(setA, setB) {
        if (setA.size === 0 || setB.size === 0) return 0;
        let intersection = 0;
        for (const elem of setA) {
            if (setB.has(elem)) {
                intersection++;
            }
        }
        const union = setA.size + setB.size - intersection;
        return intersection / union;
    }

    function groupNewsItems(items) {
        if (!items || items.length === 0) return [];
        
        const tokenized = items.map(item => {
            const textToCompare = (item.title || "") + " " + (item.original_title || "");
            return {
                item: item,
                tokens: tokenize(textToCompare)
            };
        });
        
        const clusters = [];
        const visited = new Set();
        const threshold = 0.25;
        
        for (let i = 0; i < tokenized.length; i++) {
            const current = tokenized[i];
            if (visited.has(current.item.id)) continue;
            
            const cluster = {
                id: current.item.id,
                primary: current.item,
                items: [current.item]
            };
            visited.add(current.item.id);
            
            for (let j = i + 1; j < tokenized.length; j++) {
                const other = tokenized[j];
                if (visited.has(other.item.id)) continue;
                
                const sim = jaccardSimilarity(current.tokens, other.tokens);
                if (sim >= threshold) {
                    cluster.items.push(other.item);
                    visited.add(other.item.id);
                }
            }
            clusters.push(cluster);
        }
        
        return clusters;
    }

    let lastScrollPos = 0;

    // Mapa de nombre visible -> clave source_section
    const SECTION_MAP = {
        'Economía': 'economia',
        'Sociedad': 'sociedad',
        'Deportes': 'deportes',
        'Cultura': 'cultura'
    };

    function getSectionData() {
        if (currentCategory) {
            const key = SECTION_MAP[currentCategory] || currentCategory.toLowerCase();
            return newsData.filter(item => item.source_section === key);
        }
        // Default: mostrar todo EXCEPTO artículos que pertenecen explícitamente a otra sección
        const sectionKeys = Object.values(SECTION_MAP);
        return newsData.filter(item => !sectionKeys.includes(item.source_section));
    }

    function renderNewsFeed() {
        if (!newsData || newsData.length === 0) {
            newsGrid.innerHTML = '<p style="color:var(--text-muted); font-weight:300;">No hay noticias disponibles.</p>';
            return;
        }

        const readIds = JSON.parse(localStorage.getItem(READ_ARTICLES_KEY) || '[]');
        const sectionData = getSectionData();
        let clusters = groupNewsItems(sectionData);

        if (currentFilter) {
            if (currentFilter === 'leidas') {
                clusters = clusters.filter(cluster => cluster.items.some(item => readIds.includes(item.id)));
            } else {
                clusters = clusters.filter(cluster => cluster.primary.sentiment_label === currentFilter);
            }
        }

        if (clusters.length === 0) {
            let noNewsText = 'No hay noticias que coincidan con estos filtros hoy.';
            if (currentFilter === 'leidas') noNewsText = 'No hay noticias leídas en esta sección todavía.';
            newsGrid.innerHTML = `<p style="color:var(--text-muted); font-weight:300; padding: 2rem;">${noNewsText}</p>`;
            return;
        }

        newsGrid.innerHTML = clusters.map((cluster, index) => {
            const item = cluster.primary;
            const isRead = cluster.items.some(it => readIds.includes(it.id));
            const sentimentClass = item.sentiment_label || 'neutral';
            const isMultiSource = cluster.items.length > 1;

            return `
                <div class="card glass ${isRead ? 'card-read' : ''} ${isMultiSource ? 'card-multi-source' : ''}" 
                     data-cluster-index="${index}" 
                     ${isMultiSource ? '' : `data-source="${item.source}"`} 
                     data-id="${item.id}">
                    <div class="card-img-wrap">
                        <img src="${item.image || ''}" alt="${item.title}" class="card-img" loading="lazy" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9IiMxZTI5M2IiLz48L3N2Zz4='">
                        <div class="img-overlay"></div>
                        <div class="card-top-badges">
                            <div class="card-source-badge">
                                <div class="sentiment-dot dot-${sentimentClass}" title="Sentimiento: ${sentimentClass}"></div>
                            </div>
                            ${isMultiSource ? `<div class="badge-multi-source">${cluster.items.length} Fuentes</div>` : ''}
                            ${item.category && item.category !== 'Otros' ? `<div class="badge-category cat-${item.category.toLowerCase().replace('í', 'i')}">${item.category}</div>` : ''}
                        </div>
                    </div>
                    <div class="card-content">
                        <div class="card-date">${formatDate(item.date)} ${isRead ? `<span class="read-tag">• Leído</span>` : ''}</div>
                        <h2 class="card-title">${item.title}</h2>
                        <div class="card-footer">
                            <span class="read-more">Ver narrativa</span>
                            <div class="line"></div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        document.querySelectorAll('.card').forEach(card => {
            card.addEventListener('click', (e) => {
                lastScrollPos = window.scrollY;
                const clusterIdx = e.currentTarget.getAttribute('data-cluster-index');
                const cluster = clusters[clusterIdx];
                if (cluster.items.length > 1) {
                    openSourcesModal(cluster);
                } else {
                    showDetail(cluster.primary.id);
                }
            });
        });
    }

    function renderStats() {
        // Contar solo la sección activa
        const sectionData = getSectionData();
        const clusters = groupNewsItems(sectionData);
        
        const counts = { 'positiva': 0, 'neutral': 0, 'negativa': 0 };
        const readIds = JSON.parse(localStorage.getItem(READ_ARTICLES_KEY) || '[]');
        let readCount = 0;

        clusters.forEach(cluster => {
            const label = cluster.primary.sentiment_label || 'neutral';
            if (counts.hasOwnProperty(label)) counts[label]++;
            
            const isRead = cluster.items.some(item => readIds.includes(item.id));
            if (isRead) readCount++;
        });

        statsContainer.innerHTML = `
            <div class="stat-item ${currentFilter === 'positiva' ? 'stat-active' : ''}" data-filter="positiva">
                <div class="stat-label">Positivas</div>
                <div class="stat-value text-emerald">
                    ${counts.positiva}
                    ${currentFilter === 'positiva' ? '<div class="filter-dot"></div>' : ''}
                </div>
            </div>
            <div class="stat-item ${currentFilter === 'neutral' ? 'stat-active' : ''}" data-filter="neutral">
                <div class="stat-label">Neutrales</div>
                <div class="stat-value">
                    ${counts.neutral}
                    ${currentFilter === 'neutral' ? '<div class="filter-dot"></div>' : ''}
                </div>
            </div>
            <div class="stat-item ${currentFilter === 'negativa' ? 'stat-active' : ''}" data-filter="negativa">
                <div class="stat-label">Negativas</div>
                <div class="stat-value text-rose">
                    ${counts.negativa}
                    ${currentFilter === 'negativa' ? '<div class="filter-dot"></div>' : ''}
                </div>
            </div>
            <div class="stat-item ${currentFilter === 'leidas' ? 'stat-active' : ''}" data-filter="leidas">
                <div class="stat-label">Leídas</div>
                <div class="stat-value text-indigo">
                    ${readCount}
                    ${currentFilter === 'leidas' ? '<div class="filter-dot"></div>' : ''}
                </div>
            </div>
        `;

        document.querySelectorAll('.stat-item').forEach(item => {
            item.addEventListener('click', () => {
                const filter = item.getAttribute('data-filter');
                currentFilter = (currentFilter === filter) ? null : filter;
                renderStats();
                renderNewsFeed();
            });
        });
    }

    function renderCategories() {
        const categoriesContainer = document.getElementById('categories-container');
        if (!categoriesContainer) return;

        // Siempre mostrar los 4 botones fijos; se habilitan/deshabilitan visualmente según datos
        const allCategories = [
            { label: 'Economía', key: 'economia' },
            { label: 'Sociedad',  key: 'sociedad' },
            { label: 'Deportes', key: 'deportes' },
            { label: 'Cultura',  key: 'cultura' }
        ];

        const availableSections = new Set(newsData.map(item => item.source_section).filter(Boolean));

        categoriesContainer.innerHTML = allCategories.map(cat => {
            const hasData = availableSections.has(cat.key);
            return `
            <div class="category-btn ${currentCategory === cat.label ? 'active' : ''} ${!hasData ? 'cat-empty' : ''}" 
                 data-category="${cat.label}" title="${!hasData ? 'Sin noticias hoy en esta sección' : cat.label}">
                ${cat.label}
            </div>`;
        }).join('');

        categoriesContainer.querySelectorAll('.category-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const cat = btn.getAttribute('data-category');
                currentCategory = (currentCategory === cat) ? null : cat;
                currentFilter = null; // Resetear filtro de sentimiento al cambiar sección
                renderStats();
                renderCategories();
                renderNewsFeed();
            });
        });
    }

    const sourcesModal = document.getElementById('sources-modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');

    function openSourcesModal(cluster) {
        const sourcesList = document.getElementById('modal-sources-list');
        sourcesList.innerHTML = cluster.items.map(item => {
            const sentimentClass = item.sentiment_label || 'neutral';
            return `
                <button class="source-option-btn" data-id="${item.id}">
                    <div>
                        <div class="source-option-name">
                            <div class="sentiment-dot dot-${sentimentClass}"></div>
                            ${item.source}
                        </div>
                        <div class="source-option-title">${item.title}</div>
                    </div>
                    <div class="source-option-meta">
                        <span style="font-size: 0.75rem; color: var(--text-muted);">${formatDate(item.date)}</span>
                    </div>
                </button>
            `;
        }).join('');

        // Bind clicks to source buttons
        sourcesList.querySelectorAll('.source-option-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-id');
                closeSourcesModal();
                showDetail(id);
            });
        });

        sourcesModal.classList.remove('view-hidden');
    }

    function closeSourcesModal() {
        sourcesModal.classList.add('view-hidden');
    }

    modalCloseBtn.addEventListener('click', closeSourcesModal);
    sourcesModal.addEventListener('click', (e) => {
        if (e.target === sourcesModal) {
            closeSourcesModal();
        }
    });

    function showDetail(id, fromPopState = false, replaceState = false) {
        if (!fromPopState) {
            lastScrollPos = window.scrollY;
        }
        const item = newsData.find(n => n.id === id);
        if (!item) return;

        // Marcar como leído
        const readIds = JSON.parse(localStorage.getItem(READ_ARTICLES_KEY) || '[]');
        if (!readIds.includes(id)) {
            readIds.push(id);
            localStorage.setItem(READ_ARTICLES_KEY, JSON.stringify(readIds));
        }

        // Encontrar el cluster para comparar fuentes en la vista detallada
        const allClusters = groupNewsItems(newsData);
        const cluster = allClusters.find(c => c.items.some(it => it.id === id));
        
        let sourcesSelectorHtml = '';
        if (cluster && cluster.items.length > 1) {
            sourcesSelectorHtml = `
                <div class="detail-sources-selector">
                    <span class="selector-label">Comparar fuentes:</span>
                    <div class="selector-pills">
                        ${cluster.items.map(it => `
                            <button class="source-pill ${it.id === id ? 'active' : ''}" data-id="${it.id}">
                                ${it.source}
                            </button>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        const sentimentColorClass = item.sentiment_label === 'positiva' ? 'text-emerald' : (item.sentiment_label === 'negativa' ? 'text-rose' : 'text-muted');
        const paragraphs = (item.body || '').split('\n').filter(p => p.trim() !== '');
        const bodyHtml = paragraphs.length > 0 
            ? paragraphs.map(p => `<p class="paragraph">${p}</p>`).join('')
            : `<p class="paragraph" style="color:var(--text-muted); font-style:italic;">El contenido completo no está disponible.</p>`;

        // Render Detail
        articleContent.innerHTML = `
            <div class="hero-wrap">
                <img src="${item.image || ''}" alt="${item.title}" class="hero-img" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9IiMxZTI5M2IiLz48L3N2Zz4='">
                <div class="hero-overlay"></div>
                <div class="hero-content">
                    <div class="hero-badges">
                        <span class="badge-sentiment ${sentimentColorClass}"># ${item.sentiment_label}</span>
                        ${item.category ? `<span class="badge-source">${item.category}</span>` : ''}
                    </div>
                    <h1 class="hero-title">${item.title}</h1>
                </div>
            </div>
            
            ${sourcesSelectorHtml}
            
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

        // Bind clicks to source pills
        if (cluster && cluster.items.length > 1) {
            articleContent.querySelectorAll('.source-pill').forEach(pill => {
                pill.addEventListener('click', () => {
                    const selectedId = pill.getAttribute('data-id');
                    if (selectedId !== id) {
                        showDetail(selectedId, false, true);
                    }
                });
            });
        }

        // Swap views
        mainView.classList.replace('view-active', 'view-hidden');
        detailView.classList.replace('view-hidden', 'view-active');
        backNav.classList.replace('view-hidden', 'view-active');
        window.scrollTo({ top: 0, behavior: 'instant' });

        if (!fromPopState) {
            if (replaceState) {
                history.replaceState({ view: 'detail', id: id }, '');
            } else {
                history.pushState({ view: 'detail', id: id }, '');
            }
        }
    }

    function closeDetail(fromPopState = false) {
        sortNewsByReadState();
        renderStats();
        renderNewsFeed();
        detailView.classList.replace('view-active', 'view-hidden');
        backNav.classList.replace('view-active', 'view-hidden');
        mainView.classList.replace('view-hidden', 'view-active');
        
        // Use a small timeout to ensure the DOM has reflowed before scrolling
        setTimeout(() => {
            window.scrollTo({ top: lastScrollPos, behavior: 'instant' });
        }, 10);

        if (!fromPopState && history.state && history.state.view === 'detail') {
            history.back();
        }
    }

    backBtn.addEventListener('click', () => {
        closeDetail();
    });

    window.addEventListener('popstate', (event) => {
        if (event.state && event.state.view === 'detail') {
            showDetail(event.state.id, true);
        } else {
            closeDetail(true);
        }
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
            const dStr = date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' }).replace('.', '');

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

    async function fetchData() {
        try {
            const [newsRes, moodRes, podcastRes] = await Promise.all([
                fetch('data/news.json'),
                fetch('data/mood_history.json'),
                fetch('data/podcast.json')
            ]);
            
            newsData = await newsRes.json();
            moodHistoryData = await moodRes.json();
            podcastData = await podcastRes.json();
            
            // Normalize sentiment scores to labels
            newsData.forEach(item => {
                const score = parseFloat(item.sentiment);
                if (score > 0.05) item.sentiment_label = 'positiva';
                else if (score < -0.05) item.sentiment_label = 'negativa';
                else item.sentiment_label = 'neutral';
            });
            
            sortNewsByReadState();
            renderStats();
            renderCategories();
            renderNewsFeed();
            renderMoodWidget(moodHistoryData);
            updatePodcastPlayer();
        } catch (error) {
            console.error("Error loading data:", error);
            newsGrid.innerHTML = '<p style="color:var(--text-muted); padding: 2rem;">Error cargando datos. Por favor, recarga la página.</p>';
        }
    }

    fetchData();
});

// Global function so onclick in HTML can reach it
