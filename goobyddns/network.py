"""Network and DNS update helpers for fetching the public IP and updating Linode records."""

import requests

from .config import DNSConfig, is_valid_ip_address

def get_my_wan_ipv4():
    """Return the current public IPv4 address for the machine.
    Returns:
        str | None: The validated public IPv4 address if available; otherwise None.
    """
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=5)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            candidate_ip = payload.get("ip")
        elif isinstance(payload, str):
            candidate_ip = payload
        else:
            candidate_ip = None

        if is_valid_ip_address(candidate_ip):
            return str(candidate_ip).strip()
        return None
    except (requests.RequestException, ValueError, TypeError):
        return None

def update_dns_record(config: DNSConfig, my_public_ip: str) -> bool:
    """Update the configured Linode DNS record with the current public IP.
    Args:
        config: Runtime configuration containing auth and record metadata.
        my_public_ip: Public IPv4 or IPv6 address to publish to DNS.

    Returns:
        bool: True when the Linode API accepted the update; otherwise False.
    """
    if not is_valid_ip_address(my_public_ip):
        return False

    if not config.linode_api_key or not config.domain_record_id or not config.subdomain_record_id:
        return False

    ipv_type = "AAAA" if ":" in my_public_ip else "A"
    url = f"https://api.linode.com/{config.linode_api_version}/domains/{config.domain_record_id}/records/{config.subdomain_record_id}"

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {config.linode_api_key}",
    }

    payload = {
        "target": my_public_ip,
        "name": config.fqdn,
        "type": ipv_type,
        "ttl": 300,
    }

    try:
        response = requests.put(url, headers=headers, json=payload, timeout=10)
        return response.status_code in {200, 201, 202, 204}
    except requests.RequestException:
        return False
