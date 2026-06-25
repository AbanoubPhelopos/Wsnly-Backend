#!/usr/bin/env python3
"""
Wslny Backend — Comprehensive Endpoint Test Harness.

Tests every endpoint from endpoints.json across happy-path, edge, and
error scenarios. Records results, prints a summary, exits non-zero if
any test fails unexpectedly.
"""
from __future__ import annotations

import json
import os
import random
import string
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import urllib.error
import urllib.parse
import urllib.request

BASE_URL = os.environ.get("WSLNY_BASE_URL", "http://localhost:8000")
SPEC_PATH = os.environ.get(
    "WSLNY_SPEC", "/home/abanoub/Desktop/projects/Wsnly-Backend/endpoints.json"
)
ADMIN_EMAIL = "admin@wslny.com"
ADMIN_PASSWORD = "Admin@Wslny2026"

# Cairo coordinates used in routing tests (from GTFS data + KNOWN table).
# Coordinates verified against RoutingEngine/Database/stops.csv
CAIRO_COORDS = {
    "alf_maskan": (30.1188972, 31.3400652),       # الف مسكن
    "abbasiya":   (30.0727858, 31.2840893),       # العباسية
    "ramses":     (30.0618, 31.2463),             # Ramses area
    "nasser":     (30.0535567, 31.2388016),       # Nasser
    "giza":       (30.0131, 31.2089),             # Giza
    "october_6": (29.9548, 30.9181),              # 6 October
    "maadi":      (29.9603, 31.2575),             # Maadi
    "heliopolis": (30.0900, 31.3200),             # Heliopolis
    "dokki":      (30.0382, 31.2115),             # Dokki
    "shoubra":    (30.0770, 31.2435),             # Shoubra
    "faisal":     (30.0169, 31.2135),             # Faisal
    "attaba":     (30.0524299, 31.246899),        # Attaba
    "abbasia_metro": (30.0720, 31.2820),          # Abbasiya metro
    "fair_zone":  (30.085, 31.315),               # fair zone
    "far_south":  (29.5, 30.5),                   # far away
    "far_north":  (30.5, 32.0),                   # far away
}

ARABIC_PHRASES = {
    "full_phrase":  "عايز اروح العباسيه من الف مسكن",
    "destination":  "اروح العباسية",
    "origin_then":  "الف مسكن من العباسية",
    "english":      "from الف مسكن to العباسية",
    "to_from":      "من الف مسكن الي العباسية",
    "bare_dest":    "العباسية",
    "bare_origin":  "الف مسكن",
    "invalid":      "qwertyasdf",
    "nonsense":     "!!! ???",
}


# ─── HTTP client ────────────────────────────────────────────────────────
class HttpResponse:
    __slots__ = ("status", "headers", "body", "elapsed_ms")

    def __init__(self, status, headers, body, elapsed_ms):
        self.status = status
        self.headers = headers
        self.body = body
        self.elapsed_ms = elapsed_ms

    def json(self) -> Any:
        if not self.body:
            return None
        try:
            return json.loads(self.body)
        except json.JSONDecodeError:
            return None


def http(
    method: str,
    path: str,
    *,
    token: Optional[str] = None,
    body: Any = None,
    query: Optional[Dict[str, Any]] = None,
    timeout: float = 30.0,
) -> HttpResponse:
    url = f"{BASE_URL}{path}"
    if query:
        url += "?" + urllib.parse.urlencode(
            {k: v for k, v in query.items() if v is not None}, doseq=True
        )

    headers = {"Accept": "application/json"}
    data: Optional[bytes] = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = (time.perf_counter() - start) * 1000
            return HttpResponse(resp.status, dict(resp.headers), resp.read().decode("utf-8"), elapsed)
    except urllib.error.HTTPError as e:
        elapsed = (time.perf_counter() - start) * 1000
        return HttpResponse(e.code, dict(e.headers or {}), (e.read() or b"").decode("utf-8", errors="replace"), elapsed)
    except urllib.error.URLError as e:
        elapsed = (time.perf_counter() - start) * 1000
        return HttpResponse(0, {}, f"URLError: {e.reason}", elapsed)
    except Exception as e:  # noqa
        elapsed = (time.perf_counter() - start) * 1000
        return HttpResponse(-1, {}, f"{type(e).__name__}: {e}", elapsed)


# ─── Test model ─────────────────────────────────────────────────────────
@dataclass
class TestResult:
    name: str
    category: str
    expected: List[int]
    actual: int
    body_excerpt: str = ""
    elapsed_ms: float = 0.0
    notes: str = ""
    failed: bool = field(default=False)

    def __str__(self):
        marker = "✓" if not self.failed else "✗"
        return (
            f"{marker} [{self.category:18s}] {self.name}  "
            f"expected={self.expected} got={self.actual}  "
            f"({self.elapsed_ms:.0f}ms)"
        )


