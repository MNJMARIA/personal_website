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
from common import TOPIC, api, list_repos, project_from_repo  # noqa: E402

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
    return project_from_repo({"repo": full}, repo, readme, langs)


def photos_line(project):
    n = len(project.get("gallery") or [])
    if "opengraph.githubassets.com" in (project.get("cover") or ""):
        return "у README картинок не знайдено - буде стандартна картинка GitHub (додай скриншоти в README, і вони підтягнуться)"
    return f"головне фото + {n} у галереї (з README)"


def pr_body(owner, project):
    return (
        f"@{owner}, у репозиторії **[{project['repo']}](https://github.com/{project['repo']})** "
        f"є тема `{TOPIC}`. Показати його на сайті в розділі «Проєкти»?\n\n"
        f"**✅ Опублікувати** - натисни **Merge** (сайт оновиться за 1-2 хв).\n"
        f"**❌ Не публікувати** - натисни **Close pull request**.\n"
        f"Передумала? Просто відкрий (Reopen) закритий PR і зроби Merge.\n\n"
        f"### Так виглядатиме картка\n"
        f"- **Назва:** {project['title']['ua']}\n"
        f"- **Короткий опис:** {project['summary']['ua'] or '_(порожньо - додай опис репозиторію або README)_'}\n"
        f"- **Технології:** {', '.join(project['tags']) or '-'}\n"
        f"- **Фото:** {photos_line(project)}\n\n"
        f"<details><summary>Повний опис на сторінці проєкту</summary>\n\n"
        f"{project['description']['ua'] or '_(порожньо)_'}\n\n</details>\n\n"
        f"### Хочеш змінити текст?\n"
        f"Відкрий у цьому PR файл `data/approved/{project['repo'].split('/')[1]}.json` (Files changed → ⋯ → Edit file) "
        f"і додай потрібні поля, наприклад:\n"
        f"```json\n{{\n  \"repo\": \"{project['repo']}\",\n"
        f"  \"title\": {{\"ua\": \"Назва\", \"en\": \"Title\"}},\n"
        f"  \"summary\": {{\"ua\": \"Коротко українською\", \"en\": \"Short English text\"}},\n"
        f"  \"description\": {{\"ua\": \"...\", \"en\": \"...\"}}\n}}\n```\n"
        f"Без цих полів опис береться з GitHub автоматично й оновлюється при кожній зміні README/опису.\n"
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
            json.dumps({"repo": repo["full_name"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
