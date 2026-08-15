"""Diagnostics helpers used to summarize app and platform configuration."""

from __future__ import annotations

from pathlib import Path

from .config import load_runtime_config
from .platforms import get_platform_adapter

def collect_diagnostics(config_path: Path | None = None) -> dict[str, object]:
    """Collect a summary of the app environment and configuration state.
    Args:
        config_path: Optional override path to the runtime config file.
    Returns:
        dict[str, object]: A dictionary containing platform, config, and connectivity metadata.
    """
    adapter = get_platform_adapter()
    runtime_config = load_runtime_config(config_path)
    environment = adapter.get_runtime_environment()

    return {
        "platform": environment.name,
        "platform_system": environment.platform,
        "config_directory": str(environment.config_directory),
        "config_path": str((config_path or environment.config_directory / "running_config.ini")),
        "supports_tray": adapter.supports_tray(),
        "ui_backend": adapter.get_ui_backend(),
        "fqdn": runtime_config.fqdn,
        "api_key_configured": bool(runtime_config.linode_api_key),
        "dns_record_ids_configured": bool(
            runtime_config.domain_record_id and runtime_config.subdomain_record_id
        ),
    }