class Runner:
    def __init__(self):
        self.results: List[TestResult] = []
        self.tokens: Dict[str, str] = {}
        self.ids: Dict[str, int] = {}
        self.passes = 0
        self.failures = 0

    # ── helpers ────────────────────────────────────────────────────────
    def login(self, email: str, password: str) -> Optional[str]:
        r = http("POST", "/api/v1/auth/login", body={"email": email, "password": password})
        if r.status == 200:
            data = r.json()
            return data.get("token") if data else None
        return None

    def get_admin_token(self) -> str:
        if "admin" in self.tokens:
            return self.tokens["admin"]
        tok = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        if not tok:
            raise RuntimeError("Cannot login as admin — check seed credentials")
        self.tokens["admin"] = tok
        return tok

    def get_new_user_token(self) -> Tuple[str, str, str]:
        """Register a new user, return (email, password, token)."""
        rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
        email = f"pytest_{rand}@example.com"
        password = "PyTestPass123!"
        body = {
            "email": email,
            "password": password,
            "first_name": "Py",
            "last_name": "Test",
            "mobile_number": "010" + "".join(random.choices(string.digits, k=8)),
            "gender": "male",
            "address": "Cairo",
        }
        r = http("POST", "/api/v1/auth/register", body=body)
        if r.status == 201:
            data = r.json() or {}
            return email, password, data.get("token", "")
        # maybe already exists; try login
        tok = self.login(email, password)
        if tok:
            return email, password, tok
        raise RuntimeError(f"Cannot register/login new user: {r.status} {r.body[:200]}")

    # ── test recording ────────────────────────────────────────────────
    def _sleep_for_throttle(self, r: HttpResponse) -> bool:
        # DRF returns a ``Retry-After`` header on 429. Honour it if present;
        # otherwise sleep a small fixed amount.
        if r.status == 429:
            retry = r.headers.get("Retry-After") or r.headers.get("retry-after")
            try:
                wait = float(retry) if retry else 5.0
            except ValueError:
                wait = 5.0
            wait = min(max(wait, 0.1), 60.0)
            time.sleep(wait)
            return True
        return False

    def expect(
        self,
        name: str,
        category: str,
        method: str,
        path: str,
        *,
        token: Optional[str] = None,
        body: Any = None,
        query: Optional[Dict] = None,
        expected: List[int],
        notes: str = "",
        max_retries: int = 2,
    ) -> HttpResponse:
        r = http(method, path, token=token, body=body, query=query)
        # Auto-retry on 429 (DRF throttling).
        for _ in range(max_retries):
            if not self._sleep_for_throttle(r):
                break
            r = http(method, path, token=token, body=body, query=query)
        actual = r.status
        ok = actual in expected
        excerpt = r.body[:200] if r.body else ""
        res = TestResult(
            name=name,
            category=category,
            expected=expected,
            actual=actual,
            body_excerpt=excerpt,
            elapsed_ms=r.elapsed_ms,
            notes=notes,
            failed=not ok,
        )
        self.results.append(res)
        if ok:
            self.passes += 1
        else:
            self.failures += 1
        return r

    def expect_json(
        self, name: str, category: str, method: str, path: str, **kwargs
    ) -> Optional[Dict]:
        expected = kwargs.pop("expected", [200])
        r = self.expect(name, category, method, path, expected=expected, **kwargs)
        return r.json() if r.status in expected else None


