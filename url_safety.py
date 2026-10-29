"""Basic SSRF guard for URLs opened by the research reader tool.

This rejects non-HTTP(S) URLs, embedded credentials, and hosts resolving to
non-public IP addresses. Each redirect target must be checked independently.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit


def validate_public_http_url(url: str) -> str:
    """Return a normalized public HTTP(S) URL or raise ValueError.

    DNS answers are checked before a request is made. This is defense in depth,
    not a substitute for network-level egress restrictions against DNS rebinding.
    """
    if not isinstance(url, str) or not url or len(url) > 2048:
        raise ValueError("Provide a valid URL no longer than 2048 characters.")

    try:
        parsed = urlsplit(url.strip())
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError("The URL is malformed.") from exc

    if scheme not in ("http", "https"):
        raise ValueError("Only public HTTP and HTTPS URLs are allowed.")
    if not hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("The URL must have a hostname and must not contain credentials.")

    hostname = hostname.rstrip(".")
    if not hostname:
        raise ValueError("The URL hostname is invalid.")

    effective_port = port or (443 if scheme == "https" else 80)
    try:
        address = ipaddress.ip_address(hostname)
        addresses = [address]
    except ValueError:
        try:
            records = socket.getaddrinfo(hostname, effective_port, type=socket.SOCK_STREAM)
        except (OSError, UnicodeError) as exc:
            raise ValueError("The URL hostname could not be resolved.") from exc
        addresses = []
        for record in records:
            try:
                addresses.append(ipaddress.ip_address(record[4][0]))
            except (ValueError, IndexError):
                continue

    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("URLs must resolve only to public IP addresses.")

    # Remove fragments; they are client-side and never sent to the server.
    return urlunsplit((scheme, parsed.netloc, parsed.path or "/", parsed.query, ""))
