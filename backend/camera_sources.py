"""Exact configured RTSP gateway IPs; no arbitrary URL fetching or DNS rebinding."""
import json,ipaddress
from urllib.parse import urlsplit
def validate_sources(raw):
    try:
        sources=json.loads(raw)
        if not isinstance(sources,dict) or len(sources)>20: raise ValueError()
        for key,value in sources.items():
            if not isinstance(key,str) or not 1<=len(key)<=100 or not isinstance(value,str): raise ValueError()
            parsed=urlsplit(value)
            if parsed.scheme not in ('rtsp','rtsps') or not parsed.hostname or parsed.fragment: raise ValueError()
            # Literal IPs prevent a second DNS lookup from changing the destination.
            addr=ipaddress.ip_address(parsed.hostname)
            if addr.is_loopback or addr.is_link_local or addr.is_multicast or addr.is_unspecified: raise ValueError()
            if parsed.port is not None and not 1<=parsed.port<=65535: raise ValueError()
        return sources
    except (ValueError,TypeError):
        raise ValueError('Camera sources require exact RTSP(S) gateway URLs with literal, non-metadata IP addresses; DNS names and HTTP redirects are not supported') from None
