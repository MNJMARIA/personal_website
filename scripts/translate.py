"""Безкоштовний офлайн-переклад UA <-> EN для описів проєктів (Argos Translate, ліцензія MIT/CC0).

* Нічого не відправляється стороннім сервісам, ключі й ліміти не потрібні.
* Переклад робиться лише тоді, коли тексту ще немає в кеші (.cache/translations.json),
  тому звичайні деплої швидкі. Кеш і моделі зберігає actions/cache у workflow.
* Якщо переклад недоступний (помилка встановлення, мережа), збірка НЕ падає:
  просто лишається оригінальний текст для обох мов.
* Вимкнути: змінна середовища TRANSLATE=off.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_FILE = ROOT / ".cache" / "translations.json"
CODES = {"ua": "uk", "en": "en"}


def detect(text):
    """'ua', якщо в тексті більше кирилиці, ніж латиниці, інакше 'en'."""
    cyr = len(re.findall(r"[А-Яа-яІіЇїЄєҐґ]", text))
    lat = len(re.findall(r"[A-Za-z]", text))
    return "ua" if cyr > lat else "en"


class Translator:
    def __init__(self):
        self.enabled = os.environ.get("TRANSLATE", "on").lower() != "off"
        self.cache = {}
        self.dirty = False
        self.backend_ready = None   # None - ще не пробували, True/False - результат
        self.warned = False
        if CACHE_FILE.exists():
            try:
                self.cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                self.cache = {}

    # ---- кеш ----
    @staticmethod
    def _key(text, src, dst):
        return hashlib.sha1(f"{src}>{dst}\n{text}".encode("utf-8")).hexdigest()

    def save(self):
        if self.dirty:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(json.dumps(self.cache, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- бекенд (Argos) ----
    def _warn(self, msg):
        if not self.warned:
            print(f"WARN: переклад недоступний ({msg}); лишаю оригінальний текст для обох мов")
            self.warned = True

    def _pip(self, *args):
        base = [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check"]
        try:
            subprocess.check_call(base + list(args), timeout=1200)
        except Exception:
            subprocess.check_call(base + ["--break-system-packages"] + list(args), timeout=1200)

    def _ensure_backend(self):
        if self.backend_ready is not None:
            return self.backend_ready
        try:
            try:
                import argostranslate.translate  # noqa: F401
            except ImportError:
                print("INFO: встановлюю Argos Translate (одноразово, 1-3 хв)…")
                try:  # CPU-версія torch значно легша за стандартну
                    self._pip("torch", "--index-url", "https://download.pytorch.org/whl/cpu")
                except Exception as err:
                    print(f"INFO: CPU-torch не встановився ({err}), пробую стандартний")
                self._pip("argostranslate")
            self.backend_ready = True
        except Exception as err:
            self._warn(f"не вдалося встановити Argos: {err}")
            self.backend_ready = False
        return self.backend_ready

    def _ensure_pair(self, src, dst):
        import argostranslate.package as pkg
        import argostranslate.translate as tr
        a, b = CODES[src], CODES[dst]

        def installed():
            langs = tr.get_installed_languages()
            fa = next((l for l in langs if l.code == a), None)
            fb = next((l for l in langs if l.code == b), None)
            return bool(fa and fb and fa.get_translation(fb))

        if installed():
            return True
        print(f"INFO: завантажую модель перекладу {a}->{b}…")
        pkg.update_package_index()
        package = next((p for p in pkg.get_available_packages() if p.from_code == a and p.to_code == b), None)
        if not package:
            raise RuntimeError(f"немає моделі {a}->{b}")
        pkg.install_from_path(package.download())
        return installed()

    def _argos(self, text, src, dst):
        import argostranslate.translate as tr
        return tr.translate(text, CODES[src], CODES[dst])

    # ---- публічний інтерфейс ----
    def translate(self, text, src, dst):
        """Переклад тексту (абзаци зберігаються) або None, якщо переклад недоступний."""
        text = (text or "").strip()
        if not text:
            return text
        if not self.enabled:
            return None
        key = self._key(text, src, dst)
        if key in self.cache:
            return self.cache[key]
        if not self._ensure_backend():
            return None
        try:
            self._ensure_pair(src, dst)
            parts = [p for p in re.split(r"\n\s*\n", text)]
            out = "\n\n".join(self._argos(p, src, dst).strip() if p.strip() else p for p in parts)
        except Exception as err:
            self._warn(str(err))
            self.backend_ready = False
            return None
        if out:
            self.cache[key] = out
            self.dirty = True
        return out or None

    def bilingual(self, ua_text, en_text):
        """Для пари, де обидва тексти однакові (автоматичний опис): повертає (ua, en) з перекладом."""
        text = ua_text or en_text or ""
        if not text.strip():
            return ua_text, en_text
        src = detect(text)
        dst = "en" if src == "ua" else "ua"
        other = self.translate(text, src, dst)
        if not other:
            return ua_text, en_text
        return (text, other) if src == "ua" else (other, text)


def translate_project(project, tr):
    """Дописує відсутню мову в summary / description / features автоматичних проєктів."""
    for key in ("summary", "description"):
        value = project.get(key)
        if value and value.get("ua") == value.get("en") and value.get("ua"):
            value["ua"], value["en"] = tr.bilingual(value["ua"], value["en"])
    feats = project.get("features")
    if feats and feats.get("ua") == feats.get("en") and feats.get("ua"):
        ua, en = [], []
        for item in feats["ua"]:
            u, e = tr.bilingual(item, item)
            ua.append(u)
            en.append(e)
        feats["ua"], feats["en"] = ua, en
