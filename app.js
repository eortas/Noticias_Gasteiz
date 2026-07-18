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
    const LANG_KEY = 'gasteiz_live_lang';
    let currentLang = localStorage.getItem(LANG_KEY) || 'es';

    const UI_TRANSLATIONS = {
        es: {
            subtitle: "Noticias de Vitoria-Gasteiz y Álava analizadas por Inteligencia Artificial.",
            backPortal: "Volver al portal",
            readSummary: "Leer resumen completo",
            summaryTitle: "Resumen de noticias del día",
            summaryPreview: "Colección de las noticias más relevantes de Álava y deportes, resumidas y organizadas por IA para que estés siempre informado.",
            compareSources: "Comparar fuentes:",
            verifiedAI: "Documento verificado y analizado por IA",
            noNews: "No hay noticias disponibles.",
            noNewsFilter: "No hay noticias que coincidan con estos filtros hoy.",
            noNewsRead: "No hay noticias leídas en esta sección todavía.",
            sourcesModalTitle: "Selecciona la fuente de información",
            sourcesModalSubtitle: "Esta noticia ha sido publicada por varios medios locales. Elige qué versión prefieres leer:",
            sourcesCount: "Fuentes",
            sentimentPos: "Positivas",
            sentimentNeu: "Neutrales",
            sentimentNeg: "Negativas",
            sentimentRead: "Leídas",
            sentimentTag: "Leído",
            catEconomia: "Economía",
            catSociedad: "Sociedad",
            catDeportes: "Deportes",
            catCultura: "Cultura",
            moodTitle: "El \"Mood\"",
            positiva: "Positiva",
            negativa: "Negativa",
            neutral: "Neutral"
        },
        eu: {
            subtitle: "Vitoria-Gasteizko eta Arabako albisteak Adimen Artifizialak aztertuta.",
            backPortal: "Atariara itzuli",
            readSummary: "Laburpen osoa irakurri",
            summaryTitle: "Eguneko albisteen laburpena",
            summaryPreview: "Arabako eta kiroletako albiste garrantzitsuenen bilduma, AI-k laburtu eta antolatua beti informatuta egon zaitezen.",
            compareSources: "Iturriak alderatu:",
            verifiedAI: "Agiria egiaztatuta eta AI-k aztertuta",
            noNews: "Ez dago albisterik eskuragarri.",
            noNewsFilter: "Ez dago iragazki hauekin bat datorren albisterik gaur.",
            noNewsRead: "Ez dago irakurritako albisterik atal honetan oraindik.",
            sourcesModalTitle: "Aukeratu informazio iturria",
            sourcesModalSubtitle: "Albiste hau tokiko hainbat komunikabidek argitaratu dute. Aukeratu zein bertsio irakurri nahi duzun:",
            sourcesCount: "Iturriak",
            sentimentPos: "Positiboak",
            sentimentNeu: "Neutroak",
            sentimentNeg: "Negatiboak",
            sentimentRead: "Irakurriak",
            sentimentTag: "Irakurrita",
            catEconomia: "Ekonomia",
            catSociedad: "Gizartea",
            catDeportes: "Kirolak",
            catCultura: "Kultura",
            moodTitle: "Gasteizko \"Mood\"-a",
            positiva: "Positiboa",
            negativa: "Negatiboa",
            neutral: "Neutroa"
        },
        pl: {
            subtitle: "Wiadomości z Vitoria-Gasteiz i Alavy analizowane przez Sztuczną Inteligencję.",
            backPortal: "Wróć do portalu",
            readSummary: "Przeczytaj całe podsumowanie",
            summaryTitle: "Podsumowanie wiadomości dnia",
            summaryPreview: "Zbiór najważniejszych wiadomości z Alavy i sportu, podsumowany i zorganizedowany przez AI, abyś zawsze był poinformowany.",
            compareSources: "Porównaj źródła:",
            verifiedAI: "Dokument zweryfikowany i przeanalizowany przez AI",
            noNews: "Brak dostępnych wiadomości.",
            noNewsFilter: "Brak wiadomości spełniających te filtry dzisiaj.",
            noNewsRead: "Brak przeczytanych wiadomości w tej sekcji.",
            sourcesModalTitle: "Wybierz źródło informacji",
            sourcesModalSubtitle: "Ta wiadomość została opublikowana przez kilka lokalnych mediów. Wybierz wersję, którą wolisz przeczytać:",
            sourcesCount: "Źródła",
            sentimentPos: "Pozytywne",
            sentimentNeu: "Neutralne",
            sentimentNeg: "Negatywne",
            sentimentRead: "Przeczytane",
            sentimentTag: "Przeczytane",
            catEconomia: "Ekonomia",
            catSociedad: "Społeczeństwo",
            catDeportes: "Sport",
            catCultura: "Kultura",
            moodTitle: "Nastroje miasta",
            positiva: "Pozytywna",
            negativa: "Negatywna",
            neutral: "Neutralna"
        },
        fr: {
            subtitle: "Actualités de Vitoria-Gasteiz et de l'Álava analysées par l'Intelligence Artificielle.",
            backPortal: "Retour au portail",
            readSummary: "Lire le résumé complet",
            summaryTitle: "Résumé de l'actualité du jour",
            summaryPreview: "Collection des nouvelles les plus pertinentes d'Álava et des sports, résumées et organisées par l'IA pour vous tenir informé.",
            compareSources: "Comparer les sources :",
            verifiedAI: "Document vérifié et analysé par l'IA",
            noNews: "Aucune actualité disponible.",
            noNewsFilter: "Aucune actualité ne correspond à ces filtres aujourd'hui.",
            noNewsRead: "Aucune actualité lue dans cette section pour l'instant.",
            sourcesModalTitle: "Sélectionnez la source d'information",
            sourcesModalSubtitle: "Cette actualité a été publiée par plusieurs médias locaux. Choisissez la version que vous préférez lire :",
            sourcesCount: "Sources",
            sentimentPos: "Positives",
            sentimentNeu: "Neutres",
            sentimentNeg: "Négatives",
            sentimentRead: "Lues",
            sentimentTag: "Lu",
            catEconomia: "Économie",
            catSociedad: "Société",
            catDeportes: "Sports",
            catCultura: "Culture",
            moodTitle: "L'humeur",
            positiva: "Positive",
            negativa: "Négative",
            neutral: "Neutre"
        },
        en: {
            subtitle: "News of Vitoria-Gasteiz and Álava analyzed by Artificial Intelligence.",
            backPortal: "Back to portal",
            readSummary: "Read full summary",
            summaryTitle: "Daily news summary",
            summaryPreview: "Collection of the most relevant news of Álava and sports, summarized and organized by AI to keep you always informed.",
            compareSources: "Compare sources:",
            verifiedAI: "Document verified and analyzed by AI",
            noNews: "No news available.",
            noNewsFilter: "No news matching these filters today.",
            noNewsRead: "No read news in this section yet.",
            sourcesModalTitle: "Select the information source",
            sourcesModalSubtitle: "This news has been published by several local media outlets. Choose which version you prefer to read:",
            sourcesCount: "Sources",
            sentimentPos: "Positive",
            sentimentNeu: "Neutral",
            sentimentNeg: "Negative",
            sentimentRead: "Read",
            sentimentTag: "Read",
            catEconomia: "Economy",
            catSociedad: "Society",
            catDeportes: "Sports",
            catCultura: "Culture",
            moodTitle: "The \"Mood\"",
            positiva: "Positive",
            negativa: "Negative",
            neutral: "Neutral"
        }
    };

    function initLanguage() {
        const btnEs = document.getElementById('btn-lang-es');
        const btnEu = document.getElementById('btn-lang-eu');
        const btnFr = document.getElementById('btn-lang-fr');
        const btnEn = document.getElementById('btn-lang-en');
        const btnPl = document.getElementById('btn-lang-pl');
        const subtitleText = document.getElementById('subtitle-text');
        
        // Sincronizar UI de botones al inicio
        const updateButtonActiveState = () => {
            if (btnEs) btnEs.classList.toggle('active', currentLang === 'es');
            if (btnEu) btnEu.classList.toggle('active', currentLang === 'eu');
            if (btnFr) btnFr.classList.toggle('active', currentLang === 'fr');
            if (btnEn) btnEn.classList.toggle('active', currentLang === 'en');
            if (btnPl) btnPl.classList.toggle('active', currentLang === 'pl');
        };
        
        updateButtonActiveState();
        
        // Actualizar subtítulo inicial
        if (subtitleText) {
            subtitleText.textContent = UI_TRANSLATIONS[currentLang].subtitle;
        }

        const handleLangChange = (lang) => {
            if (currentLang === lang) return;
            currentLang = lang;
            localStorage.setItem(LANG_KEY, lang);
            
            updateButtonActiveState();
            
            if (subtitleText) {
                subtitleText.textContent = UI_TRANSLATIONS[currentLang].subtitle;
            }
            
            // Volver a renderizar todas las vistas
            renderStats();
            renderCategories();
            renderNewsFeed();
            renderMoodWidget(moodHistoryData);
        };

        if (btnEs) btnEs.addEventListener('click', () => handleLangChange('es'));
        if (btnEu) btnEu.addEventListener('click', () => handleLangChange('eu'));
        if (btnFr) btnFr.addEventListener('click', () => handleLangChange('fr'));
        if (btnEn) btnEn.addEventListener('click', () => handleLangChange('en'));
        if (btnPl) btnPl.addEventListener('click', () => handleLangChange('pl'));
    }

    // Inicializar idioma
    initLanguage();

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

    // Lista ampliada de stopwords en español (coherente con el backend)
    const SPANISH_STOPWORDS = new Set([
        'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
        'aquel', 'aquella', 'aquellos', 'aquellas', 'mi', 'mis', 'tu', 'tus', 'su', 'sus', 'nuestro', 'nuestra', 'nuestros', 'nuestras',
        'vuestro', 'vuestra', 'vuestros', 'vue-stras', 'yo', 'tú', 'él', 'ella', 'nosotros', 'nosotras', 'vosotros', 'vosotras', 'ellos', 'ellas',
        'me', 'te', 'se', 'nos', 'os', 'le', 'les', 'lo', 'la', 'los', 'las', 'mí', 'ti', 'sí', 'conmigo', 'contigo', 'consigo',
        'a', 'ante', 'bajo', 'cabe', 'con', 'contra', 'de', 'desde', 'durante', 'en', 'entre', 'hacia', 'hasta', 'mediante', 'para',
        'por', 'según', 'sin', 'so', 'sobre', 'tras', 'versus', 'vía', 'al', 'del',
        'y', 'e', 'ni', 'o', 'u', 'pero', 'mas', 'sino', 'aunque', 'porque', 'pues', 'como', 'siquiera',
        'ser', 'soy', 'eres', 'es', 'somos', 'sois', 'son', 'fui', 'fuiste', 'fue', 'fuimos', 'fuisteis', 'fueron',
        'era', 'eras', 'éramos', 'erais', 'eran', 'seré', 'serás', 'será', 'seremos', 'seréis', 'serán',
        'sea', 'seas', 'seamos', 'seáis', 'sean', 'sido', 'siendo',
        'estar', 'estoy', 'estás', 'está', 'estamos', 'estáis', 'están', 'estuve', 'estuviste', 'estuvo', 'estuvimos', 'estuvisteis', 'estuvieron',
        'estaba', 'estabas', 'estábamos', 'estabais', 'estaban', 'estaré', 'estarás', 'estará', 'estaremos', 'estaréis', 'estarán',
        'esté', 'estés', 'estemos', 'estéis', 'estén', 'estado', 'estando',
        'haber', 'he', 'has', 'ha', 'hemos', 'habéis', 'han', 'había', 'habías', 'habíamos', 'habíais', 'habían',
        'haya', 'hayas', 'hayamos', 'hayáis', 'hayan', 'hubo', 'hubieron', 'hubiera', 'hubieras', 'hubiéramos', 'hubierais', 'hubieran',
        'tener', 'tengo', 'tienes', 'tiene', 'tenemos', 'tenéis', 'tienen', 'tenía', 'tenías', 'teníamos', 'teníais', 'tenían',
        'tenga', 'tengas', 'tengamos', 'tengáis', 'tengan', 'tuvo', 'tuvieron', 'tuviera', 'tuvieras', 'tuviéramos', 'tuvierais', 'tuvieran',
        'hacer', 'hago', 'haces', 'hace', 'hacemos', 'hacéis', 'hacen', 'hacía', 'hacías', 'hacíamos', 'hacíais', 'hacían',
        'haga', 'hagas', 'hagamos', 'hagáis', 'hagan', 'hizo', 'hicieron', 'hiciera', 'hicieras', 'hiciéramos', 'hicierais', 'hicieran',
        'hecho', 'haciendo',
        'poder', 'puedo', 'puedes', 'puede', 'podemos', 'podéis', 'pueden', 'podía', 'podías', 'podíamos', 'podíais', 'podían',
        'pueda', 'puedas', 'puedamos', 'puedáis', 'puedan', 'pudo', 'pudieron', 'pudiera', 'pudieras', 'pudiéramos', 'pudierais', 'pudieran',
        'decir', 'digo', 'dices', 'dice', 'decimos', 'decís', 'dicen', 'dije', 'dijiste', 'dijo', 'dijimos', 'dijisteis', 'dijeron',
        'diga', 'digas', 'digamos', 'digáis', 'digan', 'dicho', 'diciendo',
        'ir', 'voy', 'vas', 'va', 'vamos', 'vais', 'van', 'iba', 'ibas', 'íbamos', 'ibais', 'iban',
        'vaya', 'vayas', 'vayamos', 'vayáis', 'vayan',
        'muy', 'más', 'menos', 'tan', 'tanto', 'así', 'cómo', 'cuándo', 'cuando', 'dónde', 'donde', 'quién', 'quien',
        'qué', 'que', 'ya', 'todavía', 'aún', 'ahora', 'después', 'antes', 'bien', 'mal', 'tal', 'tales',
        'mismo', 'misma', 'mismos', 'mismas', 'otro', 'otra', 'otros', 'otras', 'ambos', 'ambas', 'cada', 'alguno', 'alguna',
        'algunos', 'algunas', 'ninguno', 'ninguna', 'ningunos', 'ningunas', 'todo', 'toda', 'todos', 'todas', 'mucho', 'mucha',
        'muchos', 'muchas', 'poco', 'poca', 'pocos', 'pocas', 'varios', 'varias', 'solo', 'sólo',
        'correo', 'gasteiz', 'hoy', 'noticias', 'alava', 'vitoria', 'diario', 'araba', 'html', 'htm'
    ]);

    function cleanAccents(s) {
        if (!s) return "";
        return s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/ñ/g, "n").replace(/Ñ/g, "N");
    }

    const CLEANED_STOPWORDS = new Set(Array.from(SPANISH_STOPWORDS).map(w => cleanAccents(w.toLowerCase())));

    function tokenize(text) {
        if (!text) return new Set();
        const words = cleanAccents(text.toLowerCase())
            .replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?"'']/g, " ")
            .split(/\s+/);
        const tokens = new Set();
        for (const w of words) {
            if (w.length > 2 && !CLEANED_STOPWORDS.has(w)) {
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

    function extractKeyEntities(text) {
        if (!text) return new Set();
        const clean = text.replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?"'\n\r0-9]/g, ' ');
        const words = clean.split(/\s+/);
        const entities = new Set();
        for (const w of words) {
            if (w.length < 2) continue;
            const wNorm = cleanAccents(w.toLowerCase());
            if (CLEANED_STOPWORDS.has(wNorm)) continue;
            if (w[0] === w[0].toUpperCase() && w[0] !== w[0].toLowerCase()) {
                entities.add(wNorm);
            }
        }
        return entities;
    }

    function overlapScore(setA, setB) {
        if (setA.size === 0 || setB.size === 0) return 0;
        let shared = 0;
        for (const elem of setA) {
            if (setB.has(elem)) shared++;
        }
        const minSize = Math.min(setA.size, setB.size);
        return minSize > 0 ? shared / minSize : 0;
    }

    function selectPrimaryItem(componentItems) {
        let primaryItem = componentItems[0];
        if (componentItems.length > 1) {
            const sortedForPrimary = [...componentItems].sort((a, b) => {
                const getRank = (item) => {
                    const img = item.image || "";
                    const hasRealImg = img && !img.startsWith("data:image/") && !img.includes("resumen.png") && !img.includes("resumen_");
                    const src = item.source || "";
                    const isPref = src === "El Correo" || src === "Diario de Noticias";
                    const isGasteizHoy = src === "Gasteiz Hoy";
                    
                    if (isPref && hasRealImg) return 1;
                    if (isPref && !hasRealImg) return 2;
                    if (!isGasteizHoy && hasRealImg) return 3;
                    if (!isGasteizHoy && !hasRealImg) return 4;
                    if (isGasteizHoy && hasRealImg) return 5;
                    return 6;
                };
                return getRank(a) - getRank(b);
            });
            primaryItem = sortedForPrimary[0];
        }
        return primaryItem;
    }

    function groupNewsItems(items) {
        if (!items || items.length === 0) return [];
        
        const itemsWithGroup = [];
        const itemsWithoutGroup = [];
        const clusters = [];
        
        items.forEach(item => {
            if (item.is_summary) return; // Saltar resúmenes
            
            if (item.group_id) {
                itemsWithGroup.push(item);
            } else if (item.grouped_verified === true) {
                // Noticia verificada como individual por la IA (no debe agruparse)
                clusters.push({
                    id: item.id,
                    primary: item,
                    items: [item]
                });
            } else {
                // Noticia antigua/sin verificar -> fallback a Jaccard
                itemsWithoutGroup.push(item);
            }
        });
        
        // 1. Agrupar elementos que tienen group_id precalculado por la IA
        const groupMap = {};
        itemsWithGroup.forEach(item => {
            if (!groupMap[item.group_id]) {
                groupMap[item.group_id] = [];
            }
            groupMap[item.group_id].push(item);
        });
        
        for (const gId in groupMap) {
            const compItems = groupMap[gId];
            // Conservar el orden original del listado de noticias
            compItems.sort((x, y) => items.indexOf(x) - items.indexOf(y));
            const primaryItem = selectPrimaryItem(compItems);
            clusters.push({
                id: primaryItem.id,
                primary: primaryItem,
                items: compItems
            });
        }
        
        // 2. Agrupar el resto mediante el algoritmo de similitud Jaccard (fallback)
        if (itemsWithoutGroup.length > 0) {
            const jaccardClusters = groupNewsItemsJaccard(itemsWithoutGroup);
            clusters.push(...jaccardClusters);
        }
        
        return clusters;
    }

    function groupNewsItemsJaccard(items) {
        const tokenized = items.map(item => {
            const titleText = (item.title || "") + " " + (item.original_title || "");
            const bodyText = (item.body || "") + " " + (item.original_body || "");
            return {
                item: item,
                titleTokens: tokenize(titleText),
                bodyTokens: tokenize(bodyText),
                titleEntities: extractKeyEntities(titleText)
            };
        });
        
        const n = tokenized.length;
        
        // Construir lista de adyacencia
        const adj = Array.from({ length: n }, () => []);
        for (let i = 0; i < n; i++) {
            for (let j = i + 1; j < n; j++) {
                const titleSim = jaccardSimilarity(tokenized[i].titleTokens, tokenized[j].titleTokens);
                const bodySim = jaccardSimilarity(tokenized[i].bodyTokens, tokenized[j].bodyTokens);
                
                const entI = tokenized[i].titleEntities;
                const entJ = tokenized[j].titleEntities;
                let sharedEntities = 0;
                for (const e of entI) { if (entJ.has(e)) sharedEntities++; }
                
                let matched = false;
                
                // Regla 1: Similitud Jaccard de título directa (direct matching)
                if (titleSim >= 0.20) {
                    matched = true;
                }
                // Regla 2: Similitud Jaccard de body directa
                else if (bodySim >= 0.25) {
                    matched = true;
                }
                // Regla 3: Combinación de título + body
                else if (titleSim >= 0.05 && bodySim >= 0.11) {
                    matched = true;
                }
                // Regla 4: Entidades clave y overlap
                else if (sharedEntities >= 2 && bodySim >= 0.08) {
                    matched = true;
                }
                else if (entI.size > 0 && entJ.size > 0 && overlapScore(entI, entJ) >= 0.40 && bodySim >= 0.10) {
                    matched = true;
                }
                else {
                    // Regla semántica de agresiones (normalizada)
                    const bA = tokenized[i].bodyTokens;
                    const bB = tokenized[j].bodyTokens;
                    const shared = new Set([...bA].filter(x => bB.has(x)));
                    
                    const hasWeapon = ['blanca', 'cuchilladas', 'navaja', 'cuchillo', 'apunalan', 'acuchillado', 'apunalado'].some(w => shared.has(w));
                    const hasBack = shared.has('espalda');
                    const hasYoung = shared.has('joven');
                    
                    if (hasWeapon && hasBack && hasYoung) {
                        matched = true;
                    }
                }
                
                if (matched) {
                    adj[i].push(j);
                    adj[j].push(i);
                }
            }
        }
        
        const visited = new Set();
        const clusters = [];
        
        for (let i = 0; i < n; i++) {
            if (visited.has(i)) continue;
            
            const componentIndices = [];
            const queue = [i];
            visited.add(i);
            
            while (queue.length > 0) {
                const u = queue.shift();
                componentIndices.push(u);
                
                for (const v of adj[u]) {
                    if (!visited.has(v)) {
                        visited.add(v);
                        queue.push(v);
                    }
                }
            }
            
            componentIndices.sort((x, y) => x - y);
            const componentItems = componentIndices.map(idx => tokenized[idx].item);
            const primaryItem = selectPrimaryItem(componentItems);
            
            clusters.push({
                id: primaryItem.id,
                primary: primaryItem,
                items: componentItems
            });
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
        // Separate summary items - they always show
        const summaryItems = newsData.filter(item => item.is_summary);
        
        let regularItems;
        if (currentCategory) {
            const key = SECTION_MAP[currentCategory] || currentCategory.toLowerCase();
            regularItems = newsData.filter(item => !item.is_summary && item.source_section === key);
        } else {
            // Default: mostrar todo EXCEPTO artículos que pertenecen explícitamente a otra sección
            const sectionKeys = Object.values(SECTION_MAP);
            regularItems = newsData.filter(item => !item.is_summary && !sectionKeys.includes(item.source_section));
        }
        
        return { summaryItems, regularItems };
    }

    function renderSummaryCard(item) {
        if (!item) return '';
        
        return `
            <div class="card card-summary glass" data-id="${item.id}" data-is-summary="true">
                <div class="card-img-wrap">
                    <img src="data/resumen_${currentLang}.png" alt="${UI_TRANSLATIONS[currentLang].summaryTitle}" class="card-img" loading="lazy">
                    <div class="img-overlay"></div>
                </div>
                <div class="card-content">
                    <div class="card-date">${formatDate(item.date)}</div>
                    <h2 class="card-title card-summary-title">${UI_TRANSLATIONS[currentLang].summaryTitle}</h2>
                    <p class="card-summary-preview">${UI_TRANSLATIONS[currentLang].summaryPreview}</p>
                    <div class="card-footer">
                        <span class="read-more">${UI_TRANSLATIONS[currentLang].readSummary}</span>
                        <div class="line"></div>
                    </div>
                </div>
            </div>
        `;
    }

    function renderNewsFeed() {
        if (!newsData || newsData.length === 0) {
            newsGrid.innerHTML = `<p style="color:var(--text-muted); font-weight:300;">${UI_TRANSLATIONS[currentLang].noNews}</p>`;
            return;
        }

        const readIds = JSON.parse(localStorage.getItem(READ_ARTICLES_KEY) || '[]');
        const { summaryItems, regularItems } = getSectionData();
        
        // Find the summary item (should be the first one if it exists)
        const summaryItem = summaryItems.length > 0 ? summaryItems[0] : null;
        
        let clusters = groupNewsItems(regularItems);

        if (currentFilter) {
            if (currentFilter === 'leidas') {
                clusters = clusters.filter(cluster => cluster.items.every(item => readIds.includes(item.id)));
            } else {
                clusters = clusters.filter(cluster => cluster.primary.sentiment_label === currentFilter);
            }
        }
        // Sort clusters: unread first, then by the most recent date in the cluster
        clusters.sort((a, b) => {
            const aRead = a.items.every(it => readIds.includes(it.id));
            const bRead = b.items.every(it => readIds.includes(it.id));

            if (aRead && !bRead) return 1;
            if (!aRead && bRead) return -1;

            const aMaxDate = Math.max(...a.items.map(it => new Date(it.date).getTime()));
            const bMaxDate = Math.max(...b.items.map(it => new Date(it.date).getTime()));
            return bMaxDate - aMaxDate;
        });

        if (clusters.length === 0 && !summaryItem) {
            let noNewsText = UI_TRANSLATIONS[currentLang].noNewsFilter;
            if (currentFilter === 'leidas') noNewsText = UI_TRANSLATIONS[currentLang].noNewsRead;
            newsGrid.innerHTML = `<p style="color:var(--text-muted); font-weight:300; padding: 2rem;">${noNewsText}</p>`;
            return;
        }

        // Build HTML: summary card first (if it exists and no category filter active), then regular cards
        let html = '';
        
        // Only show summary when no category filter is active (show it on the "All" view)
        if (summaryItem && !currentCategory) {
            html += renderSummaryCard(summaryItem);
        }
        
        html += clusters.map((cluster, index) => {
            const item = cluster.primary;
            const isRead = cluster.items.every(it => readIds.includes(it.id));
            const sentimentClass = item.sentiment_label || 'neutral';
            const isMultiSource = cluster.items.length > 1;

            // Obtener título traducido si está disponible
            let titleDisplay = item.title;
            if (currentLang === 'eu' && item.title_eu) {
                titleDisplay = item.title_eu;
            } else if (currentLang === 'pl' && item.title_pl) {
                titleDisplay = item.title_pl;
            } else if (currentLang === 'fr' && item.title_fr) {
                titleDisplay = item.title_fr;
            } else if (currentLang === 'en' && item.title_en) {
                titleDisplay = item.title_en;
            }
            
            const readTag = UI_TRANSLATIONS[currentLang].sentimentTag || 'Leído';
            const sourcesText = UI_TRANSLATIONS[currentLang].sourcesCount || 'Fuentes';
            
            const readMoreTexts = {
                es: "Ver narrativa",
                eu: "Istorioa ikusi",
                pl: "Zobacz historię",
                fr: "Voir l'histoire",
                en: "See story"
            };
            const readMoreText = readMoreTexts[currentLang] || readMoreTexts.es;

            return `
                <div class="card glass ${isRead ? 'card-read' : ''} ${isMultiSource ? 'card-multi-source' : ''}" 
                     data-cluster-index="${index}" 
                     ${isMultiSource ? '' : `data-source="${item.source}"`} 
                     data-id="${item.id}">
                     <div class="card-img-wrap">
                         <img src="${item.image || ''}" alt="${titleDisplay}" class="card-img" loading="lazy" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9IiMxZTI5M2IiLz48L3N2Zz4='">
                         <div class="img-overlay"></div>
                         <div class="card-top-badges">
                             <div class="card-source-badge">
                                 <div class="sentiment-dot dot-${sentimentClass}" title="Sentimiento: ${sentimentClass}"></div>
                             </div>
                             ${isMultiSource ? `<div class="badge-multi-source">${cluster.items.length} ${sourcesText}</div>` : ''}
                             ${item.category && item.category !== 'Otros' ? `<div class="badge-category cat-${item.category.toLowerCase().replace('í', 'i')}">${UI_TRANSLATIONS[currentLang]['cat' + item.category.replace('í', 'i')] || item.category}</div>` : ''}
                         </div>
                     </div>
                     <div class="card-content">
                         <div class="card-date">${formatDate(item.date)} ${isRead ? `<span class="read-tag">• ${readTag}</span>` : ''}</div>
                         <h2 class="card-title">${titleDisplay}</h2>
                         <div class="card-footer">
                             <span class="read-more">${readMoreText}</span>
                             <div class="line"></div>
                         </div>
                     </div>
                </div>
            `;
        }).join('');

        newsGrid.innerHTML = html;

        document.querySelectorAll('.card').forEach(card => {
            card.addEventListener('click', (e) => {
                lastScrollPos = window.scrollY;
                const isSummary = card.getAttribute('data-is-summary') === 'true';
                if (isSummary) {
                    showDetail(card.getAttribute('data-id'));
                    return;
                }
                const clusterIdx = card.getAttribute('data-cluster-index');
                const cluster = clusters[clusterIdx];
                if (cluster && cluster.items.length > 1) {
                    openSourcesModal(cluster);
                } else if (cluster) {
                    showDetail(cluster.primary.id);
                }
            });
        });
    }

    function renderStats() {
        // Contar solo la sección activa
        const { regularItems } = getSectionData();
        const clusters = groupNewsItems(regularItems);
        
        const counts = { 'positiva': 0, 'neutral': 0, 'negativa': 0 };
        const readIds = JSON.parse(localStorage.getItem(READ_ARTICLES_KEY) || '[]');
        let readCount = 0;

        clusters.forEach(cluster => {
            const label = cluster.primary.sentiment_label || 'neutral';
            if (counts.hasOwnProperty(label)) counts[label]++;
            
            const isRead = cluster.items.every(item => readIds.includes(item.id));
            if (isRead) readCount++;
        });

        statsContainer.innerHTML = `
            <div class="stat-item ${currentFilter === 'positiva' ? 'stat-active' : ''}" data-filter="positiva">
                <div class="stat-label">${UI_TRANSLATIONS[currentLang].sentimentPos}</div>
                <div class="stat-value text-emerald">
                    ${counts.positiva}
                    ${currentFilter === 'positiva' ? '<div class="filter-dot"></div>' : ''}
                </div>
            </div>
            <div class="stat-item ${currentFilter === 'neutral' ? 'stat-active' : ''}" data-filter="neutral">
                <div class="stat-label">${UI_TRANSLATIONS[currentLang].sentimentNeu}</div>
                <div class="stat-value">
                    ${counts.neutral}
                    ${currentFilter === 'neutral' ? '<div class="filter-dot"></div>' : ''}
                </div>
            </div>
            <div class="stat-item ${currentFilter === 'negativa' ? 'stat-active' : ''}" data-filter="negativa">
                <div class="stat-label">${UI_TRANSLATIONS[currentLang].sentimentNeg}</div>
                <div class="stat-value text-rose">
                    ${counts.negativa}
                    ${currentFilter === 'negativa' ? '<div class="filter-dot"></div>' : ''}
                </div>
            </div>
            <div class="stat-item ${currentFilter === 'leidas' ? 'stat-active' : ''}" data-filter="leidas">
                <div class="stat-label">${UI_TRANSLATIONS[currentLang].sentimentRead}</div>
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
            { label: 'Economía', key: 'economia', translationKey: 'catEconomia' },
            { label: 'Sociedad',  key: 'sociedad', translationKey: 'catSociedad' },
            { label: 'Deportes', key: 'deportes', translationKey: 'catDeportes' },
            { label: 'Cultura',  key: 'cultura', translationKey: 'catCultura' }
        ];

        const availableSections = new Set(newsData.map(item => item.source_section).filter(Boolean));

        categoriesContainer.innerHTML = allCategories.map(cat => {
            const hasData = availableSections.has(cat.key);
            const labelDisplay = UI_TRANSLATIONS[currentLang][cat.translationKey] || cat.label;
            const tooltipText = !hasData 
                ? (currentLang === 'eu' ? 'Ez dago albisterik gaur atal honetan' : 'Sin noticias hoy en esta sección') 
                : labelDisplay;
            return `
            <div class="category-btn ${currentCategory === cat.label ? 'active' : ''} ${!hasData ? 'cat-empty' : ''}" 
                 data-category="${cat.label}" title="${tooltipText}">
                ${labelDisplay}
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
                renderMoodWidget(moodHistoryData);
            });
        });
    }

    const sourcesModal = document.getElementById('sources-modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');

    function openSourcesModal(cluster) {
        const sourcesList = document.getElementById('modal-sources-list');
        const modalTitle = document.querySelector('.modal-title');
        const modalSubtitle = document.querySelector('.modal-subtitle');
        
        if (modalTitle) modalTitle.textContent = UI_TRANSLATIONS[currentLang].sourcesModalTitle;
        if (modalSubtitle) modalSubtitle.textContent = UI_TRANSLATIONS[currentLang].sourcesModalSubtitle;

        sourcesList.innerHTML = cluster.items.map(item => {
            const sentimentClass = item.sentiment_label || 'neutral';
            let optTitle = item.title;
            if (currentLang === 'eu' && item.title_eu) {
                optTitle = item.title_eu;
            } else if (currentLang === 'pl' && item.title_pl) {
                optTitle = item.title_pl;
            } else if (currentLang === 'fr' && item.title_fr) {
                optTitle = item.title_fr;
            } else if (currentLang === 'en' && item.title_en) {
                optTitle = item.title_en;
            }
            return `
                <button class="source-option-btn" data-id="${item.id}" data-source="${item.source}">
                    <div>
                        <div class="source-option-name">
                            <div class="sentiment-dot dot-${sentimentClass}"></div>
                        </div>
                        <div class="source-option-title">${optTitle}</div>
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

        // Sincronizar el texto del botón volver
        const backBtnText = document.getElementById('back-btn-text');
        if (backBtnText) {
            backBtnText.textContent = UI_TRANSLATIONS[currentLang].backPortal;
        }

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
                    <span class="selector-label">${UI_TRANSLATIONS[currentLang].compareSources}</span>
                    <div class="selector-pills">
                        ${cluster.items.map(it => `
                            <button class="source-pill ${it.id === id ? 'active' : ''}" data-id="${it.id}" data-source="${it.source}"></button>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        const sentimentColorClass = item.sentiment_label === 'positiva' ? 'text-emerald' : (item.sentiment_label === 'negativa' ? 'text-rose' : 'text-muted');
        
        let detailTitle = item.title;
        if (currentLang === 'eu' && item.title_eu) {
            detailTitle = item.title_eu;
        } else if (currentLang === 'pl' && item.title_pl) {
            detailTitle = item.title_pl;
        } else if (currentLang === 'fr' && item.title_fr) {
            detailTitle = item.title_fr;
        } else if (currentLang === 'en' && item.title_en) {
            detailTitle = item.title_en;
        }
        
        let bodyContent = item.body || '';
        if (currentLang === 'eu' && item.body_eu) {
            bodyContent = item.body_eu;
        } else if (currentLang === 'pl' && item.body_pl) {
            bodyContent = item.body_pl;
        } else if (currentLang === 'fr' && item.body_fr) {
            bodyContent = item.body_fr;
        } else if (currentLang === 'en' && item.body_en) {
            bodyContent = item.body_en;
        }
        
        let bodyHtml = '';

        if (item.is_summary) {
            const introTexts = {
                es: 'Aquí tienes las noticias del día resumidas para gente con poco tiempo disponible, siempre actualizadas y disponibles para ti.',
                eu: 'Hemen dituzu eguneko albisteak denbora gutxi dutenentzako laburtuta, beti eguneratuta eta zuretzat eskuragarri.',
                pl: 'Oto dzisiejsze wiadomości podsumowane dla osób z ograniczonym czasem, zawsze aktualne i dostępne dla Ciebie.',
                fr: 'Voici le résumé de l\'actualité du jour pour les personnes pressées, toujours à jour et disponible pour vous.',
                en: 'Here is the summary of the day\'s news for people with limited time, always updated and available for you.'
            };
            const introText = introTexts[currentLang] || introTexts.es;
            const intro = `<p class="paragraph" style="font-weight: 400; font-size: 1.4rem; color: var(--indigo-500);">${introText}</p>`;
            const rawBody = bodyContent.trim();
            
            const fallbackTexts = {
                es: 'El contenido completo no está disponible.',
                eu: 'Eduki osoa ez dago eskuragarri.',
                pl: 'Pełna treść jest niedostępna.',
                fr: 'Le contenu complet n\'est pas disponible.',
                en: 'Full content is not available.'
            };
            const fallbackText = fallbackTexts[currentLang] || fallbackTexts.es;
            
            // For virtual summaries (generated in frontend), preserve bullet structure by splitting on newlines
            if (item.id && item.id.startsWith('resumen_virtual_')) {
                const lines = rawBody.split('\n').filter(s => s.trim().length > 0);
                const summaryHtml = lines.map(s => `<p class="paragraph">${s.trim()}</p>`).join('');
                bodyHtml = intro + summaryHtml;
            } else {
                // For AI-generated summaries: split on '. ' to show each sentence as a paragraph
                const parts = rawBody.split('. ');
                const sentences = parts
                    .map((s, i) => i < parts.length - 1 ? s.trim() + '.' : s.trim())
                    .filter(s => s.length > 1);
                const summaryHtml = sentences.length > 0
                    ? sentences.map(s => `<p class="paragraph">${s}</p>`).join('')
                    : `<p class="paragraph" style="color:var(--text-muted); font-style:italic;">${fallbackText}</p>`;
                bodyHtml = intro + summaryHtml;
            }
        } else {
            const paragraphs = bodyContent.split('\n').filter(p => p.trim() !== '');
            const fallbackTexts = {
                es: 'El contenido completo no está disponible.',
                eu: 'Eduki osoa ez dago eskuragarri.',
                pl: 'Pełna treść jest niedostępna.',
                fr: 'Le contenu complet n\'est pas disponible.',
                en: 'Full content is not available.'
            };
            const fallbackText = fallbackTexts[currentLang] || fallbackTexts.es;
            bodyHtml = paragraphs.length > 0 
                ? paragraphs.map(p => `<p class="paragraph">${p}</p>`).join('')
                : `<p class="paragraph" style="color:var(--text-muted); font-style:italic;">${fallbackText}</p>`;
        }

        // For summary items, use the localized resumen image
        const heroImage = item.is_summary ? `data/resumen_${currentLang}.png` : (item.image || '');
        
        // Render Detail
        articleContent.innerHTML = `
            <div class="hero-wrap">
                <img src="${heroImage}" alt="${detailTitle}" class="hero-img" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9IiMxZTI5M2IiLz48L3N2Zz4='">
                <div class="hero-overlay"></div>
                <div class="hero-content">
                    <div class="hero-badges">
                        <span class="badge-sentiment ${sentimentColorClass}"># ${UI_TRANSLATIONS[currentLang][item.sentiment_label] || item.sentiment_label}</span>
                        ${item.category ? `<span class="badge-source">${UI_TRANSLATIONS[currentLang]['cat' + item.category.replace('í', 'i')] || item.category}</span>` : ''}
                    </div>
                    <h1 class="hero-title">${detailTitle}</h1>
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
                    <div class="footer-note">${UI_TRANSLATIONS[currentLang].verifiedAI}</div>
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
    
    function renderMoodWidget(historyArg) {
        const widget = document.getElementById('mood-widget-container');
        if (!widget) return;

        const sectionKey = currentCategory ? (SECTION_MAP[currentCategory] || currentCategory.toLowerCase()) : 'alava';
        
        let sectionHistory = [];
        if (historyArg && !Array.isArray(historyArg)) {
            sectionHistory = historyArg[sectionKey] || [];
        } else if (moodHistoryData && !Array.isArray(moodHistoryData)) {
            sectionHistory = moodHistoryData[sectionKey] || [];
        } else if (Array.isArray(historyArg)) {
            sectionHistory = historyArg;
        } else if (Array.isArray(moodHistoryData)) {
            sectionHistory = moodHistoryData;
        }

        if (sectionHistory.length === 0) {
            widget.style.display = 'none';
            return;
        }

        widget.style.display = 'block';

        const todayMood = sectionHistory[sectionHistory.length - 1];
        const score = todayMood.score;

        const moodTitleEl = document.getElementById('mood-title');
        const moodTextEl = document.getElementById('mood-text');
        const moodMarkerEl = document.getElementById('mood-marker');

        // Nombres de sección dinámicos y genitivos para Euskera
        const basqueSectionNames = {
            'economia': 'Ekonomia',
            'sociedad': 'Gizartea',
            'deportes': 'Kirolak',
            'cultura': 'Kultura',
            'alava': 'Gasteiz'
        };
        const basqueGenitives = {
            'economia': 'Ekonomiako',
            'sociedad': 'Gizarteko',
            'deportes': 'Kiroletako',
            'cultura': 'Kulturako',
            'alava': 'Gasteizko'
        };
        const spanishSectionNames = {
            'economia': 'Economía',
            'sociedad': 'Sociedad',
            'deportes': 'Deportes',
            'cultura': 'Cultura',
            'alava': 'Vitoria-Gasteiz'
        };
        const polishSectionNames = {
            'economia': 'Ekonomia',
            'sociedad': 'Społeczeństwo',
            'deportes': 'Sport',
            'cultura': 'Kultura',
            'alava': 'Vitoria-Gasteiz'
        };
        const frenchSectionNames = {
            'economia': 'Économie',
            'sociedad': 'Société',
            'deportes': 'Sports',
            'cultura': 'Culture',
            'alava': 'Vitoria-Gasteiz'
        };
        const englishSectionNames = {
            'economia': 'Economy',
            'sociedad': 'Society',
            'deportes': 'Sports',
            'cultura': 'Culture',
            'alava': 'Vitoria-Gasteiz'
        };

        const sectionName = currentCategory || 'Vitoria-Gasteiz';

        if (moodTitleEl) {
            if (currentLang === 'eu') {
                const genitive = basqueGenitives[sectionKey] || (sectionName + 'ko');
                moodTitleEl.textContent = `Gaurko ${genitive} "Mood"-a`;
            } else if (currentLang === 'pl') {
                const polName = polishSectionNames[sectionKey] || sectionName;
                moodTitleEl.textContent = `Nastrój w: ${polName}`;
            } else if (currentLang === 'fr') {
                const frName = frenchSectionNames[sectionKey] || sectionName;
                moodTitleEl.textContent = `L'humeur de ${frName} aujourd'hui est`;
            } else if (currentLang === 'en') {
                const enName = englishSectionNames[sectionKey] || sectionName;
                moodTitleEl.textContent = `The "Mood" of ${enName} today is`;
            } else {
                const espName = spanishSectionNames[sectionKey] || sectionName;
                moodTitleEl.textContent = `El "Mood" de ${espName} hoy es`;
            }
        }

        const currentLangName = {
            es: spanishSectionNames[sectionKey] || sectionName,
            eu: basqueSectionNames[sectionKey] || sectionName,
            pl: polishSectionNames[sectionKey] || sectionName,
            fr: frenchSectionNames[sectionKey] || sectionName,
            en: englishSectionNames[sectionKey] || sectionName
        }[currentLang];

        const moodTexts = {
            es: {
                neutral: `${currentLangName} está neutral`,
                excellent: `${currentLangName} está de excelente humor`,
                good: `${currentLangName} tiene un buen día`,
                difficult: `${currentLangName} tiene un día difícil`,
                sad: `${currentLangName} está algo decaído`
            },
            eu: {
                neutral: `${currentLangName} neutral dago`,
                excellent: `${currentLangName} umore bikainean dago`,
                good: `${currentLangName}ek egun ona du`,
                difficult: `${currentLangName}ek egun zaila du`,
                sad: `${currentLangName} apur bat goibel dago`
            },
            pl: {
                neutral: `${currentLangName} jest neutralny`,
                excellent: `${currentLangName} ma doskonały nastrój`,
                good: `${currentLangName} ma dobry dzień`,
                difficult: `${currentLangName} ma trudny dzień`,
                sad: `${currentLangName} jest nieco przygnębiony`
            },
            fr: {
                neutral: `${currentLangName} est neutre`,
                excellent: `${currentLangName} est d'excellente humeur`,
                good: `${currentLangName} passe une bonne journée`,
                difficult: `${currentLangName} passe une journée difficile`,
                sad: `${currentLangName} est un peu morose`
            },
            en: {
                neutral: `${currentLangName} is neutral`,
                excellent: `${currentLangName} is in an excellent mood`,
                good: `${currentLangName} has a good day`,
                difficult: `${currentLangName} has a difficult day`,
                sad: `${currentLangName} is a bit down`
            }
        };

        const currentMoodTexts = moodTexts[currentLang] || moodTexts.es;

        let emoji = '😐';
        let text = currentMoodTexts.neutral;

        if (score > 0.3) {
            emoji = '😄';
            text = currentMoodTexts.excellent;
        } else if (score > 0.05) {
            emoji = '🙂';
            text = currentMoodTexts.good;
        } else if (score < -0.3) {
            emoji = '😞';
            text = currentMoodTexts.difficult;
        } else if (score < -0.05) {
            emoji = '😕';
            text = currentMoodTexts.sad;
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
        const lastDays = sectionHistory.slice(-daysToShow);

        chartEl.innerHTML = lastDays.map(day => {
            const dayScore = day.score;
            let barColor = 'var(--text-muted)';
            if (dayScore > 0.05) barColor = 'var(--emerald-400)';
            if (dayScore < -0.05) barColor = 'var(--rose-400)';

            const absScore = Math.abs(dayScore);
            const heightPct = Math.max(10, absScore * 100);

            const date = new Date(day.date);
            const localeStr = currentLang === 'eu' ? 'eu-ES' : (currentLang === 'pl' ? 'pl-PL' : 'es-ES');
            const dStr = date.toLocaleDateString(localeStr, { day: 'numeric', month: 'short' }).replace('.', '');

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

    function createVirtualSummary() {
        // Find news items from Alava/Deportes that would be summarizable
        const avalaOrDeportes = newsData.filter(item => {
            const section = (item.category || item.source_section || '').toLowerCase();
            return section.includes('álava') || section.includes('alava') || section.includes('deporte');
        }).slice(0, 10); // Take top 10
        
        if (avalaOrDeportes.length < 2) return null;
        
        const bodyText = avalaOrDeportes.map((item) => {
            const preview = (item.body || '').substring(0, 300).replace(/\n/g, ' ').trim();
            return `- ${item.title}. ${preview.substring(0, preview.lastIndexOf('.') + 1) || preview + '.'}`;
        }).join('\n\n');
        
        return {
            id: 'resumen_virtual_' + new Date().toISOString().split('T')[0],
            title: 'Resumen de noticias del día',
            body: 'Hoy en Vitoria-Gasteiz y Álava los temas más destacados son:\n\n' + bodyText + '\n\nEste resumen se genera automáticamente desde la web y mostrará el contenido completo del resumen con IA cuando esté disponible desde el servidor.',
            url: '',
            source: 'Gasteiz Live',
            date: new Date().toISOString(),
            sentiment: 0.2,
            image: '',
            source_section: 'resumen',
            category: 'Resumen del Día',
            is_summary: true,
            rewritten: false,
            sentiment_label: 'neutral'
        };
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
            
            // If no AI summary item exists, create a virtual one from the latest Alava/Deportes news
            const hasAISummary = newsData.some(item => item.is_summary);
            if (!hasAISummary) {
                const virtualSummary = createVirtualSummary();
                if (virtualSummary) {
                    newsData.unshift(virtualSummary);
                    console.log('Virtual summary card created (no AI summary available)');
                }
            }
            
            sortNewsByReadState();
            renderStats();
            renderCategories();
            renderNewsFeed();
            renderMoodWidget(moodHistoryData);
            updatePodcastPlayer();
        } catch (error) {
            console.error("Error loading data:", error);
            const grid = document.getElementById('news-grid');
            if (grid) {
                grid.innerHTML = `
                    <div style="color:var(--text-muted); padding: 2rem; font-family: monospace; text-align: left; background: #fee2e2; border-radius: 8px; border: 1px solid #fca5a5; margin: 2rem;">
                        <h3 style="color:#b91c1c; margin-top: 0;">Error cargando datos</h3>
                        <p style="font-weight: bold; color: #7f1d1d;">${error.message}</p>
                        <pre style="white-space: pre-wrap; font-size: 0.85rem; color: #991b1b; background: #fef2f2; padding: 10px; border-radius: 4px; border: 1px solid #fecaca; margin-bottom: 0; overflow-x: auto;">${error.stack}</pre>
                    </div>
                `;
            } else {
                alert("Error cargando datos:\n" + error.message + "\n" + error.stack);
            }
        }
    }

    try {
        fetchData();
    } catch (globalError) {
        console.error("Global init error:", globalError);
        alert("Global init error:\n" + globalError.message + "\n" + globalError.stack);
    }
});

// Global function so onclick in HTML can reach it
