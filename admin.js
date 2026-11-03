// ==========================================
// АДМІНКА «ДОДАТИ ПРОЄКТ» - видима лише власниці сайту.
//
// Як це працює: сторінка статична, тож "пароль" - це персональний токен GitHub
// (fine-grained, доступ лише до цього репозиторію, право Contents: Read and write).
// Без токена кнопки немає, а навіть якщо знати про #admin - зберегти нічого не вдасться,
// бо запис у репозиторій GitHub дозволить лише власниці.
// Збереження = один коміт у репозиторій -> Actions перебудовує сайт (1-2 хв).
// ==========================================
(() => {
    const CFG = {
        owner: 'MNJMARIA',
        repo: 'personal_website',
        branch: 'main',
        manualPath: 'data/projects.manual.json',
        imageDir: 'images/projects',
        tokenKey: 'admin_gh_token',
    };

    let token = null;
    try { token = localStorage.getItem(CFG.tokenKey); } catch (e) { /* приватний режим */ }

    // ---------- GitHub API ----------
    const gh = async (path, options = {}) => {
        const res = await fetch('https://api.github.com' + path, {
            ...options,
            headers: {
                Accept: 'application/vnd.github+json',
                Authorization: 'Bearer ' + token,
                'X-GitHub-Api-Version': '2022-11-28',
                ...(options.body ? { 'Content-Type': 'application/json' } : {}),
            },
        });
        if (!res.ok) {
            const err = new Error(`GitHub ${res.status}: ${(await res.text()).slice(0, 200)}`);
            err.status = res.status;
            throw err;
        }
        return res.status === 204 ? null : res.json();
    };
    const repoPath = `/repos/${CFG.owner}/${CFG.repo}`;

    // true - токен підходить; false - токен недійсний/без прав; null - немає зв'язку (токен не чіпаємо)
    const canPush = async () => {
        try { return !!(await gh(repoPath)).permissions?.push; } catch (e) {
            return [401, 403, 404].includes(e.status) ? false : null;
        }
    };

    // ---------- допоміжні ----------
    const el = (tag, className, html) => {
        const n = document.createElement(tag);
        if (className) n.className = className;
        if (html != null) n.innerHTML = html; // тільки статичні шаблони, без даних користувача
        return n;
    };

    const translit = (s) => {
        const map = { а:'a',б:'b',в:'v',г:'h',ґ:'g',д:'d',е:'e',є:'ie',ж:'zh',з:'z',и:'y',і:'i',ї:'i',й:'i',к:'k',л:'l',м:'m',н:'n',о:'o',п:'p',р:'r',с:'s',т:'t',у:'u',ф:'f',х:'kh',ц:'ts',ч:'ch',ш:'sh',щ:'shch',ь:'',ю:'iu',я:'ia','’':'',"'":'' };
        return s.toLowerCase().split('').map((c) => (c in map ? map[c] : c)).join('')
            .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40) || 'project';
    };

    const bytesToBase64 = (bytes) => {
        let bin = '';
        for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
        return btoa(bin);
    };
    const textToBase64 = (text) => bytesToBase64(new TextEncoder().encode(text));
    const base64ToText = (b64) => new TextDecoder().decode(Uint8Array.from(atob(b64.replace(/\s/g, '')), (c) => c.charCodeAt(0)));

    // Стискаємо фото до JPEG ≤ 1600px, щоб сайт швидко вантажився
    const compress = async (file, max = 1600, quality = 0.85) => {
        const bmp = await createImageBitmap(file);
        const k = Math.min(1, max / Math.max(bmp.width, bmp.height));
        const canvas = document.createElement('canvas');
        canvas.width = Math.round(bmp.width * k);
        canvas.height = Math.round(bmp.height * k);
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#111215';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(bmp, 0, 0, canvas.width, canvas.height);
        const blob = await new Promise((r) => canvas.toBlob(r, 'image/jpeg', quality));
        return bytesToBase64(new Uint8Array(await blob.arrayBuffer()));
    };

    const toast = (message, isError) => {
        const t = el('div', 'admin-toast' + (isError ? ' error' : ''));
        t.textContent = message;
        document.body.appendChild(t);
        setTimeout(() => t.remove(), 7000);
    };

    // ---------- один коміт: фото + оновлений JSON ----------
    const saveProject = async (entry, images) => {
        const blobs = [];
        for (const img of images) {
            const blob = await gh(`${repoPath}/git/blobs`, { method: 'POST', body: JSON.stringify({ content: img.base64, encoding: 'base64' }) });
            blobs.push({ path: img.path, mode: '100644', type: 'blob', sha: blob.sha });
        }

        for (let attempt = 0; attempt < 3; attempt++) {
            const ref = await gh(`${repoPath}/git/ref/heads/${CFG.branch}`);
            const parentSha = ref.object.sha;
            const parent = await gh(`${repoPath}/git/commits/${parentSha}`);

            const file = await gh(`${repoPath}/contents/${CFG.manualPath}?ref=${parentSha}`);
            const list = JSON.parse(base64ToText(file.content));
            if (list.some((p) => p.id === entry.id)) entry.id += '-' + Date.now().toString(36).slice(-3);
            list.unshift(entry);
            const json = await gh(`${repoPath}/git/blobs`, { method: 'POST', body: JSON.stringify({ content: JSON.stringify(list, null, 2) + '\n', encoding: 'utf-8' }) });

            const tree = await gh(`${repoPath}/git/trees`, {
                method: 'POST',
                body: JSON.stringify({ base_tree: parent.tree.sha, tree: [...blobs, { path: CFG.manualPath, mode: '100644', type: 'blob', sha: json.sha }] }),
            });
            const commit = await gh(`${repoPath}/git/commits`, {
                method: 'POST',
                body: JSON.stringify({ message: `Додати проєкт: ${entry.title.ua}`, tree: tree.sha, parents: [parentSha] }),
            });
            try {
                await gh(`${repoPath}/git/refs/heads/${CFG.branch}`, { method: 'PATCH', body: JSON.stringify({ sha: commit.sha, force: false }) });
                return;
            } catch (e) {
                if (e.status !== 422 || attempt === 2) throw e; // хтось встиг зробити коміт - пробуємо ще раз
            }
        }
    };

    // ---------- вікна ----------
    const openModal = (title, bodyNode) => {
        const overlay = el('div', 'admin-overlay');
        const box = el('div', 'admin-modal');
        const head = el('div', 'admin-modal-head', `<h3></h3><button type="button" class="admin-close" aria-label="Close">×</button>`);
        head.querySelector('h3').textContent = title;
        box.append(head, bodyNode);
        overlay.appendChild(box);
        const close = () => overlay.remove();
        head.querySelector('.admin-close').addEventListener('click', close);
        overlay.addEventListener('mousedown', (e) => { if (e.target === overlay) close(); });
        document.body.appendChild(overlay);
        return close;
    };

    const openTokenModal = () => {
        const form = el('form', 'admin-form', `
            <p class="admin-hint">Вставте персональний токен GitHub (fine-grained) з доступом <b>лише до цього репозиторію</b>
            і правом <b>Contents: Read and write</b>. Він зберігається тільки в цьому браузері.
            <a href="https://github.com/settings/personal-access-tokens/new" target="_blank" rel="noopener">Створити токен ↗</a></p>
            <input type="password" name="token" placeholder="github_pat_..." autocomplete="off" required>
            <div class="admin-status"></div>
            <button type="submit" class="btn btn-primary">Увійти</button>`);
        const close = openModal('Вхід власниці сайту', form);
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            token = form.token.value.trim();
            form.querySelector('.admin-status').textContent = 'Перевіряю…';
            if ((await canPush()) === true) {
                try { localStorage.setItem(CFG.tokenKey, token); } catch (err) { /* ignore */ }
                close();
                showToolbar();
                toast('Адмін-режим увімкнено.');
            } else {
                token = null;
                form.querySelector('.admin-status').textContent = 'Токен не підійшов: потрібен доступ Contents: Read and write до цього репозиторію.';
            }
        });
    };

    const openProjectForm = () => {
        const form = el('form', 'admin-form', `
            <label>Назва * <input name="title_ua" required maxlength="120"></label>
            <label>Назва англійською <input name="title_en" maxlength="120" placeholder="необов’язково"></label>
            <label>Опис * <textarea name="desc_ua" rows="5" required></textarea></label>
            <label>Опис англійською <textarea name="desc_en" rows="4" placeholder="необов’язково"></textarea></label>
            <label>Технології (через кому) <input name="tags" placeholder="Java, Spring Boot, PostgreSQL"></label>
            <label>Посилання (GitHub / демо) <input name="link" type="url" placeholder="https://github.com/..."></label>
            <label>Головне фото * <input name="cover" type="file" accept="image/*" required></label>
            <label>Додаткові фото <input name="gallery" type="file" accept="image/*" multiple></label>
            <div class="admin-status"></div>
            <div class="admin-actions">
                <button type="submit" class="btn btn-primary">Зберегти</button>
                <button type="button" class="btn btn-secondary admin-cancel">Скасувати</button>
            </div>`);
        const close = openModal('Новий проєкт', form);
        form.querySelector('.admin-cancel').addEventListener('click', close);

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const status = form.querySelector('.admin-status');
            const submit = form.querySelector('button[type=submit]');
            submit.disabled = true;
            try {
                status.textContent = 'Стискаю фото…';
                const titleUa = form.title_ua.value.trim();
                const slug = translit(titleUa);
                const dir = `${CFG.imageDir}/${slug}`;
                const images = [{ path: `${dir}/cover.jpg`, base64: await compress(form.cover.files[0]) }];
                const extra = [...form.gallery.files];
                for (let i = 0; i < extra.length; i++) {
                    images.push({ path: `${dir}/${i + 1}.jpg`, base64: await compress(extra[i]) });
                }

                const descUa = form.desc_ua.value.trim();
                const link = form.link.value.trim();
                const entry = {
                    id: slug,
                    visible: true,
                    title: { ua: titleUa, en: form.title_en.value.trim() || titleUa },
                    description: { ua: descUa, en: form.desc_en.value.trim() || descUa },
                    tags: form.tags.value.split(',').map((t) => t.trim()).filter(Boolean),
                    links: link ? [{ label: /github\.com/i.test(link) ? 'GitHub Repository' : 'Open', url: link }] : [],
                    cover: images[0].path,
                    gallery: images.slice(1).map((i) => i.path),
                    created: new Date().toISOString().slice(0, 10),
                    updated: new Date().toISOString().slice(0, 10),
                };

                status.textContent = 'Зберігаю в репозиторій…';
                await saveProject(entry, images);
                close();
                toast('Проєкт збережено! Сайт оновиться приблизно за 1-2 хвилини - тоді перезавантажте сторінку.');
            } catch (err) {
                console.error(err);
                status.textContent = 'Помилка: ' + err.message;
                submit.disabled = false;
            }
        });
    };

    // ---------- панель на сторінці ----------
    const showToolbar = () => {
        if (document.querySelector('.admin-toolbar')) return;
        const section = document.querySelector('#projects .container');
        if (!section) return;
        const bar = el('div', 'admin-toolbar');
        const add = el('button', 'btn btn-primary admin-add');
        add.type = 'button';
        add.textContent = '+ Додати проєкт';
        add.addEventListener('click', openProjectForm);
        const out = el('button', 'admin-logout');
        out.type = 'button';
        out.textContent = 'Вийти з адмін-режиму';
        out.addEventListener('click', () => {
            try { localStorage.removeItem(CFG.tokenKey); } catch (e) { /* ignore */ }
            token = null;
            bar.remove();
        });
        bar.append(add, out);
        section.querySelector('.section-title').after(bar);
    };

    const init = async () => {
        if (token) {
            const ok = await canPush();
            if (ok !== false) showToolbar();
            else { token = null; try { localStorage.removeItem(CFG.tokenKey); } catch (e) { /* ignore */ } }
        }
        if (location.hash === '#admin' && !token) openTokenModal();
    };
    window.addEventListener('hashchange', () => { if (location.hash === '#admin' && !token) openTokenModal(); });
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})();
