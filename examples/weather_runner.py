#!/usr/bin/env python3
"""
mlang_weather_runner.py

A small MLLang-aware Python command runner.

Goal:
- Receive ONLY MLLang packets as instructions.
- Parse the packet.
- Look at N:@PY -> <verb>.
- Execute only allowlisted local functions.
- Return an updated MLLang packet with O:{...} output.

No third-party packages required.

Supported verbs:
- weather.forecast
- weather.rain_check
- weather.avg_temp
- weather.search_url

Weather data source:
- Open-Meteo Forecast API + Open-Meteo Geocoding API
- No API key required for personal/non-commercial use.

Example:
echo 'V:0.1.r1; I:wx-long-beach-001; G:{loc:"Long Beach, CA", days:7}; N:@PY -> weather.rain_check; H:done; P:0.80;' | python3 mlang_weather_runner.py
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import statistics
import sys
import textwrap
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


AGENT_ID = "@PY"

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

DEFAULT_TIMEOUT_SECONDS = 12
DEFAULT_RAIN_THRESHOLD_PCT = 30
DEFAULT_TEMP_UNIT = "fahrenheit"
DEFAULT_PRECIP_UNIT = "inch"


class MLLangError(Exception):
    """Raised for parse, routing, or execution errors."""


# ----------------------------
# MLLang parsing helpers
# ----------------------------

def strip_outer_packet_noise(text: str) -> str:
    """
    Accept raw one-line packet, stdin text, or fenced packet-ish content.
    This intentionally stays conservative.
    """
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    # Collapse newlines into spaces because locked packets should be one logical line.
    text = " ".join(line.strip() for line in text.splitlines() if line.strip())
    return text


def split_top_level(text: str, sep: str) -> List[str]:
    """
    Split on sep only when not inside quotes/braces/brackets/parens.

    Example:
    split_top_level('G:{loc:"Long Beach, CA", days:7}; N:@PY -> weather.forecast;', ';')
    """
    parts: List[str] = []
    buf: List[str] = []
    quote: Optional[str] = None
    escape = False
    depth = 0

    opens = {"{", "[", "("}
    closes = {"}", "]", ")"}

    for ch in text:
        if escape:
            buf.append(ch)
            escape = False
            continue

        if ch == "\\":
            buf.append(ch)
            escape = True
            continue

        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue

        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            continue

        if ch in opens:
            depth += 1
            buf.append(ch)
            continue

        if ch in closes:
            depth = max(0, depth - 1)
            buf.append(ch)
            continue

        if ch == sep and depth == 0:
            part = "".join(buf).strip()
            if part:
                parts.append(part)
            buf = []
            continue

        buf.append(ch)

    part = "".join(buf).strip()
    if part:
        parts.append(part)

    return parts


def split_key_value(text: str, sep: str = ":") -> Tuple[str, str]:
    """
    Split the first top-level key/value separator.
    """
    quote: Optional[str] = None
    escape = False
    depth = 0

    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue

        if ch == "\\":
            escape = True
            continue

        if quote:
            if ch == quote:
                quote = None
            continue

        if ch in ("'", '"'):
            quote = ch
            continue

        if ch in "{[(":
            depth += 1
            continue

        if ch in "}])":
            depth = max(0, depth - 1)
            continue

        if ch == sep and depth == 0:
            return text[:i].strip(), text[i + 1 :].strip()

    raise MLLangError(f"ERR_BAD_PACKET: Expected '{sep}' in: {text}")


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        inner = value[1:-1]
        return bytes(inner, "utf-8").decode("unicode_escape")
    return value


def parse_value(value: str) -> Any:
    value = value.strip()

    if value == "":
        return ""

    if value.startswith("{") and value.endswith("}"):
        return parse_map(value[1:-1])

    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [parse_value(part) for part in split_top_level(inner, ",")]

    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return unquote(value)

    low = value.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in ("null", "none"):
        return None

    if re.fullmatch(r"-?\d+", value):
        try:
            return int(value)
        except ValueError:
            pass

    if re.fullmatch(r"-?\d+\.\d+", value):
        try:
            return float(value)
        except ValueError:
            pass

    # Bare MLLang atom.
    return value


def parse_map(inner: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not inner.strip():
        return out

    for part in split_top_level(inner, ","):
        key, raw_value = split_key_value(part, ":")
        out[key.strip()] = parse_value(raw_value)

    return out


@dataclass
class Packet:
    slots: Dict[str, Any]
    order: List[str]
    raw: str

    def get_map(self, key: str) -> Dict[str, Any]:
        value = self.slots.get(key)
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        return {"value": value}


def parse_packet(text: str) -> Packet:
    text = strip_outer_packet_noise(text)
    if not text.startswith("V:"):
        raise MLLangError("ERR_BAD_PACKET: Packet must start with V:<version>, for example V:0.1.r1;")

    slots: Dict[str, Any] = {}
    order: List[str] = []

    for part in split_top_level(text, ";"):
        key, raw_value = split_key_value(part, ":")
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_^!-]*", key):
            raise MLLangError(f"ERR_BAD_PACKET: Bad slot key: {key}")
        slots[key] = parse_value(raw_value)
        order.append(key)

    if "V" not in slots:
        raise MLLangError("ERR_MISSING_SLOT: V slot required")
    if "N" not in slots:
        raise MLLangError("ERR_MISSING_SLOT: N slot required (use N:@AGENT -> verb)")

    return Packet(slots=slots, order=order, raw=text)


# ----------------------------
# MLLang formatting helpers
# ----------------------------

def quote_atom(s: str) -> str:
    """
    Quote strings only when needed. Keeps compact MLLang readable.
    """
    if re.fullmatch(r"[A-Za-z0-9_@./:+<>=-]+", s):
        return s
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        # Weather APIs sometimes return long floats. Keep stable but compact.
        return f"{value:.2f}".rstrip("0").rstrip(".")
    if isinstance(value, str):
        return quote_atom(value)
    if isinstance(value, list):
        return "[" + ", ".join(format_value(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k}:{format_value(v)}" for k, v in value.items()) + "}"
    return quote_atom(str(value))


def packet_with_output(packet: Packet, output: Dict[str, Any], en: str) -> str:
    slots = dict(packet.slots)
    order = list(packet.order)

    if "O" not in slots:
        order.append("O")
    if "EN" not in slots:
        order.append("EN")

    slots["O"] = output
    slots["EN"] = en

    rendered = []
    for key in order:
        if key in slots:
            rendered.append(f"{key}:{format_value(slots[key])}")
    return "; ".join(rendered) + ";"


def inject_trace(raw: str, root_id: str, parent_id: Optional[str], depth: int) -> str:
    """Append/replace TR:{root,parent,depth} slot on a raw packet string. v0.2 multi-hop tracing."""
    import re
    payload = {"root": root_id, "depth": depth}
    if parent_id:
        payload["parent"] = parent_id
    tr_str = "TR:" + format_value(payload)
    raw_stripped = raw.strip()
    if raw_stripped.endswith(";"):
        raw_stripped = raw_stripped[:-1]
    # Remove any existing TR: slot, regardless of position.
    raw_stripped = re.sub(r"(^|;\s*)TR:\{[^}]*\}", lambda m: ";" if m.group(1) else "", raw_stripped)
    raw_stripped = raw_stripped.strip().rstrip(";").strip()
    return f"{raw_stripped}; {tr_str};"


def cap_packet_with_output(packet: Packet, output: Dict[str, Any], cap: Dict[str, Any], en: str) -> str:
    """v0.2 RFC-0001 T:cap response. Emits T:cap; O:{...}; CAP:{structured...}; EN:..."""
    slots = dict(packet.slots)
    order = list(packet.order)

    for slot in ("T", "O", "CAP", "EN"):
        if slot not in slots:
            order.append(slot)

    slots["T"] = "cap"
    slots["O"] = output
    slots["CAP"] = cap
    slots["EN"] = en

    rendered = []
    for key in order:
        if key in slots:
            rendered.append(f"{key}:{format_value(slots[key])}")
    return "; ".join(rendered) + ";"


def error_packet(packet: Optional[Packet], err: str) -> str:
    safe_err = err.replace("\n", " ")
    if packet is None:
        return (
            'V:0.1.r1; I:error; N:@PY -> report; '
            f'O:{{ok:false, err:{format_value(safe_err)}}}; '
            f'EN:{format_value("MLLang runner failed before packet was fully parsed.")};'
        )
    return packet_with_output(
        packet,
        {"ok": False, "err": safe_err},
        "MLLang runner failed; see O.err.",
    )


# ----------------------------
# Routing
# ----------------------------

def parse_next_slot(packet: Packet) -> Tuple[str, str]:
    n_raw = packet.slots.get("N", "")
    # v0.2 alternative: N:{agent:"@X", verb:"y"} — gemini-safe (the `@` stays
    # inside a quoted value, so vendor tokenizers don't rewrite it as a path).
    if isinstance(n_raw, dict):
        target = str(n_raw.get("agent", "")).strip()
        verb = str(n_raw.get("verb", "")).strip()
        if not target or not verb:
            raise MLLangError(
                "ERR_BAD_PACKET: N map form must contain agent and verb (N:{agent:'@X', verb:'y'})"
            )
        if not re.fullmatch(r"@[A-Za-z0-9_-]+", target):
            raise MLLangError(f"ERR_BAD_PACKET: N.agent must look like @AGENT; got {target!r}")
        return target, verb
    n_value = str(n_raw).strip()
    match = re.fullmatch(r"(@[A-Za-z0-9_-]+)\s*->\s*([A-Za-z0-9_.-]+)", n_value)
    if not match:
        raise MLLangError("ERR_BAD_PACKET: N slot must look like: N:@AGENT -> verb (or N:{agent:'@AGENT', verb:'y'})")
    target, verb = match.group(1), match.group(2)
    return target, verb


def normalize_verb(verb: str) -> str:
    aliases = {
        "forecast": "weather.forecast",
        "weather": "weather.forecast",
        "weather.forecast": "weather.forecast",
        "rain": "weather.rain_check",
        "rain_check": "weather.rain_check",
        "weather.rain": "weather.rain_check",
        "weather.rain_check": "weather.rain_check",
        "avg_temp": "weather.avg_temp",
        "temperature.avg": "weather.avg_temp",
        "weather.avg_temp": "weather.avg_temp",
        "search": "weather.search_url",
        "google.search": "weather.search_url",
        "weather.search": "weather.search_url",
        "weather.search_url": "weather.search_url",
    }
    return aliases.get(verb, verb)


# ----------------------------
# Weather API helpers
# ----------------------------

def http_get_json(url: str, params: Dict[str, Any], timeout: int = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
    query = urllib.parse.urlencode(params, doseq=True)
    full_url = f"{url}?{query}"
    request = urllib.request.Request(
        full_url,
        headers={
            "User-Agent": "mlang-weather-runner/0.1 (+local-script)"
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    data = json.loads(body)
    if isinstance(data, dict) and data.get("error"):
        raise MLLangError(f"Weather API error: {data.get('reason') or data}")
    return data


def geocode_location(location: str) -> Dict[str, Any]:
    data = http_get_json(
        GEOCODE_URL,
        {
            "name": location,
            "count": 1,
            "language": "en",
            "format": "json",
        },
    )
    results = data.get("results") or []
    if not results:
        raise MLLangError(f"No geocoding result for location: {location}")
    result = results[0]
    return {
        "name": result.get("name"),
        "admin1": result.get("admin1"),
        "country": result.get("country"),
        "country_code": result.get("country_code"),
        "latitude": result.get("latitude"),
        "longitude": result.get("longitude"),
        "timezone": result.get("timezone") or "auto",
    }


def display_location(geo: Dict[str, Any]) -> str:
    parts = [geo.get("name"), geo.get("admin1"), geo.get("country")]
    return ", ".join(str(p) for p in parts if p)


def fetch_weather_forecast(geo: Dict[str, Any], days: int) -> Dict[str, Any]:
    days = max(1, min(int(days), 16))
    return http_get_json(
        FORECAST_URL,
        {
            "latitude": geo["latitude"],
            "longitude": geo["longitude"],
            "timezone": geo.get("timezone") or "auto",
            "forecast_days": days,
            "temperature_unit": DEFAULT_TEMP_UNIT,
            "precipitation_unit": DEFAULT_PRECIP_UNIT,
            "current": [
                "temperature_2m",
                "precipitation",
                "weather_code",
            ],
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "precipitation_probability_max",
            ],
            "hourly": [
                "temperature_2m",
                "precipitation",
                "precipitation_probability",
            ],
        },
    )


def get_location_from_goal(goal: Dict[str, Any]) -> str:
    location = (
        goal.get("loc")
        or goal.get("location")
        or goal.get("place")
        or goal.get("q")
        or goal.get("city")
    )
    if not location:
        raise MLLangError('Missing location. Put loc:"Long Beach, CA" inside G:{...}.')
    return str(location)


def get_days_from_goal(goal: Dict[str, Any], default: int = 7) -> int:
    try:
        return int(goal.get("days", default))
    except (TypeError, ValueError):
        return default


def daily_rows(forecast: Dict[str, Any]) -> List[Dict[str, Any]]:
    daily = forecast.get("daily") or {}
    times = daily.get("time") or []
    hi = daily.get("temperature_2m_max") or []
    lo = daily.get("temperature_2m_min") or []
    rain_sum = daily.get("precipitation_sum") or []
    rain_prob = daily.get("precipitation_probability_max") or []

    rows: List[Dict[str, Any]] = []
    for i, date_value in enumerate(times):
        rows.append(
            {
                "date": date_value,
                "hi_f": hi[i] if i < len(hi) else None,
                "lo_f": lo[i] if i < len(lo) else None,
                "rain_in": rain_sum[i] if i < len(rain_sum) else None,
                "rain_prob_pct": rain_prob[i] if i < len(rain_prob) else None,
            }
        )
    return rows


def resolve_date_token(token: Any, timezone_name: Optional[str] = None) -> str:
    """
    Resolve today/tomorrow using local machine date.
    If you need exact remote timezone behavior, the API daily rows are still authoritative;
    this is only for selecting row labels.
    """
    token_s = str(token or "today").lower()
    today = dt.date.today()
    if token_s in ("today", "now"):
        return today.isoformat()
    if token_s == "tomorrow":
        return (today + dt.timedelta(days=1)).isoformat()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", token_s):
        return token_s
    return token_s


def window_hours(name: str) -> Tuple[int, int]:
    """
    Returns [start_hour, end_hour) in local forecast time.
    """
    name = (name or "morning").lower()
    table = {
        "early_morning": (5, 9),
        "morning": (6, 12),
        "midday": (11, 14),
        "afternoon": (12, 18),
        "evening": (18, 22),
        "night": (22, 24),
        "day": (6, 18),
    }
    return table.get(name, (6, 12))


# ----------------------------
# Weather verbs
# ----------------------------

def run_weather_forecast(packet: Packet) -> Tuple[Dict[str, Any], str]:
    goal = packet.get_map("G")
    location = get_location_from_goal(goal)
    days = get_days_from_goal(goal, default=7)

    geo = geocode_location(location)
    forecast = fetch_weather_forecast(geo, days)
    rows = daily_rows(forecast)

    rainy_days = [
        row["date"]
        for row in rows
        if (row.get("rain_prob_pct") or 0) >= DEFAULT_RAIN_THRESHOLD_PCT
        or (row.get("rain_in") or 0) > 0
    ]

    output = {
        "ok": True,
        "tool": "weather.forecast",
        "loc": display_location(geo),
        "days": len(rows),
        "rainy_days": rainy_days,
        "daily": rows,
        "src": "open-meteo",
    }
    en = f"Weather forecast returned {len(rows)} days for {display_location(geo)}."
    return output, en


def run_rain_check(packet: Packet) -> Tuple[Dict[str, Any], str]:
    goal = packet.get_map("G")
    location = get_location_from_goal(goal)
    days = get_days_from_goal(goal, default=7)
    date_token = goal.get("date", goal.get("when", "next_7_days"))
    threshold = int(goal.get("rain_threshold_pct", DEFAULT_RAIN_THRESHOLD_PCT))

    geo = geocode_location(location)
    forecast = fetch_weather_forecast(geo, days)
    rows = daily_rows(forecast)

    selected = rows
    token_s = str(date_token).lower()
    if token_s not in ("next_7_days", "next7", "week", "all"):
        wanted = resolve_date_token(date_token, geo.get("timezone"))
        selected = [row for row in rows if row["date"] == wanted]
        if not selected:
            raise MLLangError(f"No forecast row found for date={wanted}; available={rows[0]['date']}..{rows[-1]['date']}")

    rain_days = []
    for row in selected:
        prob = row.get("rain_prob_pct") or 0
        amount = row.get("rain_in") or 0
        if prob >= threshold or amount > 0:
            rain_days.append(row)

    will_rain = bool(rain_days)
    output = {
        "ok": True,
        "tool": "weather.rain_check",
        "loc": display_location(geo),
        "date": date_token,
        "threshold_pct": threshold,
        "will_rain": will_rain,
        "rain_days": rain_days,
        "src": "open-meteo",
    }

    if will_rain:
        en = f"Rain is possible for {display_location(geo)}; {len(rain_days)} matching day(s) found."
    else:
        en = f"No rain signal met the threshold for {display_location(geo)} in the selected window."
    return output, en


def run_avg_temp(packet: Packet) -> Tuple[Dict[str, Any], str]:
    goal = packet.get_map("G")
    location = get_location_from_goal(goal)
    days = get_days_from_goal(goal, default=2)
    date_token = goal.get("date", goal.get("when", "today"))
    window = str(goal.get("window", "morning"))

    geo = geocode_location(location)
    forecast = fetch_weather_forecast(geo, days)

    wanted_date = resolve_date_token(date_token, geo.get("timezone"))
    start_hour = int(goal.get("start_hour", window_hours(window)[0]))
    end_hour = int(goal.get("end_hour", window_hours(window)[1]))

    hourly = forecast.get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []

    selected_temps: List[float] = []
    selected_hours: List[str] = []
    for t, temp in zip(times, temps):
        # Open-Meteo local time format: YYYY-MM-DDTHH:MM
        if not isinstance(t, str) or "T" not in t:
            continue
        date_part, time_part = t.split("T", 1)
        if date_part != wanted_date:
            continue
        hour = int(time_part.split(":", 1)[0])
        if start_hour <= hour < end_hour and temp is not None:
            selected_temps.append(float(temp))
            selected_hours.append(t)

    if not selected_temps:
        raise MLLangError(f"No hourly temperatures found for {wanted_date} {start_hour}:00-{end_hour}:00")

    avg_f = statistics.mean(selected_temps)
    output = {
        "ok": True,
        "tool": "weather.avg_temp",
        "loc": display_location(geo),
        "date": wanted_date,
        "window": window,
        "hours": selected_hours,
        "avg_f": round(avg_f, 1),
        "samples": len(selected_temps),
        "src": "open-meteo",
    }
    en = f"Average {window} temperature for {display_location(geo)} on {wanted_date} is {avg_f:.1f} F."
    return output, en


def run_search_url(packet: Packet) -> Tuple[Dict[str, Any], str]:
    """
    Safe replacement for 'scrape Google weather'.
    It creates a Google search URL, but does not scrape Google result pages.

    Use weather.forecast/rain_check/avg_temp for machine-readable weather answers.
    """
    goal = packet.get_map("G")
    location = get_location_from_goal(goal)
    when = str(goal.get("date", goal.get("when", ""))).strip()
    query = "weather " + location + (f" {when}" if when else "")
    url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)

    output = {
        "ok": True,
        "tool": "weather.search_url",
        "query": query,
        "url": url,
        "note": "search_url_only; no_google_scrape; use_weather_forecast_for_data",
    }
    en = "Created a Google weather search URL; did not scrape Google."
    return output, en


ALLOWED_VERBS = {
    "weather.forecast": run_weather_forecast,
    "weather.rain_check": run_rain_check,
    "weather.avg_temp": run_avg_temp,
    "weather.search_url": run_search_url,
}


def execute_packet(packet: Packet) -> str:
    target, raw_verb = parse_next_slot(packet)
    if target != AGENT_ID:
        raise MLLangError(f"ERR_TARGET_MISMATCH: This runner only handles {AGENT_ID}; packet target was {target}")

    verb = normalize_verb(raw_verb)
    if verb not in ALLOWED_VERBS:
        allowed = ", ".join(sorted(ALLOWED_VERBS))
        raise MLLangError(f"ERR_NOT_CAPABLE: Unsupported verb '{raw_verb}'. Allowed: {allowed}")

    output, en = ALLOWED_VERBS[verb](packet)
    return packet_with_output(packet, output, en)


# ----------------------------
# Examples and selftest
# ----------------------------

EXAMPLES = {
    "next_7_days_rain_long_beach": 'V:0.1.r1; I:wx-lb-7d-rain; G:{loc:"Long Beach, CA", days:7, date:next_7_days}; N:@PY -> weather.rain_check; H:done; P:0.80;',
    "today_rain_long_beach": 'V:0.1.r1; I:wx-lb-today-rain; G:{loc:"Long Beach, CA", days:2, date:today}; N:@PY -> weather.rain_check; H:done; P:0.80;',
    "tomorrow_rain_long_beach": 'V:0.1.r1; I:wx-lb-tomorrow-rain; G:{loc:"Long Beach, CA", days:3, date:tomorrow}; N:@PY -> weather.rain_check; H:done; P:0.80;',
    "avg_morning_temp_long_beach": 'V:0.1.r1; I:wx-lb-morning-temp; G:{loc:"Long Beach, CA", days:2, date:today, window:morning}; N:@PY -> weather.avg_temp; H:done; P:0.80;',
    "forecast_long_beach": 'V:0.1.r1; I:wx-lb-forecast; G:{loc:"Long Beach, CA", days:7}; N:@PY -> weather.forecast; H:done; P:0.80;',
    "google_weather_search_url": 'V:0.1.r1; I:wx-lb-google-url; G:{loc:"Long Beach, CA", date:today}; N:@PY -> weather.search_url; H:done; P:0.75;',
}


def run_selftest() -> None:
    packet = parse_packet(EXAMPLES["forecast_long_beach"])
    assert packet.slots["V"] == "0.1.r1"
    assert packet.get_map("G")["loc"] == "Long Beach, CA"
    assert parse_next_slot(packet) == ("@PY", "weather.forecast")

    map_test = parse_value('{loc:"Long Beach, CA", days:7, tags:[rain, temp]}')
    assert map_test["loc"] == "Long Beach, CA"
    assert map_test["days"] == 7
    assert map_test["tags"] == ["rain", "temp"]

    rendered = packet_with_output(packet, {"ok": True, "x": [1, 2]}, "ok")
    assert "O:{ok:true" in rendered
    print("SELFTEST_PASS")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Execute allowlisted weather functions from an MLLang packet.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Examples:
              python3 mlang_weather_runner.py --examples
              echo 'V:0.1.r1; I:wx; G:{loc:"Long Beach, CA", days:7}; N:@PY -> weather.forecast; H:done; P:0.80;' | python3 mlang_weather_runner.py
            """
        ),
    )
    parser.add_argument("--packet", help="MLLang packet string. If omitted, stdin is used.")
    parser.add_argument("--examples", action="store_true", help="Print MLLang-only example packets.")
    parser.add_argument("--selftest", action="store_true", help="Run parser selftest only; no network.")
    args = parser.parse_args(argv)

    if args.examples:
        for name, packet in EXAMPLES.items():
            print(f"# {name}")
            print(packet)
        return 0

    if args.selftest:
        run_selftest()
        return 0

    raw = args.packet if args.packet is not None else sys.stdin.read()

    packet: Optional[Packet] = None
    try:
        packet = parse_packet(raw)
        print(execute_packet(packet))
        return 0
    except Exception as exc:
        print(error_packet(packet, str(exc)))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