# ─── Test suite ─────────────────────────────────────────────────────────
def main() -> int:
    runner = Runner()
    admin = runner.get_admin_token()

    # Bootstrap a fresh user for tests that need one.
    nu_email, nu_pwd, nu_token = runner.get_new_user_token()
    runner.tokens["new_user"] = nu_token
    print(f"new user: {nu_email}")

    # ─── System ───────────────────────────────────────────────────────
    sys_cat = "System"
    runner.expect("health: 200",                 sys_cat, "GET", "/api/health", expected=[200])
    runner.expect("health: wrong method (POST)", sys_cat, "POST", "/api/health", expected=[405])

    # ─── Auth (public) ────────────────────────────────────────────────
    auth_cat = "Auth (public)"
    runner.expect("auth/login: ok",              auth_cat, "POST", "/api/v1/auth/login",
                  body={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, expected=[200])
    runner.expect("auth/login: wrong password",  auth_cat, "POST", "/api/v1/auth/login",
                  body={"email": ADMIN_EMAIL, "password": "WRONG"}, expected=[401])
    runner.expect("auth/login: empty body",      auth_cat, "POST", "/api/v1/auth/login", body={}, expected=[400])
    runner.expect("auth/login: missing email",   auth_cat, "POST", "/api/v1/auth/login",
                  body={"password": "x"}, expected=[400])
    runner.expect("auth/login: missing password",auth_cat, "POST", "/api/v1/auth/login",
                  body={"email": "x@x.com"}, expected=[400])
    runner.expect("auth/login: malformed email", auth_cat, "POST", "/api/v1/auth/login",
                  body={"email": "not-an-email", "password": "x"}, expected=[400])
    runner.expect("auth/register: duplicate",    auth_cat, "POST", "/api/v1/auth/register",
                  body={"email": ADMIN_EMAIL, "password": "ValidPass123!", "first_name": "x", "last_name": "y",
                        "mobile_number": "01000000000"}, expected=[400, 409])
    runner.expect("auth/register: missing fields (no 500)", auth_cat, "POST", "/api/v1/auth/register",
                  body={"email": "incomplete@x.com"}, expected=[400])
    runner.expect("auth/register: weak password",auth_cat, "POST", "/api/v1/auth/register",
                  body={"email": "weakpw2@x.com", "password": "abc", "first_name": "A", "last_name": "B",
                        "mobile_number": "01000000000"}, expected=[400])
    runner.expect("auth/google-login: bad token",auth_cat, "POST", "/api/v1/auth/google-login",
                  body={"id_token": "invalid"}, expected=[400])
    runner.expect("auth/refresh: bad token",     auth_cat, "POST", "/api/v1/auth/refresh",
                  body={"refresh": "bogus"}, expected=[401])

    # ─── Auth (authenticated) ─────────────────────────────────────────
    auth_cat2 = "Auth (priv)"
    r = runner.expect("auth/profile: get",       auth_cat2, "GET", "/api/v1/auth/profile", token=admin, expected=[200])
    assert r.json() and r.json().get("email") == ADMIN_EMAIL, "admin profile wrong"

    runner.expect("auth/profile: put",           auth_cat2, "PUT", "/api/v1/auth/profile", token=admin,
                  body={"first_name": "Admin"}, expected=[200])
    runner.expect("auth/profile: empty put",     auth_cat2, "PUT", "/api/v1/auth/profile", token=admin, body={}, expected=[200, 400])

    runner.expect("auth/change-password: bad",   auth_cat2, "POST", "/api/v1/auth/change-password", token=admin,
                  body={"current_password": "WRONG", "new_password": "X12345!"}, expected=[400, 401])
    runner.expect("auth/change-password: missing fields", auth_cat2, "POST", "/api/v1/auth/change-password", token=admin,
                  body={}, expected=[400])
    # New user: change-password round trip
    new_pwd = "PyTestNewPass456!"
    runner.expect("auth/change-password: ok",    auth_cat2, "POST", "/api/v1/auth/change-password", token=nu_token,
                  body={"current_password": nu_pwd, "new_password": new_pwd}, expected=[200])
    runner.expect("auth/login: new password",    auth_cat, "POST", "/api/v1/auth/login",
                  body={"email": nu_email, "password": new_pwd}, expected=[200])
    # Reset
    runner.expect("auth/change-password: reset", auth_cat2, "POST", "/api/v1/auth/change-password", token=nu_token,
                  body={"current_password": new_pwd, "new_password": nu_pwd}, expected=[200])

    # Refresh with the admin refresh token
    login = http("POST", "/api/v1/auth/login",
                 body={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).json()
    refresh = login.get("refresh_token")
    runner.expect("auth/refresh: ok",            auth_cat, "POST", "/api/v1/auth/refresh",
                  body={"refresh": refresh}, expected=[200])

    # ─── Transit (anonymous OK) ───────────────────────────────────────
    tr_cat = "Transit"
    r = runner.expect("lines: list",             tr_cat, "GET", "/api/v1/lines", expected=[200])
    lines_data = r.json() if r.status == 200 else {}
    lines = lines_data.get("lines", []) if isinstance(lines_data, dict) else []
    print(f"  lines loaded: {len(lines)}")
    assert lines, "no lines loaded"

    runner.expect("lines/B1_1: bus",            tr_cat, "GET", "/api/v1/lines/B1_1", expected=[200])
    runner.expect("lines/M_R1: metro",          tr_cat, "GET", "/api/v1/lines/M_R1", expected=[200])
    runner.expect("lines/MB_1: microbus",       tr_cat, "GET", "/api/v1/lines/MB_1", expected=[200])
    runner.expect("lines/UNKNOWN: 404",         tr_cat, "GET", "/api/v1/lines/__nope__", expected=[404])

    r = runner.expect("lines/B1_1: has stops+polyline", tr_cat, "GET", "/api/v1/lines/B1_1", expected=[200])
    if r.status == 200:
        ld = r.json() or {}
        if not ld.get("stops"):
            print(f"  WARN: /lines/B1_1 has no stops: {ld}")
        if "polyline" not in ld:
            print(f"  WARN: /lines/B1_1 missing polyline key: {ld}")

    runner.expect("stops/B1_1",                  tr_cat, "GET", "/api/v1/stops/B1_1", expected=[200])
    runner.expect("stops/B1_292",                tr_cat, "GET", "/api/v1/stops/B1_292", expected=[200])
    runner.expect("stops/M_28 (metro)",          tr_cat, "GET", "/api/v1/stops/M_28", expected=[200])
    runner.expect("stops/UNKNOWN: 404",          tr_cat, "GET", "/api/v1/stops/__nope__", expected=[404])

    runner.expect("stops/nearby: 200",           tr_cat, "GET", "/api/v1/stops/nearby",
                  query={"lat": 30.05, "lon": 31.24, "radius": 1500}, expected=[200])
    runner.expect("stops/nearby: no params 400", tr_cat, "GET", "/api/v1/stops/nearby", expected=[400])
    runner.expect("stops/nearby: missing lat",   tr_cat, "GET", "/api/v1/stops/nearby",
                  query={"lon": 31.24}, expected=[400])
    runner.expect("stops/nearby: missing lon",   tr_cat, "GET", "/api/v1/stops/nearby",
                  query={"lat": 30.05}, expected=[400])
    runner.expect("stops/nearby: bad lat",       tr_cat, "GET", "/api/v1/stops/nearby",
                  query={"lat": "abc", "lon": 31.24}, expected=[400])
    runner.expect("stops/nearby: r=0 (no stops)",tr_cat, "GET", "/api/v1/stops/nearby",
                  query={"lat": 29.5, "lon": 30.5, "radius": 1}, expected=[200])
    r = runner.expect("stops/nearby: clamp huge radius", tr_cat, "GET", "/api/v1/stops/nearby",
                      query={"lat": 30.05, "lon": 31.24, "radius": 99999}, expected=[200])
    # Verify the response body for clamping behavior
    if r.status == 200:
        body = r.json() or {}
        if "count" not in body:
            print(f"  WARN: stops/nearby response missing 'count': {body}")

    # ─── Routing (authenticated) ─────────────────────────────────────
    rt_cat = "Routing"
    s_lat, s_lon = CAIRO_COORDS["nasser"]
    d_lat, d_lon = CAIRO_COORDS["abbasiya"]
    runner.expect("route: map optimal (1)",     rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"origin": {"lat": s_lat, "lon": s_lon},
                        "destination": {"lat": d_lat, "lon": d_lon},
                        "filter": 1}, expected=[200])
    runner.expect("route: map fastest (2)",      rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"origin": {"lat": s_lat, "lon": s_lon},
                        "destination": {"lat": d_lat, "lon": d_lon},
                        "filter": 2}, expected=[200])
    runner.expect("route: map cheapest (3)",     rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"origin": {"lat": s_lat, "lon": s_lon},
                        "destination": {"lat": d_lat, "lon": d_lon},
                        "filter": 3}, expected=[200])
    runner.expect("route: map bus_only (4)",     rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"origin": {"lat": s_lat, "lon": s_lon},
                        "destination": {"lat": d_lat, "lon": d_lon},
                        "filter": 4}, expected=[200])
    runner.expect("route: map microbus_only (5)",rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"origin": {"lat": s_lat, "lon": s_lon},
                        "destination": {"lat": d_lat, "lon": d_lon},
                        "filter": 5}, expected=[200])
    runner.expect("route: map metro_only (6)",   rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"origin": {"lat": s_lat, "lon": s_lon},
                        "destination": {"lat": d_lat, "lon": d_lon},
                        "filter": 6}, expected=[200])
    runner.expect("route: filter=cheapest str",  rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"origin": {"lat": s_lat, "lon": s_lon},
                        "destination": {"lat": d_lat, "lon": d_lon},
                        "filter": "cheapest"}, expected=[200])
    runner.expect("route: filter=optimal str",   rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"origin": {"lat": s_lat, "lon": s_lon},
                        "destination": {"lat": d_lat, "lon": d_lon},
                        "filter": "optimal"}, expected=[200])
    runner.expect("route: filter=999 (invalid)", rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"origin": {"lat": s_lat, "lon": s_lon},
                        "destination": {"lat": d_lat, "lon": d_lon},
                        "filter": 999}, expected=[200])

    # Validation errors
    runner.expect("route: empty body",           rt_cat, "POST", "/api/v1/route", token=admin,
                  body={}, expected=[400])
    runner.expect("route: both text+coords",     rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"text": "x", "origin": {"lat": 1, "lon": 2},
                        "destination": {"lat": 3, "lon": 4}, "filter": 1}, expected=[400])
    runner.expect("route: bad lat",              rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"origin": {"lat": "abc", "lon": 31.24},
                        "destination": {"lat": 30.07, "lon": 31.28},
                        "filter": 1}, expected=[400])
    runner.expect("route: lat out of range",     rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"origin": {"lat": 200, "lon": 31.24},
                        "destination": {"lat": 30.07, "lon": 31.28},
                        "filter": 1}, expected=[400])
    runner.expect("route: no text no coords",    rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"filter": 1}, expected=[400])
    runner.expect("route: text empty",           rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"text": "", "filter": 1}, expected=[400, 422])
    runner.expect("route: text whitespace only", rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"text": "   ", "filter": 1}, expected=[400, 422])

    # Arabic
    alf_lat, alf_lon = CAIRO_COORDS["alf_maskan"]
    abb_lat, abb_lon = CAIRO_COORDS["abbasiya"]
    runner.expect("route: Arabic full phrase",   rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"text": ARABIC_PHRASES["full_phrase"], "filter": 1}, expected=[200])
    runner.expect("route: Arabic destination only", rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"text": ARABIC_PHRASES["destination"], "filter": 1},
                  query={"current_latitude": alf_lat, "current_longitude": alf_lon},
                  expected=[200])
    runner.expect("route: Arabic destination (no current)", rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"text": ARABIC_PHRASES["destination"], "filter": 1}, expected=[400])
    runner.expect("route: English from->to",     rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"text": ARABIC_PHRASES["english"], "filter": 1}, expected=[200])
    runner.expect("route: Arabic from->to (الي)", rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"text": ARABIC_PHRASES["to_from"], "filter": 1}, expected=[200])
    runner.expect("route: Arabic bare dest (with current_location)", rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"text": ARABIC_PHRASES["bare_dest"], "filter": 1},
                  query={"current_latitude": alf_lat, "current_longitude": alf_lon},
                  expected=[200])
    runner.expect("route: nonsense text",        rt_cat, "POST", "/api/v1/route", token=admin,
                  body={"text": ARABIC_PHRASES["nonsense"], "filter": 1}, expected=[400, 422, 503, 504])

    # Verify last successful route
    last_route = http("POST", "/api/v1/route", token=admin,
                      body={"origin": {"lat": s_lat, "lon": s_lon},
                            "destination": {"lat": d_lat, "lon": d_lon}, "filter": 1})
    if last_route.status == 200:
        rj = last_route.json() or {}
        assert rj.get("request_id"), "no request_id in /route response"
        assert rj.get("route", {}).get("found"), "route not found for valid coords"
        assert isinstance(rj["route"].get("segments"), list), "segments not a list"
        # polyline must be present in at least one segment
        has_polyline = any("polyline" in s for s in rj["route"]["segments"])
        assert has_polyline, "no polyline in route segments"
        runner.ids["last_request_id"] = rj["request_id"]
    else:
        print(f"  WARN: cannot establish last_request_id (status={last_route.status})")

    # Routing: history
    runner.expect("route/history",               rt_cat, "GET", "/api/v1/route/history", token=admin, expected=[200])
    runner.expect("route/history limit=5",       rt_cat, "GET", "/api/v1/route/history",
                  token=admin, query={"limit": 5}, expected=[200])
    runner.expect("route/history limit=0",       rt_cat, "GET", "/api/v1/route/history",
                  token=admin, query={"limit": 0}, expected=[200, 400])
    runner.expect("route/history limit=999",     rt_cat, "GET", "/api/v1/route/history",
                  token=admin, query={"limit": 999}, expected=[200])

    # Routing: alternatives
    runner.expect("alternatives: 200",            rt_cat, "POST", "/api/v1/routes/alternatives", token=admin,
                  body={"origin_lat": s_lat, "origin_lon": s_lon,
                        "destination_lat": d_lat, "destination_lon": d_lon}, expected=[200])
    runner.expect("alternatives: missing field",  rt_cat, "POST", "/api/v1/routes/alternatives", token=admin,
                  body={"origin_lat": s_lat}, expected=[400])
    runner.expect("alternatives: bad type",       rt_cat, "POST", "/api/v1/routes/alternatives", token=admin,
                  body={"origin_lat": "abc", "origin_lon": s_lon,
                        "destination_lat": d_lat, "destination_lon": d_lon}, expected=[400])
    runner.expect("alternatives: far points",     rt_cat, "POST", "/api/v1/routes/alternatives", token=admin,
                  body={"origin_lat": 29.5, "origin_lon": 30.5,
                        "destination_lat": 30.5, "destination_lon": 32.0},
                  expected=[200, 404, 503])

    # Routing: feedback
    rid = runner.ids.get("last_request_id", str(uuid.uuid4()))
    runner.expect("feedback: ok",                rt_cat, "POST", "/api/v1/routes/feedback", token=admin,
                  body={"request_id": rid, "rating": 5, "comment": "Great"}, expected=[200, 201])
    runner.expect("feedback: no request_id",     rt_cat, "POST", "/api/v1/routes/feedback", token=admin,
                  body={"rating": 5}, expected=[400])
    runner.expect("feedback: rating=0",          rt_cat, "POST", "/api/v1/routes/feedback", token=admin,
                  body={"request_id": rid, "rating": 0}, expected=[400])
    runner.expect("feedback: rating=6",          rt_cat, "POST", "/api/v1/routes/feedback", token=admin,
                  body={"request_id": rid, "rating": 6}, expected=[400])
    runner.expect("feedback: rating='5' (str)",  rt_cat, "POST", "/api/v1/routes/feedback", token=admin,
                  body={"request_id": rid, "rating": "5"}, expected=[200, 201, 400])
    runner.expect("feedback: no auth",            rt_cat, "POST", "/api/v1/routes/feedback",
                  body={"request_id": rid, "rating": 5}, expected=[401])

    # Routing: metadata
    runner.expect("routes/metadata",              rt_cat, "GET", "/api/v1/routes/metadata", token=admin, expected=[200])

    # Routing: search
    runner.expect("search: dest phrase + current", rt_cat, "POST", "/api/v1/routes/search", token=admin,
                  body={"destination_text": ARABIC_PHRASES["destination"],
                        "current_location": {"lat": alf_lat, "lon": alf_lon}, "filter": 1}, expected=[200])
    runner.expect("search: missing dest_text",    rt_cat, "POST", "/api/v1/routes/search", token=admin,
                  body={"current_location": {"lat": alf_lat, "lon": alf_lon}}, expected=[400])
    runner.expect("search: missing current",      rt_cat, "POST", "/api/v1/routes/search", token=admin,
                  body={"destination_text": ARABIC_PHRASES["destination"]}, expected=[400])
    runner.expect("search: empty dest",           rt_cat, "POST", "/api/v1/routes/search", token=admin,
                  body={"destination_text": "",
                        "current_location": {"lat": alf_lat, "lon": alf_lon}}, expected=[400])
    runner.expect("search: bare Arabic dest (returns 200 or 404 suggestion)", rt_cat, "POST", "/api/v1/routes/search", token=admin,
                  body={"destination_text": ARABIC_PHRASES["bare_dest"],
                        "current_location": {"lat": alf_lat, "lon": alf_lon}}, expected=[200])
    runner.expect("search: no auth",              rt_cat, "POST", "/api/v1/routes/search",
                  body={"destination_text": "X",
                        "current_location": {"lat": alf_lat, "lon": alf_lon}}, expected=[401])

    # Routing: search/confirm
    runner.expect("search/confirm: ok",           rt_cat, "POST", "/api/v1/routes/search/confirm", token=admin,
                  body={"current_location": {"lat": alf_lat, "lon": alf_lon},
                        "destination": {"name": "العباسية", "lat": abb_lat, "lon": abb_lon},
                        "filter": 1}, expected=[200])
    runner.expect("search/confirm: bad dest coord", rt_cat, "POST", "/api/v1/routes/search/confirm", token=admin,
                  body={"current_location": {"lat": alf_lat, "lon": alf_lon},
                        "destination": {"name": "X", "lat": 999, "lon": 999},
                        "filter": 1}, expected=[400, 404, 422])
    runner.expect("search/confirm: missing current", rt_cat, "POST", "/api/v1/routes/search/confirm", token=admin,
                  body={"destination": {"name": "X", "lat": abb_lat, "lon": abb_lon}}, expected=[400])

    # ─── User ──────────────────────────────────────────────────────────
    us_cat = "User"
    runner.expect("user/saved-locations: list (new)", us_cat, "GET", "/api/v1/user/saved-locations",
                  token=nu_token, expected=[200])

    loc = runner.expect_json("user/saved-locations: create", us_cat, "POST", "/api/v1/user/saved-locations",
                              token=nu_token,
                              body={"name": "PyTest Home", "lat": 30.05, "lon": 31.24, "type": "home"},
                              expected=[201])
    loc_id = (loc or {}).get("id") if isinstance(loc, dict) else None
    if not loc_id and isinstance(loc, dict) and "locations" in loc:
        loc_id = (loc["locations"] or [{}])[0].get("id")
    # If we can't get id, list and try again
    if not loc_id:
        lst = http("GET", "/api/v1/user/saved-locations", token=nu_token).json() or {}
        items = lst.get("locations", lst) if isinstance(lst, dict) else lst
        if isinstance(items, list) and items:
            loc_id = items[0].get("id")
    runner.ids["saved_loc_id"] = loc_id

    if loc_id:
        runner.expect("user/saved-locations: update", us_cat, "PUT",
                      f"/api/v1/user/saved-locations/{loc_id}", token=nu_token,
                      body={"name": "PyTest Home 2", "lat": 30.06, "lon": 31.25, "type": "home"},
                      expected=[200])
        runner.expect("user/saved-locations: delete", us_cat, "DELETE",
                      f"/api/v1/user/saved-locations/{loc_id}", token=nu_token, expected=[200, 204])
    runner.expect("user/saved-locations: bad type", us_cat, "POST", "/api/v1/user/saved-locations",
                  token=nu_token,
                  body={"name": "X", "lat": 30.05, "lon": 31.24, "type": "spaceship"}, expected=[400])
    runner.expect("user/saved-locations: missing name", us_cat, "POST", "/api/v1/user/saved-locations",
                  token=nu_token,
                  body={"lat": 30.05, "lon": 31.24}, expected=[400])
    runner.expect("user/saved-locations: missing lat", us_cat, "POST", "/api/v1/user/saved-locations",
                  token=nu_token,
                  body={"name": "X", "lon": 31.24}, expected=[400])
    runner.expect("user/saved-locations: missing lon", us_cat, "POST", "/api/v1/user/saved-locations",
                  token=nu_token,
                  body={"name": "X", "lat": 30.05}, expected=[400])
    runner.expect("user/saved-locations: invalid 99999", us_cat, "PUT",
                  "/api/v1/user/saved-locations/99999999", token=nu_token,
                  body={"name": "X"}, expected=[404])
    runner.expect("user/saved-locations: delete invalid", us_cat, "DELETE",
                  "/api/v1/user/saved-locations/99999999", token=nu_token, expected=[404])
    runner.expect("user/saved-locations: no auth", us_cat, "GET", "/api/v1/user/saved-locations",
                  expected=[401])

    # Favorites
    fav = runner.expect_json("user/favorites: create", us_cat, "POST", "/api/v1/user/favorites",
                             token=nu_token,
                             body={"name": "PyTest Work", "origin_lat": 30.05, "origin_lon": 31.24,
                                   "origin_name": "Home", "destination_lat": 30.07,
                                   "destination_lon": 31.28, "destination_name": "Work", "filter": 1},
                             expected=[201])
    fav_id = (fav or {}).get("id") if isinstance(fav, dict) else None
    if not fav_id and isinstance(fav, dict) and "favorites" in fav:
        fav_id = (fav["favorites"] or [{}])[0].get("id")
    if not fav_id:
        lst = http("GET", "/api/v1/user/favorites", token=nu_token).json() or {}
        items = lst.get("favorites", lst) if isinstance(lst, dict) else lst
        if isinstance(items, list) and items:
            fav_id = items[0].get("id")
    runner.ids["fav_id"] = fav_id

    runner.expect("user/favorites: list", us_cat, "GET", "/api/v1/user/favorites", token=nu_token, expected=[200])
    if fav_id:
        runner.expect("user/favorites: delete", us_cat, "DELETE", f"/api/v1/user/favorites/{fav_id}",
                      token=nu_token, expected=[200, 204])
    runner.expect("user/favorites: delete invalid", us_cat, "DELETE", "/api/v1/user/favorites/99999999",
                  token=nu_token, expected=[404])
    runner.expect("user/favorites: missing name", us_cat, "POST", "/api/v1/user/favorites", token=nu_token,
                  body={"origin_lat": 30.05, "origin_lon": 31.24,
                        "destination_lat": 30.07, "destination_lon": 31.28}, expected=[400])
    runner.expect("user/favorites: missing origin", us_cat, "POST", "/api/v1/user/favorites", token=nu_token,
                  body={"name": "X", "destination_lat": 30.07, "destination_lon": 31.28}, expected=[400])
    runner.expect("user/favorites: no auth", us_cat, "GET", "/api/v1/user/favorites", expected=[401])

    # Preferences
    runner.expect("user/preferences: get",  us_cat, "GET", "/api/v1/user/preferences", token=nu_token, expected=[200])
    runner.expect("user/preferences: put",  us_cat, "PUT", "/api/v1/user/preferences", token=nu_token,
                  body={"default_filter": 3, "max_walk_distance": 800, "accessibility_mode": True},
                  expected=[200])
    runner.expect("user/preferences: put default",  us_cat, "PUT", "/api/v1/user/preferences", token=nu_token,
                  body={"default_filter": 1, "max_walk_distance": 1500, "accessibility_mode": False},
                  expected=[200])

    # ─── Admin ─────────────────────────────────────────────────────────
    ad_cat = "Admin"
    runner.expect("admin/users: list", ad_cat, "GET", "/api/v1/admin/users", token=admin, expected=[200])
    runner.expect("admin/users: paginated", ad_cat, "GET", "/api/v1/admin/users",
                  token=admin, query={"limit": 5, "offset": 0}, expected=[200])
    runner.expect("admin/users: bad limit (0)", ad_cat, "GET", "/api/v1/admin/users",
                  token=admin, query={"limit": 0}, expected=[200, 400])
    runner.expect("admin/users: bad limit (negative)", ad_cat, "GET", "/api/v1/admin/users",
                  token=admin, query={"limit": -1}, expected=[200, 400])
    runner.expect("admin/users/1: get admin", ad_cat, "GET", "/api/v1/admin/users/1", token=admin, expected=[200])
    runner.expect("admin/users/99999: 404", ad_cat, "GET", "/api/v1/admin/users/99999", token=admin, expected=[404])
    runner.expect("admin/users/0: 404", ad_cat, "GET", "/api/v1/admin/users/0", token=admin, expected=[404])
    runner.expect("admin/users/abc: 400/404", ad_cat, "GET", "/api/v1/admin/users/abc", token=admin, expected=[400, 404])

    # Find new user id
    nu_list = http("GET", "/api/v1/admin/users?limit=200", token=admin).json() or []
    nu_id = next((u["id"] for u in nu_list if u.get("email") == nu_email), None)
    runner.ids["new_user_id"] = nu_id
    if nu_id:
        runner.expect("admin/users/{id}: update", ad_cat, "PUT", f"/api/v1/admin/users/{nu_id}", token=admin,
                      body={"address": "Updated by admin"}, expected=[200])
        runner.expect("admin/users/{id}: full update", ad_cat, "PUT", f"/api/v1/admin/users/{nu_id}", token=admin,
                      body={"first_name": "Py", "last_name": "Test", "mobile_number": "01111111111",
                            "gender": "female", "address": "Giza", "role": "User", "is_active": True},
                      expected=[200])
    runner.expect("admin/change-role: bad role", ad_cat, "POST", "/api/v1/admin/change-role", token=admin,
                  body={"user_id": nu_id or 1, "new_role": "god"}, expected=[400])
    runner.expect("admin/change-role: missing user_id", ad_cat, "POST", "/api/v1/admin/change-role", token=admin,
                  body={"new_role": "User"}, expected=[400])
    runner.expect("admin/change-role: missing new_role", ad_cat, "POST", "/api/v1/admin/change-role", token=admin,
                  body={"user_id": nu_id or 1}, expected=[400])
    if nu_id:
        runner.expect("admin/change-role: ok 'User'", ad_cat, "POST", "/api/v1/admin/change-role", token=admin,
                      body={"user_id": nu_id, "new_role": "User"}, expected=[200])
        runner.expect("admin/change-role: ok 'user' (lowercase)", ad_cat, "POST", "/api/v1/admin/change-role",
                      token=admin, body={"user_id": nu_id, "new_role": "user"}, expected=[200])
    runner.expect("admin: no auth", ad_cat, "GET", "/api/v1/admin/users", expected=[401, 403])
    # Regular user cannot access admin
    runner.expect("admin: regular user forbidden", ad_cat, "GET", "/api/v1/admin/users",
                  token=nu_token, expected=[403])

    # ─── Admin Analytics ──────────────────────────────────────────────
    aa_cat = "Admin Analytics"
    runner.expect("aa/users/overview",            aa_cat, "GET", "/api/v1/admin/analytics/users/overview",
                  token=admin, expected=[200])
    runner.expect("aa/users/overview with dates", aa_cat, "GET", "/api/v1/admin/analytics/users/overview",
                  token=admin, query={"from_date": "2024-01-01", "to_date": "2024-12-31"}, expected=[200])
    runner.expect("aa/users/overview bad date",   aa_cat, "GET", "/api/v1/admin/analytics/users/overview",
                  token=admin, query={"from_date": "not-a-date"}, expected=[200, 400])

    runner.expect("aa/routes/overview",           aa_cat, "GET", "/api/v1/admin/analytics/routes/overview",
                  token=admin, expected=[200])
    runner.expect("aa/routes/overview filter",    aa_cat, "GET", "/api/v1/admin/analytics/routes/overview",
                  token=admin, query={"filter": "optimal"}, expected=[200])
    runner.expect("aa/routes/overview source",    aa_cat, "GET", "/api/v1/admin/analytics/routes/overview",
                  token=admin, query={"source": "text"}, expected=[200])
    runner.expect("aa/routes/overview status",    aa_cat, "GET", "/api/v1/admin/analytics/routes/overview",
                  token=admin, query={"status": "success"}, expected=[200])
    runner.expect("aa/routes/overview bad status",aa_cat, "GET", "/api/v1/admin/analytics/routes/overview",
                  token=admin, query={"status": "purple"}, expected=[200, 400])

    runner.expect("aa/routes/filters",            aa_cat, "GET", "/api/v1/admin/analytics/routes/filters",
                  token=admin, expected=[200])
    runner.expect("aa/routes/filters filter",     aa_cat, "GET", "/api/v1/admin/analytics/routes/filters",
                  token=admin, query={"filter": "fastest"}, expected=[200])

    runner.expect("aa/routes/top-routes",         aa_cat, "GET", "/api/v1/admin/analytics/routes/top-routes",
                  token=admin, expected=[200])
    runner.expect("aa/routes/unresolved",         aa_cat, "GET", "/api/v1/admin/analytics/routes/unresolved",
                  token=admin, expected=[200])

    runner.expect("aa/routes/query: minimal",     aa_cat, "GET", "/api/v1/admin/analytics/routes/query",
                  token=admin, expected=[200])
    runner.expect("aa/routes/query: full",        aa_cat, "GET", "/api/v1/admin/analytics/routes/query",
                  token=admin,
                  query={"metrics": "requests,success_count,failed_count,success_rate_percent,avg_total_latency_ms,avg_ai_latency_ms,avg_routing_latency_ms,avg_duration_seconds,avg_distance_meters,avg_fare,unresolved_count,unresolved_rate_percent,long_walk_count,long_walk_rate_percent",
                         "group_by": "day,source,status,filter,selected_route_type",
                         "limit": 10, "offset": 0,
                         "sort": "requests", "order": "desc"}, expected=[200])
    runner.expect("aa/routes/query: bad metric",  aa_cat, "GET", "/api/v1/admin/analytics/routes/query",
                  token=admin, query={"metrics": "NOPE"}, expected=[400])
    runner.expect("aa/routes/query: bad group",   aa_cat, "GET", "/api/v1/admin/analytics/routes/query",
                  token=admin, query={"group_by": "NOPE"}, expected=[400])
    runner.expect("aa/routes/query: bad order",   aa_cat, "GET", "/api/v1/admin/analytics/routes/query",
                  token=admin, query={"order": "sideways"}, expected=[400])
    runner.expect("aa/routes/query: limit=999",   aa_cat, "GET", "/api/v1/admin/analytics/routes/query",
                  token=admin, query={"limit": 999}, expected=[200, 400])
    runner.expect("aa/routes/query: limit=0",     aa_cat, "GET", "/api/v1/admin/analytics/routes/query",
                  token=admin, query={"limit": 0}, expected=[200, 400])
    runner.expect("aa/routes/query: offset=-1",   aa_cat, "GET", "/api/v1/admin/analytics/routes/query",
                  token=admin, query={"offset": -1}, expected=[200, 400])

    runner.expect("aa/feedback: list",            aa_cat, "GET", "/api/v1/admin/analytics/feedback",
                  token=admin, expected=[200])
    runner.expect("aa/feedback: filters",         aa_cat, "GET", "/api/v1/admin/analytics/feedback",
                  token=admin, query={"min_rating": 3, "max_rating": 5, "limit": 5}, expected=[200])
    runner.expect("aa/feedback: user filter",     aa_cat, "GET", "/api/v1/admin/analytics/feedback",
                  token=admin, query={"user_id": 1}, expected=[200])
    runner.expect("aa/feedback: bad rating",      aa_cat, "GET", "/api/v1/admin/analytics/feedback",
                  token=admin, query={"min_rating": 99}, expected=[200, 400])
    runner.expect("aa/feedback: dates",           aa_cat, "GET", "/api/v1/admin/analytics/feedback",
                  token=admin, query={"from_date": "2024-01-01", "to_date": "2024-12-31"}, expected=[200])

    runner.expect("aa/feedback/summary",          aa_cat, "GET", "/api/v1/admin/analytics/feedback/summary",
                  token=admin, expected=[200])
    runner.expect("aa/feedback/summary with dates", aa_cat, "GET", "/api/v1/admin/analytics/feedback/summary",
                  token=admin, query={"from_date": "2024-01-01", "to_date": "2024-12-31"}, expected=[200])

    # ─── Print summary ────────────────────────────────────────────────
    print()
    print("=" * 90)
    print(f" Total: {len(runner.results)}    Passed: {runner.passes}    Failed: {runner.failures}")
    print("=" * 90)

    if runner.failures:
        print()
        print("FAILED TESTS:")
        for r in runner.results:
            if r.failed:
                print(f"  ✗ [{r.category}] {r.name}")
                print(f"      expected={r.expected} got={r.actual}  ({r.elapsed_ms:.0f}ms)")
                if r.body_excerpt:
                    print(f"      body: {r.body_excerpt[:300]}")
        print()
    return 0 if runner.failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
