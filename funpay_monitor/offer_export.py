"""
Fetch FunPay offer page and export remaining quantities to an Excel file.

Usage example:
python funpay_monitor/offer_export.py --url https://funpay.com/lots/offer?id=61189219 --cookies "sessid=...; other=..." --output funpay_monitor/funpay_offers.xlsx
By default will also try to use funpay_monitor/cookie.json if present (browser export format).
"""

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook


DEFAULT_URL = "https://funpay.com/lots/offer?id=61189219"
DEFAULT_COOKIE_JSON = Path(__file__).with_name("cookie.json")
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export FunPay offer quantities to Excel.")
    parser.add_argument("--url", default=DEFAULT_URL, help="Offer page URL.")
    parser.add_argument(
        "--cookies",
        help="Cookie string (e.g. \"sessid=...; other=...\") for authenticated request.",
    )
    parser.add_argument(
        "--cookies-file",
        help="Path to a file containing the cookie string (first line is used).",
    )
    parser.add_argument(
        "--cookie-json",
        default=str(DEFAULT_COOKIE_JSON),
        help="Path to cookie JSON export (Chrome/Firefox). Used if present.",
    )
    parser.add_argument(
        "--output",
        default=str(Path("funpay_monitor") / "funpay_offers.xlsx"),
        help="Where to save the Excel file.",
    )
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="User-Agent header for the request.",
    )
    parser.add_argument(
        "--save-html",
        help="Optional path to save fetched HTML for troubleshooting.",
    )
    return parser.parse_args()


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _parse_int(value: str) -> Optional[int]:
    if not value:
        return None
    match = re.search(r"\d+", value)
    return int(match.group()) if match else None


def _parse_cookie_string(raw: str) -> Dict[str, str]:
    cookies: Dict[str, str] = {}
    for chunk in raw.split(";"):
        if "=" not in chunk:
            continue
        name, val = chunk.split("=", 1)
        name = name.strip()
        val = val.strip()
        if name:
            cookies[name] = val
    return cookies


def _load_cookie_json(path: Path) -> Dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "cookies" in data:
        data = data["cookies"]
    if not isinstance(data, list):
        raise ValueError("Cookie JSON must be a list or contain a 'cookies' list.")

    cookies: Dict[str, str] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        value = item.get("value")
        if not name or value is None:
            continue
        domain = item.get("domain")
        if domain and "funpay.com" not in domain:
            continue
        cookies[name] = str(value)

    if not cookies:
        raise ValueError("No valid cookies found in JSON.")
    return cookies


def load_cookies(cookie_arg: Optional[str], file_arg: Optional[str], json_arg: Optional[str]) -> Dict[str, str]:
    # Priority: explicit cookie file > inline cookie string > JSON export (default path if exists).
    if file_arg:
        path = Path(file_arg)
        if not path.exists():
            raise FileNotFoundError(f"Cookie file not found: {file_arg}")
        cookie_arg = path.read_text(encoding="utf-8").splitlines()[0].strip()
        return _parse_cookie_string(cookie_arg)

    if cookie_arg:
        return _parse_cookie_string(cookie_arg)

    if json_arg:
        json_path = Path(json_arg)
        if json_path.exists():
            return _load_cookie_json(json_path)
        if json_path != DEFAULT_COOKIE_JSON:
            raise FileNotFoundError(f"Cookie JSON not found: {json_arg}")

    return {}


def fetch_html(url: str, cookies: Dict[str, str], user_agent: str) -> str:
    headers = {
        "User-Agent": user_agent,
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": url,
    }
    response = requests.get(url, headers=headers, cookies=cookies, timeout=20)
    response.raise_for_status()
    return response.text


def _pick_title(container) -> Optional[str]:
    if container is None:
        return None
    title_tag = (
        container.select_one("[data-title]")
        or container.select_one("[data-name]")
        or container.select_one(".tc-title, .title, .name, .offer-title, .lot-title, .desc")
    )
    if not title_tag:
        return None
    raw = title_tag.get("data-title") or title_tag.get("data-name") or title_tag.get_text(" ", strip=True)
    return _clean_text(raw)


def _pick_price(container) -> Optional[str]:
    if container is None:
        return None
    price_tag = (
        container.select_one("[data-price]")
        or container.select_one(".tc-price, .price, .cost")
    )
    if not price_tag:
        return None
    raw = price_tag.get("data-price") or price_tag.get_text(" ", strip=True)
    return _clean_text(raw)


