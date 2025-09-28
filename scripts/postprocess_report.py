import json
import os
import re
from datetime import datetime

# Load data from JSON files
with open("docs/index.json", "r", encoding="utf-8") as f:
    index_data = json.load(f)
with open("docs/news/news.json", "r", encoding="utf-8") as f:
    news_data = json.load(f)

# Helper: flatten nested dictionaries (one level deep) into a single level with composite keys
def flatten_dict(d, parent_key=""):
    items = {}
    for k, v in d.items():
        new_key = f"{parent_key}_{k}" if parent_key else k
        if isinstance(v, dict):
            # Flatten nested dict (recursive)
            items.update(flatten_dict(v, new_key))
        else:
            items[new_key] = v
    return items

# Prepare containers
report_list = []        # list of combined report entries
news_by_ticker = {}     # dict to map ticker -> list of news items
market_news = []        # list for general market news

# Organize news by ticker and general market news
if isinstance(news_data, list):
    # If news_data is a list of news items (each with a 'ticker' field or general news without one)
    for item in news_data:
        if isinstance(item, dict):
            ticker = item.get("ticker") or item.get("symbol")
            if ticker:
                news_by_ticker.setdefault(ticker, []).append(item)
            else:
                market_news.append(item)
elif isinstance(news_data, dict):
    # If news_data is a dict with tickers as keys (and possibly a special key for market/general news)
    for key, val in news_data.items():
        if key.lower() in ("market", "general", "all"):
            # Market-wide news
            if isinstance(val, list):
                market_news.extend(val)
            elif val:
                market_news.append(val)
        else:
            # Ticker-specific news
            # Ensure it's a list of news items
            if isinstance(val, list):
                news_by_ticker[key] = val
            else:
                news_by_ticker[key] = [val]

# Determine structure of index_data for market vs tickers
market_entries = []  # list of (name, data) for market indices or summary
ticker_entries = []  # list of (symbol, data) for individual tickers

# Identify market data section (if any)
market_section = None
if "market" in index_data:
    market_section = index_data["market"]
elif "indices" in index_data:
    market_section = index_data["indices"]

if market_section:
    if isinstance(market_section, dict):
        # If dict, it might be a single summary or multiple indices keyed by name
        # Check if values are dicts (indicating multiple entries)
        multiple = any(isinstance(v, dict) for v in market_section.values())
        if multiple:
            for name, data in market_section.items():
                if isinstance(data, dict):
                    market_entries.append((name, data))
        else:
            # Single market summary (all values are scalar)
            market_entries.append(("Market", market_section))
    elif isinstance(market_section, list):
        for item in market_section:
            if isinstance(item, dict):
                name = item.get("symbol") or item.get("name") or item.get("index") or "Market"
                market_entries.append((name, item))

# Identify ticker data section
if "tickers" in index_data:
    tickers_section = index_data["tickers"]
elif "data" in index_data:
    tickers_section = index_data["data"]
else:
    # If no explicit section, assume index_data itself is tickers dict
    tickers_section = index_data

if isinstance(tickers_section, dict):
    for sym, data in tickers_section.items():
        ticker_entries.append((sym, data))
elif isinstance(tickers_section, list):
    for item in tickers_section:
        if isinstance(item, dict):
            sym = item.get("symbol") or item.get("ticker") or item.get("name")
            if sym:
                # Make a shallow copy to avoid modifying original when adding symbol
                data_copy = item.copy()
                ticker_entries.append((sym, data_copy))

# Build combined report list
# Process market entries first (market indices or summary)
for name, data in market_entries:
    flat = flatten_dict(data)
    # Ensure a unified 'symbol' field
    symbol = name
    if "symbol" in flat:
        symbol = flat["symbol"]
    flat["symbol"] = symbol
    # Attach market news if this is the sole market entry
    # (If multiple indices exist, general news will be added as separate entry later)
    if len(market_entries) == 1 and market_news:
        flat["news"] = market_news
    report_list.append(flat)

# Process ticker entries
for sym, data in ticker_entries:
    flat = flatten_dict(data)
    flat["symbol"] = sym
    if sym in news_by_ticker:
        flat["news"] = news_by_ticker[sym]
    report_list.append(flat)

# If there are general market news items and multiple market indices (or none identified),
# add a separate entry to report for "MARKET" news.
if market_news and not (len(market_entries) == 1):
    report_list.insert(0, {"symbol": "MARKET", "news": market_news})

# Write the combined JSON report
with open("docs/report.json", "w", encoding="utf-8") as f:
    json.dump(report_list, f, ensure_ascii=False, indent=2)

# Determine report date (use current date if not specified in data)
report_date = datetime.utcnow().strftime("%Y-%m-%d")
for key in ("date", "last_updated", "report_date"):
    if key in index_data and isinstance(index_data[key], str):
        report_date = index_data[key]
        break

# Generate Markdown summary
md_lines = []
md_lines.append(f"# Daily Market Report for {report_date}")
md_lines.append("")  # blank line

