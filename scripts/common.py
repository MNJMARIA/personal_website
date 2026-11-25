"""Спільні функції для скриптів сайту (лише стандартна бібліотека Python)."""
import json
import os
import re
import urllib.error
import urllib.request

API = "https://api.github.com"
# Репозиторій потрапляє на сайт, лише якщо має цю тему (Topics) на GitHub.
TOPIC = os.environ.get("PORTFOLIO_TOPIC", "portfolio")


def api(path, method="GET", body=None, text=False):
    """Виклик GitHub API. 404 -> None. Інші помилки -> виняток."""
    url = path if path.startswith("http") else API + path
    headers = {
        "Accept": "application/vnd.github.raw+json" if text else "application/vnd.github+json",
        "User-Agent": "portfolio-site-sync",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        raise
    if text:
        return raw
    return json.loads(raw) if raw.strip() else None


def list_repos(owner):
    """Усі публічні репозиторії користувача (з полем topics)."""
    repos, page = [], 1
    while True:
        chunk = api(f"/users/{owner}/repos?per_page=100&page={page}&sort=pushed")
        if not chunk:
            break
        repos.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
    return repos


# ---------------------------------------------------------------- тексти ----

def prepare_markdown(md):
    """Прибирає коментарі, код, HTML-таблиці й теги (з <br> робить пробіл)."""
    md = re.sub(r"<!--.*?-->", "", md or "", flags=re.S)
    md = re.sub(r"```.*?```", "", md, flags=re.S)
    md = re.sub(r"~~~.*?~~~", "", md, flags=re.S)
    md = re.sub(r"<table\b.*?</table>", "", md, flags=re.S | re.I)
    md = re.sub(r"<br\s*/?>", " ", md, flags=re.I)
    md = re.sub(r"<[^>]+>", "", md)
    return md


def md_paragraphs(md):
    """Звичайні абзаци тексту з README (без заголовків, списків, таблиць, бейджів, коду)."""
    md = prepare_markdown(md)
    out = []
    for block in re.split(r"\n\s*\n", md):
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        lines = [l for l in lines if not re.match(r"(#{1,6}\s|={3,}$|-{3,}$|\*{3,}$)", l)]
        if not lines:
            continue
        if any(re.match(r"([-*+]\s|\d+[.)]\s|\||>)", l) for l in lines):
            continue
        text = " ".join(lines)
        text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
        text = re.sub(r"\[([^\]]*)\]\[[^\]]*\]", r"\1", text)
        text = re.sub(r"(\*\*|__|\*|`|~~)", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        if text.endswith(":"):
            continue  # вступ до списку, а не опис
        if len(text) >= 40 and re.search(r"[A-Za-zА-Яа-яІіЇїЄєҐґ]{3}", text):
            out.append(text)
    return out


def truncate(text, limit):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    ends = [cut.rfind(m) for m in (". ", "! ", "? ")]
    best = max(ends)
    if best >= limit * 0.5:
        return cut[: best + 1]
    space = cut.rfind(" ")
    return (cut[:space] if space > 0 else cut).rstrip(" ,;:-") + "…"


BADGE_HINTS = (
    "shields.io", "badgen.net", "badge.fury.io", "forthebadge.com", "codecov.io", "coveralls.io",
    "travis-ci", "circleci.com", "sonarcloud.io", "snyk.io", "codacy.com", "visitor-badge",
    "hits.seeyoufarm", "star-history", "komarev.com", "badge", "/actions/workflows/",
)
MAX_GALLERY = 12
# іконки й логотипи не підходять як фото проєкту
NON_PHOTO = re.compile(r"(^|[/_.-])(icon|icons|logo|favicon|avatar|sprite)([/_.-]|$)", re.I)


def readme_images(readme, repo):
    """Абсолютні посилання на картинки з README (без бейджів), у порядку появи."""
    full = repo["full_name"]
    branch = repo.get("default_branch") or "main"
    text = re.sub(r"<!--.*?-->", "", readme or "", flags=re.S)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    found = []
    for m in re.finditer(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+[\"'][^\"']*[\"'])?\s*\)", text):
        found.append((m.start(), m.group(1)))
    for m in re.finditer(r"<img\b[^>]*?\bsrc\s*=\s*[\"']([^\"']+)[\"']", text, flags=re.I):
        found.append((m.start(), m.group(1)))
    urls = []
    for _, raw in sorted(found):
        url = raw.strip()
        if not url or url.startswith(("data:", "#", "..")):
            continue
        if re.match(r"https?://github\.com/[^/]+/[^/]+/blob/", url):
            url = re.sub(r"^https?://github\.com/([^/]+/[^/]+)/blob/", r"https://raw.githubusercontent.com/\1/", url)
            url = url.split("?")[0]
        elif not re.match(r"https?://", url):
            if re.match(r"[a-z][a-z0-9+.-]*:", url, flags=re.I):
                continue
            path = url.split("?")[0].split("#")[0].lstrip("./").lstrip("/")
            url = f"https://raw.githubusercontent.com/{full}/{branch}/{path}"
        if any(h in url.lower() for h in BADGE_HINTS):
            continue
        if NON_PHOTO.search(url.split("?")[0].lower().split("://", 1)[-1]):
            continue
        url = url.replace(" ", "%20")
        if url not in urls:
            urls.append(url)
    return urls[: MAX_GALLERY + 1]


PHOTO_DIRS = {"screens", "screenshots", "screenshot", "img", "imgs", "images", "image", "pictures", "photos",
              "figures", "plots", "results", "media", "docs", "assets", "gallery", "demo", "preview", "previews", "pics"}
PHOTO_DIRS_FIRST = {"screens", "screenshots", "screenshot", "gallery", "demo", "preview", "previews"}
SKIP_DIRS = {"node_modules", ".git", ".github", "build", "dist", "venv", ".venv", "__pycache__", "android", "ios", "web",
             "windows", "macos", "linux", "res", "test", "tests", "vendor", "target", "out"}
PHOTO_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def natural_key(text):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", text)]


def raw_url(repo, path):
    from urllib.parse import quote
    branch = repo.get("default_branch") or "main"
    return f"https://raw.githubusercontent.com/{repo['full_name']}/{branch}/{quote(path)}"


def folder_images(repo, tree):
    """Фото з типових папок репозиторію (screens, screenshots, img, images, docs, ...): [(шлях, url)].

    Використовується, коли README не містить картинок. Папки screens/screenshots мають пріоритет.
    """
    found = []
    for node in (tree or {}).get("tree", []):
        path = node.get("path", "")
        if node.get("type") != "blob" or not path.lower().endswith(PHOTO_EXT):
            continue
        size = node.get("size") or 0
        if size < 5 * 1024 or size > 15 * 1024 * 1024:
            continue
        *dirs, filename = path.split("/")
        low = [d.lower() for d in dirs]
        if not low or not (set(low) & PHOTO_DIRS) or (set(low) & SKIP_DIRS):
            continue
        if NON_PHOTO.search(path.lower()):
            continue
        rank = 0 if set(low) & PHOTO_DIRS_FIRST else 1
        found.append((rank, natural_key(path), path))
    found.sort()
    return [(path, raw_url(repo, path)) for _, _, path in found[: MAX_GALLERY + 1]]


def resolve_repo_path(repo, value):
    """'repo:images/a.png' -> посилання на файл у репозиторії проєкту; інше без змін."""
    if isinstance(value, str) and value.startswith("repo:"):
        return raw_url(repo, value[5:].lstrip("/"))
    return value


FEATURE_HEAD = re.compile(r"(feature|можливост|функціонал|функції|functionality|capabilit|highlights|що вміє|what it does)", re.I)


def clean_inline(text):
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"(\*\*|__|\*|`|~~)", "", text)
    text = re.sub(r"^\[[ xX]\]\s*", "", text.strip())
    return re.sub(r"\s+", " ", text).strip()


def readme_features(md, limit=10):
    """Список можливостей з розділу README «Можливості / Features».

    Якщо розділ має підрозділи (###), кожен підрозділ дає один пункт «Назва - перше речення».
    Інакше беруться пункти маркованого списку.
    """
    lines = prepare_markdown(md).splitlines()
    heads = []
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if m:
            heads.append((i, len(m.group(1)), clean_inline(m.group(2))))
    for idx, (start, level, title) in enumerate(heads):
        if not FEATURE_HEAD.search(title):
            continue
        end = next((j for j, lv, _ in heads[idx + 1:] if lv <= level), len(lines))
        subs = [(j, t) for j, lv, t in heads[idx + 1:] if j < end and lv == level + 1]
        items = []
        if subs:
            for j, sub_title in subs:
                stop = min(next((j2 for j2, lv, _ in heads if j2 > j and lv <= level + 1), end), end)
                body = "\n".join(lines[j + 1:stop])
                paras = md_paragraphs(body)
                if paras:
                    first = paras[0]
                else:
                    bullets = re.findall(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$", body, flags=re.M)
                    first = clean_inline(bullets[0]) if bullets else ""
                items.append(f"{sub_title} - {truncate(first, 150)}" if first else sub_title)
        else:
            raw = [(len(m.group(1)), m.group(2)) for m in
                   re.finditer(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$", "\n".join(lines[start + 1:end]), flags=re.M)]
            if raw:
                base = min(ind for ind, _ in raw)
                items = [clean_inline(t) for ind, t in raw if ind == base]
        items = [truncate(x, 200) for x in items if x]
        if items:
            return items[:limit]
    return []


def pretty_title(name):
    title = re.sub(r"[-_]+", " ", name).strip()
    return title[:1].upper() + title[1:] if title.islower() else title


def describe(repo, readme):
    """Короткий опис для картки (summary) та довший для сторінки (description)."""
    repo_desc = (repo.get("description") or "").strip()
    paras = md_paragraphs(readme)
    summary_src = repo_desc or (paras[0] if paras else "")
    long_parts = [truncate(p, 450) for p in paras[:2]] or ([repo_desc] if repo_desc else [])
    summary = truncate(summary_src, 180)
    description = "\n\n".join(long_parts)
    return {
        "summary": {"ua": summary, "en": summary},
        "description": {"ua": description, "en": description},
    }


def project_from_repo(entry, repo, readme, languages, tree=None):
    """Збирає проєкт на основі репозиторію GitHub + ручних правок з data/approved/*.json."""
    full = repo["full_name"]
    auto = describe(repo, readme)
    tags = list((languages or {}).keys())[:4]
    for topic in repo.get("topics") or []:
        if topic != TOPIC and topic.replace("-", " ").lower() not in [t.lower() for t in tags]:
            tags.append(topic.replace("-", " "))
    tags = tags[:7]
    title = pretty_title(repo["name"])
    photos = (entry.get("photos") or "auto").lower()      # auto | readme | none
    images = [] if photos == "none" else readme_images(readme, repo)
    photo_source = "readme" if images else "none"
    if not images and photos == "auto":
        images = [url for _, url in folder_images(repo, tree)]
        photo_source = "folders" if images else "none"
    features = readme_features(readme)
    links = [{"label": "GitHub Repository", "url": repo["html_url"]}]
    if repo.get("homepage") and re.match(r"https?://", repo["homepage"]):
        links.append({"label": "Live Demo", "url": repo["homepage"]})
    project = {
        "id": re.sub(r"[^a-z0-9_-]+", "-", repo["name"].lower()),
        "source": "github",
        "repo": full,
        "title": {"ua": title, "en": title},
        "kind": "GitHub",
        "summary": auto["summary"],
        "description": auto["description"],
        "tags": tags,
        "links": links,
        "cover": images[0] if images else f"https://opengraph.githubassets.com/1/{full}",
        "gallery": images[1:] if images else [],
        "created": repo.get("created_at"),
        "updated": repo.get("pushed_at") or repo.get("updated_at"),
    }
    if features:
        project["features"] = {"ua": features, "en": features}
    project["_auto_images"] = not entry.get("cover")  # build_site.py сам вибере головне фото серед завантажених
    project["_photo_source"] = photo_source
    for key in ("title", "summary", "description", "tags", "links", "cover", "gallery", "features", "kind", "gallery_title", "tagline"):
        if entry.get(key):
            project[key] = entry[key]
    # cover/gallery можуть вказувати на файли самого репозиторію проєкту: "repo:images/a.png"
    project["cover"] = resolve_repo_path(repo, project.get("cover"))
    project["gallery"] = [resolve_repo_path(repo, g) for g in project.get("gallery") or []]
    # своє головне фото задано вручну, а галерею не задано: усі знайдені фото йдуть у галерею (без дубліката обкладинки)
    if entry.get("cover") and not entry.get("gallery"):
        project["gallery"] = [u for u in images if u != project["cover"]][:MAX_GALLERY]
    if entry.get("skills") is not None:
        project["skills"] = entry["skills"]
    return project
