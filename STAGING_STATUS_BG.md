# BAGER SITE LINK — staging GPS v0.3.4

## Реално изпълнено

- Изолиран GitHub клон `staging/gps-v034-validation`.
- Качен GPS модул `static/gps-v03.mjs` (commit `cd431f05f210683b660c134a6e4d2eb18155e91a`); не е изпълнен CI тест върху staging commit.
- Сървърно GPS hardening в `app/main.py`, commit `67f4b5c75f1e2fbd40a76a931d9e08e2bdf3cd6b`: ограничение на `device_event_id`, защита от чужд идентификатор и правилно съотнасяне на офлайн точки към смяна.
- Локалният архив v0.3.4 премина 34 JavaScript и 4 Python API теста; това НЕ е проверка на GitHub клона.

## Оставащи липсващи в GitHub клона файлове от v0.3.4

- `static/gps-reliability.mjs`
- `static/field-command.js`
- `static/field-command.css`
- `tests/test_gps_integrity.py`

Клиентските `static/app.js` и `templates/app.html` също още не са синхронизирани с пакета v0.3.4. Следователно staging клонът НЕ е пълен release кандидат и не бива да се внедрява.

## Правила

- Не променяйте `main` или продукционната база.
- Преди Render staging: синхронизирайте всички файлове, изпълнете тестове върху същия commit, осигурете отделна база и проверете настройките за секрети.