# Market summary section (if any market entries present)
if market_entries:
    md_lines.append("## Market Summary")
    for name, data in market_entries:
        # Prefer a descriptive name if available
        display_name = name
        if isinstance(data, dict):
            if data.get("shortName"):
                display_name = data["shortName"]
            elif data.get("name"):
                display_name = data["name"]
        # Flatten data for easier field access
        flat = flatten_dict(data) if isinstance(data, dict) else {}
        # Identify fields for price, change, percent
        price = None
        change = None
        percent = None
        for k, v in flat.items():
            lk = k.lower()
            if price is None and lk in ("price", "close", "last", "regularmarketprice"):
                price = v
            if change is None and lk in ("change", "change_amount", "regularmarketchange"):
                change = v
            if percent is None and ("percent" in lk or "changepercent" in lk):
                percent = v
        # Convert to floats for formatting
        try:
            price_val = float(price)
        except:
            price_val = None
        try:
            change_val = float(change)
        except:
            change_val = None
        try:
            percent_val = float(str(percent).replace("%", "").strip())
        except:
            percent_val = None

        # Construct summary sentence
        if price_val is None:
            summary = f"{display_name}: closed"
        else:
            price_str = f"{price_val:.2f}".rstrip("0").rstrip(".")
            if change_val is None and percent_val is None:
                summary = f"{display_name} closed at {price_str}"
            else:
                # Determine direction
                if percent_val is None and change_val is not None:
                    percent_val = (change_val / (price_val - change_val) * 100) if price_val and change_val else None
                if change_val is None and percent_val is not None:
                    change_val = (percent_val / 100.0) * (price_val if percent_val != 0 else 0)
                # Format changes
                change_str = f"{change_val:.2f}".rstrip("0").rstrip(".") if change_val is not None else "0"
                percent_str = f"{percent_val:.2f}%".rstrip("0").rstrip(".") if percent_val is not None else "0%"
                if change_val is not None and change_val > 0:
                    summary = f"{display_name} rose {percent_str} (up {change_str}) to {price_str}"
                elif change_val is not None and change_val < 0:
                    summary = f"{display_name} fell {percent_str} (down {change_str}) to {price_str}"
                else:
                    summary = f"{display_name} closed unchanged at {price_str}"
        md_lines.append(f"- {summary}")
    md_lines.append("")

# Ticker performance section
if ticker_entries:
    md_lines.append("## Ticker Performance")
    for sym, data in ticker_entries:
        # Combine symbol and company name if available
        display_name = sym
        if isinstance(data, dict):
            if data.get("shortName"):
                display_name = f"{sym} ({data['shortName']})"
            elif data.get("name") and data.get("name") != sym:
                display_name = f"{sym} ({data['name']})"
        flat = flatten_dict(data) if isinstance(data, dict) else {}
        # Identify price, change, percent
        price = None; change = None; percent = None
        for k, v in flat.items():
            lk = k.lower()
            if price is None and lk in ("price", "close", "last", "regularmarketprice"):
                price = v
            if change is None and lk in ("change", "change_amount", "regularmarketchange"):
                change = v
            if percent is None and ("percent" in lk and "change" in lk or "changepercent" in lk):
                percent = v
        try:
            price_val = float(price)
        except:
            price_val = None
        try:
            change_val = float(change)
        except:
            change_val = None
        try:
            percent_val = float(str(percent).replace("%", "").strip())
        except:
            percent_val = None

        if price_val is None:
            perf = f"{display_name}: n/a"
        else:
            price_str = f"{price_val:.2f}".rstrip("0").rstrip(".")
            if change_val is None and percent_val is None:
                perf = f"{display_name} closed at {price_str}"
            else:
                if percent_val is None and change_val is not None:
                    percent_val = (change_val / (price_val - change_val) * 100) if price_val and change_val else None
                if change_val is None and percent_val is not None:
                    change_val = (percent_val / 100.0) * (price_val if percent_val != 0 else 0)
                change_str = f"{change_val:.2f}".rstrip("0").rstrip(".") if change_val is not None else "0"
                percent_str = f"{percent_val:.2f}%".rstrip("0").rstrip(".") if percent_val is not None else "0%"
                if change_val is not None and change_val > 0:
                    perf = f"{display_name} rose {percent_str} (up {change_str}) to {price_str}"
                elif change_val is not None and change_val < 0:
                    perf = f"{display_name} fell {percent_str} (down {change_str}) to {price_str}"
                else:
                    perf = f"{display_name} closed unchanged at {price_str}"
        md_lines.append(f"- {perf}")
    md_lines.append("")

# News highlights section
all_tickers_with_news = list(news_by_ticker.keys())
if market_news or all_tickers_with_news:
    md_lines.append("## News Highlights")
    # General market news first
    for item in market_news:
        if isinstance(item, dict):
            title = item.get("headline") or item.get("title") or item.get("summary") or ""
            url = item.get("url") or item.get("link")
        else:
            title = str(item)
            url = None
        if title:
            if url:
                md_lines.append(f"- [Market] [{title}]({url})")
            else:
                md_lines.append(f"- [Market] {title}")
    # Ticker-specific news
    for ticker, news_list in news_by_ticker.items():
        for item in news_list:
            if isinstance(item, dict):
                title = item.get("headline") or item.get("title") or item.get("summary") or ""
                url = item.get("url") or item.get("link")
            else:
                title = str(item)
                url = None
            if title:
                if url:
                    md_lines.append(f"- [{ticker}] [{title}]({url})")
                else:
                    md_lines.append(f"- [{ticker}] {title}")
    md_lines.append("")

