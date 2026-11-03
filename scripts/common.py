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

def md_paragraphs(md):
    """Звичайні абзаци тексту з README (без заголовків, списків, таблиць, бейджів, коду)."""
    md = re.sub(r"<!--.*?-->", "", md or "", flags=re.S)
    md = re.sub(r"```.*?```", "", md, flags=re.S)
    md = re.sub(r"~~~.*?~~~", "", md, flags=re.S)
    md = re.sub(r"<[^>]+>", "", md)
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


def project_from_repo(entry, repo, readme, languages):
    """Збирає проєкт на основі репозиторію GitHub + ручних правок з data/approved/*.json."""
    full = repo["full_name"]
    auto = describe(repo, readme)
    tags = list((languages or {}).keys())[:4]
    for topic in repo.get("topics") or []:
        if topic != TOPIC and topic.replace("-", " ").lower() not in [t.lower() for t in tags]:
            tags.append(topic.replace("-", " "))
    tags = tags[:7]
    title = pretty_title(repo["name"])
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
        "cover": f"https://opengraph.githubassets.com/1/{full}",
        "gallery": [],
        "created": repo.get("created_at"),
        "updated": repo.get("pushed_at") or repo.get("updated_at"),
    }
    for key in ("title", "summary", "description", "tags", "links", "cover", "gallery", "kind", "gallery_title", "tagline"):
        if entry.get(key):
            project[key] = entry[key]
    return project
