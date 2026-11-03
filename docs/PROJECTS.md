# Проєкти на сайті: як це працює

Сайт хоститься на **GitHub Pages** (безкоштовно), деплой робить GitHub Actions.
Розділ «Проєкти» читає `projects.json`, який збирається при кожному деплої з двох джерел:

| Джерело | Де лежить | Як змінюється |
|---|---|---|
| Ручні проєкти (з фото, галереєю) | `data/projects.manual.json`, фото в `images/` | кнопка **«+ Додати проєкт»** на сайті або правка JSON |
| Репозиторії GitHub | `data/approved/<repo>.json` (лише `{"repo": "..."}`) | автоматично через Pull Request |

## Позначити репозиторій для сайту
1. На сторінці репозиторію GitHub натисни ⚙ біля **About** і додай тему (topic) **`portfolio`**.
2. Протягом ≤3 годин (або вручну: Actions → *Propose new projects* → Run workflow) у цьому репозиторії з'явиться Pull Request
   **«Додати на сайт: …»** з прев'ю картки. GitHub надішле сповіщення (пошта / мобільний застосунок GitHub).
3. **Merge** - проєкт з'явиться на сайті за 1-2 хв. **Close** - відхилено (його більше не пропонуватимуть; передумала - Reopen + Merge).

Після підтвердження все синхронізується саме:
* змінила опис репозиторію або README → короткий опис, теги і дата «Оновлено» оновляться (щодня вночі або після будь-якого пушу в цей репозиторій);
* видалила репозиторій або зняла тему `portfolio` → проєкт зникає з сайту.

Короткий опис = опис репозиторію (About) або перший абзац README (до 180 символів). Повний опис на сторінці проєкту = перші 2 абзаци README.
Щоб задати свій текст/назву/обкладинку/двомовність, відредагуй `data/approved/<repo>.json`:
```json
{
  "repo": "MNJMARIA/my-project",
  "title":       {"ua": "Назва", "en": "Title"},
  "summary":     {"ua": "Коротко", "en": "Short"},
  "description": {"ua": "Довгий опис", "en": "Long description"},
  "cover": "images/my-project.jpg",
  "gallery": ["images/a.jpg", "images/b.jpg"]
}
```

## Кнопка «Додати проєкт» (тільки для власниці)
1. Створи токен: GitHub → Settings → Developer settings → Fine-grained tokens → *Generate new token*:
   Repository access = **Only select repositories → personal_website**, Permissions → **Contents: Read and write**. Термін дії - до 1 року.
2. Відкрий `https://<твій-сайт>/#admin`, встав токен. Він зберігається лише в цьому браузері; без нього кнопки немає.
3. «+ Додати проєкт» → назва, опис, технології, головне фото й додаткові → **Зберегти**.
   Фото стискаються в браузері, усе потрапляє в репозиторій одним комітом, сайт оновлюється за 1-2 хв.

## Одноразове налаштування репозиторію
1. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
2. **Settings → Actions → General → Workflow permissions:** *Read and write permissions* і галочка
   **Allow GitHub Actions to create and approve pull requests**.
3. Запусти *Deploy site to GitHub Pages* вручну (Actions → Run workflow). Адреса: `https://<user>.github.io/personal_website/`
   (якщо перейменувати репозиторій на `<user>.github.io`, адреса буде `https://<user>.github.io/`).
4. Коли новий сайт перевірено - Netlify можна вимкнути.

Примітка: GitHub вимикає заплановані workflow у публічних репозиторіях без активності ~60 днів - тоді просто натисни *Enable workflow* на вкладці Actions.
