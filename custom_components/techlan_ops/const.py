from __future__ import annotations

from ._shared.shared_const import (
    ALARM_STATE_CODES,
    ARM_CONFIRM_CODES,
    ARMED_CODES,
    ATTR_PKU,
    CONF_ARM_ID,
    CONF_BASE_URL,
    CONF_COMMAND_TIMEOUT,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_SELECTED_LOOPS,
    CONF_WS_PATH,
    CONFIRM,
    DEFAULT_ARM_ID,
    DEFAULT_BASE_URL,
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WS_PATH,
    DISARM_CONFIRM_CODES,
    DISARMED_CODES,
    STATE_NAMES,
)

DOMAIN = "techlan_ops"
PLATFORMS = ["sensor", "binary_sensor", "switch"]

# Версия схемы config entry: minor обновляется при миграциях (async_migrate_entry).
CONFIG_MINOR_VERSION = 3

# Версия интеграции (синхронизировать с manifest.json).
INTEGRATION_VERSION = "0.6.2"

# Идентификатор и параметры родительского устройства.
PARENT_IDENTIFIER = "arm_ops"
DEVICE_NAME = "SecurARM"
DEVICE_MODEL = "SecurARM Сервер"
