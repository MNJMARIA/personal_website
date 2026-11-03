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
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import TOPIC, api, project_from_repo  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
FILES = ["index.html", "style.css", "script.js", "projects.js", "admin.js"]
DIRS = ["images", "files", "data"]


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
        projects.append(project_from_repo(entry, repo, readme, languages))

    projects.sort(key=sort_key, reverse=True)
    payload = {
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "projects": projects,
    }
    (OUT / "projects.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK: {len(projects)} проєктів -> {OUT / 'projects.json'}")


if __name__ == "__main__":
    main()
