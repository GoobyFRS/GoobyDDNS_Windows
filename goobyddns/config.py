"""Configuration and validation helpers for the GoobyDDNS desktop client."""

import configparser
import ipaddress
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "GoobyDDNS"
CONFIG_NAME = "running_config.ini"
TEMPLATE_NAME = "template.ini"

@dataclass(frozen=True)
class DNSConfig:
    """Runtime configuration for a Linode DNS record update.
    Attributes:
        linode_api_key: API token used to authenticate to Linode.
        linode_api_version: API version suffix used in URLs.
        domain_record_id: Parent domain record ID for the DNS zone.
        subdomain_record_id: Subdomain record ID to update.
        fqdn: Fully qualified domain name that should be refreshed.
    """

    linode_api_key: str | None
    linode_api_version: str
    domain_record_id: str | None
    subdomain_record_id: str | None
    fqdn: str

def get_base_path() -> Path:
    """Return the repository root used for default templates and resources.
    Returns:
        Path: The project root directory.
    """
    return Path(__file__).resolve().parents[1]

def get_default_config_directory() -> Path:
    """Return the user-level configuration directory for GoobyDDNS.
    Returns:
        Path: The directory where runtime configuration is stored.
    """
    app_data = os.environ.get("APPDATA")
    if app_data:
        return Path(app_data) / APP_NAME
    return Path.home() / ".config" / APP_NAME

def is_valid_ip_address(value: str | None) -> bool:
    """Check whether a value is a valid IPv4 or IPv6 address.
    Args:
        value: The candidate IP text to validate.
    Returns:
        bool: True when the value is a valid IP address; otherwise False.
    """
    if value is None:
        return False

    candidate = value.strip()
    if not candidate:
        return False

    try:
        ipaddress.ip_address(candidate)
        return True
    except ValueError:
        return False

def validate_fqdn(value: str | None) -> str:
    """Normalize and validate a fully qualified domain name.
    Args:
        value: FQDN string to validate.
    Returns:
        str: A normalized lowercase domain name without a trailing dot.
    Raises:
        ValueError: If the hostname is missing, malformed, or contains invalid labels.
    """
    if value is None:
        raise ValueError("FQDN is required.")

    hostname = value.strip().lower()
    if not hostname:
        raise ValueError("FQDN cannot be empty.")
    if hostname.endswith("."):
        hostname = hostname[:-1]
    if len(hostname) > 253:
        raise ValueError("FQDN is too long.")

    labels = hostname.split(".")
    if len(labels) < 2:
        raise ValueError("FQDN must include a hostname and domain.")

    for label in labels:
        if not label or len(label) > 63:
            raise ValueError("FQDN contains an invalid label.")
        if label.startswith("-") or label.endswith("-"):
            raise ValueError("FQDN labels may not start or end with a hyphen.")

        allowed_characters = set("abcdefghijklmnopqrstuvwxyz0123456789-")
        if any(character not in allowed_characters for character in label):
            raise ValueError("FQDN contains unsupported characters.")

    return hostname

def _coerce_config_value(value):
    """Normalize a configuration value from an environment or INI file.
    Args:
        value: The raw string value to clean.
    Returns:
        str | None: A stripped value, or None if the field resolves to empty text.
    """
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None

def _read_config_parser(config_path: Path) -> configparser.ConfigParser:
    """Read a config file while tolerating common UTF encodings.
    Args:
        config_path: Location of the configuration file.
    Returns:
        configparser.ConfigParser: A parser instance containing any decoded settings.
    """
    parser = configparser.ConfigParser()
    if not config_path.exists():
        return parser

    raw = config_path.read_bytes()
    encodings = ["utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "utf-8"]

    for encoding in encodings:
        try:
            parsed_text = raw.decode(encoding)
            parser.read_string(parsed_text)
            return parser
        except (UnicodeDecodeError, configparser.Error):
            continue

    return parser

def ensure_config_file(config_path: Path | None = None) -> Path:
    """Ensure the runtime config exists and return its absolute path.
    Args:
        config_path: Optional explicit path for the configuration file.
    Returns:
        Path: The resolved path to the runtime config.
    """
    config_directory = config_path.parent if config_path else get_default_config_directory()
    config_directory.mkdir(parents=True, exist_ok=True)

    resolved_config_path = config_path or config_directory / CONFIG_NAME
    template_path = get_base_path() / TEMPLATE_NAME

    if not resolved_config_path.exists() and template_path.exists():
        shutil.copy2(template_path, resolved_config_path)

    return resolved_config_path

def load_runtime_config(config_path: Path | None = None) -> DNSConfig:
    """Load the current runtime configuration from the environment and INI file.
    Args:
        config_path: Optional path to the INI file instead of the default config directory.
    Returns:
        DNSConfig: A validated configuration object ready for runtime use.
    """
    resolved_config_path = ensure_config_file(config_path) if config_path else ensure_config_file()
    parser = _read_config_parser(resolved_config_path)

    linode_api_key = _coerce_config_value(
        os.environ.get("LINODE_API_KEY", parser.get("linode", "LINODE_API_KEY", fallback=None)))
    linode_api_version = _coerce_config_value(
        os.environ.get("LINODE_API_VERSION", parser.get("linode", "LINODE_API_VERSION", fallback="v4"))
    ) or "v4"
    domain_record_id = _coerce_config_value(
        os.environ.get("DOMAIN_RECORD_ID", parser.get("linode", "DOMAIN_RECORD_ID", fallback=None)))
    subdomain_record_id = _coerce_config_value(
        os.environ.get("SUBDOMAIN_RECORD_ID", parser.get("linode", "SUBDOMAIN_RECORD_ID", fallback=None)))

    fqdn_value = _coerce_config_value(
        os.environ.get("FQDN", parser.get("dns", "FQDN", fallback="unknown"))
    ) or "unknown"
    try:
        fqdn = validate_fqdn(fqdn_value)
    except ValueError:
        fqdn = "unknown"

    return DNSConfig(
        linode_api_key=linode_api_key,
        linode_api_version=linode_api_version,
        domain_record_id=domain_record_id,
        subdomain_record_id=subdomain_record_id,
        fqdn=fqdn,)

def save_runtime_config(configuration: DNSConfig, config_path: Path | None = None) -> Path:
    """Persist a DNSConfig object to the configured INI file.
    Args:
        configuration: Runtime configuration to write.
        config_path: Optional override target file path.
    Returns:
        Path: The path to the saved config file.
    """
    fqdn = validate_fqdn(configuration.fqdn)
    resolved_config_path = ensure_config_file(config_path) if config_path else ensure_config_file()
    config_parser = configparser.ConfigParser()
    config_parser["linode"] = {
        "LINODE_API_KEY": configuration.linode_api_key or "",
        "LINODE_API_VERSION": configuration.linode_api_version or "v4",
        "DOMAIN_RECORD_ID": configuration.domain_record_id or "",
        "SUBDOMAIN_RECORD_ID": configuration.subdomain_record_id or "",
    }
    config_parser["dns"] = {
        "FQDN": fqdn,
    }
    with resolved_config_path.open("w", encoding="utf-8") as config_file:
        config_parser.write(config_file)
    return resolved_config_path
