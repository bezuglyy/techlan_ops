# Techlan ARM

Кастомная интеграция для [Home Assistant](https://www.home-assistant.io) · версия **0.4.0**.

![icon](custom_components/techlan_ops/brand/icon.png)

| | |
|---|---|
| Домен | `techlan_ops` |
| Версия | 0.4.0 |
| Тип | custom integration |

## Описание

Управление охранно-пожарной системой Болид ServerSkif (Techlan ARM).

## Возможности

- Бинарные датчики (движение, контакты и т.п.)
- Кнопки и действия
- Сенсоры и мониторинг состояния
- Переключатели и вкл/выкл устройства

## Установка

1. Скопируйте папку `custom_components/{domain}/` в каталог `custom_components/` конфигурации Home Assistant.
2. Перезапустите Home Assistant.
3. Настройки → Устройства и службы → Добавить интеграцию → **{mname}**.

> Установка через HACS: добавьте репозиторий `https://github.com/bezuglyy/{repo}` как Custom repository (категория Integration).

## Лицензия

MIT
