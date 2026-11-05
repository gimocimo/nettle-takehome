"""Webhook URLs are customer-supplied: never let them point the server at its own
network (database, metadata service, internal APIs)."""
import ipaddress
import socket
from urllib.parse import urlparse

from django.conf import settings


class UnsafeWebhookURL(Exception):
    pass


def check_url(url):
    parsed = urlparse(url)
    allow_private = settings.WEBHOOK_ALLOW_PRIVATE_HOSTS
    if parsed.scheme != "https" and not (allow_private and parsed.scheme == "http"):
        raise UnsafeWebhookURL("Webhook URLs must use https.")
    if not parsed.hostname:
        raise UnsafeWebhookURL("Webhook URL has no host.")
    if allow_private:
        return
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(parsed.hostname, parsed.port or 443)}
    except socket.gaierror as exc:
        raise UnsafeWebhookURL(f"Cannot resolve {parsed.hostname}.") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise UnsafeWebhookURL(f"{parsed.hostname} resolves to a non-public address.")
