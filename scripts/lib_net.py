#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time, hashlib, re, urllib.parse as up
from typing import Optional, Tuple, Dict, Any, Iterable
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA = "regg92s-marketbot/1.0"

def build_session(timeout_connect: float = 2.0, timeout_read: float = 3.0,
                  total_retries: int = 3, backoff: float = 0.8) -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    retries = Retry(
        total=total_retries,
        backoff_factor=backoff,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))

    # pakker timeouts inn i session objektet via helper
    s.request_timeout = (timeout_connect, timeout_read)  # type: ignore[attr-defined]
    return s

def _strip_tracking(url: str) -> str:
    parts = up.urlsplit(url)
    q = up.parse_qsl(parts.query, keep_blank_values=True)
    q = [(k,v) for (k,v) in q if not re.match(r'^(utm_|gclid|fbclid|igshid|mc_cid|mc_eid)', k, re.I)]
    return up.urlunsplit((parts.scheme, parts.netloc, parts.path, up.urlencode(q), ""))

def normalize_url(url: str) -> str:
    url = url.strip()
    url = _strip_tracking(url)
    url = url.replace("http://", "https://")
    # fjern trailing slash på path hvis ikke bare '/'
    parts = up.urlsplit(url)
    path = parts.path
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return up.urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))

def normalize_title(t: str) -> str:
    return re.sub(r'\s+', ' ', t or "").strip().lower()

def dedup_news(items: Iterable[Dict[str, Any]]) -> list[Dict[str, Any]]:
    seen = set()
    out = []
    for it in items:
        t = normalize_title(it.get("title",""))
        u = normalize_url(it.get("url",""))
        ts = it.get("timestamp_iso","")
        key = (t, u, ts)
        if key in seen: continue
        seen.add(key); out.append(it)
    return out

def fetch_first_ok(session: requests.Session, urls: Iterable[str],
                   etag: Optional[str] = None, lastmod: Optional[str] = None) -> Tuple[Optional[bytes], str, Dict[str,str]]:
    """
    Prøver URL-ene i rekkefølge til en lykkes (status 200/304).
    Returnerer (body|None ved 304), brukt_url, headers (ETag/Last-Modified hvis sendt).
    """
    hdrs = {}
    if etag: hdrs["If-None-Match"] = etag
    if lastmod: hdrs["If-Modified-Since"] = lastmod
    last_exc = None
    for u in urls:
        try:
            r = session.get(u, headers=hdrs, timeout=session.request_timeout)  # type: ignore
            if r.status_code == 304:
                return None, u, {
                    "etag": r.headers.get("ETag",""),
                    "last_modified": r.headers.get("Last-Modified",""),
                }
            if 200 <= r.status_code < 300:
                return r.content, u, {
                    "etag": r.headers.get("ETag",""),
                    "last_modified": r.headers.get("Last-Modified",""),
                }
        except Exception as e:
            last_exc = e
            time.sleep(0.2)
    if last_exc:
        raise last_exc
    raise RuntimeError("No URL responded OK")

def choose_first_available_png(session: requests.Session, base_variants: list[str]) -> Optional[str]:
    """
    Gitt flere fullstendige PNG-URL-er (speil eller alternative filer), returner første som svarer 200.
    """
    for u in base_variants:
        try:
            r = session.head(u, timeout=session.request_timeout)  # type: ignore
            if 200 <= r.status_code < 300:
                return u
        except Exception:
            pass
    return None
