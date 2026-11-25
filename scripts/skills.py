"""Розділ «Навички»: data/skills.json + технології з проєктів (за каталогом data/skill-catalog.json).

Технології, яких ще немає в розділі, додаються в категорію з каталогу. Список збирається при кожному
деплої, тому коли проєкт зникає з сайту, його «власні» навички теж зникають.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load():
    skills = json.loads((ROOT / "data/skills.json").read_text(encoding="utf-8"))
    catalog = json.loads((ROOT / "data/skill-catalog.json").read_text(encoding="utf-8"))["technologies"]
    return skills, catalog


def _norm(text):
    return re.sub(r"\s+", " ", str(text).strip().lower())


def lookup(catalog):
    """alias (нижній регістр) -> запис каталогу"""
    table = {}
    for tech in catalog:
        for alias in [tech["name"]] + tech.get("aliases", []):
            table.setdefault(_norm(alias), tech)
    return table


def is_present(name, skills):
    """Чи згадується технологія як окреме слово в будь-якому пункті будь-якої категорії."""
    pattern = re.compile(r"(?<![\w+#.])" + re.escape(name) + r"(?![\w+#])", re.I)
    return any(pattern.search(item) for cat in skills["categories"] for item in cat["items"])


def project_skill_names(project):
    """Теги проєкту, які участь у навичках: поле skills (False - вимкнути, список - свої), інакше tags."""
    chosen = project.get("skills")
    if chosen is False:
        return []
    return list(chosen) if isinstance(chosen, list) else list(project.get("tags") or [])


def new_skills(project, skills, catalog_table, extra=None):
    """[(технологія, id категорії)] - що проєкт додасть до розділу навичок."""
    ignore = {_norm(x) for x in skills.get("ignore", [])}
    result, seen = [], set()
    for tag in project_skill_names(project):
        tech = catalog_table.get(_norm(tag))
        if not tech or _norm(tech["name"]) in ignore or _norm(tag) in ignore or tech["name"] in seen:
            continue
        if is_present(tech["name"], skills) or any(t == tech["name"] for t, _ in (extra or [])):
            continue
        seen.add(tech["name"])
        result.append((tech["name"], tech["category"]))
    return result


def merge(skills, catalog, projects):
    """Повертає копію skills з доданими технологіями з проєктів."""
    merged = json.loads(json.dumps(skills))
    table = lookup(catalog)
    by_id = {c["id"]: c for c in merged["categories"]}
    for project in projects:
        for name, cat_id in new_skills(project, merged, table):
            if cat_id in by_id:
                by_id[cat_id]["items"].append(name)
    return merged


def render_html(skills, indent="                    "):
    parts = []
    for cat in skills["categories"]:
        if not cat["items"]:
            continue
        title = cat["title"]
        items = "\n".join(f'{indent}        <li>{html.escape(i)}</li>' for i in cat["items"])
        parts.append(
            f'{indent}<div class="skill-category">\n'
            f'{indent}    <h3 data-ua="{html.escape(title["ua"], quote=True)}" data-en="{html.escape(title["en"], quote=True)}">'
            f'{html.escape(title["ua"])}</h3>\n'
            f'{indent}    <ul class="skill-list">\n{items}\n{indent}    </ul>\n'
            f'{indent}</div>'
        )
    return "\n".join(parts)