# Write the markdown report
with open("docs/report.md", "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines))

# Generate HTML table (for standalone page and index insertion)
# Compose table rows from report_list
rows_html = ""
for entry in report_list:
    # Only include entries that have price data (skip pure news entries)
    has_price = any(key.lower() in ("price", "close", "last", "regularmarketprice") for key in entry.keys())
    if not has_price:
        continue
    sym = entry.get("symbol", "")
    # Extract values for price, change, percent
    price_val = None; change_val = None; percent_val = None
    for k, v in entry.items():
        lk = k.lower()
        if price_val is None and lk in ("price", "close", "last", "regularmarketprice"):
            price_val = v
        if change_val is None and lk in ("change", "change_amount", "regularmarketchange"):
            change_val = v
        if percent_val is None and ("percent" in lk and "change" in lk):
            percent_val = v
    try:
        price_val = float(price_val)
    except:
        pass
    try:
        change_val = float(change_val)
    except:
        pass
    try:
        percent_val = float(str(percent_val).replace("%", "").strip())
    except:
        pass

    # Format values for table display
    if isinstance(price_val, float):
        price_str = f"{price_val:.2f}"
        if price_str.endswith(".00"):
            price_str = price_str[:-3]
    else:
        price_str = str(price_val) if price_val is not None else ""
    if isinstance(change_val, float):
        if change_val > 0:
            change_str = f"+{change_val:.2f}"
        elif change_val < 0:
            change_str = f"{change_val:.2f}"
        else:
            change_str = "0.00"
    else:
        change_str = str(change_val) if change_val is not None else ""
    if isinstance(percent_val, float):
        if percent_val > 0:
            percent_str = f"+{percent_val:.2f}%"
        elif percent_val < 0:
            percent_str = f"{percent_val:.2f}%"
        else:
            percent_str = "0.00%"
    else:
        percent_str = str(percent_val) if percent_val is not None else ""
    rows_html += (f"<tr><td>{sym}</td>"
                  f"<td>{price_str}</td>"
                  f"<td>{change_str}</td>"
                  f"<td>{percent_str}</td></tr>\n")

# Full table HTML string
table_html = (
    '<table id="daily-report-table" border="1">\n'
    '  <thead><tr><th>Symbol</th><th>Price</th><th>Change</th><th>% Change</th></tr></thead>\n'
    '  <tbody>\n' + rows_html + '  </tbody>\n</table>'
)

# Write standalone HTML table page
html_page = (f"<!DOCTYPE html>\n<html>\n<head>\n"
             f"  <meta charset=\"UTF-8\">\n  <title>Daily Report Table</title>\n</head>\n"
             f"<body>\n  <h1>Daily Market Report Table for {report_date}</h1>\n  {table_html}\n</body>\n</html>")
with open("docs/report_table.html", "w", encoding="utf-8") as f:
    f.write(html_page)

# If main index.html exists, inject the updated charts list and table
if os.path.exists("docs/index.html"):
    with open("docs/index.html", "r", encoding="utf-8") as f:
        index_html = f.read()
    # Update charts list using filelist.json
    try:
        with open("docs/filelist.json", "r", encoding="utf-8") as f:
            file_list = json.load(f)
    except:
        file_list = []
    files = []
    if isinstance(file_list, dict):
        # If filelist is a dict, combine all values
        for val in file_list.values():
            if isinstance(val, list):
                files.extend(val)
            elif isinstance(val, str):
                files.append(val)
    elif isinstance(file_list, list):
        files = file_list
    # Normalize file names (strip any path, ensure .png)
    chart_files = []
    for fname in files:
        name = fname.split("/")[-1]
        if name:
            chart_files.append(name)
    chart_files.sort()
    items_html = ""
    for name in chart_files:
        items_html += f"    <li><a href=\"charts/{name}\">{name}</a></li>\n"
    # Replace content between CHARTS_LIST_START and CHARTS_LIST_END markers
    index_html = re.sub(r'<!-- CHARTS_LIST_START -->(.*?)<!-- CHARTS_LIST_END -->',
                        f'<!-- CHARTS_LIST_START -->\n{items_html}    <!-- CHARTS_LIST_END -->',
                        index_html, flags=re.DOTALL)
    # Remove any old table and insert the updated table at bottom of body
    index_html = re.sub(r'<table id="daily-report-table".*?</table>', "", index_html, flags=re.DOTALL)
    if "</body>" in index_html:
        index_html = index_html.replace("</body>", f"{table_html}\n</body>")
    else:
        index_html += f"\n{table_html}"
    # Write back the updated index.html
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(index_html)
