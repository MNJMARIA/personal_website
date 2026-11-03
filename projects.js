// ==========================================
// ПРОЄКТИ: картки й окремі сторінки генеруються з projects.json
// (джерело: ручні проєкти + репозиторії GitHub, див. scripts/build_site.py)
// ==========================================
(() => {
    const DATA_URL = 'projects.json';                    // генерується під час деплою
    const FALLBACK_URL = 'data/projects.manual.json';    // для локальної розробки (Live Server)

    const T = {
        about:    { ua: 'Про проєкт', en: 'About the Project' },
        features: { ua: 'Основні можливості', en: 'Key Features' },
        stack:    { ua: 'Стек технологій', en: 'Tech Stack' },
        gallery:  { ua: 'Галерея', en: 'Gallery' },
        open:     { ua: 'Відкрити кейс проєкту →', en: 'Open project case →' },
        empty:    { ua: 'Проєкти скоро з’являться.', en: 'Projects are coming soon.' },
        failed:   { ua: 'Не вдалося завантажити проєкти.', en: 'Could not load projects.' },
        created:  { ua: 'Створено', en: 'Created' },
        updated:  { ua: 'Оновлено', en: 'Updated' },
    };

    // ---------- допоміжні ----------
    const make = (tag, className, text) => {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text != null) node.textContent = text;
        return node;
    };

    // Двомовний текст: зберігаємо в data-ua / data-en, перемикач мови (script.js) підставляє потрібний.
    const bi = (node, value) => {
        const v = typeof value === 'string' ? { ua: value, en: value } : (value || {});
        const ua = v.ua || v.en || '';
        const en = v.en || v.ua || '';
        node.dataset.ua = ua;
        node.dataset.en = en;
        node.textContent = ua;
        return node;
    };

    // Дозволяємо лише http(s) та відносні шляхи
    const safeUrl = (u) => {
        if (!u || typeof u !== 'string') return '';
        if (/^[a-z][a-z0-9+.-]*:/i.test(u)) return /^https?:/i.test(u) ? u : '';
        return u;
    };

    const setBg = (node, url, gradient) => {
        const clean = safeUrl(url);
        const img = clean ? `url("${clean.replace(/ /g, '%20').replace(/"/g, '%22')}")` : '';
        node.style.backgroundImage = [gradient, img].filter(Boolean).join(', ');
    };

    const pageId = (p) => 'project-' + String(p.id).toLowerCase().replace(/[^a-z0-9_-]+/g, '-');

    const sortKey = (p) => {
        const v = p.updated || p.created || '';
        return v.length === 4 ? v + '-01-01' : v;
    };

    const formatDate = (value, lang) => {
        if (!value) return '';
        if (/^\d{4}$/.test(value)) return value;
        const d = new Date(value);
        if (isNaN(d)) return '';
        return d.toLocaleDateString(lang === 'ua' ? 'uk-UA' : 'en-GB', { month: 'long', year: 'numeric' })
            .replace(/\s*р\.$/, '');
    };

    const datesLine = (p) => {
        const out = {};
        ['ua', 'en'].forEach((lang) => {
            const parts = [];
            const created = formatDate(p.created, lang);
            const updated = formatDate(p.updated, lang);
            if (created) parts.push(`${T.created[lang]}: ${created}`);
            if (updated && updated !== created) parts.push(`${T.updated[lang]}: ${updated}`);
            out[lang] = parts.join(' · ');
        });
        return out;
    };

    const shorten = (text, limit) => {
        text = (text || '').replace(/\s+/g, ' ').trim();
        if (text.length <= limit) return text;
        const cut = text.slice(0, limit);
        const space = cut.lastIndexOf(' ');
        return cut.slice(0, space > 0 ? space : limit).replace(/[ ,;:.-]+$/, '') + '…';
    };

    const summaryOf = (p) => {
        if (p.summary && (p.summary.ua || p.summary.en)) return p.summary;
        const d = p.description || {};
        return { ua: shorten(d.ua, 170), en: shorten(d.en || d.ua, 170) };
    };

    // ---------- картка ----------
    const buildCard = (p) => {
        const card = make('div', 'project-card');
        card.dataset.project = pageId(p);
        card.tabIndex = 0;
        card.setAttribute('role', 'button');

        const image = make('div', 'project-card-image');
        setBg(image, p.cover, 'linear-gradient(rgba(0,0,0,0.2), #050506)');

        const info = make('div', 'project-card-info');
        info.appendChild(make('span', 'project-tag', p.tagline || (p.tags || []).slice(0, 3).join(' / ')));
        info.appendChild(bi(make('h3'), p.title));

        const summary = summaryOf(p);
        if (summary.ua || summary.en) info.appendChild(bi(make('p', 'project-card-summary'), summary));

        const dates = datesLine(p);
        if (dates.ua) info.appendChild(bi(make('p', 'project-dates'), dates));

        info.appendChild(bi(make('p', 'project-card-cta'), T.open));
        card.append(image, info);

        const open = () => openProjectPage(card.dataset.project);
        card.addEventListener('click', open);
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); }
        });
        return card;
    };

    // ---------- сторінка проєкту ----------
    const buildPage = (p) => {
        const page = make('div', 'project-page-view');
        page.id = pageId(p);

        // hero
        const hero = make('section', 'proj-hero');
        setBg(hero, p.cover, 'linear-gradient(to bottom, rgba(5, 5, 6, 0.4), var(--bg-pure-black))');
        const heroBox = make('div', 'proj-hero-container');
        const dates = datesLine(p);
        const metaUa = [p.kind, dates.ua].filter(Boolean).join(' // ');
        const metaEn = [p.kind, dates.en].filter(Boolean).join(' // ');
        if (metaUa) heroBox.appendChild(bi(make('span', 'proj-meta-tag'), { ua: metaUa, en: metaEn }));
        heroBox.appendChild(bi(make('h1', 'proj-hero-title'), p.title));
        hero.appendChild(heroBox);
        page.appendChild(hero);

        // опис + технології
        const details = make('section', 'proj-details-section');
        const container = make('div', 'proj-container');
        const layout = make('div', 'proj-info-layout');

        const main = make('div', 'proj-main-desc');
        main.appendChild(bi(make('h2'), T.about));
        const desc = p.description || summaryOf(p);
        const uaParas = String(desc.ua || '').split(/\n\s*\n/).filter(Boolean);
        const enParas = String(desc.en || desc.ua || '').split(/\n\s*\n/).filter(Boolean);
        for (let i = 0; i < Math.max(uaParas.length, 1); i++) {
            main.appendChild(bi(make('p'), { ua: uaParas[i] || '', en: enParas[i] || uaParas[i] || '' }));
        }
        const feats = p.features;
        if (feats && feats.ua && feats.ua.length) {
            main.appendChild(bi(make('h2'), T.features));
            const list = make('ul', 'project-feature-list');
            feats.ua.forEach((text, i) => list.appendChild(bi(make('li'), { ua: text, en: (feats.en || [])[i] || text })));
            main.appendChild(list);
        }

        const side = make('div', 'proj-sidebar-tags');
        side.appendChild(bi(make('h3'), T.stack));
        const labels = make('div', 'overlay-tech-labels');
        (p.tags || []).forEach((t) => labels.appendChild(make('span', null, t)));
        side.appendChild(labels);
        (p.links || []).forEach((l) => {
            const url = safeUrl(l.url);
            if (!url) return;
            const a = make('a', 'proj-git-btn link-primary', `${l.label || 'Link'} ↗`);
            a.href = url;
            a.target = '_blank';
            a.rel = 'noopener noreferrer';
            side.appendChild(a);
        });

        layout.append(main, side);
        container.appendChild(layout);
        details.appendChild(container);
        page.appendChild(details);

        // галерея
        const gallery = (p.gallery || []).filter((g) => safeUrl(g));
        if (gallery.length) {
            const section = make('section', 'proj-gallery-section');
            const box = make('div', 'proj-container');
            box.appendChild(bi(make('h2', 'section-subheading'), p.gallery_title || T.gallery));
            const carousel = make('div', 'carousel-container');
            const prev = make('button', 'carousel-nav prev-btn', '←');
            const next = make('button', 'carousel-nav next-btn', '→');
            prev.setAttribute('aria-label', 'Previous');
            next.setAttribute('aria-label', 'Next');
            const track = make('div', 'carousel-track');
            gallery.forEach((src) => {
                const slide = make('div', 'carousel-slide');
                setBg(slide, src);
                track.appendChild(slide);
            });
            carousel.append(prev, track, next);
            box.appendChild(carousel);
            section.appendChild(box);
            page.appendChild(section);
        }

        const footer = make('footer', 'proj-inner-footer');
        footer.appendChild(make('p', null, '© 2026 MARIIA STEPANOVA'));
        page.appendChild(footer);
        return page;
    };

    // ---------- завантаження й рендер ----------
    const load = async () => {
        for (const url of [DATA_URL, FALLBACK_URL]) {
            try {
                const res = await fetch(url, { cache: 'no-cache' });
                if (!res.ok) continue;
                const data = await res.json();
                const list = Array.isArray(data) ? data : data.projects;
                if (Array.isArray(list)) {
                    return Array.isArray(data)
                        ? list.filter((p) => p.visible !== false).sort((a, b) => sortKey(b).localeCompare(sortKey(a)))
                        : list;
                }
            } catch (e) { /* пробуємо наступне джерело */ }
        }
        return null;
    };

    const render = (projects) => {
        const grid = document.getElementById('projects-grid');
        const pages = document.getElementById('project-pages');
        if (!grid || !pages) return;
        grid.textContent = '';
        pages.textContent = '';

        if (!projects || !projects.length) {
            grid.appendChild(bi(make('p', 'projects-status'), projects ? T.empty : T.failed));
        } else {
            projects.forEach((p) => {
                grid.appendChild(buildCard(p));
                const page = buildPage(p);
                pages.appendChild(page);
                page.querySelectorAll('.carousel-container').forEach((c) => window.setupCarousel && window.setupCarousel(c));
            });
        }

        if (window.applyLanguage) window.applyLanguage();

        // якщо сторінку оновили всередині кейсу (#view-project-...)
        if (location.hash.startsWith('#view-')) openProjectPage(location.hash.slice(6));
        document.dispatchEvent(new CustomEvent('projects:rendered', { detail: { count: (projects || []).length } }));
    };

    const start = async () => render(await load());
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
    else start();
})();
