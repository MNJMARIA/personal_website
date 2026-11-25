#!/usr/bin/env python3
"""Збирає статичний сайт у _site/ для GitHub Pages.

* копіює index.html, стилі, скрипти, images/, files/, data/
* генерує _site/projects.json:
    - ручні проєкти з data/projects.manual.json
    - проєкти з GitHub, підтверджені через PR (data/approved/*.json)
      з актуальними описом, датами й тегами; якщо репозиторій видалено
      або з нього зняли тему `portfolio` - проєкт зникає.
"""
import datetime
import hashlib
import json
import re
import shutil
import struct
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import skills as skills_mod  # noqa: E402
from common import TOPIC, api, project_from_repo  # noqa: E402
from translate import Translator, translate_project  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
FILES = ["index.html", "style.css", "script.js", "projects.js", "admin.js"]
DIRS = ["images", "files", "data"]


# ---------------------------------------------------------------- фото ----
MAX_IMAGE_BYTES = 15 * 1024 * 1024     # одне фото
MAX_TOTAL_BYTES = 250 * 1024 * 1024    # усі завантажені фото (ліміт Pages на сайт - 1 ГБ)
EXT_BY_TYPE = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp",
               "image/avif": "avif", "image/svg+xml": "svg"}


def fetch_image(url):
    """Завантажує картинку без жодних змін (байти зберігаються як є - без втрати якості)."""
    req = urllib.request.Request(url, headers={"User-Agent": "portfolio-site-build"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read(MAX_IMAGE_BYTES + 1)
        ctype = resp.headers.get_content_type()
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("файл завеликий")
    return data, ctype


def sniff_ext(data, ctype):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:4] == b"GIF8":
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[4:12] in (b"ftypavif", b"ftypavis"):
        return "avif"
    if b"<svg" in data[:2000].lower():
        return "svg"
    return EXT_BY_TYPE.get(ctype)


def image_size(data, ext):
    """(ширина, висота) для png/jpg/gif/webp, інакше None."""
    try:
        if ext == "png":
            return struct.unpack(">II", data[16:24])
        if ext == "gif":
            return struct.unpack("<HH", data[6:10])
        if ext == "jpg":
            i = 2
            while i + 9 < len(data):
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                i += 2
                if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                    continue
                length = struct.unpack(">H", data[i:i + 2])[0]
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                    h, w = struct.unpack(">HH", data[i + 3:i + 7])
                    return w, h
                i += length
        if ext == "webp":
            kind = data[12:16]
            if kind == b"VP8X":
                return 1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little")
            if kind == b"VP8L":
                bits = int.from_bytes(data[21:25], "little")
                return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
            if kind == b"VP8 ":
                return struct.unpack("<H", data[26:28])[0] & 0x3FFF, struct.unpack("<H", data[28:30])[0] & 0x3FFF
    except Exception:
        pass
    return None


def localize_images(project, state):
    """Завантажує фото GitHub-проєкту в _site/media/ (оригінали, без стиснення).

    Файли називаються за хешем вмісту: замінила картинку в README - на сайті з'явиться нова.
    Головне фото обирається серед завантажених: пропускаються крихітні, віддається перевага
    широким (ландшафтним). Вертикальні скриншоти телефона показуються повністю (cover_fit=contain).
    """
    auto = project.pop("_auto_images", False)
    project.pop("_photo_source", None)
    candidates = [u for u in [project.get("cover")] + list(project.get("gallery") or []) if u]
    mapping, sizes = {}, {}
    for url in dict.fromkeys(candidates):
        if not re.match(r"https?://", url):
            mapping[url] = url
            local = ROOT / url
            if local.is_file():            # своє фото з репозиторію сайту: дізнаємося пропорції
                data = local.read_bytes()
                sizes[url] = image_size(data, sniff_ext(data, "") or "")
            continue
        try:
            data, ctype = fetch_image(url)
            ext = sniff_ext(data, ctype)
            if not ext:
                raise ValueError(f"не картинка ({ctype})")
            if state["bytes"] + len(data) > MAX_TOTAL_BYTES:
                raise ValueError("перевищено загальний ліміт розміру фото")
            name = f"media/{project['id']}/{hashlib.sha1(data).hexdigest()[:12]}.{ext}"
            target = OUT / name
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                state["bytes"] += len(data)
            mapping[url] = name
            sizes[name] = image_size(data, ext)
        except Exception as err:
            print(f"WARN: {project['id']}: не вдалося завантажити {url}: {err}")

    cover = mapping.get(project.get("cover"))
    gallery = [mapping[u] for u in (project.get("gallery") or []) if u in mapping]
    if auto:
        pool = ([cover] if cover else []) + gallery
        pool = [n for n in dict.fromkeys(pool) if (sizes.get(n) or (9999, 9999))[0] >= 300 and (sizes.get(n) or (9999, 9999))[1] >= 300]
        wide = next((n for n in pool[:4] if sizes.get(n) and sizes[n][0] >= 800 and sizes[n][0] / sizes[n][1] >= 1.3), None)
        cover = wide or (pool[0] if pool else None)
        gallery = [n for n in pool if n != cover]
    project["cover"] = cover
    project["gallery"] = gallery
    dims = sizes.get(cover)
    project["cover_fit"] = "contain" if dims and dims[0] / dims[1] < 0.9 else "cover"
    if not cover:
        project.pop("cover")
        project.pop("cover_fit")


def sort_key(p):
    value = p.get("updated") or p.get("created") or ""
    if len(value) == 4:
        value += "-01-01"
    return value


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for name in FILES:
        shutil.copy2(ROOT / name, OUT / name)
    for name in DIRS:
        if (ROOT / name).exists():
            shutil.copytree(ROOT / name, OUT / name)
    (OUT / ".nojekyll").write_text("")

    projects = []
    manual_repos = set()
    media_state = {"bytes": 0}
    translator = Translator()

    # 1) ручні проєкти
    manual = json.loads((ROOT / "data/projects.manual.json").read_text(encoding="utf-8"))
    for item in manual:
        if item.get("visible") is False:
            continue
        if item.get("repo"):
            manual_repos.add(item["repo"].lower())
            try:
                repo = api(f"/repos/{item['repo']}")
            except Exception as err:  # мережа/ліміти - не критично для ручних
                print(f"WARN: не вдалося оновити дати для {item['repo']}: {err}")
                repo = None
            if repo:
                item.setdefault("created", repo.get("created_at"))
                item["updated"] = repo.get("pushed_at") or item.get("updated")
        projects.append(item)

    # 2) проєкти з GitHub, підтверджені через Pull Request
    for path in sorted((ROOT / "data/approved").glob("*.json")):
        entry = json.loads(path.read_text(encoding="utf-8"))
        full = entry["repo"]
        if full.lower() in manual_repos or entry.get("hidden"):
            continue
        repo = api(f"/repos/{full}")  # інша помилка, ніж 404, зупинить збірку: сайт лишиться як був
        if repo is None:
            print(f"INFO: {full} видалено - проєкт прибрано з сайту")
            continue
        if TOPIC not in (repo.get("topics") or []):
            print(f"INFO: у {full} немає теми '{TOPIC}' - проєкт прибрано з сайту")
            continue
        readme = api(f"/repos/{full}/readme", text=True) or ""
        languages = api(f"/repos/{full}/languages") or {}
        branch = repo.get("default_branch") or "main"
        tree = api(f"/repos/{full}/git/trees/{branch}?recursive=1")
        project = project_from_repo(entry, repo, readme, languages, tree)
        translate_project(project, translator)
        localize_images(project, media_state)
        projects.append(project)
    translator.save()

    projects.sort(key=sort_key, reverse=True)

    # 3) розділ «Навички»: data/skills.json + технології з усіх проєктів на сайті
    skills_data, catalog = skills_mod.load()
    merged = skills_mod.merge(skills_data, catalog, projects)
    added = [i for a, b in zip(skills_data["categories"], merged["categories"]) for i in b["items"][len(a["items"]):]]
    index = (OUT / "index.html").read_text(encoding="utf-8")
    index, n = re.subn(r"(<!-- SKILLS:START[^>]*-->\n).*?(\n\s*<!-- SKILLS:END -->)",
                       lambda m: m.group(1) + skills_mod.render_html(merged) + m.group(2), index, flags=re.S)
    if n:
        (OUT / "index.html").write_text(index, encoding="utf-8")
    else:
        print("WARN: у index.html немає маркерів SKILLS:START/END - навички не оновлено")
    print(f"INFO: автоматично додано навичок: {len(added)} {added}")

    payload = {
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "projects": projects,
    }
    (OUT / "projects.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK: {len(projects)} проєктів, фото {media_state['bytes'] // 1024} КБ -> {OUT / 'projects.json'}")


if __name__ == "__main__":
    main()
