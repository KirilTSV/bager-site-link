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
