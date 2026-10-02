#!/usr/bin/env python3
"""Send ETF prices to Bark.

Defaults are set for ZEB.TO and ZBAL.TO. The script is designed to be
run once by a scheduler such as launchd.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


DEFAULT_SYMBOLS = ("ZEB.TO", "ZBAL.TO")
DEFAULT_BARK_URL = "https://api.day.app/FGRt2RZaMpT529AomX5rD8/Body%20Text"
GOOGLE_FINANCE_URL = "https://www.google.com/finance/quote"
TIMEZONE = "America/Vancouver"


class NotifierError(RuntimeError):
    """Raised when price lookup or notification delivery fails."""


def read_url(url: str, timeout: int = 20) -> bytes:
    request = Request(url, headers={"User-Agent": "ETF-Bark-Notifier/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        urllib_error = f"HTTP {exc.code} from {url}: {body}"
    except URLError as exc:
        urllib_error = f"Could not reach {url}: {exc.reason}"

    try:
        completed = subprocess.run(
            ["curl", "-fsSL", url],
            check=True,
            capture_output=True,
            timeout=timeout,
        )
        return completed.stdout
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise NotifierError(f"{urllib_error}; curl fallback also failed: {exc}") from exc


def fetch_quotes(symbols: tuple[str, ...]) -> list[dict[str, Any]]:
    return [fetch_google_quote(symbol) for symbol in symbols]


def google_symbol(symbol: str) -> tuple[str, str]:
    if symbol.endswith(".TO"):
        return symbol.removesuffix(".TO"), "TSE"

    raise NotifierError(f"Unsupported symbol format: {symbol}. Expected Toronto tickers like ZEB.TO.")


def fetch_google_quote(symbol: str) -> dict[str, Any]:
    ticker, exchange = google_symbol(symbol)
    page_url = f"{GOOGLE_FINANCE_URL}/{quote(ticker)}:{quote(exchange)}"
    page = html.unescape(read_url(page_url).decode("utf-8", errors="replace"))
    pattern = re.compile(
        r'\["[^"]+",\["'
        + re.escape(ticker)
        + r'","'
        + re.escape(exchange)
        + r'"\],"([^"]+)",\d+,"([A-Z]+)",\[([-0-9.]+),([-0-9.]+),([-0-9.]+),'
    )
    match = pattern.search(page)
    if not match:
        raise NotifierError(f"Could not parse Google Finance quote page for {symbol}")

    name, currency, price, change, change_pct = match.groups()
    return {
        "symbol": symbol,
        "shortName": name,
        "currency": currency,
        "regularMarketPrice": float(price),
        "regularMarketChange": float(change),
        "regularMarketChangePercent": float(change_pct),
    }


def format_price_line(quote_data: dict[str, Any]) -> str:
    symbol = quote_data["symbol"]
    price = quote_data.get("regularMarketPrice")
    currency = quote_data.get("currency", "")
    change = quote_data.get("regularMarketChange")
    change_pct = quote_data.get("regularMarketChangePercent")

    if price is None:
        return f"{symbol}: price unavailable"

    suffix = ""
    if change is not None and change_pct is not None:
        sign = "+" if change >= 0 else ""
        suffix = f" ({sign}{change:.2f}, {sign}{change_pct:.2f}%)"

    return f"{symbol}: {price:.2f} {currency}{suffix}"


def normalize_bark_base(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if not parsed.scheme or not parsed.netloc or not parts:
        raise NotifierError("BARK_URL must look like https://api.day.app/<key>")

    token = parts[0]
    return f"{parsed.scheme}://{parsed.netloc}/{token}"


def send_bark_message(bark_url: str, title: str, body: str) -> None:
    base = normalize_bark_base(bark_url)
    url = f"{base}/{quote(title, safe='')}/{quote(body, safe='')}"
    payload = read_url(url)
    try:
        response = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise NotifierError(f"Bark returned a non-JSON response: {payload[:200]!r}") from exc

    if response.get("code") != 200:
        message = response.get("message") or response.get("error") or response
        raise NotifierError(f"Bark rejected the notification: {message}")


def build_message(symbols: tuple[str, ...]) -> tuple[str, str]:
    quotes = fetch_quotes(symbols)
    now = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    lines = [format_price_line(quote_data) for quote_data in quotes]
    return "ETF Price Update", f"{now}\n" + "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send ETF prices to Bark.")
    parser.add_argument(
        "--symbols",
        default=",".join(DEFAULT_SYMBOLS),
        help="Comma-separated ETF tickers. Default: ZEB.TO,ZBAL.TO",
    )
    parser.add_argument(
        "--bark-url",
        default=os.environ.get("BARK_URL", DEFAULT_BARK_URL),
        help="Bark URL or BARK_URL env var. Example: https://api.day.app/<key>",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the message without sending it.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    symbols = tuple(symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip())

    try:
        title, body = build_message(symbols)
        if args.dry_run:
            print(title)
            print(body)
        else:
            send_bark_message(args.bark_url, title, body)
            print(f"Sent Bark notification for {', '.join(symbols)}")
    except NotifierError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