def parse_offers(html: str) -> List[Dict[str, Optional[str]]]:
    soup = BeautifulSoup(html, "html.parser")
    offers: List[Dict[str, Optional[str]]] = []
    seen_keys = set()
    quantity_selectors = "[data-amount],[data-quantity],[data-qty],.tc-quantity,.quantity,.count"

    for qty_tag in soup.select(quantity_selectors):
        amount = (
            _parse_int(qty_tag.get("data-amount"))
            or _parse_int(qty_tag.get("data-quantity"))
            or _parse_int(qty_tag.get("data-qty"))
            or _parse_int(qty_tag.get_text(" ", strip=True))
        )
        if amount is None:
            continue

        container = qty_tag
        title = None
        price = None
        for _ in range(4):
            if hasattr(container, "select_one"):
                if not title:
                    title = _pick_title(container)
                if price is None:
                    price = _pick_price(container)
            if title:
                break
            container = container.parent
            if container is None:
                break

        if not title:
            continue

        key = (title, amount)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        offers.append({"title": title, "amount": amount, "price": price, "accounts": None})

    if offers:
        return offers

    # FunPay single-offer fallback: title in page header, availability in a param-item h5 containing "Налич".
    title_tag = soup.select_one("div.page-header h1") or soup.select_one("h1")
    title = _clean_text(title_tag.get_text(" ", strip=True)) if title_tag else None

    amount = None
    for item in soup.select("div.param-item"):
        header = item.find("h5")
        if not header:
            continue
        header_text = header.get_text(" ", strip=True).lower()
        if "налич" in header_text or "налiч" in header_text:
            amount_tag = item.find(class_="text-bold") or item.find("div")
            amount = _parse_int(amount_tag.get_text(" ", strip=True) if amount_tag else None)
            break

    price_tag = soup.select_one(".payment-value") or soup.select_one("[data-price]")
    price = _clean_text(price_tag.get_text(" ", strip=True)) if price_tag else None

    if title and amount is not None:
        offers.append({"title": title, "amount": amount, "price": price, "accounts": None})

    if offers:
        return offers

    # FunPay offer edit page fallback: accounts listed in textarea[name="secrets"], amount in hidden input[name="amount"].
    secrets_area = soup.select_one('textarea[name="secrets"]')
    secret_lines: List[str] = []
    if secrets_area:
        raw_secrets = secrets_area.get_text("\n", strip=False)
        secret_lines = [line.strip() for line in raw_secrets.splitlines() if line.strip()]
        amount = len(secret_lines)
    else:
        amount_input = soup.select_one('input[name="amount"]')
        amount = _parse_int(amount_input.get("value")) if amount_input else None

    price_input = soup.select_one('input[name="price"]')
    price = price or (_clean_text(price_input.get("value")) if price_input and price_input.get("value") else None)

    if title and amount is not None:
        offers.append({"title": title, "amount": amount, "price": price, "accounts": secret_lines or None})

    return offers


def export_to_excel(offers: List[Dict[str, Optional[str]]], url: str, output_path: str) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "FunPay"
    ws.append(["Title", "Remaining", "Price", "Accounts Listed", "Source URL", "Fetched At"])

    fetched_at = dt.datetime.now().isoformat(timespec="seconds")
    if not offers:
        ws.append(["No offers parsed", None, None, 0, url, fetched_at])
    else:
        for offer in offers:
            accounts_count = len(offer.get("accounts") or [])
            ws.append(
                [
                    offer.get("title"),
                    offer.get("amount"),
                    offer.get("price"),
                    accounts_count,
                    url,
                    fetched_at,
                ]
            )

    accounts_rows: List[List[Optional[str]]] = []
    for offer in offers:
        accounts = offer.get("accounts") or []
        title = offer.get("title")
        for idx, acc in enumerate(accounts, start=1):
            accounts_rows.append([title, idx, acc])

    if accounts_rows:
        ws_acc = wb.create_sheet("Accounts")
        ws_acc.append(["Offer Title", "#", "Account"])
        for row in accounts_rows:
            ws_acc.append(row)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)


def main() -> int:
    args = parse_args()
    try:
        cookies = load_cookies(args.cookies, args.cookies_file, args.cookie_json)
    except Exception as exc:
        print(f"[error] Failed to load cookies: {exc}", file=sys.stderr)
        return 1

    try:
        html = fetch_html(args.url, cookies, args.user_agent)
    except requests.HTTPError as exc:
        print(f"[error] HTTP error: {exc} (status {exc.response.status_code})", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"[error] Request failed: {exc}", file=sys.stderr)
        return 1

    if args.save_html:
        Path(args.save_html).write_text(html, encoding="utf-8")

    offers = parse_offers(html)
    export_to_excel(offers, args.url, args.output)

    print(f"[ok] Parsed {len(offers)} offers and wrote {args.output}")
    if args.save_html:
        print(f"[info] Saved HTML copy to {args.save_html}")
    if not offers:
        print("[warn] No offers matched; adjust selectors or check cookies/auth.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
