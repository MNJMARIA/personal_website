#!/usr/bin/env python3
"""Шукає репозиторії з темою `portfolio`, яких ще немає на сайті, і для кожного
відкриває Pull Request у репозиторії сайту.  Merge = опублікувати, Close = відхилити.

Запуск локально для перевірки опису:   python3 scripts/propose_projects.py --preview OWNER/REPO
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import skills as skills_mod  # noqa: E402
from common import TOPIC, api, folder_images, list_repos, project_from_repo  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DRY = os.environ.get("DRY_RUN") == "1"


def run(*cmd):
    return subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True).stdout


def preview(full):
    repo = api(f"/repos/{full}")
    if repo is None:
        sys.exit(f"{full}: не знайдено")
    readme = api(f"/repos/{full}/readme", text=True) or ""
    langs = api(f"/repos/{full}/languages") or {}
    branch = repo.get("default_branch") or "main"
    tree = api(f"/repos/{full}/git/trees/{branch}?recursive=1")
    project = project_from_repo({"repo": full}, repo, readme, langs, tree)
    project["_folder_candidates"] = folder_images(repo, tree)
    skills, catalog = skills_mod.load()
    project["_new_skills"] = skills_mod.new_skills(project, skills, skills_mod.lookup(catalog))
    project["_categories"] = {c["id"]: c["title"]["en"] for c in skills["categories"]}
    return project


def photos_block(project, name):
    source = project.get("_photo_source")
    n = len(project.get("gallery") or [])
    if source == "readme":
        return f"{n + 1} картинок з README: перша - головне фото картки, решта - карусель."
    if source == "folders":
        found = project.get("_folder_candidates") or []
        thumbs = " ".join(f'<img src="{url}" width="130" title="{path}">' for path, url in found[:6])
        listing = "\n".join(f"  - `{path}`" for path, _ in found[:12])
        return (
            "**у README картинок немає, але вони знайдені в папках репозиторію** і за замовчуванням "
            "будуть додані (перше - головне фото, решта - карусель):\n\n"
            f"{thumbs}\n\n{listing}\n\n"
            f"  **Додати ці фото?** Так - просто зроби **Merge**. Ні - у файлі `data/approved/{name}.json` "
            f'заміни `"photos": "auto"` на `"photos": "none"`. '
            f'Інше головне фото: додай рядок `"cover": "repo:шлях/до/файлу.jpg"`.'
        )
    return ("не знайдено ні в README, ні в папках - буде стандартна картинка GitHub. Додай скриншоти в README "
            "або в папку `docs/screens` чи `images` репозиторію - вони підтягнуться.")


def skills_line(project):
    new = project.get("_new_skills") or []
    if not new:
        return "нових немає (технології проєкту вже є в розділі «Навички»)"
    cats = project.get("_categories") or {}
    parts = ", ".join(f"{name} → {cats.get(cat, cat)}" for name, cat in new)
    return f'буде додано в розділ «Навички»: {parts}. Не потрібно? Додай у файл проєкту `"skills": false`.'


def pr_body(owner, project):
    name = project["repo"].split("/")[1]
    return (
        f"@{owner}, у репозиторії **[{project['repo']}](https://github.com/{project['repo']})** "
        f"є тема `{TOPIC}`. Показати його на сайті в розділі «Проєкти»?\n\n"
        f"**✅ Опублікувати** - натисни **Merge** (сайт оновиться за 1-2 хв).\n"
        f"**❌ Не публікувати** - натисни **Close pull request**.\n"
        f"Передумала? Відкрий (Reopen) закритий PR і зроби Merge.\n\n"
        f"### Так виглядатиме картка\n"
        f"- **Назва:** {project['title']['ua']}\n"
        f"- **Короткий опис:** {project['summary']['ua'] or '_(порожньо - додай опис репозиторію або README)_'}\n"
        f"  (на сайті автоматично перекладається українською/англійською)\n"
        f"- **Технології:** {', '.join(project['tags']) or '-'}\n"
        f"- **Навички:** {skills_line(project)}\n"
        f"- **Фото:** {photos_block(project, name)}\n\n"
        f"<details><summary>Повний опис на сторінці проєкту</summary>\n\n"
        f"{project['description']['ua'] or '_(порожньо)_'}\n\n</details>\n\n"
        f"### Хочеш щось змінити до публікації?\n"
        f"Відкрий у цьому PR файл `data/approved/{name}.json` (Files changed → ⋯ → Edit file) "
        f"і додай потрібні поля, наприклад:\n"
        f"```json\n{{\n  \"repo\": \"{project['repo']}\",\n  \"photos\": \"auto\",\n"
        f"  \"title\": {{\"ua\": \"Назва\", \"en\": \"Title\"}},\n"
        f"  \"summary\": {{\"ua\": \"Коротко українською\", \"en\": \"Short English text\"}},\n"
        f"  \"cover\": \"repo:images/main.jpg\"\n}}\n```\n"
        f"Без полів `title`/`summary`/`description` текст береться з GitHub автоматично, перекладається і оновлюється "
        f"при зміні README/опису. `photos`: `auto` (README, а якщо там порожньо - папки), `readme`, `none`.\n"
    )


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--preview":
        print(json.dumps(preview(sys.argv[2]), ensure_ascii=False, indent=2))
        return

    site_repo = os.environ["GITHUB_REPOSITORY"]
    owner = site_repo.split("/")[0]
    base = (api(f"/repos/{site_repo}") or {}).get("default_branch", "main")

    known = {p.stem.lower() for p in (ROOT / "data/approved").glob("*.json")}
    known |= {json.loads(p.read_text(encoding="utf-8"))["repo"].split("/")[1].lower()
              for p in (ROOT / "data/approved").glob("*.json")}
    for item in json.loads((ROOT / "data/projects.manual.json").read_text(encoding="utf-8")):
        if item.get("repo"):
            known.add(item["repo"].split("/")[1].lower())

    candidates = [
        r for r in list_repos(owner)
        if TOPIC in (r.get("topics") or []) and not r["fork"] and not r["archived"]
        and r["full_name"].lower() != site_repo.lower()
        and r["name"].lower() not in known
    ]
    print(f"Кандидатів: {len(candidates)}")
    created = 0
    for repo in candidates:
        branch = f"propose/{repo['name']}"
        if api(f"/repos/{site_repo}/pulls?state=all&head={owner}:{branch}"):
            continue  # вже пропонували (відкритий, прийнятий або відхилений PR)
        project = preview(repo["full_name"])
        if DRY:
            print("DRY:", repo["full_name"], "->", project["summary"]["ua"])
            continue
        run("git", "checkout", "-q", base)
        run("git", "checkout", "-q", "-B", branch)
        (ROOT / "data/approved").mkdir(parents=True, exist_ok=True)
        (ROOT / "data/approved" / f"{repo['name']}.json").write_text(
            json.dumps({"repo": repo["full_name"], "photos": "auto"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run("git", "add", "data/approved")
        run("git", "-c", "user.name=github-actions[bot]",
            "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
            "commit", "-q", "-m", f"Додати проєкт {repo['name']}")
        run("git", "push", "-q", "--force", "origin", branch)
        pr = api(f"/repos/{site_repo}/pulls", "POST", {
            "title": f"Додати на сайт: {project['title']['ua']}",
            "head": branch, "base": base, "body": pr_body(owner, project)})
        api(f"/repos/{site_repo}/issues/{pr['number']}/assignees", "POST", {"assignees": [owner]})
        run("git", "checkout", "-q", base)
        created += 1
        print(f"PR #{pr['number']} для {repo['full_name']}")
    print(f"Створено PR: {created}")


if __name__ == "__main__":
    main()
