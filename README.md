# SecurARM
![Release](https://img.shields.io/github/v/release/bezuglyy/techlan_ops?label=Release&style=flat-square) ![HACS](https://img.shields.io/badge/HACS-Custom%20Repository-purple?style=flat-square) ![License](https://img.shields.io/github/license/bezuglyy/techlan_ops?style=flat-square) ![HA](https://img.shields.io/badge/HA-2025.1%2B-2ea44f?style=flat-square)
Кастомная интеграция для [Home Assistant](https://www.home-assistant.io) · версия **0.6.2**.
![icon](custom_components/techlan_ops/brand/icon.png)
| | |
|---|---|
| Домен | `techlan_ops` |
| Версия | 0.6.2 |
| Тип | custom integration |
## Описание
Управление охранно-пожарной системой Болид ServerSkif (**SecurARM**). Отображаемое имя интеграции — **SecurARM**; домен `techlan_ops` и `entity_id` не меняются.
### Возможности
- Бинарные датчики (движение, контакты и т.п.)
- Кнопки и действия
- Сенсоры и мониторинг состояния
- Переключатели и вкл/выкл устройства
### Изменения 0.6.2
- 🖼️ **Фирменный знак SecurARM** (щит с шестернёй и замком, логотип автора) в `brand/` — icon/logo + тёмные варианты и `@2x`.
### Изменения 0.6.1
- 🏷️ **Переименование в SecurARM:** отображаемое имя интеграции и устройств — **SecurARM** (сервер ОПС SecurARM Server), обновлены логотипы/иконки (`brand/`, вордмарк **SECURARM**).
- ⚠️ Домен `techlan_ops`, `unique_id` и все `entity_id` **не изменены** — история и автоматизации сохраняются.
### Изменения 0.6.0
- **Постоянное WebSocket-соединение** с реконнектом (backoff 1→30 с), keepalive и лимитами — меньше нагрузки на ServerSkif.
- **Подтверждение команд:** после взятия/снятия ждём состояние 24/109 в пределах таймаута (по умолчанию 30 с), 1 ретрай; ошибки — понятным текстом.
- **HA-события** `techlan_ops_state_changed` и `techlan_ops_alarm` для автоматизаций.
- Расширенная **диагностика** (маскирует секреты), **Repairs**, enum-классы, миграция схемы (minor 3, опция `command_timeout`).
- Новый **фирменный брендинг** (светлая/тёмная тема).
### Установка
1. Скопируйте папку `custom_components/techlan_ops/` в каталог `custom_components/` конфигурации Home Assistant.
2. Перезапустите Home Assistant.
3. Настройки → Устройства и службы → Добавить интеграцию → **SecurARM**.
> Установка через HACS: добавьте репозиторий `https://github.com/bezuglyy/techlan_ops` как Custom repository (категория Integration).
---
## Description
Control of the Bolide ServerSkif fire/security system (**SecurARM**). The integration display name is **SecurARM**; the domain `techlan_ops` and all `entity_id`s are unchanged.
### Features
- Binary sensors (motion, contacts, etc.)
- Buttons and actions
- Sensors and state monitoring
- Switches and on/off controls
### Installation
1. Copy the `custom_components/techlan_ops/` folder into the `custom_components/` directory of your Home Assistant configuration.
2. Restart Home Assistant.
3. Settings → Devices & Services → Add Integration → **SecurARM**.
> HACS: add `https://github.com/bezuglyy/techlan_ops` as a Custom repository (category Integration).
---
**Автор / Author:**
![Bezuglyj E.N.](logo-bezuglyj.png)
## License / Лицензия
MIT
