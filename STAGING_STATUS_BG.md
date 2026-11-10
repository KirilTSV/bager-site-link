# BAGER SITE LINK — staging GPS validation

## Доказани GitHub действия
- Отделен клон `staging/gps-v034-validation`, без промени в `main`.
- Сървърна GPS защита в `app/main.py`: ограничение на event ID, проверка за собственост, отнасяне на закъснели точки по времето на смяната.
- Добавен автентикиран `GET /api/shift/status` (commit `360fee18bca3d42ff45343ccfcbfa5076cddce2c`).
- Качен `static/gps-v03.mjs` (commit `cd431f05f210683b660c134a6e4d2eb18155e91a`).
- Качени регресионни тестове `tests/gps-event-id.test.mjs`, `tests/gps-hardening.test.mjs`, `tests/test_gps_integrity.py`, `tests/test_shift_status.py` и изолиран тестов стартер `tests/run_isolated.py`.
- Създаден GitHub Actions workflow `.github/workflows/gps-staging.yml` (commit `98425c2cff7fc4af25839050f8f8b095974a4e68`).

## Проверки и ограничения
- На локалния пакет v0.3.4: 34/34 JavaScript теста преминаха; Python изолираните тестове преминаха (отделни процеси и бази).
- **Не е потвърдено**, че GitHub Actions workflow е стартирал или преминал на конкретния staging commit.
- Клиентският код от v0.3.4 **не е напълно синхронизиран**. Остават `static/gps-reliability.mjs`, `static/field-command.js`, `static/field-command.css`, съответните актуализации на `static/app.js` и `templates/app.html` и пълният комплект JS тестове.
- Поради това staging клонът **не е готов за Render deployment**.
- Не е проверяван реален PostgreSQL или Android GPS.

## Задължителен следващ gate
1. Синхронизиране на оставащите файлове от v0.3.4.
2. Сравнение на staging commit с архивния кандидат.
3. Положителен GitHub Actions резултат за същия commit.
4. Едва след това отделна Render база и услуга, без достъп до production DB.

## Синхронизация — 10.11.2026, следващ етап

- `static/field-command.js` качен (commit `210c05adf8afa098a1e729ef613979d4d528ea82`). Това е самостоятелен GPS диагностичен панел; **не е идентичен по байтове** с локалния архив v0.3.4.
- `static/field-command.css` качен (commit `3ac1dfd3b871e3e2cd219e430ef8ad60a0da5d7e`). Също не е байтово идентичен с локалния архив.
- **Блокери:** липсва `static/gps-reliability.mjs`; не са синхронизирани `static/app.js` и `templates/app.html`; няма потвърден CI резултат върху крайния commit; няма браузърен/Android тест.
- **Не се допуска Render deployment** преди пълно свързване и потвърдени тестове. Няма промяна в `main`.

## 10.11.2026 — реално свързване на GPS UI

- `static/app.js` интегрира `GpsEngineV03` + `IndexedGpsStore`, възстановява GPS при активна смяна и опитва синхронизация при възстановяване на връзката; commit `2e081b1edd74b263e407d75d86d5497cc8c208e0`.
- `templates/app.html` зарежда Field Command CSS и JS; commit `85bfd14d7a4d64e44494259522638922d120abd9`.
- `tests/gps-wiring.test.mjs` проверява статично връзките; GitHub Actions workflow включва теста (commit `d7d73ce28ed809a36b50414623b2c27b2ef3dc4b`).
- Прочетени обратно от GitHub и проверени като текст: `static/app.js`, `templates/app.html`, `static/field-command.js`, `static/field-command.css`, `static/gps-v03.mjs`.
- **Все още липсва** `static/gps-reliability.mjs` от локалния архив; v0.3 GPS двигателят не го импортира пряко, но пълна байтова синхронизация с v0.3.4 не е постигната.
- **Няма потвърден зелен GitHub Actions run за крайния commit**. Не са проведени браузърни, Android или PostgreSQL тестове. Следователно staging НЕ е готов за Render.

## Инженерен одит — 10.11.2026

- Коригирана миграция на legacy GPS queue в `static/app.js`: при невалиден запис оригиналната опашка се запазва, вместо да се изтрива (commit `a01e58efd748c45b4862a94d841b724ef5795eb0`).
- Коригирана `tests/test_pilot_flow.py`, така че да не подменя изолирания `DATABASE_URL` (commit `e3168adc97f80c0b1ae2908e7c7cb20013642300`).
- Изпълнени тестове на **локалния архив**, а не на крайния GitHub commit: 34/34 JS, локални Python API тестове успешни.
- GitHub API за workflow runs по commit `e3168adc97f80c0b1ae2908e7c7cb20013642300` върна празен списък. Това API филтрира само pull-request-triggered runs и **не доказва**, че push workflow не е стартирал.
- Няма мрежов достъп от работния контейнер до github.com за clone, затова **не може да се потвърди изпълнение на пълния staging tree** в този контейнер.
- Няма разрешение да се декларира 100% готовност без staging интеграционни и реални Android проверки. Production не е променяна.

## Инженерна верификация — 10.11.2026 (текуща сесия)

**Локален архив:** `BAGER_SITE_LINK_V034_GPS_INTEGRITY.zip` (извлечен в изолирана работна директория). Реално изпълнени команди:

- `node --test tests/*.test.mjs tests/gps/*.test.mjs` → **34/34 passed**.
- `python tests/run_isolated.py` → **2 + 1 + 1 = 4 passed** в отделни SQLite тестови бази.
- SHA-256 на локалния архив: `static/gps-v03.mjs` = `34bc1206bb692554bcb5a6f29aab23fee4eded6d51cdb3b4f52b31dc3872ee23`; `static/gps-reliability.mjs` = `0b220f187d89134c2cd48b7f05abd74146dc989c5c5e13f228c36371ad7db729`.

**Извършени нови промени в staging:**

- GitHub Actions проверява синтаксиса на `app.js`, `field-command.js`, `gps-v03.mjs`, `sw.js` чрез `node --check` (commit `14f72a1e3b0e2234570554f1f390000ffa855b97`).
- Legacy GPS миграцията открива повтарящи се event ID, за да избегне тихо презаписване на точки (commit `0814ccdda9882fadfaca913424f73c0d17a2c581`).

**Строги ограничения:** тестовете са върху локалния архив, **не върху текущия GitHub commit**. В staging още няма доказано успешен GitHub Actions run, няма потвърдена реална PostgreSQL интеграция, няма браузърен и Android полеви тест. Няма нов Render deployment и няма промени в `main`. До доказване на тези условия не се декларира release-ready статус.
