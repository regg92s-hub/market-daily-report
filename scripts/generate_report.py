#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_report.py  -  Market Daily Report
Versjon: 2026-05-30-northstar-v4

Ny i v4:
- RSI daily, weekly og monthly (alle tre timeframes)
- MACD standard 12/26/9 + MACD14 (14/28/9)
- 3yr MA avstand (SMA156 weekly): nær = bra, langt over = dårlig, under = potensiale
- 36WMA avstand som kortsiktig MA-filter
- Northstar score 0-100 av alle datapunkter
- Sektorscore (snitt): Aksjer, Tech, Edelmetaller, Råvarer, Valuta, Crypto, Renter
- Instrumenter sortert etter score, alle datapunkter vist
- 9 ratio-charts
- 4-panel mørke charts: pris+MA, RSI, MACD, MACD14
"""
import os, json, time, math, re, html
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import urlparse

import requests
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

VERSION = "2026-05-30-northstar-v4"
import base64 as _b64mod
PORTFOLIO_HTML_B64 = (
    "PCFkb2N0eXBlIGh0bWw+CjxodG1sIGxhbmc9Im5vIj4KPGhlYWQ+CjxtZXRhIGNoYXJzZXQ9InV0Zi04Ij4KPHRpdGxlPlBvcnRl"
    "ZiZvc2xhc2g7bGplPC90aXRsZT4KPG1ldGEgbmFtZT0idmlld3BvcnQiIGNvbnRlbnQ9IndpZHRoPWRldmljZS13aWR0aCxpbml0"
    "aWFsLXNjYWxlPTEiPgo8c3R5bGU+Cjpyb290ey0tYmc6IzBiMGQxMDstLXBhbmVsOiMxMjE2MWM7LS1wYW5lbDI6IzE3MWMyMzst"
    "LXRleHQ6I2U3ZWRmMzstLW11dGVkOiM5YWE3YjU7LS1ib3JkZXI6IzI3MzEzZDstLWFjY2VudDojNWFhOWZmfQoqe2JveC1zaXpp"
    "bmc6Ym9yZGVyLWJveH0KYm9keXttYXJnaW46MDtmb250LWZhbWlseTpzeXN0ZW0tdWksLWFwcGxlLXN5c3RlbSxzYW5zLXNlcmlm"
    "O2JhY2tncm91bmQ6dmFyKC0tYmcpO2NvbG9yOnZhcigtLXRleHQpO2xpbmUtaGVpZ2h0OjEuNDV9Ci53cmFwe21heC13aWR0aDox"
    "NjAwcHg7bWFyZ2luOjAgYXV0bztwYWRkaW5nOjIwcHggMTZweCA0MHB4fQpoMXttYXJnaW46MCAwIDRweDtmb250LXNpemU6MjRw"
    "eH1oMnttYXJnaW46MCAwIDZweDtmb250LXNpemU6MThweH0KLnRvcG5vdGV7Y29sb3I6dmFyKC0tbXV0ZWQpO21hcmdpbjowIDAg"
    "MThweDtmb250LXNpemU6MTNweH0KLnRhYnN7ZGlzcGxheTpmbGV4O2dhcDo4cHg7bWFyZ2luOjAgMCAxOHB4O2JvcmRlci1ib3R0"
    "b206MXB4IHNvbGlkIHZhcigtLWJvcmRlcil9Ci50YWJ7cGFkZGluZzoxMHB4IDE4cHg7Y29sb3I6dmFyKC0tbXV0ZWQpO3RleHQt"
    "ZGVjb3JhdGlvbjpub25lO2ZvbnQtc2l6ZToxNHB4O2ZvbnQtd2VpZ2h0OjYwMDtib3JkZXItYm90dG9tOjJweCBzb2xpZCB0cmFu"
    "c3BhcmVudDttYXJnaW4tYm90dG9tOi0xcHh9Ci50YWI6aG92ZXJ7Y29sb3I6dmFyKC0tdGV4dCl9LnRhYi5hY3RpdmV7Y29sb3I6"
    "dmFyKC0tdGV4dCk7Ym9yZGVyLWJvdHRvbS1jb2xvcjp2YXIoLS1hY2NlbnQpfQouc2VjdGlvbnttYXJnaW46MCAwIDIycHg7cGFk"
    "ZGluZzoxNnB4O2JvcmRlcjoxcHggc29saWQgdmFyKC0tYm9yZGVyKTtib3JkZXItcmFkaXVzOjE0cHg7YmFja2dyb3VuZDp2YXIo"
    "LS1wYW5lbCl9Ci5kaXNjbGFpbWVye2ZvbnQtc2l6ZToxMnB4O2NvbG9yOnZhcigtLW11dGVkKTtiYWNrZ3JvdW5kOiMxYTE0MDc7"
    "Ym9yZGVyOjFweCBzb2xpZCAjM2EyZTEwO2JvcmRlci1yYWRpdXM6MTBweDtwYWRkaW5nOjEwcHggMTRweDttYXJnaW4tYm90dG9t"
    "OjE4cHh9Ci5ncmlkMntkaXNwbGF5OmdyaWQ7Z3JpZC10ZW1wbGF0ZS1jb2x1bW5zOjFmciAxZnI7Z2FwOjE4cHh9CkBtZWRpYSht"
    "YXgtd2lkdGg6OTAwcHgpey5ncmlkMntncmlkLXRlbXBsYXRlLWNvbHVtbnM6MWZyfX0KLmNhcC1yb3d7ZGlzcGxheTpmbGV4O2Zs"
    "ZXgtd3JhcDp3cmFwO2dhcDoxMnB4O2FsaWduLWl0ZW1zOmZsZXgtZW5kO21hcmdpbi10b3A6MTBweH0KLmZpZWxke2Rpc3BsYXk6"
    "ZmxleDtmbGV4LWRpcmVjdGlvbjpjb2x1bW47Z2FwOjRweH0KLmZpZWxkIGxhYmVse2ZvbnQtc2l6ZToxMXB4O2NvbG9yOnZhcigt"
    "LW11dGVkKX0KLmZpZWxkIGlucHV0e2JhY2tncm91bmQ6dmFyKC0tcGFuZWwyKTtib3JkZXI6MXB4IHNvbGlkIHZhcigtLWJvcmRl"
    "cik7Ym9yZGVyLXJhZGl1czo4cHg7Y29sb3I6dmFyKC0tdGV4dCk7cGFkZGluZzo4cHggMTBweDtmb250LXNpemU6MTRweDt3aWR0"
    "aDoxNjBweH0KLmZpZWxkIGlucHV0OmZvY3Vze291dGxpbmU6bm9uZTtib3JkZXItY29sb3I6dmFyKC0tYWNjZW50KX0KLmJ0bnti"
    "YWNrZ3JvdW5kOnZhcigtLWFjY2VudCk7Y29sb3I6IzA2MTIxZjtib3JkZXI6bm9uZTtib3JkZXItcmFkaXVzOjhweDtwYWRkaW5n"
    "OjlweCAxNnB4O2ZvbnQtc2l6ZToxM3B4O2ZvbnQtd2VpZ2h0OjcwMDtjdXJzb3I6cG9pbnRlcn0KLmJ0bjpob3ZlcntmaWx0ZXI6"
    "YnJpZ2h0bmVzcygxLjEpfQouYnRuLnNlY29uZGFyeXtiYWNrZ3JvdW5kOnZhcigtLXBhbmVsMik7Y29sb3I6dmFyKC0tdGV4dCk7"
    "Ym9yZGVyOjFweCBzb2xpZCB2YXIoLS1ib3JkZXIpfQoua3Bpe2Rpc3BsYXk6ZmxleDtnYXA6MThweDtmbGV4LXdyYXA6d3JhcDtt"
    "YXJnaW4tdG9wOjEycHh9Ci5rcGkgLmt7YmFja2dyb3VuZDp2YXIoLS1wYW5lbDIpO2JvcmRlcjoxcHggc29saWQgdmFyKC0tYm9y"
    "ZGVyKTtib3JkZXItcmFkaXVzOjEwcHg7cGFkZGluZzoxMHB4IDE0cHg7bWluLXdpZHRoOjEzMHB4fQoua3BpIC5rIC5sYmx7Zm9u"
    "dC1zaXplOjExcHg7Y29sb3I6dmFyKC0tbXV0ZWQpfQoua3BpIC5rIC52YWx7Zm9udC1zaXplOjIwcHg7Zm9udC13ZWlnaHQ6NzAw"
    "O21hcmdpbi10b3A6MnB4fQp0YWJsZXt3aWR0aDoxMDAlO2JvcmRlci1jb2xsYXBzZTpjb2xsYXBzZTtmb250LXNpemU6MTNweDtt"
    "YXJnaW4tdG9wOjEwcHh9CnRoe2JhY2tncm91bmQ6dmFyKC0tcGFuZWwyKTtwYWRkaW5nOjdweCA5cHg7dGV4dC1hbGlnbjpsZWZ0"
    "O2JvcmRlci1ib3R0b206MXB4IHNvbGlkIHZhcigtLWJvcmRlcik7Y29sb3I6dmFyKC0tbXV0ZWQpO2ZvbnQtd2VpZ2h0OjYwMH0K"
    "dGR7cGFkZGluZzo2cHggOXB4O2JvcmRlci1ib3R0b206MXB4IHNvbGlkICMxZTI1MzA7dmVydGljYWwtYWxpZ246bWlkZGxlfQp0"
    "cjpsYXN0LWNoaWxkIHRke2JvcmRlci1ib3R0b206bm9uZX0KLnBpbGx7ZGlzcGxheTppbmxpbmUtYmxvY2s7cGFkZGluZzoycHgg"
    "OHB4O2JvcmRlci1yYWRpdXM6N3B4O2ZvbnQtc2l6ZToxMnB4O2ZvbnQtd2VpZ2h0OjcwMH0KLnJlY3tmb250LXdlaWdodDo3MDB9"
    "Ci5yZWMuYnV5e2NvbG9yOiM1MGM4Nzh9LnJlYy5hZGR7Y29sb3I6IzdlYzg4YX0ucmVjLmhvbGR7Y29sb3I6IzlhYTdiNX0ucmVj"
    "LnRyaW17Y29sb3I6I2YwYTUwMH0ucmVjLnNlbGx7Y29sb3I6I2UwNTA1MH0KLnBvc2lucHV0e3dpZHRoOjgwcHg7YmFja2dyb3Vu"
    "ZDp2YXIoLS1wYW5lbDIpO2JvcmRlcjoxcHggc29saWQgdmFyKC0tYm9yZGVyKTtib3JkZXItcmFkaXVzOjZweDtjb2xvcjp2YXIo"
    "LS10ZXh0KTtwYWRkaW5nOjRweCA2cHg7Zm9udC1zaXplOjEycHh9Ci5sZWdlbmR7Zm9udC1zaXplOjExcHg7Y29sb3I6dmFyKC0t"
    "bXV0ZWQpO2xpbmUtaGVpZ2h0OjEuNzttYXJnaW4tdG9wOjEwcHh9Ci5sZWdlbmQgY29kZXtiYWNrZ3JvdW5kOnZhcigtLXBhbmVs"
    "Mik7cGFkZGluZzoxcHggNXB4O2JvcmRlci1yYWRpdXM6NHB4O2NvbG9yOnZhcigtLXRleHQpfQouaGlzdHttYXgtaGVpZ2h0OjI4"
    "MHB4O292ZXJmbG93LXk6YXV0bzttYXJnaW4tdG9wOjEwcHh9Ci5oaXN0IC5oe3BhZGRpbmc6OHB4IDEwcHg7Ym9yZGVyLWJvdHRv"
    "bToxcHggc29saWQgIzFlMjUzMDtmb250LXNpemU6MTJweH0KLmhpc3QgLmggLnR7Y29sb3I6dmFyKC0tbXV0ZWQpO2ZvbnQtc2l6"
    "ZToxMXB4fQoubXV0ZWR7Y29sb3I6dmFyKC0tbXV0ZWQpfQpzdmcucGlle2Rpc3BsYXk6YmxvY2s7bWFyZ2luOjAgYXV0b30KLmxl"
    "Z2VuZC1waWV7ZGlzcGxheTpmbGV4O2ZsZXgtZGlyZWN0aW9uOmNvbHVtbjtnYXA6NXB4O21hcmdpbi10b3A6OHB4fQoubGVnZW5k"
    "LXBpZSAubGl7ZGlzcGxheTpmbGV4O2FsaWduLWl0ZW1zOmNlbnRlcjtnYXA6OHB4O2ZvbnQtc2l6ZToxMnB4fQoubGVnZW5kLXBp"
    "ZSAuc3d7d2lkdGg6MTJweDtoZWlnaHQ6MTJweDtib3JkZXItcmFkaXVzOjNweDtmbGV4Om5vbmV9CmZvb3RlcnttYXJnaW4tdG9w"
    "OjE4cHg7Y29sb3I6dmFyKC0tbXV0ZWQpO2ZvbnQtc2l6ZToxMnB4fQo8L3N0eWxlPgo8L2hlYWQ+Cjxib2R5Pgo8ZGl2IGNsYXNz"
    "PSJ3cmFwIj4KPG5hdiBjbGFzcz0idGFicyI+CiAgPGEgY2xhc3M9InRhYiIgaHJlZj0iaW5kZXguaHRtbCI+JiMxMjgyMDA7IFRy"
    "ZW5kLW92ZXJzaWt0PC9hPgogIDxhIGNsYXNzPSJ0YWIiIGhyZWY9InJlcG9ydC5odG1sIj4mIzEyODIwMjsgTWFya2V0IERhaWx5"
    "IFJlcG9ydDwvYT4KICA8YSBjbGFzcz0idGFiIGFjdGl2ZSIgaHJlZj0icG9ydGZvbGlvLmh0bWwiPiYjMTI4MTg4OyBQb3J0ZWYm"
    "b3NsYXNoO2xqZTwvYT4KPC9uYXY+CjxoMT5Qb3J0ZWYmb3NsYXNoO2xqZTwvaDE+CjxwIGNsYXNzPSJ0b3Bub3RlIiBpZD0idG9w"
    "bm90ZSI+TGFzdGVyIGRhdGEmaGVsbGlwOzwvcD4KCjxkaXYgY2xhc3M9ImRpc2NsYWltZXIiPgo8c3Ryb25nPkRpdHQgZWdldCBy"
    "YW1tZXZlcmsgJm1kYXNoOyBpa2tlIGZpbmFuc3ImYXJpbmc7ZGdpdm5pbmcuPC9zdHJvbmc+CkRldHRlIHZlcmt0Jm9zbGFzaDt5"
    "ZXQgdmlzZXIgaHZhIGRpbiBOb3J0aHN0YXItbWV0b2Rpa2sgdGlsc2llciBiYXNlcnQgcCZhcmluZzsgdHJlbmQtc2NvcmUsIGlr"
    "a2UgZW4gYW5iZWZhbGluZy4KQWxsIGRhdGEgZXIgdGVrbmlzayBvZyBrYW4gdiZhZWxpZztyZSBmZWlsIGVsbGVyIHV0ZGF0ZXJ0"
    "LiBEdSB0YXIgYWxsZSBiZXNsdXRuaW5nZXIgc2Vsdi4KPC9kaXY+Cgo8ZGl2IGNsYXNzPSJzZWN0aW9uIj4KICA8aDI+JiMxMjgx"
    "NzY7IEthcGl0YWw8L2gyPgogIDxkaXYgY2xhc3M9ImNhcC1yb3ciPgogICAgPGRpdiBjbGFzcz0iZmllbGQiPgogICAgICA8bGFi"
    "ZWw+U3RhcnRrYXBpdGFsIChrcik8L2xhYmVsPgogICAgICA8aW5wdXQgdHlwZT0ibnVtYmVyIiBpZD0ic3RhcnRDYXAiIHBsYWNl"
    "aG9sZGVyPSIxMDAwMDAiIHN0ZXA9IjEwMDAiPgogICAgPC9kaXY+CiAgICA8ZGl2IGNsYXNzPSJmaWVsZCI+CiAgICAgIDxsYWJl"
    "bD5OeXR0IGlubnNrdWRkIChrcik8L2xhYmVsPgogICAgICA8aW5wdXQgdHlwZT0ibnVtYmVyIiBpZD0iYWRkQ2FwIiBwbGFjZWhv"
    "bGRlcj0iMCIgc3RlcD0iMTAwMCI+CiAgICA8L2Rpdj4KICAgIDxidXR0b24gY2xhc3M9ImJ0biIgaWQ9ImFwcGx5Q2FwIj5PcHBk"
    "YXRlciBrYXBpdGFsPC9idXR0b24+CiAgICA8YnV0dG9uIGNsYXNzPSJidG4gc2Vjb25kYXJ5IiBpZD0icmViYWxhbmNlIj5PbWZv"
    "cmRlbCBuJmFyaW5nOyAodWtlbnRsaWcpPC9idXR0b24+CiAgPC9kaXY+CiAgPGRpdiBjbGFzcz0ia3BpIj4KICAgIDxkaXYgY2xh"
    "c3M9ImsiPjxkaXYgY2xhc3M9ImxibCI+VG90YWwga2FwaXRhbDwvZGl2PjxkaXYgY2xhc3M9InZhbCIgaWQ9ImtUb3RhbCI+Jm5k"
    "YXNoOzwvZGl2PjwvZGl2PgogICAgPGRpdiBjbGFzcz0iayI+PGRpdiBjbGFzcz0ibGJsIj5JbnZlc3RlcnQ8L2Rpdj48ZGl2IGNs"
    "YXNzPSJ2YWwiIGlkPSJrSW52ZXN0ZWQiPiZuZGFzaDs8L2Rpdj48L2Rpdj4KICAgIDxkaXYgY2xhc3M9ImsiPjxkaXYgY2xhc3M9"
    "ImxibCI+Q2FzaDwvZGl2PjxkaXYgY2xhc3M9InZhbCIgaWQ9ImtDYXNoIj4mbmRhc2g7PC9kaXY+PC9kaXY+CiAgICA8ZGl2IGNs"
    "YXNzPSJrIj48ZGl2IGNsYXNzPSJsYmwiPkNhc2ggJTwvZGl2PjxkaXYgY2xhc3M9InZhbCIgaWQ9ImtDYXNoUGN0Ij4mbmRhc2g7"
    "PC9kaXY+PC9kaXY+CiAgPC9kaXY+CiAgPGRpdiBjbGFzcz0iY2FwLXJvdyIgc3R5bGU9Im1hcmdpbi10b3A6MTRweCI+CiAgICA8"
    "ZGl2IGNsYXNzPSJmaWVsZCI+CiAgICAgIDxsYWJlbD5NJmFyaW5nO2wgY2FzaC1idWZmZXIgKCUpPC9sYWJlbD4KICAgICAgPGlu"
    "cHV0IHR5cGU9Im51bWJlciIgaWQ9ImNhc2hUYXJnZXQiIHZhbHVlPSIxNSIgbWluPSIwIiBtYXg9IjEwMCIgc3RlcD0iNSI+CiAg"
    "ICA8L2Rpdj4KICAgIDxkaXYgY2xhc3M9ImZpZWxkIj4KICAgICAgPGxhYmVsPk1ha3MgdmVrdCBwZXIgcG9zaXNqb24gKCUpPC9s"
    "YWJlbD4KICAgICAgPGlucHV0IHR5cGU9Im51bWJlciIgaWQ9Im1heFBvcyIgdmFsdWU9IjI1IiBtaW49IjUiIG1heD0iMTAwIiBz"
    "dGVwPSI1Ij4KICAgIDwvZGl2PgogIDwvZGl2Pgo8L2Rpdj4KCjxkaXYgY2xhc3M9ImdyaWQyIj4KICA8ZGl2IGNsYXNzPSJzZWN0"
    "aW9uIj4KICAgIDxoMj4mIzEyOTUxODsgQW5iZWZhbHQgZm9yZGVsaW5nPC9oMj4KICAgIDxwIGNsYXNzPSJtdXRlZCIgc3R5bGU9"
    "ImZvbnQtc2l6ZToxMnB4Ij5WZWt0ZXQgZXR0ZXIgdHJlbmQtc2NvcmUuIEgmb3NsYXNoO3llcmUgc2NvcmUgPSBzdCZvc2xhc2g7"
    "cnJlIHRpbGxhdHQgdmVrdC4gQ2FzaC1idWZmZXIgaG9sZGVzIGlnamVuLjwvcD4KICAgIDxkaXYgaWQ9InBpZVdyYXAiPjwvZGl2"
    "PgogICAgPGRpdiBjbGFzcz0ibGVnZW5kLXBpZSIgaWQ9InBpZUxlZ2VuZCI+PC9kaXY+CiAgPC9kaXY+CiAgPGRpdiBjbGFzcz0i"
    "c2VjdGlvbiI+CiAgICA8aDI+JiMxMjgyMjE7IFBvc2lzam9uZXIgJmFtcDsgYW5iZWZhbGluZzwvaDI+CiAgICA8cCBjbGFzcz0i"
    "bXV0ZWQiIHN0eWxlPSJmb250LXNpemU6MTJweCI+U2tyaXYgaW5uIG4mYXJpbmc7diZhZWxpZztyZW5kZSB2ZWt0ICglKSBkdSBh"
    "bGxlcmVkZSBlaWVyLiBBbmJlZmFsaW5nZW4gdGFyIGhlbnN5biB0aWwgZWtzaXN0ZXJlbmRlIHBvc2lzam9uZXIuPC9wPgogICAg"
    "PHRhYmxlIGlkPSJwb3NUYWJsZSI+PHRoZWFkPjx0cj4KICAgICAgPHRoPlJhdGlvL0luc3RydW1lbnQ8L3RoPjx0aD5TY29yZTwv"
    "dGg+PHRoPkVpZXIgJTwvdGg+PHRoPk0mYXJpbmc7bCAlPC90aD48dGg+QW5iZWZhbGluZzwvdGg+CiAgICA8L3RyPjwvdGhlYWQ+"
    "PHRib2R5IGlkPSJwb3NCb2R5Ij48L3Rib2R5PjwvdGFibGU+CiAgPC9kaXY+CjwvZGl2PgoKPGRpdiBjbGFzcz0ic2VjdGlvbiI+"
    "CiAgPGgyPiYjMTI4MjAyOyBFbmRyaW5nc2xvZ2c8L2gyPgogIDxwIGNsYXNzPSJtdXRlZCIgc3R5bGU9ImZvbnQtc2l6ZToxMnB4"
    "Ij5IdmVyIG9tZm9yZGVsaW5nIG9nIGthcGl0YWxlbmRyaW5nIGxvZ2dlcyBoZXIgKGxhZ3JldCBsb2thbHQgaSBuZXR0bGVzZXJl"
    "bikuPC9wPgogIDxkaXYgY2xhc3M9Imhpc3QiIGlkPSJoaXN0Qm94Ij48L2Rpdj4KICA8YnV0dG9uIGNsYXNzPSJidG4gc2Vjb25k"
    "YXJ5IiBpZD0iY2xlYXJIaXN0IiBzdHlsZT0ibWFyZ2luLXRvcDoxMHB4Ij5UJm9zbGFzaDttIGxvZ2c8L2J1dHRvbj4KPC9kaXY+"
    "Cgo8ZGl2IGNsYXNzPSJzZWN0aW9uIj4KICA8aDI+JiM4NTA1OyYjNjUwMzk7IFNsaWsgZnVuZ2VyZXIgbW9kZWxsZW48L2gyPgog"
    "IDxkaXYgY2xhc3M9ImxlZ2VuZCI+CiAgPGNvZGU+TSZhcmluZztsICU8L2NvZGU+IGJlcmVnbmVzIGZyYSB0cmVuZC1zY29yZTog"
    "a3VuIHJhdGlvZXIvaW5zdHJ1bWVudGVyIG1lZCBzY29yZSAmZ2U7IDU1IGYmYXJpbmc7ciB0aWxkZWx0IHZla3QuIFZla3QgZXIg"
    "cHJvcG9yc2pvbmFsIG1lZCBzY29yZSBvdmVyIHRlcnNrZWxlbi48YnI+CiAgPGNvZGU+Q2FzaC1idWZmZXI8L2NvZGU+IChzdGFu"
    "ZGFyZCAxNSUpIGhvbGRlcyBhbGx0aWQgaWdqZW4gZiZvc2xhc2g7ciBmb3JkZWxpbmcgJm1kYXNoOyBkdSB0YXIga3VuIHBvc2lz"
    "am9uZXIgbiZhcmluZztyIG5vZSBzZXIgbG92ZW5kZSB1dC48YnI+CiAgPGNvZGU+TWFrcyB2ZWt0PC9jb2RlPiBwZXIgcG9zaXNq"
    "b24gaGluZHJlciBhdCBhbHQgc2FtbGVzIGkgJmVhY3V0ZTtuIGlkJmVhY3V0ZTsuPGJyPgogIDxjb2RlPktKJk9zbGFzaDtQPC9j"
    "b2RlPjogc2NvcmUgJmdlOyA1NSBvZyBkdSBlaWVyIG1pbmRyZSBlbm4gbSZhcmluZztsLiA8Y29kZT5MRUdHIFRJTDwvY29kZT46"
    "IGdvZCBzY29yZSwgbGl0dCB1bmRlciBtJmFyaW5nO2wuPGJyPgogIDxjb2RlPkhPTEQ8L2NvZGU+OiBwb3Npc2pvbiB0YXR0LCBp"
    "a2tlIG92ZXJraiZvc2xhc2g7cHQgZW5uJmFyaW5nOyAmbWRhc2g7IGJlaG9sZGVzIHNlbHYgb20gc2NvcmUgZmFsbGVyLCB0aWwg"
    "ZGVuIGJsaXIgPGVtPnZlbGRpZzwvZW0+IG92ZXJraiZvc2xhc2g7cHQuPGJyPgogIDxjb2RlPlNLQUxFUiBBVjwvY29kZT46IGt1"
    "biBuJmFyaW5nO3IgUlNJICZnZTsgNjUgT0cgTUFDRC1oaXN0ICZnZTsgMiBPRyBzdHJ1a2tldCBsYW5ndCBvdmVyIDM2V01BLzN5"
    "ciBNQSAmbWRhc2g7IGVsbGVyIG4mYXJpbmc7ciBkdSB0cmVuZ2VyIGNhc2ggdGlsIGtsYXJ0IGJlZHJlIG11bGlnaGV0ZXIuPGJy"
    "PgogIDxjb2RlPkZ1bGwgcG9ydGVmJm9zbGFzaDtsamU8L2NvZGU+OiBodmlzIGFsdCBlciBmdWxsdCBvZyBjYXNoIGVyIHVuZGVy"
    "IG0mYXJpbmc7bCwgZm9yZXNsJmFyaW5nO3Mga3VuIHNraWZ0ZSBuJmFyaW5nO3IgZW4gc3Zha2VyZSBwb3Npc2pvbiBrYW4gdmlr"
    "ZSBmb3IgZW4ga2xhcnQgc3RlcmtlcmUuCiAgPC9kaXY+CjwvZGl2PgoKPGZvb3Rlcj5EYXRhOiA8YSBocmVmPSJpbmRleC5qc29u"
    "IiBzdHlsZT0iY29sb3I6dmFyKC0tbXV0ZWQpIj5pbmRleC5qc29uPC9hPiAmYnVsbDsgTGFncmVzIGxva2FsdCBpIGRpbiBuZXR0"
    "bGVzZXIgKGxvY2FsU3RvcmFnZSk8L2Zvb3Rlcj4KPC9kaXY+Cgo8c2NyaXB0Pgpjb25zdCBMU19LRVkgPSAibnNfcG9ydGZvbGlv"
    "X3YxIjsKY29uc3QgQ0FTSF9USFJFU0hPTEQgPSA1NTsgICAgIC8vIG1pbiBzY29yZSBmb3Igw6UgZsOlIHRpbGRlbHQgdmVrdApj"
    "b25zdCBPVkVSQk9VR0hUX1JTSSA9IDY1Owpjb25zdCBPVkVSQk9VR0hUX01BQ0QgPSAyOwpjb25zdCBTVFJFVENIXzM2ID0gMC4y"
    "MDsgICAgICAgLy8gMjAlIG92ZXIgMzZNQQpjb25zdCBTVFJFVENIXzNZUiA9IDAuMzA7ICAgICAgLy8gMzAlIG92ZXIgM3lyCgps"
    "ZXQgU1RBVEUgPSBsb2FkU3RhdGUoKTsKbGV0IERBVEEgPSBudWxsOwoKZnVuY3Rpb24gbG9hZFN0YXRlKCl7CiAgdHJ5eyBjb25z"
    "dCBzID0gSlNPTi5wYXJzZShsb2NhbFN0b3JhZ2UuZ2V0SXRlbShMU19LRVkpKTsgaWYocykgcmV0dXJuIHM7IH1jYXRjaChlKXt9"
    "CiAgcmV0dXJuIHsgc3RhcnRDYXA6IDEwMDAwMCwgY2FzaDogMTAwMDAwLCBpbnZlc3RlZDogMCwgcG9zaXRpb25zOiB7fSwgaGlz"
    "dG9yeTogW10sIGNhc2hUYXJnZXQ6IDE1LCBtYXhQb3M6IDI1IH07Cn0KZnVuY3Rpb24gc2F2ZVN0YXRlKCl7IGxvY2FsU3RvcmFn"
    "ZS5zZXRJdGVtKExTX0tFWSwgSlNPTi5zdHJpbmdpZnkoU1RBVEUpKTsgfQpmdW5jdGlvbiBrcihuKXsgcmV0dXJuIChNYXRoLnJv"
    "dW5kKG4pKS50b0xvY2FsZVN0cmluZygibm8tTk8iKSArICIga3IiOyB9CmZ1bmN0aW9uIHBjdChuKXsgcmV0dXJuIChuKS50b0Zp"
    "eGVkKDEpICsgIiUiOyB9CmZ1bmN0aW9uIG5vdygpeyByZXR1cm4gbmV3IERhdGUoKS50b0xvY2FsZVN0cmluZygibm8tTk8iKTsg"
    "fQoKZnVuY3Rpb24gbG9nSGlzdChtc2cpewogIFNUQVRFLmhpc3RvcnkudW5zaGlmdCh7IHQ6IG5vdygpLCBtc2cgfSk7CiAgaWYo"
    "U1RBVEUuaGlzdG9yeS5sZW5ndGggPiAyMDApIFNUQVRFLmhpc3RvcnkucG9wKCk7Cn0KCmFzeW5jIGZ1bmN0aW9uIGluaXQoKXsK"
    "ICB0cnl7CiAgICBjb25zdCByID0gYXdhaXQgZmV0Y2goImluZGV4Lmpzb24iLCB7Y2FjaGU6Im5vLXN0b3JlIn0pOwogICAgREFU"
    "QSA9IGF3YWl0IHIuanNvbigpOwogICAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInRvcG5vdGUiKS5pbm5lckhUTUwgPQogICAg"
    "ICAiVHJlbmQtZGF0YSBnZW5lcmVydDogIiArIChEQVRBLmdlbmVyYXRlZF9sb2NhbHx8IiIpICsgIiAmYnVsbDsgIiArIChEQVRB"
    "LnZlcnNpb258fCIiKTsKICB9Y2F0Y2goZSl7CiAgICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgidG9wbm90ZSIpLnRleHRDb250"
    "ZW50ID0gIkt1bm5lIGlra2UgbGFzdGUgaW5kZXguanNvbjogIiArIGU7CiAgICByZXR1cm47CiAgfQogIC8vIGluaXQgY2FwaXRh"
    "bCBpbnB1dHMKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgic3RhcnRDYXAiKS52YWx1ZSA9IFNUQVRFLnN0YXJ0Q2FwOwogIGRv"
    "Y3VtZW50LmdldEVsZW1lbnRCeUlkKCJjYXNoVGFyZ2V0IikudmFsdWUgPSBTVEFURS5jYXNoVGFyZ2V0OwogIGRvY3VtZW50Lmdl"
    "dEVsZW1lbnRCeUlkKCJtYXhQb3MiKS52YWx1ZSA9IFNUQVRFLm1heFBvczsKICByZW5kZXIoKTsKfQoKLy8gQnlnZyBrYW5kaWRh"
    "dGxpc3RlIGZyYSB0cmVuZF9yYXRpb3MgKyBpbnN0cnVtZW50LXNjb3JlcwpmdW5jdGlvbiBjYW5kaWRhdGVzKCl7CiAgY29uc3Qg"
    "b3V0ID0gW107CiAgKERBVEEudHJlbmRfcmF0aW9zfHxbXSkuZm9yRWFjaCh0PT57CiAgICBvdXQucHVzaCh7IGlkOiB0LnJpZCwg"
    "bGFiZWw6IHQubGFiZWwsIHNjb3JlOiB0LnNjb3JlLAogICAgICByc2k6IHQucXJzaSA/PyB0Lm1yc2ksIG1hY2Q6IHQubWFjZF9x"
    "ID8/IHQubWFjZF9tLAogICAgICBkMzY6IHQuZGlzdDM2cSA/PyB0LmRpc3QzNm0sIGQzeXI6IG51bGwsIGtpbmQ6InJhdGlvIiB9"
    "KTsKICB9KTsKICByZXR1cm4gb3V0Owp9CgovLyBCZXJlZ24gbcOlbC12ZWt0ZXIgZnJhIHNjb3JlCmZ1bmN0aW9uIHRhcmdldFdl"
    "aWdodHMoY2FuZHMpewogIGNvbnN0IGNhc2hUYXJnZXQgPSBjbGFtcChwYXJzZUZsb2F0KGRvY3VtZW50LmdldEVsZW1lbnRCeUlk"
    "KCJjYXNoVGFyZ2V0IikudmFsdWUpfHwxNSwgMCwgMTAwKTsKICBjb25zdCBtYXhQb3MgPSBjbGFtcChwYXJzZUZsb2F0KGRvY3Vt"
    "ZW50LmdldEVsZW1lbnRCeUlkKCJtYXhQb3MiKS52YWx1ZSl8fDI1LCA1LCAxMDApOwogIGNvbnN0IGludmVzdGFibGUgPSAxMDAg"
    "LSBjYXNoVGFyZ2V0OwogIGNvbnN0IGVsaWcgPSBjYW5kcy5maWx0ZXIoYyA9PiBjLnNjb3JlID49IENBU0hfVEhSRVNIT0xEKTsK"
    "ICBjb25zdCBzdW1FeGNlc3MgPSBlbGlnLnJlZHVjZSgoYSxjKT0+YSsoYy5zY29yZS1DQVNIX1RIUkVTSE9MRCksMCk7CiAgY29u"
    "c3Qgd2VpZ2h0cyA9IHt9OwogIGlmKHN1bUV4Y2VzcyA+IDApewogICAgZWxpZy5mb3JFYWNoKGM9PnsKICAgICAgbGV0IHcgPSBp"
    "bnZlc3RhYmxlICogKGMuc2NvcmUtQ0FTSF9USFJFU0hPTEQpL3N1bUV4Y2VzczsKICAgICAgd2VpZ2h0c1tjLmlkXSA9IE1hdGgu"
    "bWluKHcsIG1heFBvcyk7CiAgICB9KTsKICAgIC8vIHJlLW5vcm1hbGlzZXIgaHZpcyBtYXhQb3Mga3V0dGV0IG5vZQogICAgbGV0"
    "IHRvdCA9IE9iamVjdC52YWx1ZXMod2VpZ2h0cykucmVkdWNlKChhLGIpPT5hK2IsMCk7CiAgICBpZih0b3Q+MCAmJiB0b3QgPCBp"
    "bnZlc3RhYmxlKXsKICAgICAgLy8gZm9yZGVsIHJlc3RlbiBww6UgZGUgc29tIGlra2UgZXIgY2FwcGVkCiAgICAgIC8vIGVua2Vs"
    "IHRpbG7DpnJtaW5nOiBza2FsZXIgb3BwIHByb3BvcnNqb25hbHQgaW5uZW5mb3IgbWF4UG9zCiAgICAgIGxldCByb29tID0gZWxp"
    "Zy5maWx0ZXIoYz0+d2VpZ2h0c1tjLmlkXSA8IG1heFBvcyk7CiAgICAgIGxldCBkZWZpY2l0ID0gaW52ZXN0YWJsZSAtIHRvdDsK"
    "ICAgICAgbGV0IHJvb21TdW0gPSByb29tLnJlZHVjZSgoYSxjKT0+YSsobWF4UG9zLXdlaWdodHNbYy5pZF0pLDApOwogICAgICBp"
    "Zihyb29tU3VtPjApIHJvb20uZm9yRWFjaChjPT57IHdlaWdodHNbYy5pZF0rPSBkZWZpY2l0KihtYXhQb3Mtd2VpZ2h0c1tjLmlk"
    "XSkvcm9vbVN1bTsgfSk7CiAgICB9CiAgfQogIHJldHVybiB7IHdlaWdodHMsIGNhc2hUYXJnZXQsIG1heFBvcyB9Owp9CgpmdW5j"
    "dGlvbiBjbGFtcCh2LGEsYil7IHJldHVybiBNYXRoLm1heChhLCBNYXRoLm1pbihiLCB2KSk7IH0KCi8vIFJldHVybmVyZXIgY29k"
    "ZSAoc3RhYmlsKSArIGxhYmVsICh2aXNuaW5nKSArIGNscyArIHdoeQpmdW5jdGlvbiByZWNvbW1lbmRhdGlvbihjLCBvd25QY3Qs"
    "IHRhcmdldFBjdCl7CiAgY29uc3QgcnNpID0gYy5yc2kgPz8gNTA7CiAgY29uc3QgbWFjZCA9IGMubWFjZCA/PyAwOwogIGNvbnN0"
    "IGQzNiA9IGMuZDM2ID8/IDA7CiAgY29uc3QgdmVyeU92ZXJib3VnaHQgPSAocnNpID49IE9WRVJCT1VHSFRfUlNJKSAmJiAobWFj"
    "ZCA+PSBPVkVSQk9VR0hUX01BQ0QpICYmIChkMzYgPj0gU1RSRVRDSF8zNik7CiAgaWYob3duUGN0ID4gMCl7CiAgICBpZih2ZXJ5"
    "T3ZlcmJvdWdodCkgcmV0dXJuIHtjb2RlOiJTQ0FMRSIsIGxhYmVsOiJTS0FMRVIgQVYiLCBjbHM6InNlbGwiLCB3aHk6YFZlbGRp"
    "ZyBvdmVya2omb3NsYXNoO3B0IChSU0kgJHtNYXRoLnJvdW5kKHJzaSl9LCBNQUNEIGgmb3NsYXNoO3ksIHN0cnVra2V0ICR7KGQz"
    "NioxMDApLnRvRml4ZWQoMCl9JSlgfTsKICAgIGlmKGMuc2NvcmUgPCAzNSkgcmV0dXJuIHtjb2RlOiJTQ0FMRSIsIGxhYmVsOiJT"
    "S0FMRVIgQVYiLCBjbHM6InRyaW0iLCB3aHk6IlNjb3JlIGJydXR0IG5lZCBpIG5lZ2F0aXYgc29uZSJ9OwogICAgaWYob3duUGN0"
    "IDwgdGFyZ2V0UGN0IC0gMykgcmV0dXJuIHtjb2RlOiJBREQiLCBsYWJlbDoiTEVHRyBUSUwiLCBjbHM6ImFkZCIsIHdoeToiVW5k"
    "ZXIgbSZhcmluZztsdmVrdCwgdHJlbmQgaW50YWt0In07CiAgICByZXR1cm4ge2NvZGU6IkhPTEQiLCBsYWJlbDoiSE9MRCIsIGNs"
    "czoiaG9sZCIsIHdoeToiUG9zaXNqb24gdGF0dCwgaWtrZSBvdmVya2omb3NsYXNoO3B0ICZtZGFzaDsgYmVob2xkIn07CiAgfSBl"
    "bHNlIHsKICAgIGlmKGMuc2NvcmUgPj0gQ0FTSF9USFJFU0hPTEQgJiYgdGFyZ2V0UGN0ID4gMCkgcmV0dXJuIHtjb2RlOiJCVVki"
    "LCBsYWJlbDoiS0omT3NsYXNoO1AiLCBjbHM6ImJ1eSIsIHdoeTpgU2NvcmUgJHtjLnNjb3JlfSAmZ2U7ICR7Q0FTSF9USFJFU0hP"
    "TER9LCBsb3ZlbmRlIGVudHJ5YH07CiAgICByZXR1cm4ge2NvZGU6IldBSVQiLCBsYWJlbDoiQVZWRU5UIiwgY2xzOiJob2xkIiwg"
    "d2h5OmBTY29yZSAke2Muc2NvcmV9IHVuZGVyIHRlcnNrZWwgJHtDQVNIX1RIUkVTSE9MRH1gfTsKICB9Cn0KCmZ1bmN0aW9uIHJl"
    "bmRlcigpewogIGNvbnN0IGNhbmRzID0gY2FuZGlkYXRlcygpOwogIGNvbnN0IHsgd2VpZ2h0cywgY2FzaFRhcmdldCB9ID0gdGFy"
    "Z2V0V2VpZ2h0cyhjYW5kcyk7CgogIC8vIEtQSXMKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgia1RvdGFsIikudGV4dENvbnRl"
    "bnQgPSBrcihTVEFURS5jYXNoICsgU1RBVEUuaW52ZXN0ZWQpOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJrSW52ZXN0ZWQi"
    "KS50ZXh0Q29udGVudCA9IGtyKFNUQVRFLmludmVzdGVkKTsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgia0Nhc2giKS50ZXh0"
    "Q29udGVudCA9IGtyKFNUQVRFLmNhc2gpOwogIGNvbnN0IHRvdGFsID0gU1RBVEUuY2FzaCArIFNUQVRFLmludmVzdGVkOwogIGRv"
    "Y3VtZW50LmdldEVsZW1lbnRCeUlkKCJrQ2FzaFBjdCIpLnRleHRDb250ZW50ID0gdG90YWw+MCA/IHBjdChTVEFURS5jYXNoL3Rv"
    "dGFsKjEwMCkgOiAi4oCTIjsKCiAgLy8gUG9zaXNqb25zdGFiZWxsCiAgY29uc3QgYm9keSA9IGRvY3VtZW50LmdldEVsZW1lbnRC"
    "eUlkKCJwb3NCb2R5Iik7CiAgYm9keS5pbm5lckhUTUwgPSAiIjsKICBjYW5kcy5zb3J0KChhLGIpPT5iLnNjb3JlLWEuc2NvcmUp"
    "LmZvckVhY2goYz0+ewogICAgY29uc3Qgb3duID0gU1RBVEUucG9zaXRpb25zW2MuaWRdIHx8IDA7CiAgICBjb25zdCB0Z3QgPSB3"
    "ZWlnaHRzW2MuaWRdIHx8IDA7CiAgICBjb25zdCByZWMgPSByZWNvbW1lbmRhdGlvbihjLCBvd24sIHRndCk7CiAgICBjb25zdCBz"
    "YyA9IHNjb3JlQ29sb3IoYy5zY29yZSk7CiAgICBjb25zdCB0ciA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoInRyIik7CiAgICB0"
    "ci5pbm5lckhUTUwgPQogICAgICBgPHRkPjxzdHJvbmc+JHtjLmxhYmVsfTwvc3Ryb25nPjwvdGQ+YCsKICAgICAgYDx0ZD48c3Bh"
    "biBjbGFzcz0icGlsbCIgc3R5bGU9ImJhY2tncm91bmQ6JHtzY30yMDtjb2xvcjoke3NjfTtib3JkZXI6MXB4IHNvbGlkICR7c2N9"
    "NDAiPiR7Yy5zY29yZX08L3NwYW4+PC90ZD5gKwogICAgICBgPHRkPjxpbnB1dCBjbGFzcz0icG9zaW5wdXQiIHR5cGU9Im51bWJl"
    "ciIgbWluPSIwIiBtYXg9IjEwMCIgc3RlcD0iMSIgdmFsdWU9IiR7b3dufSIgZGF0YS1pZD0iJHtjLmlkfSI+PC90ZD5gKwogICAg"
    "ICBgPHRkPiR7dGd0PjA/dGd0LnRvRml4ZWQoMSkrIiUiOiImbmRhc2g7In08L3RkPmArCiAgICAgIGA8dGQ+PHNwYW4gY2xhc3M9"
    "InJlYyAke3JlYy5jbHN9Ij4ke3JlYy5sYWJlbH08L3NwYW4+PGJyPjxzcGFuIGNsYXNzPSJtdXRlZCIgc3R5bGU9ImZvbnQtc2l6"
    "ZToxMXB4Ij4ke3JlYy53aHl9PC9zcGFuPjwvdGQ+YDsKICAgIGJvZHkuYXBwZW5kQ2hpbGQodHIpOwogIH0pOwogIGJvZHkucXVl"
    "cnlTZWxlY3RvckFsbCgiLnBvc2lucHV0IikuZm9yRWFjaChpbnA9PnsKICAgIGlucC5hZGRFdmVudExpc3RlbmVyKCJjaGFuZ2Ui"
    "LCBlPT57CiAgICAgIGNvbnN0IGlkID0gZS50YXJnZXQuZGF0YXNldC5pZDsKICAgICAgY29uc3QgdiA9IGNsYW1wKHBhcnNlRmxv"
    "YXQoZS50YXJnZXQudmFsdWUpfHwwLCAwLCAxMDApOwogICAgICBTVEFURS5wb3NpdGlvbnNbaWRdID0gdjsKICAgICAgcmVjYWxj"
    "SW52ZXN0ZWQoKTsKICAgICAgc2F2ZVN0YXRlKCk7IHJlbmRlcigpOwogICAgfSk7CiAgfSk7CgogIC8vIFBpZTogZmFrdGlzayBm"
    "b3JkZWxpbmcgKGVpZGUgcG9zaXNqb25lciArIGNhc2gpCiAgZHJhd1BpZShjYW5kcyk7CgogIC8vIEhpc3RvcmlrawogIHJlbmRl"
    "ckhpc3QoKTsKICBzYXZlU3RhdGUoKTsKfQoKZnVuY3Rpb24gcmVjYWxjSW52ZXN0ZWQoKXsKICBjb25zdCB0b3RhbCA9IFNUQVRF"
    "LmNhc2ggKyBTVEFURS5pbnZlc3RlZDsKICBjb25zdCBvd25TdW0gPSBPYmplY3QudmFsdWVzKFNUQVRFLnBvc2l0aW9ucykucmVk"
    "dWNlKChhLGIpPT5hK2IsMCk7CiAgU1RBVEUuaW52ZXN0ZWQgPSB0b3RhbCAqIE1hdGgubWluKG93blN1bSwxMDApLzEwMDsKICBT"
    "VEFURS5jYXNoID0gdG90YWwgLSBTVEFURS5pbnZlc3RlZDsKfQoKZnVuY3Rpb24gc2NvcmVDb2xvcihzKXsKICBpZihzPj03NSkg"
    "cmV0dXJuICIjNTBjODc4IjsgaWYocz49NTUpIHJldHVybiAiI2YwYTUwMCI7CiAgaWYocz49MzUpIHJldHVybiAiI2UwODAzMCI7"
    "IHJldHVybiAiI2UwNTA1MCI7Cn0KCmZ1bmN0aW9uIGRyYXdQaWUoY2FuZHMpewogIGNvbnN0IHRvdGFsID0gU1RBVEUuY2FzaCAr"
    "IFNUQVRFLmludmVzdGVkOwogIGNvbnN0IHNsaWNlcyA9IFtdOwogIGNhbmRzLmZvckVhY2goYz0+ewogICAgY29uc3Qgb3duID0g"
    "U1RBVEUucG9zaXRpb25zW2MuaWRdfHwwOwogICAgaWYob3duPjApIHNsaWNlcy5wdXNoKHtsYWJlbDpjLmxhYmVsLCBwY3Q6b3du"
    "LCB2YWw6IHRvdGFsKm93bi8xMDAsIGNvbDogc2NvcmVDb2xvcihjLnNjb3JlKX0pOwogIH0pOwogIGNvbnN0IGNhc2hQY3QgPSB0"
    "b3RhbD4wID8gU1RBVEUuY2FzaC90b3RhbCoxMDAgOiAxMDA7CiAgc2xpY2VzLnB1c2goe2xhYmVsOiJDYXNoIiwgcGN0OmNhc2hQ"
    "Y3QsIHZhbDpTVEFURS5jYXNoLCBjb2w6IiMzYTQ0NTIifSk7CgogIGNvbnN0IHNpemU9MjQwLCByPTExMCwgY3g9c2l6ZS8yLCBj"
    "eT1zaXplLzI7CiAgbGV0IGFuZz0tTWF0aC5QSS8yOwogIGxldCBwYXRocz0iIjsKICBzbGljZXMuZm9yRWFjaChzPT57CiAgICBj"
    "b25zdCBhMiA9IGFuZyArIChzLnBjdC8xMDApKk1hdGguUEkqMjsKICAgIGNvbnN0IHgxPWN4K3IqTWF0aC5jb3MoYW5nKSwgeTE9"
    "Y3krcipNYXRoLnNpbihhbmcpOwogICAgY29uc3QgeDI9Y3grcipNYXRoLmNvcyhhMiksIHkyPWN5K3IqTWF0aC5zaW4oYTIpOwog"
    "ICAgY29uc3QgbGFyZ2UgPSAoYTItYW5nKT5NYXRoLlBJPzE6MDsKICAgIGlmKHMucGN0PjAuMDEpIHBhdGhzICs9IGA8cGF0aCBk"
    "PSJNJHtjeH0sJHtjeX0gTCR7eDF9LCR7eTF9IEEke3J9LCR7cn0gMCAke2xhcmdlfSwxICR7eDJ9LCR7eTJ9IFoiIGZpbGw9IiR7"
    "cy5jb2x9IiBzdHJva2U9IiMwYjBkMTAiIHN0cm9rZS13aWR0aD0iMiI+PC9wYXRoPmA7CiAgICBhbmc9YTI7CiAgfSk7CiAgZG9j"
    "dW1lbnQuZ2V0RWxlbWVudEJ5SWQoInBpZVdyYXAiKS5pbm5lckhUTUwgPQogICAgYDxzdmcgY2xhc3M9InBpZSIgd2lkdGg9IiR7"
    "c2l6ZX0iIGhlaWdodD0iJHtzaXplfSIgdmlld0JveD0iMCAwICR7c2l6ZX0gJHtzaXplfSI+JHtwYXRoc308L3N2Zz5gOwogIGNv"
    "bnN0IGxlZyA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJwaWVMZWdlbmQiKTsKICBsZWcuaW5uZXJIVE1MID0gIiI7CiAgc2xp"
    "Y2VzLmZpbHRlcihzPT5zLnBjdD4wLjAxKS5mb3JFYWNoKHM9PnsKICAgIGNvbnN0IGQ9ZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgi"
    "ZGl2Iik7IGQuY2xhc3NOYW1lPSJsaSI7CiAgICBkLmlubmVySFRNTD1gPHNwYW4gY2xhc3M9InN3IiBzdHlsZT0iYmFja2dyb3Vu"
    "ZDoke3MuY29sfSI+PC9zcGFuPmArCiAgICAgIGA8c3Bhbj4ke3MubGFiZWx9OiA8c3Ryb25nPiR7cy5wY3QudG9GaXhlZCgxKX0l"
    "PC9zdHJvbmc+IDxzcGFuIGNsYXNzPSJtdXRlZCI+KCR7a3Iocy52YWwpfSk8L3NwYW4+PC9zcGFuPmA7CiAgICBsZWcuYXBwZW5k"
    "Q2hpbGQoZCk7CiAgfSk7Cn0KCmZ1bmN0aW9uIHJlbmRlckhpc3QoKXsKICBjb25zdCBib3g9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5"
    "SWQoImhpc3RCb3giKTsKICBpZighU1RBVEUuaGlzdG9yeS5sZW5ndGgpeyBib3guaW5uZXJIVE1MPSc8ZGl2IGNsYXNzPSJtdXRl"
    "ZCIgc3R5bGU9ImZvbnQtc2l6ZToxMnB4Ij5JbmdlbiBlbmRyaW5nZXIgZW5uJmFyaW5nOy48L2Rpdj4nOyByZXR1cm47IH0KICBi"
    "b3guaW5uZXJIVE1MID0gU1RBVEUuaGlzdG9yeS5tYXAoaD0+YDxkaXYgY2xhc3M9ImgiPjxkaXYgY2xhc3M9InQiPiR7aC50fTwv"
    "ZGl2PiR7aC5tc2d9PC9kaXY+YCkuam9pbigiIik7Cn0KCi8vIC0tLSBLYXBpdGFsLWhhbmRsaW5nZXIgLS0tCmRvY3VtZW50Lmdl"
    "dEVsZW1lbnRCeUlkKCJhcHBseUNhcCIpLmFkZEV2ZW50TGlzdGVuZXIoImNsaWNrIiwgKCk9PnsKICBjb25zdCBzdGFydCA9IHBh"
    "cnNlRmxvYXQoZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInN0YXJ0Q2FwIikudmFsdWUpfHwwOwogIGNvbnN0IGFkZCA9IHBhcnNl"
    "RmxvYXQoZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImFkZENhcCIpLnZhbHVlKXx8MDsKICBjb25zdCBvbGRUb3RhbCA9IFNUQVRF"
    "LmNhc2ggKyBTVEFURS5pbnZlc3RlZDsKICBpZihzdGFydCAhPT0gU1RBVEUuc3RhcnRDYXAgJiYgb2xkVG90YWwgPT09IFNUQVRF"
    "LnN0YXJ0Q2FwKXsKICAgIC8vIGbDuHJzdGUgZ2FuZyAvIGp1c3RlcmluZyBhdiBzdGFydGthcGl0YWwKICAgIFNUQVRFLnN0YXJ0"
    "Q2FwID0gc3RhcnQ7IFNUQVRFLmNhc2ggPSBzdGFydCAtIFNUQVRFLmludmVzdGVkOwogICAgbG9nSGlzdChgU3RhcnRrYXBpdGFs"
    "IHNhdHQgdGlsICR7a3Ioc3RhcnQpfWApOwogIH0KICBpZihhZGQ+MCl7CiAgICBTVEFURS5jYXNoICs9IGFkZDsKICAgIGxvZ0hp"
    "c3QoYE55dHQgaW5uc2t1ZGQ6ICR7a3IoYWRkKX0gKHRvdGFsOiAke2tyKFNUQVRFLmNhc2grU1RBVEUuaW52ZXN0ZWQpfSlgKTsK"
    "ICAgIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJhZGRDYXAiKS52YWx1ZT0iIjsKICB9CiAgU1RBVEUuY2FzaFRhcmdldCA9IGNs"
    "YW1wKHBhcnNlRmxvYXQoZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImNhc2hUYXJnZXQiKS52YWx1ZSl8fDE1LDAsMTAwKTsKICBT"
    "VEFURS5tYXhQb3MgPSBjbGFtcChwYXJzZUZsb2F0KGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJtYXhQb3MiKS52YWx1ZSl8fDI1"
    "LDUsMTAwKTsKICBzYXZlU3RhdGUoKTsgcmVuZGVyKCk7Cn0pOwoKZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInJlYmFsYW5jZSIp"
    "LmFkZEV2ZW50TGlzdGVuZXIoImNsaWNrIiwgKCk9PnsKICBjb25zdCBjYW5kcyA9IGNhbmRpZGF0ZXMoKTsKICBjb25zdCB7IHdl"
    "aWdodHMgfSA9IHRhcmdldFdlaWdodHMoY2FuZHMpOwogIGxldCBjaGFuZ2VzPVtdOwogIGNhbmRzLmZvckVhY2goYz0+ewogICAg"
    "Y29uc3Qgb3duID0gU1RBVEUucG9zaXRpb25zW2MuaWRdfHwwOwogICAgY29uc3QgdGd0ID0gd2VpZ2h0c1tjLmlkXXx8MDsKICAg"
    "IGNvbnN0IHJlYyA9IHJlY29tbWVuZGF0aW9uKGMsIG93biwgdGd0KTsKICAgIGlmKHJlYy5jb2RlPT09IkJVWSIpeyBpZih0Z3Q+"
    "MCAmJiBvd248dGd0KXsgU1RBVEUucG9zaXRpb25zW2MuaWRdPXBhcnNlRmxvYXQodGd0LnRvRml4ZWQoMSkpOyBjaGFuZ2VzLnB1"
    "c2goYEtKJk9zbGFzaDtQICR7Yy5sYWJlbH0gJnJhcnI7ICR7dGd0LnRvRml4ZWQoMSl9JWApO30gfQogICAgZWxzZSBpZihyZWMu"
    "Y29kZT09PSJBREQiKXsgU1RBVEUucG9zaXRpb25zW2MuaWRdPXBhcnNlRmxvYXQodGd0LnRvRml4ZWQoMSkpOyBjaGFuZ2VzLnB1"
    "c2goYExFR0cgVElMICR7Yy5sYWJlbH0gJnJhcnI7ICR7dGd0LnRvRml4ZWQoMSl9JWApOyB9CiAgICBlbHNlIGlmKHJlYy5jb2Rl"
    "PT09IlNDQUxFIil7IGlmKG93bj4wKXsgU1RBVEUucG9zaXRpb25zW2MuaWRdPTA7IGNoYW5nZXMucHVzaChgU0tBTEVSIEFWICR7"
    "Yy5sYWJlbH0gKGZyYSAke293bn0lKWApO30gfQogIH0pOwogIHJlY2FsY0ludmVzdGVkKCk7CiAgaWYoY2hhbmdlcy5sZW5ndGgp"
    "IGxvZ0hpc3QoIk9tZm9yZGVsaW5nOiAiICsgY2hhbmdlcy5qb2luKCIsICIpKTsKICBlbHNlIGxvZ0hpc3QoIk9tZm9yZGVsaW5n"
    "OiBpbmdlbiBlbmRyaW5nZXIgYW5iZWZhbHQiKTsKICBzYXZlU3RhdGUoKTsgcmVuZGVyKCk7Cn0pOwoKZG9jdW1lbnQuZ2V0RWxl"
    "bWVudEJ5SWQoImNsZWFySGlzdCIpLmFkZEV2ZW50TGlzdGVuZXIoImNsaWNrIiwgKCk9PnsKICBpZihjb25maXJtKCJUJm9zbGFz"
    "aDttbWUgaGVsZSBlbmRyaW5nc2xvZ2dlbj8iKSl7IFNUQVRFLmhpc3Rvcnk9W107IHNhdmVTdGF0ZSgpOyByZW5kZXJIaXN0KCk7"
    "IH0KfSk7Cgppbml0KCk7Cjwvc2NyaXB0Pgo8L2JvZHk+CjwvaHRtbD4K"
)

TZ  = ZoneInfo("Europe/Oslo")
NOW = datetime.now(tz=TZ)

DOCS     = Path("docs")
CHARTS   = DOCS / "charts"
NEWS_DIR = DOCS / "news"
DOCS.mkdir(exist_ok=True)
CHARTS.mkdir(exist_ok=True)
NEWS_DIR.mkdir(exist_ok=True)

FORCE_INPUT       = os.environ.get("FORCE_RUN", "false").lower() == "true"
IN_GITHUB_ACTIONS = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
FORCE = FORCE_INPUT or IN_GITHUB_ACTIONS

print(f"Full run: {FORCE} at {NOW.isoformat()} (version {VERSION})")
with open(DOCS / "run_mode.json", "w", encoding="utf-8") as f:
    json.dump({"force": FORCE, "now": NOW.isoformat(), "version": VERSION}, f, indent=2)

if not FORCE and not ((NOW.hour == 19 and NOW.minute >= 45) or (NOW.hour == 20 and NOW.minute <= 10)):
    with open(DOCS / "heartbeat.json", "w", encoding="utf-8") as f:
        json.dump({"last_run_local": NOW.isoformat(), "version": VERSION}, f, indent=2)
    with open(DOCS / "index.html", "w", encoding="utf-8") as f:
        f.write(f"<!doctype html><meta charset='utf-8'><title>Market Daily Report</title>"
                f"<h1>Market Daily Report</h1><p>{NOW.isoformat()}</p>"
                f"<p>Full rapport genereres kl. 20:00 Europe/Oslo.</p>")
    raise SystemExit(0)

LOG = []
def log(msg):
    print(msg)
    LOG.append(f"{datetime.now().isoformat()}  {msg}")

def flush_log():
    with open(DOCS / "run_log.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(LOG) + "\n")

YF_SESSION = requests.Session()
YF_SESSION.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "*/*",
                            "Accept-Language": "en-US,en;q=0.9"})

FRED_KEY  = os.environ.get("FRED_API_KEY", "").strip()
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# ─── INSTRUMENTS ───────────────────────────────────────────────
INSTRUMENT_GROUPS = [
    {
        "key": "renter_spreads", "title": "0. Renter & Spreads", "sector": "Renter",
        "description": "10yr yield, yieldkurve, realrente, kredittstress. Forteller makroregime.",
        "instruments": [
            {"id": "UTEN",  "label": "10yr UST",       "symbol_label": "UTEN",  "source": "yf",          "candidates": ["UTEN"]},
            {"id": "2S10S", "label": "2s10s kurve",     "symbol_label": "FRED",  "source": "fred_spread"},
            {"id": "SCHP",  "label": "10yr realrente",  "symbol_label": "SCHP",  "source": "yf",          "candidates": ["SCHP"]},
            {"id": "TLT",   "label": "20yr UST",        "symbol_label": "TLT",   "source": "yf",          "candidates": ["TLT"]},
            {"id": "HYG",   "label": "High Yield",      "symbol_label": "HYG",   "source": "yf",          "candidates": ["HYG", "JNK"]},
            {"id": "LQD",   "label": "IG Kreditt",      "symbol_label": "LQD",   "source": "yf",          "candidates": ["LQD"]},
        ],
    },
    {
        "key": "aksjer", "title": "1. Aksjer", "sector": "Aksjer",
        "description": "Bred aksjeeksponering, vekstsyklus og regional styrke.",
        "instruments": [
            {"id": "SPY",  "label": "S&P 500",          "symbol_label": "SPY",   "source": "yf", "candidates": ["SPY"]},
            {"id": "QQQ",  "label": "Nasdaq-100",        "symbol_label": "QQQ",   "source": "yf", "candidates": ["QQQ"]},
            {"id": "IWM",  "label": "Russell 2000",      "symbol_label": "IWM",   "source": "yf", "candidates": ["IWM"]},
            {"id": "ACWI", "label": "ACWI",              "symbol_label": "ACWI",  "source": "yf", "candidates": ["ACWI"]},
            {"id": "EXSA", "label": "STOXX Europe 600",  "symbol_label": "EXSA",  "source": "yf", "candidates": ["EXSA.DE","EXSA","MEUD"]},
            {"id": "EEM",  "label": "MSCI EM",           "symbol_label": "EEM",   "source": "yf", "candidates": ["EEM","VWO"]},
            {"id": "VNQ",  "label": "Housing US",        "symbol_label": "VNQ",   "source": "yf", "candidates": ["VNQ"]},
            {"id": "IAI",  "label": "Broker/Dealers",    "symbol_label": "IAI",   "source": "yf", "candidates": ["IAI"]},
        ],
    },
    {
        "key": "tech", "title": "2. Tech & Halvledere", "sector": "Tech",
        "description": "Teknologilederskap og AI-infrastruktur.",
        "instruments": [
            {"id": "SOXQ", "label": "Semiconductors",   "symbol_label": "SOXQ",  "source": "yf", "candidates": ["SOXQ","SOXX"]},
            {"id": "HACK", "label": "Cybersecurity",    "symbol_label": "HACK",  "source": "yf", "candidates": ["HACK","CIBR"]},
            {"id": "SKYY", "label": "Cloud",            "symbol_label": "SKYY",  "source": "yf", "candidates": ["SKYY","CLOU"]},
            {"id": "BOTZ", "label": "Robotics/AI",      "symbol_label": "BOTZ",  "source": "yf", "candidates": ["BOTZ","IRBO"]},
        ],
    },
    {
        "key": "rawarer", "title": "3. Råvarer", "sector": "Rawarer",
        "description": "Inflasjonspress, reflasjon og rawvaresyklus.",
        "instruments": [
            {"id": "BCOM",  "label": "Commodity bred",  "symbol_label": "BCOM",  "source": "yf", "candidates": ["BCOM","PDBC","DBC"]},
            {"id": "USO",   "label": "Olje (WTI)",      "symbol_label": "USO",   "source": "yf", "candidates": ["USO","BNO"]},
            {"id": "UNG",   "label": "Naturgass",       "symbol_label": "UNG",   "source": "yf", "candidates": ["UNG"]},
            {"id": "COPX",  "label": "Kobber miners",   "symbol_label": "COPX",  "source": "yf", "candidates": ["COPX","JJC"]},
            {"id": "XME",   "label": "Metals/Mining",   "symbol_label": "XME",   "source": "yf", "candidates": ["XME"]},
            {"id": "XLE",   "label": "Energy",          "symbol_label": "XLE",   "source": "yf", "candidates": ["XLE"]},
            {"id": "DBA",   "label": "Agri/mat",        "symbol_label": "DBA",   "source": "yf", "candidates": ["DBA"]},
        ],
    },
    {
        "key": "edelmetaller", "title": "4. Edelmetaller", "sector": "Edelmetaller",
        "description": "Gull, solv, gruvere. Northstar sin kjernesektor.",
        "instruments": [
            {"id": "GLD",  "label": "Gull",             "symbol_label": "GLD",   "source": "yf", "candidates": ["GLD","IAU"]},
            {"id": "SLV",  "label": "Solv",             "symbol_label": "SLV",   "source": "yf", "candidates": ["SLV","SIVR"]},
            {"id": "GDX",  "label": "Gull miners",      "symbol_label": "GDX",   "source": "yf", "candidates": ["GDX"]},
            {"id": "GDXJ", "label": "Junior gull",      "symbol_label": "GDXJ",  "source": "yf", "candidates": ["GDXJ"]},
            {"id": "SIL",  "label": "Solv miners",      "symbol_label": "SIL",   "source": "yf", "candidates": ["SIL"]},
            {"id": "SILJ", "label": "Junior solv",      "symbol_label": "SILJ",  "source": "yf", "candidates": ["SILJ"]},
            {"id": "PPLT", "label": "Platina",          "symbol_label": "PPLT",  "source": "yf", "candidates": ["PPLT","PLTM"]},
            {"id": "PALL", "label": "Palladium",        "symbol_label": "PALL",  "source": "yf", "candidates": ["PALL"]},
        ],
    },
    {
        "key": "uranium", "title": "5. Uranium & Energiomstilling", "sector": "Rawarer",
        "description": "Northstar bullish roadmap. Venter pa $100 breakout.",
        "instruments": [
            {"id": "URA",  "label": "Uranium ETF",      "symbol_label": "URA",   "source": "yf", "candidates": ["URA"]},
            {"id": "URNM", "label": "Uranium miners",   "symbol_label": "URNM",  "source": "yf", "candidates": ["URNM"]},
            {"id": "NLR",  "label": "Nuclear energy",   "symbol_label": "NLR",   "source": "yf", "candidates": ["NLR"]},
            {"id": "ICLN", "label": "Clean energy",     "symbol_label": "ICLN",  "source": "yf", "candidates": ["ICLN"]},
        ],
    },
    {
        "key": "valuta", "title": "6. Valuta & Dollar", "sector": "Valuta",
        "description": "Dollar-regimet. Northstar Milkshake Arc: bearish USD langsiktig.",
        "instruments": [
            {"id": "UUP", "label": "DXY",               "symbol_label": "UUP",   "source": "yf", "candidates": ["UUP","USDU"]},
            {"id": "FXE", "label": "EUR/USD",            "symbol_label": "FXE",   "source": "yf", "candidates": ["FXE"]},
            {"id": "FXY", "label": "JPY",                "symbol_label": "FXY",   "source": "yf", "candidates": ["FXY"]},
            {"id": "CEW", "label": "EM Currencies",      "symbol_label": "CEW",   "source": "yf", "candidates": ["CEW"]},
            {"id": "FXA", "label": "AUD",                "symbol_label": "FXA",   "source": "yf", "candidates": ["FXA"]},
        ],
    },
    {
        "key": "crypto", "title": "7. Crypto & Volatilitet", "sector": "Crypto",
        "description": "Risiko-on spekulasjon og likviditetsindikator.",
        "instruments": [
            {"id": "BTC",  "label": "BTC",               "symbol_label": "BTC",   "source": "yf", "candidates": ["BTC-USD","BITO","IBIT"]},
            {"id": "ETHA", "label": "ETH",               "symbol_label": "ETH",   "source": "yf", "candidates": ["ETH-USD","ETHA"]},
            {"id": "VIXY", "label": "VIX",               "symbol_label": "VIXY",  "source": "yf", "candidates": ["VIXY"]},
        ],
    },
]

RATIO_PAIRS = [
    ("GLD",  "SPY",  "GLD/SPY"),
    ("GDX",  "GLD",  "GDX/GLD"),
    ("SLV",  "GLD",  "SLV/GLD"),
    ("URA",  "SPY",  "URA/SPY"),
    ("XLE",  "SPY",  "XLE/SPY"),
    ("EEM",  "SPY",  "EEM/SPY"),
    ("IWM",  "SPY",  "IWM/SPY"),
    ("COPX", "SPY",  "COPX/SPY"),
    ("GDX",  "SPY",  "GDX/SPY"),
    ("USO",  "ACWI", "USO/ACWI"),
    ("GLD",  "ACWI", "GLD/ACWI"),
    ("BTC",  "ACWI", "BTC/ACWI"),
]

ALL_IDS = [i["id"] for g in INSTRUMENT_GROUPS for i in g["instruments"]]

# ─── TREND-OVERSIKT RATIOER (ny hovedside) ─────────────────────
TREND_TICKERS = {
    "GULL":    ["GLD", "IAU"],
    "GLOBAL":  ["ACWI"],
    "URAN":    ["URNM", "URA"],
    "OLJE":    ["USO", "BNO"],
    "DBA":     ["DBA"],
    "CRYPTO":  ["BTC-USD", "BITO", "IBIT"],
    "NOK":     ["NOK=X"],
    "EIENDOM": ["CAST.ST", "TRET.AS"],
}
NOK_INVERT = True

TREND_RATIOS = [
    ("GULL",   "GLOBAL",  "GLD / ACWI"),
    ("NOK",    "GLOBAL",  "NOK / ACWI"),
    ("URAN",   "GLOBAL",  "URNM / ACWI"),
    ("OLJE",   "GLOBAL",  "USO / ACWI"),
    ("DBA",    "GLOBAL",  "DBA / ACWI"),
    ("CRYPTO", "GLOBAL",  "BTC / ACWI"),
    ("GULL",   "URAN",    "GLD / URNM"),
    ("GULL",   "CRYPTO",  "GLD / BTC"),
    ("GULL",   "OLJE",    "GLD / USO"),
    ("GULL",   "EIENDOM", "GLD / CAST.ST"),
]

# ─── MATH ──────────────────────────────────────────────────────
def SMA(s, n):
    return s.rolling(n).mean()

def RSI(s, n=14):
    d  = s.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    rs = up.ewm(alpha=1/n, adjust=False).mean() / dn.ewm(alpha=1/n, adjust=False).mean()
    return 100 - (100 / (1 + rs))

def MACD_calc(s, fast=12, slow=26, sig=9):
    ef = s.ewm(span=fast, adjust=False).mean()
    es = s.ewm(span=slow, adjust=False).mean()
    m  = ef - es
    sl = m.ewm(span=sig, adjust=False).mean()
    return m, sl, m - sl

def pct_dist(a, b):
    try:
        return (a - b) / b if b and not np.isnan(b) else np.nan
    except Exception:
        return np.nan

def safe_id(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s)

# ─── DATA ──────────────────────────────────────────────────────
def normalize_yf_df(data):
    if data is None or getattr(data, "empty", True):
        return None
    df = data.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)
    if "close" not in df.columns:
        return None
    df["close_use"] = pd.to_numeric(df["close"], errors="coerce")
    if "volume" not in df.columns:
        df["volume"] = np.nan
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()[~df.index.duplicated(keep="last")].dropna(subset=["close_use"])
    return df if len(df) >= 50 else None

def yf_series_from_candidates(candidates):
    for sym in candidates:
        for attempt in range(3):
            try:
                data = yf.download(sym, period="max", interval="1d",
                                   auto_adjust=True, progress=False,
                                   session=YF_SESSION, threads=False)
                df = normalize_yf_df(data)
                if df is not None:
                    log(f"  yf ok: {sym}")
                    return df, sym
            except Exception as e:
                log(f"  yf error {sym} try{attempt+1}: {e}")
            time.sleep(1 + attempt)
    return None, None

def fred_series(series_id):
    if not FRED_KEY:
        return None
    try:
        r = requests.get(
            f"{FRED_BASE}?series_id={series_id}&api_key={FRED_KEY}&file_type=json&observation_start=1990-01-01",
            timeout=60)
        r.raise_for_status()
        obs = r.json().get("observations", [])
        if not obs:
            return None
        df = pd.DataFrame(obs)[["date","value"]]
        df["date"]  = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.set_index("date").sort_index().dropna().asfreq("B").ffill()
        df["close_use"] = df["value"]
        df["volume"]    = np.nan
        log(f"  fred ok: {series_id}")
        return df[["close_use","volume"]]
    except Exception as e:
        log(f"  fred error {series_id}: {e}")
        return None

def fred_2s10s_series():
    y2  = fred_series("DGS2")
    y10 = fred_series("DGS10")
    if y2 is None or y10 is None:
        return None, None
    df = pd.DataFrame(index=y10.index.union(y2.index))
    df["y2"]  = y2["close_use"]
    df["y10"] = y10["close_use"]
    df = df.sort_index().ffill().dropna()
    df["close_use"] = df["y10"] - df["y2"]
    df["volume"]    = np.nan
    return df[["close_use","volume"]], "FRED:DGS10-DGS2"

def get_instrument_series(inst):
    if inst["source"] == "yf":
        return yf_series_from_candidates(inst["candidates"])
    if inst["source"] == "fred_spread":
        return fred_2s10s_series()
    raise ValueError(f"Unknown source: {inst['source']}")

def with_indicators(df):
    out = df.copy()
    out["sma36"]  = SMA(out["close_use"], 36)
    out["sma156"] = SMA(out["close_use"], 156)
    out["rsi14"]  = RSI(out["close_use"], 14)
    m,  sl,  h   = MACD_calc(out["close_use"], 12, 26, 9)
    out["macd"] = m;  out["macd_signal"] = sl;  out["macd_hist"] = h
    m14, sl14, h14 = MACD_calc(out["close_use"], 14, 28, 9)
    out["macd14"] = m14; out["macd14_signal"] = sl14; out["macd14_hist"] = h14
    return out

def resample_frames(base_df):
    daily   = with_indicators(base_df)
    weekly  = with_indicators(base_df.resample("W-FRI").last().dropna(how="all"))
    monthly = with_indicators(base_df.resample("ME").last().dropna(how="all"))
    return daily, weekly, monthly

def frame_summary(df, is_weekly=False):
    if df is None or df.empty:
        return {}
    last   = float(df["close_use"].iloc[-1])
    sma36  = df["sma36"].iloc[-1]  if "sma36"  in df.columns else np.nan
    sma156 = df["sma156"].iloc[-1] if "sma156" in df.columns else np.nan

    def fv(col):
        v = df[col].iloc[-1] if col in df.columns else np.nan
        return float(v) if pd.notna(v) else None

    macd_cross = macd14_cross = None
    if len(df) >= 2:
        ld  = df["macd"].iloc[-1]   - df["macd_signal"].iloc[-1]
        pd_ = df["macd"].iloc[-2]   - df["macd_signal"].iloc[-2]
        macd_cross = bool(ld > 0 and pd_ <= 0)
        ld14  = df["macd14"].iloc[-1]   - df["macd14_signal"].iloc[-1]
        pd14  = df["macd14"].iloc[-2]   - df["macd14_signal"].iloc[-2]
        macd14_cross = bool(ld14 > 0 and pd14 <= 0)

    # Trend: er MA stigende? (sammenlign MA naa vs 8 perioder siden)
    sma36_rising = sma156_rising = None
    if "sma36" in df.columns and len(df) >= 10:
        prev = df["sma36"].iloc[-9]
        if pd.notna(prev) and pd.notna(sma36):
            sma36_rising = bool(sma36 > prev)
    if "sma156" in df.columns and len(df) >= 10:
        prev = df["sma156"].iloc[-9]
        if pd.notna(prev) and pd.notna(sma156):
            sma156_rising = bool(sma156 > prev)

    # Volum-bekreftelse: siste volum vs 20-perioders snitt
    vol_confirm = None
    if "volume" in df.columns:
        recent_vol = df["volume"].iloc[-1]
        avg_vol    = df["volume"].tail(20).mean()
        if pd.notna(recent_vol) and pd.notna(avg_vol) and avg_vol > 0:
            vol_confirm = float(recent_vol / avg_vol)

    return {
        "last":               last,
        "sma36":              float(sma36)  if pd.notna(sma36)  else None,
        "sma156":             float(sma156) if pd.notna(sma156) else None,
        "close_above_sma36":  bool(last > float(sma36))  if pd.notna(sma36)  else None,
        "close_above_sma156": bool(last > float(sma156)) if pd.notna(sma156) else None,
        "sma36_rising":       sma36_rising,
        "sma156_rising":      sma156_rising,
        "vol_confirm":        vol_confirm,
        "dist_to_36MA":       float(pct_dist(last, float(sma36)))  if pd.notna(sma36)  else None,
        "dist_to_3yr_MA":     float(pct_dist(last, float(sma156))) if (pd.notna(sma156) and is_weekly) else None,
        "rsi14":              fv("rsi14"),
        "macd":               fv("macd"),      "macd_signal":  fv("macd_signal"),
        "macd_hist":          fv("macd_hist"), "macd_cross":   macd_cross,
        "macd14":             fv("macd14"),    "macd14_signal":fv("macd14_signal"),
        "macd14_hist":        fv("macd14_hist"),"macd14_cross":macd14_cross,
    }

def trend_label(w):
    """Klassifiser trend basert paa pris vs MA + MA-retning."""
    above36  = w.get("close_above_sma36")
    above156 = w.get("close_above_sma156")
    rising36 = w.get("sma36_rising")
    rising156= w.get("sma156_rising")
    if above36 and above156 and rising36:
        return ("Opptrend", "#50c878")
    if above36 and rising36:
        return ("Stigende", "#7ec88a")
    if (not above36) and rising36:
        return ("Dip i trend", "#f0a500")
    if (not above36) and (rising36 is False):
        return ("Nedtrend", "#e05050")
    if above36 and (rising36 is False):
        return ("Topper ut", "#e08030")
    return ("Noeytral", "#9aa7b5")

# ─── NORTHSTAR SCORE (dynamisk, vektet 33/33/33) ───────────────
def _rsi_subscore(rsi):
    """RSI -> 0..1. Lavere RSI = bedre (dynamisk, ikke bøtter).
    RSI 30 -> ~1.0, RSI 50 -> ~0.6, RSI 70 -> ~0.2, RSI 85+ -> ~0."""
    if rsi is None:
        return None
    # lineær rampe: 30 og lavere = 1.0, 85 og høyere = 0.0
    x = (85.0 - rsi) / (85.0 - 30.0)
    return max(0.0, min(1.0, x))

def _macd_subscore(hist, macd_line):
    """MACD -> 0..1. Lavere/mer negativ histogram = bedre entry (dynamisk).
    Normaliserer histogram mot MACD-linjens størrelse for å være skala-uavhengig."""
    if hist is None:
        return None
    scale = abs(macd_line) if (macd_line not in (None, 0)) else None
    if scale and scale > 0:
        norm = hist / scale          # typisk -1..+1+
    else:
        norm = hist
    # norm <= -0.5 (sterkt negativ, mulig bunn) -> 1.0
    # norm  =  0.0 (nær null)                   -> 0.6
    # norm >= +1.0 (høyt positivt, allerede løpt)-> 0.0
    if norm <= -0.5:
        return 1.0
    if norm <= 0:
        return 0.6 + (abs(norm) / 0.5) * 0.4      # 0 -> 0.6, -0.5 -> 1.0
    # positiv: faller fra 0.6 mot 0 ved norm=1.0
    return max(0.0, 0.6 - (norm / 1.0) * 0.6)

def _ma_subscore(dist):
    """Avstand til MA (fraksjon) -> 0..1. Naer eller rett under = best (dynamisk).
    Mer enn 3% UNDER MA teller negativt: instrumentet faller inn i negativ
    makrotrend, ikke bare en lavrisiko-dip.

    Profil:
      0%..+45% over  -> 0.92 ned mot 0   (stretched over MA = darlig entry)
      -3%..0%        -> 0.92..1.0          (ideal sone)
      -15%..-3%      -> 0.30..0.92         (begynnende svakhet under MA)
      < -15%         -> 0.1                (klart i negativ trend)
    """
    if dist is None:
        return None
    p = dist * 100.0
    if p >= 0:
        return max(0.0, 0.92 - (p / 45.0) * 0.92)
    if p >= -3:
        return 1.0 + (p / 3.0) * 0.08        # 0% ->1.0, -3% ->0.92
    if p >= -15:
        # lineaer 0.92 (ved -3%) ned til 0.30 (ved -15%)
        frac = (abs(p) - 3) / (15 - 3)
        return 0.92 - frac * (0.92 - 0.30)
    return 0.1

def _fmt_sub(frac):
    return f"{frac*100:.0f}%" if frac is not None else "–"

def northstar_score(entry):
    """
    Vektet score 0-100. Hoeyere = lavrisiko entry.
    Tre like hovedkomponenter (hver 33.3%):
      RSI   : weekly (13%) + monthly (20%)   [hoeyere tidsramme vektes mer]
      MACD  : weekly (13%) + monthly (20%)
      MA    : 36WMA (13%) + 3yr MA (20%)
    Alle delscorer er dynamiske funksjoner av verdien (ikke boetter).
    """
    w = entry.get("frames",{}).get("weekly")  or {}
    m = entry.get("frames",{}).get("monthly") or {}

    # delvekter (sum = 100)
    W_RSI_W, W_RSI_M   = 13.0, 20.0
    W_MACD_W, W_MACD_M = 13.0, 20.0
    W_MA_36,  W_MA_3YR = 13.0, 20.0

    points = []
    total  = 0.0
    maxtot = 0.0

    def add(label, frac, weight, raw_note):
        nonlocal total, maxtot
        maxtot += weight
        if frac is None:
            points.append((label, 0, round(weight), "ingen data"))
            return
        pts = frac * weight
        total += pts
        points.append((label, round(pts), round(weight), raw_note))

    # ── RSI (33%) ──
    rsi_w = w.get("rsi14"); rsi_m = m.get("rsi14")
    add("RSI W",  _rsi_subscore(rsi_w), W_RSI_W,
        f"{rsi_w:.1f} ({_fmt_sub(_rsi_subscore(rsi_w))})" if rsi_w is not None else "ingen data")
    add("RSI M",  _rsi_subscore(rsi_m), W_RSI_M,
        f"{rsi_m:.1f} ({_fmt_sub(_rsi_subscore(rsi_m))})" if rsi_m is not None else "ingen data")

    # ── MACD (33%) ──
    mh_w = w.get("macd_hist"); ml_w = w.get("macd")
    mh_m = m.get("macd_hist"); ml_m = m.get("macd")
    add("MACD W", _macd_subscore(mh_w, ml_w), W_MACD_W,
        f"hist {mh_w:.4f} ({_fmt_sub(_macd_subscore(mh_w, ml_w))})" if mh_w is not None else "ingen data")
    add("MACD M", _macd_subscore(mh_m, ml_m), W_MACD_M,
        f"hist {mh_m:.4f} ({_fmt_sub(_macd_subscore(mh_m, ml_m))})" if mh_m is not None else "ingen data")

    # ── MA (33%) ──
    d36  = w.get("dist_to_36MA")
    d3yr = w.get("dist_to_3yr_MA")
    add("36WMA", _ma_subscore(d36),  W_MA_36,
        f"{d36*100:+.1f}% ({_fmt_sub(_ma_subscore(d36))})" if d36 is not None else "ingen data")
    add("3yr MA", _ma_subscore(d3yr), W_MA_3YR,
        f"{d3yr*100:+.1f}% ({_fmt_sub(_ma_subscore(d3yr))})" if d3yr is not None else "ingen data")

    # normaliser til 0-100 selv om noen komponenter mangler data
    if maxtot > 0:
        score = round(total / maxtot * 100)
    else:
        score = 0
    return min(score, 100), points

def score_synthetic_series(price_series):
    """
    Beregn Northstar-score for en syntetisk prisserie (f.eks. en ratio).
    Bruker EKSAKT samme scoremodell som northstar_score.
    Returnerer (score, points, frames-dict).
    """
    df = pd.DataFrame({"close_use": price_series, "volume": np.nan}).dropna(subset=["close_use"])
    if len(df) < 200:
        return None, None, None
    daily, weekly, monthly = resample_frames(df)
    entry = {"frames": {
        "daily":   frame_summary(daily,   is_weekly=False),
        "weekly":  frame_summary(weekly,  is_weekly=True),
        "monthly": frame_summary(monthly, is_weekly=False),
    }}
    score, points = northstar_score(entry)
    return score, points, entry["frames"]

def score_ratio_series(price_series):
    """
    Score for en makro-ratio. Bruker MAANEDLIG + 3-MAANEDERS (kvartal) tidsramme,
    50/50 vekt per komponent (ikke weekly/monthly som instrumentene).
    Egnet for langsiktige makro-trender der ukentlig stoey er irrelevant.
    Tre like hovedkomponenter (RSI / MACD / MA), hver delt 50/50 M og Q.
    """
    df = pd.DataFrame({"close_use": price_series, "volume": np.nan}).dropna(subset=["close_use"])
    if len(df) < 200:
        return None, None, None
    monthly   = with_indicators(df.resample("ME").last().dropna(how="all"))
    quarterly = with_indicators(df.resample("QE").last().dropna(how="all"))
    fm = frame_summary(monthly,   is_weekly=False)
    fq = frame_summary(quarterly, is_weekly=False)
    # For ratioer bruker vi 36-perioders MA paa hver tidsramme som "trend-MA".
    # dist_to_36MA finnes paa begge. 3yr-MA er ikke meningsfull paa kvartal.
    points = []
    total = 0.0; maxtot = 0.0
    def add(label, frac, weight, note):
        nonlocal total, maxtot
        maxtot += weight
        if frac is None:
            points.append((label, 0, round(weight), "ingen data")); return
        total += frac*weight
        points.append((label, round(frac*weight), round(weight), note))

    W = 16.67  # 33.3% delt 50/50

    rm = fm.get("rsi14"); rq = fq.get("rsi14")
    add("RSI M", _rsi_subscore(rm), W, f"{rm:.1f} ({_fmt_sub(_rsi_subscore(rm))})" if rm else "ingen data")
    add("RSI 3M", _rsi_subscore(rq), W, f"{rq:.1f} ({_fmt_sub(_rsi_subscore(rq))})" if rq else "ingen data")

    hm = fm.get("macd_hist"); lm = fm.get("macd")
    hq = fq.get("macd_hist"); lq = fq.get("macd")
    add("MACD M", _macd_subscore(hm, lm), W, f"hist {hm:.4f}" if hm is not None else "ingen data")
    add("MACD 3M", _macd_subscore(hq, lq), W, f"hist {hq:.4f}" if hq is not None else "ingen data")

    dm = fm.get("dist_to_36MA"); dq = fq.get("dist_to_36MA")
    add("36M MA", _ma_subscore(dm), W, f"{dm*100:+.1f}%" if dm is not None else "ingen data")
    add("36Q MA", _ma_subscore(dq), W, f"{dq*100:+.1f}%" if dq is not None else "ingen data")

    score = round(total/maxtot*100) if maxtot > 0 else 0
    return min(score,100), points, {"monthly": fm, "quarterly": fq}

def monthly_ratio_score_history(price_series, months=6):
    """Ratio-score per maaned bakover (bruker score_ratio_series)."""
    out = []
    s = price_series.dropna()
    if len(s) < 200:
        return out
    midx = s.resample("ME").last().dropna().index
    for ts in midx[-months:]:
        sub = s[s.index <= ts]
        sc, _, _ = score_ratio_series(sub)
        if sc is not None:
            out.append(sc)
    return out

def weekly_score_history(price_series, weeks=26):
    """Score per uke bakover (default 26 uker = 6 mnd) for sparkline/trend."""
    out = []
    s = price_series.dropna()
    if len(s) < 200:
        return out
    # ukentlige fredager
    weekly_idx = s.resample("W-FRI").last().dropna().index
    for ts in weekly_idx[-weeks:]:
        sub = s[s.index <= ts]
        sc, _, _ = score_synthetic_series(sub)
        if sc is not None:
            out.append(sc)
    return out

def monthly_score_history(price_series, months=6):
    """Score per maaned bakover (default 6 mnd) for trendgraf paa hovedside."""
    out = []
    s = price_series.dropna()
    if len(s) < 200:
        return out
    monthly_idx = s.resample("ME").last().dropna().index
    for ts in monthly_idx[-months:]:
        sub = s[s.index <= ts]
        sc, _, _ = score_synthetic_series(sub)
        if sc is not None:
            out.append(sc)
    return out

def score_label(s):
    if s >= 75: return ("groen",  "Lavrisiko entry")
    if s >= 55: return ("gul",    "Noytral")
    if s >= 35: return ("oransje","Avvent")
    return           ("rod",     "Unnga/trim")

def score_color(s):
    if s is None: return "#9aa7b5"
    if s >= 75:   return "#50c878"
    if s >= 55:   return "#f0a500"
    if s >= 35:   return "#e08030"
    return              "#e05050"

# ─── PLOTTING ──────────────────────────────────────────────────
BG="#0b0d10"; FG="#e7edf3"; GRID="#27313d"; PANEL="#12161c"
C_PRICE="#5aa9ff"; C_SMA36="#f5b324"; C_SMA156="#ff6b6b"
C_RSI="#7ec8e3"; C_SIG="#f5b324"; C_MACD="#5aa9ff"; C_MACD14="#c084fc"

def _style_ax(ax):
    ax.set_facecolor(BG)
    ax.tick_params(colors=FG, labelsize=9)
    for sp in ax.spines.values(): sp.set_color(GRID)
    ax.yaxis.label.set_color(FG)
    ax.grid(True, color=GRID, linewidth=0.5, linestyle=":", alpha=0.6)

def plot_compact(df, title, out_path, ma_label_long="SMA156 (3yr)",
                 ma_short=36, ma_long=156, ma_short_label="SMA36"):
    """Forbedret 4-panel chart: pris+MA, RSI (sonet), MACD, MACD14.
    Tydeligere fonter, fyllte RSI-soner, naa-verdi-etiketter til hoeyre.
    ma_short/ma_long lar charts paa ulike tidsrammer bruke passende MA-perioder."""
    try:
        s = df["close_use"].dropna()
        if len(s) < 2:
            return
        fig, axes = plt.subplots(4, 1, sharex=True, figsize=(12, 10.5),
                                 facecolor=BG, gridspec_kw={"height_ratios":[3.2,1,1,1], "hspace":0.12})
        for ax in axes: _style_ax(ax)

        # ── Panel 0: Pris + MA ──
        sma36  = SMA(s, ma_short)
        sma156 = SMA(s, ma_long)
        axes[0].plot(s.index, s, color=C_PRICE, lw=1.6, label="Close")
        axes[0].plot(s.index, sma36, color=C_SMA36, lw=1.2, label=ma_short_label)
        if sma156.notna().any():
            axes[0].plot(s.index, sma156, color=C_SMA156, lw=1.1, ls="--", label=ma_label_long)
        # naa-verdi markoer
        last_v = s.iloc[-1]
        axes[0].scatter([s.index[-1]], [last_v], color=C_PRICE, s=28, zorder=5)
        axes[0].annotate(f"{last_v:,.2f}", xy=(s.index[-1], last_v),
                         xytext=(6,0), textcoords="offset points",
                         color=C_PRICE, fontsize=9, fontweight="bold", va="center")
        axes[0].set_title(title, fontsize=12, color=FG, fontweight="bold", pad=8)
        axes[0].legend(loc="upper left", fontsize=8.5, facecolor=PANEL,
                       labelcolor=FG, framealpha=0.85, edgecolor=GRID)

        # ── Panel 1: RSI med fyllte soner ──
        rsi = RSI(s)
        axes[1].axhspan(70, 100, color="#e05050", alpha=0.08)
        axes[1].axhspan(0, 30,   color="#50c878", alpha=0.08)
        axes[1].plot(s.index, rsi, color=C_RSI, lw=1.3)
        axes[1].axhline(70, color="#e05050", ls="--", lw=0.8, alpha=0.7)
        axes[1].axhline(50, color=GRID,      ls=":",  lw=0.6)
        axes[1].axhline(30, color="#50c878", ls="--", lw=0.8, alpha=0.7)
        axes[1].set_ylim(0, 100)
        axes[1].set_yticks([30,50,70])
        axes[1].set_ylabel("RSI 14", color=FG, fontsize=9)
        if rsi.notna().any():
            rv = rsi.iloc[-1]
            axes[1].annotate(f"{rv:.0f}", xy=(s.index[-1], rv), xytext=(6,0),
                             textcoords="offset points", color=C_RSI, fontsize=9,
                             fontweight="bold", va="center")

        # ── Panel 2: MACD 12/26/9 ──
        m, sig, hist = MACD_calc(s, 12, 26, 9)
        colors2 = ["#50c878" if v >= 0 else "#e05050" for v in hist.fillna(0)]
        bw = max(2, (s.index[-1]-s.index[0]).days/len(s)*0.7) if len(s)>1 else 3
        axes[2].bar(s.index, hist, color=colors2, alpha=0.5, width=bw)
        axes[2].plot(s.index, m,   color=C_MACD, lw=1.1, label="MACD")
        axes[2].plot(s.index, sig, color=C_SIG,  lw=1.0, label="Signal")
        axes[2].axhline(0, color=GRID, lw=0.6)
        axes[2].set_ylabel("MACD", color=FG, fontsize=9)
        axes[2].legend(loc="upper left", fontsize=8, facecolor=PANEL,
                       labelcolor=FG, framealpha=0.85, edgecolor=GRID)

        # ── Panel 3: MACD14 14/28/9 ──
        m14, sig14, hist14 = MACD_calc(s, 14, 28, 9)
        colors3 = ["#50c878" if v >= 0 else "#e05050" for v in hist14.fillna(0)]
        axes[3].bar(s.index, hist14, color=colors3, alpha=0.5, width=bw)
        axes[3].plot(s.index, m14,   color=C_MACD14, lw=1.1, label="MACD14")
        axes[3].plot(s.index, sig14, color=C_SIG,    lw=1.0, label="Signal")
        axes[3].axhline(0, color=GRID, lw=0.6)
        axes[3].set_ylabel("MACD14", color=FG, fontsize=9)
        axes[3].legend(loc="upper left", fontsize=8, facecolor=PANEL,
                       labelcolor=FG, framealpha=0.85, edgecolor=GRID)
        locator = mdates.AutoDateLocator()
        axes[3].xaxis.set_major_locator(locator)
        axes[3].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))

        plt.tight_layout(pad=0.8)
        plt.savefig(out_path, dpi=125, facecolor=BG, bbox_inches="tight")
        plt.close(fig)
    except Exception as e:
        log(f"plot error {title}: {e}")

def plot_series_3panel(series, title, out_path, ma_n=36, ma_label="36"):
    """3-panel chart for en (allerede resamplet) serie: pris+36MA, RSI, MACD.
    Brukes for trend-ratioenes maanedlige og 3-maaneders charts."""
    try:
        s = series.dropna()
        if len(s) < 5:
            return
        fig, axes = plt.subplots(3, 1, sharex=True, figsize=(12, 8),
                                 facecolor=BG, gridspec_kw={"height_ratios":[3,1,1], "hspace":0.12})
        for ax in axes: _style_ax(ax)

        ma = SMA(s, ma_n)
        axes[0].plot(s.index, s, color=C_PRICE, lw=1.6, label="Ratio")
        if ma.notna().any():
            axes[0].plot(s.index, ma, color=C_SMA36, lw=1.2, label=f"SMA{ma_label}")
        last_v = s.iloc[-1]
        axes[0].scatter([s.index[-1]], [last_v], color=C_PRICE, s=28, zorder=5)
        axes[0].annotate(f"{last_v:,.3f}", xy=(s.index[-1], last_v), xytext=(6,0),
                         textcoords="offset points", color=C_PRICE, fontsize=9,
                         fontweight="bold", va="center")
        axes[0].set_title(title, fontsize=12, color=FG, fontweight="bold", pad=8)
        axes[0].legend(loc="upper left", fontsize=8.5, facecolor=PANEL,
                       labelcolor=FG, framealpha=0.85, edgecolor=GRID)

        rsi = RSI(s)
        axes[1].axhspan(70,100, color="#e05050", alpha=0.08)
        axes[1].axhspan(0,30,   color="#50c878", alpha=0.08)
        axes[1].plot(s.index, rsi, color=C_RSI, lw=1.3)
        axes[1].axhline(70, color="#e05050", ls="--", lw=0.8, alpha=0.7)
        axes[1].axhline(30, color="#50c878", ls="--", lw=0.8, alpha=0.7)
        axes[1].set_ylim(0,100); axes[1].set_yticks([30,50,70])
        axes[1].set_ylabel("RSI 14", color=FG, fontsize=9)

        m, sig, hist = MACD_calc(s, 12, 26, 9)
        colors2 = ["#50c878" if v>=0 else "#e05050" for v in hist.fillna(0)]
        bw = max(5, (s.index[-1]-s.index[0]).days/len(s)*0.7) if len(s)>1 else 8
        axes[2].bar(s.index, hist, color=colors2, alpha=0.5, width=bw)
        axes[2].plot(s.index, m,   color=C_MACD, lw=1.1, label="MACD")
        axes[2].plot(s.index, sig, color=C_SIG,  lw=1.0, label="Signal")
        axes[2].axhline(0, color=GRID, lw=0.6)
        axes[2].set_ylabel("MACD", color=FG, fontsize=9)
        axes[2].legend(loc="upper left", fontsize=8, facecolor=PANEL,
                       labelcolor=FG, framealpha=0.85, edgecolor=GRID)
        locator = mdates.AutoDateLocator()
        axes[2].xaxis.set_major_locator(locator)
        axes[2].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))

        plt.tight_layout(pad=0.8)
        plt.savefig(out_path, dpi=125, facecolor=BG, bbox_inches="tight")
        plt.close(fig)
    except Exception as e:
        log(f"plot_series_3panel error {title}: {e}")

def plot_ratio(df_num, df_den, label, out_path):
    try:
        combined = pd.DataFrame({"num": df_num["close_use"], "den": df_den["close_use"]}).dropna()
        if len(combined) < 50: return
        combined["ratio"] = combined["num"] / combined["den"]
        weekly = combined["ratio"].resample("W-FRI").last().dropna()
        if len(weekly) < 36: return
        ws = pd.Series(weekly.values, index=weekly.index)

        fig, axes = plt.subplots(2,1, sharex=True, figsize=(11,6), facecolor=BG)
        for ax in axes: _style_ax(ax)
        axes[0].plot(weekly.index, weekly.values, color=C_SMA36, lw=1.2, label=label)
        sma36 = SMA(ws, 36)
        if sma36.notna().any():
            axes[0].plot(weekly.index, sma36.values, color=C_PRICE, lw=0.9, ls="--", label="SMA36")
        axes[0].set_title(f"Ratio: {label}", fontsize=10, color=FG)
        axes[0].legend(fontsize=7, facecolor=BG, labelcolor=FG, framealpha=0.7)
        rsi = RSI(ws)
        axes[1].plot(weekly.index, rsi.values, color=C_RSI, lw=1.0)
        axes[1].axhline(70, color="#e05050", ls="--", lw=0.7)
        axes[1].axhline(30, color="#50c878", ls="--", lw=0.7)
        axes[1].set_ylim(0,100)
        axes[1].set_ylabel("RSI(14)", color=FG, fontsize=8)
        locator = mdates.AutoDateLocator()
        axes[1].xaxis.set_major_locator(locator)
        axes[1].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        plt.tight_layout(pad=0.7)
        plt.savefig(out_path, dpi=120, facecolor=BG)
        plt.close(fig)
        log(f"  ratio: {label}")
    except Exception as e:
        log(f"  ratio error {label}: {e}")

# ─── NEWS ──────────────────────────────────────────────────────
def last_n_days_posts(url, days=4):
    from bs4 import BeautifulSoup
    out = []
    try:
        r = requests.get(url, timeout=30); r.raise_for_status()
        soup  = BeautifulSoup(r.text, "lxml")
        items = soup.find_all("item")
        cutoff = pd.Timestamp(NOW.date()) - pd.Timedelta(days=days)
        for it in items[:20]:
            tn = it.find("title"); ln = it.find("link")
            if not tn or not ln: continue
            title = tn.get_text(strip=True); link = ln.get_text(strip=True)
            pub = it.find("pubdate")
            ts  = pd.to_datetime(pub.get_text(strip=True)) if pub else None
            if ts is not None:
                if ts.tzinfo is None: ts = ts.tz_localize("UTC")
                if ts.tz_convert(TZ) < pd.Timestamp(cutoff, tz=TZ): continue
            out.append({"title": title, "link": link,
                        "published": ts.tz_convert(TZ).isoformat() if ts else ""})
    except Exception as e:
        log(f"rss error {url}: {e}")
    return out

# ─── MAIN LOOP ─────────────────────────────────────────────────
log(f"Starting - {len(ALL_IDS)} instruments")
raw_cache = {}

summary = {
    "generated_local": NOW.isoformat(),
    "assets": {},
    "categories": [
        {"key": g["key"], "title": g["title"], "description": g["description"],
         "sector": g.get("sector",""), "instrument_ids": [i["id"] for i in g["instruments"]]}
        for g in INSTRUMENT_GROUPS
    ],
}

for group in INSTRUMENT_GROUPS:
    for inst in group["instruments"]:
        iid = inst["id"]
        log(f"Fetching {iid}...")
        df, resolved = get_instrument_series(inst)

        entry = {
            "id": iid, "display_name": inst["label"], "symbol_label": inst["symbol_label"],
            "resolved_symbol": resolved, "source": inst["source"],
            "category_key": group["key"], "category_title": group["title"],
            "sector": group.get("sector",""),
            "frames": {"daily":{}, "weekly":{}, "monthly":{}},
            "missing_data": df is None or getattr(df,"empty",True),
        }
        if entry["missing_data"]:
            summary["assets"][iid] = entry; log(f"  MISSING: {iid}"); continue

        raw_cache[iid] = df
        daily, weekly, monthly = resample_frames(df)
        entry["frames"]["daily"]   = frame_summary(daily,   is_weekly=False)
        entry["frames"]["weekly"]  = frame_summary(weekly,  is_weekly=True)
        entry["frames"]["monthly"] = frame_summary(monthly, is_weekly=False)

        last_252 = daily.tail(252)
        entry["52w_high"] = float(last_252["close_use"].max()) if not last_252.empty else None
        entry["52w_low"]  = float(last_252["close_use"].min()) if not last_252.empty else None

        score, score_points = northstar_score(entry)
        emoji, slabel = score_label(score)
        entry["northstar_score"]        = score
        entry["northstar_score_label"]  = slabel
        entry["northstar_score_points"] = score_points

        if not weekly.empty:
            plot_compact(weekly.tail(400), f"{inst['label']} ({inst['symbol_label']}) - weekly",
                         CHARTS / f"{iid}_weekly_compact.png")
        if not monthly.empty:
            plot_compact(monthly.tail(400), f"{inst['label']} ({inst['symbol_label']}) - monthly",
                         CHARTS / f"{iid}_monthly_compact.png")

        summary["assets"][iid] = entry
        log(f"  OK: {iid} score={score}")

# ─── VS GULL: relativ styrke mot gull per instrument ───────────
# Northstar: vurder alt mot gull, ikke bare egen MA. Beregner hver
# instrument-ratio mot GLD: over stigende 36W-MA = slaar gull.
gold_df = raw_cache.get("GLD")
for iid, a in summary["assets"].items():
    if a.get("missing_data") or iid == "GLD" or gold_df is None:
        a["vs_gold"] = None
        continue
    inst_df = raw_cache.get(iid)
    if inst_df is None:
        a["vs_gold"] = None
        continue
    try:
        comb = pd.DataFrame({"i": inst_df["close_use"], "g": gold_df["close_use"]}).dropna()
        if len(comb) < 60:
            a["vs_gold"] = None
            continue
        ratio = (comb["i"]/comb["g"]).resample("W-FRI").last().dropna()
        if len(ratio) < 40:
            a["vs_gold"] = None
            continue
        ma = ratio.rolling(36).mean()
        last = float(ratio.iloc[-1])
        ma_now = float(ma.iloc[-1]) if pd.notna(ma.iloc[-1]) else None
        ma_prev = float(ma.iloc[-9]) if (len(ma) >= 9 and pd.notna(ma.iloc[-9])) else None
        above = (last > ma_now) if ma_now else None
        rising = (ma_now > ma_prev) if (ma_now and ma_prev) else None
        dist = ((last-ma_now)/ma_now) if ma_now else None
        if above and rising:   vstate, vcol = "Slaar gull", "#50c878"
        elif above:            vstate, vcol = "Over gull-MA", "#7ec88a"
        elif rising:           vstate, vcol = "Snur vs gull", "#f0a500"
        else:                  vstate, vcol = "Taper mot gull", "#e05050"
        a["vs_gold"] = {"state": vstate, "col": vcol, "dist": dist}
    except Exception:
        a["vs_gold"] = None

# Sector scores
sector_scores = {}
for iid, a in summary["assets"].items():
    if a.get("missing_data") or a.get("northstar_score") is None: continue
    sec = a.get("sector","Annet")
    sector_scores.setdefault(sec, []).append(a["northstar_score"])

sector_summary = {}
for sec, scores in sector_scores.items():
    avg = round(sum(scores)/len(scores), 1)
    emoji, label = score_label(avg)
    sector_summary[sec] = {"avg_score": avg, "label": label, "n": len(scores)}

# ─── MAKRO-REGIME (NFTRH-stil): yield-kurve + Fed-likviditet ───
log("Makro-regime...")
regime = {}

# 1) Yield-kurve 2s10s: invertert (< 0) vs un-invertert (> 0)
yc_df = raw_cache.get("2S10S")
if yc_df is not None and not yc_df.empty:
    yc_last = float(yc_df["close_use"].iloc[-1])
    yc_3m_ago = float(yc_df["close_use"].iloc[-63]) if len(yc_df) >= 63 else yc_last
    yc_dir = "stiler" if yc_last > yc_3m_ago else "flater"
    if yc_last < 0:
        regime["yield_curve"] = {"label": f"Invertert ({yc_last:.2f})", "col": "#e05050",
                                 "note": f"Resesjonsvarsel aktivt, {yc_dir}"}
    elif yc_last < 0.5:
        regime["yield_curve"] = {"label": f"Un-invertering ({yc_last:.2f})", "col": "#f0a500",
                                 "note": f"Hoey resesjonsrisiko etter un-invertering, {yc_dir}"}
    else:
        regime["yield_curve"] = {"label": f"Normal ({yc_last:.2f})", "col": "#50c878",
                                 "note": f"Kurven {yc_dir}"}
else:
    regime["yield_curve"] = {"label": "ingen data", "col": "#9aa7b5", "note": "FRED-noekkel mangler?"}

# 2) Fed-balanse (WALCL): stigende = stimulativt, fallende = QT
fed_df = fred_series("WALCL")
if fed_df is not None and not fed_df.empty:
    fed_last = float(fed_df["close_use"].iloc[-1])
    fed_3m   = float(fed_df["close_use"].iloc[-63]) if len(fed_df) >= 63 else fed_last
    fed_12m  = float(fed_df["close_use"].iloc[-252]) if len(fed_df) >= 252 else fed_last
    chg_3m = (fed_last/fed_3m - 1)*100 if fed_3m else 0
    if fed_last > fed_3m:
        regime["fed_liquidity"] = {"label": f"Stigende ({chg_3m:+.1f}% 3m)", "col": "#50c878",
                                   "note": "Stimulativ fase - likviditet inn (NFTRH: QE-naer)"}
    elif fed_last > fed_12m * 0.98:
        regime["fed_liquidity"] = {"label": f"Baser seg ({chg_3m:+.1f}% 3m)", "col": "#f0a500",
                                   "note": "Balanse baser seg - mulig vending mot stimulering"}
    else:
        regime["fed_liquidity"] = {"label": f"Fallende ({chg_3m:+.1f}% 3m)", "col": "#e05050",
                                   "note": "QT paagaar - likviditet ut"}
else:
    regime["fed_liquidity"] = {"label": "ingen data", "col": "#9aa7b5", "note": "FRED-noekkel mangler?"}

# 3) 10yr yield-retning (Continuum): over/under stigende?
ten_df = raw_cache.get("UTEN")
if ten_df is not None and not ten_df.empty:
    ten_last = float(ten_df["close_use"].iloc[-1])
    ten_ma = ten_df["close_use"].rolling(200).mean()
    ten_ma_last = float(ten_ma.iloc[-1]) if pd.notna(ten_ma.iloc[-1]) else None
    if ten_ma_last:
        if ten_last > ten_ma_last:
            regime["yields"] = {"label": f"Stigende ({ten_last:.2f})", "col": "#e05050",
                                "note": "10yr over 200d MA - rentepress oppover"}
        else:
            regime["yields"] = {"label": f"Fallende ({ten_last:.2f})", "col": "#50c878",
                                "note": "10yr under 200d MA"}

# Stock-vs-gold regime (Northstar kapitalrotasjon): hvor mange aksjer slaar gull?
equity_ids = [i["id"] for g in INSTRUMENT_GROUPS if g["sector"] in ("Aksjer","Tech") for i in g["instruments"]]
beats = []; loses = []
for iid in equity_ids:
    vg = summary["assets"].get(iid,{}).get("vs_gold")
    if not vg:
        continue
    sym = summary["assets"].get(iid,{}).get("symbol_label", iid)
    if vg.get("state","").startswith("Slaar"):
        beats.append(sym)
    else:
        loses.append(sym)
total_eq = len(beats) + len(loses)
if total_eq > 0:
    beat_str = ", ".join(beats) if beats else "ingen"
    lose_str = ", ".join(loses) if loses else "ingen"
    detail = f"Slaar gull: {beat_str}. Taper: {lose_str}."
    if len(beats) == 0:
        regime["rotation"] = {"label": f"0 av {total_eq} slaar gull", "col": "#e05050",
                              "note": f"Alle aksjer i bear market vs gull - kapitalrotasjon paagaar. {detail}"}
    elif len(beats) < total_eq/2:
        regime["rotation"] = {"label": f"{len(beats)} av {total_eq} slaar gull", "col": "#f0a500",
                              "note": f"Faa aksjer slaar gull - rotasjon mot hard assets. {detail}"}
    else:
        regime["rotation"] = {"label": f"{len(beats)} av {total_eq} slaar gull", "col": "#50c878",
                              "note": f"Aksjer holder foelge med gull. {detail}"}

# ─── MAKRO-REGIME CHARTS (3-maaneders) ─────────────────────────
def plot_macro_3m(series, title, out_path, zero_line=False):
    """Enkelt 3-maaneders linjechart for makro-serie (yield-kurve, Fed, yield)."""
    try:
        q = series.resample("QE").last().dropna()
        if len(q) < 4:
            return False
        fig, ax = plt.subplots(figsize=(11, 4.5), facecolor=BG)
        _style_ax(ax)
        ax.plot(q.index, q.values, color=C_PRICE, lw=1.8)
        ma = q.rolling(8).mean()
        if ma.notna().any():
            ax.plot(q.index, ma.values, color=C_SMA36, lw=1.1, ls="--", label="8Q MA")
        if zero_line:
            ax.axhline(0, color="#e05050", lw=1.0, ls="--", alpha=0.7)
        last_v = q.iloc[-1]
        ax.scatter([q.index[-1]], [last_v], color=C_PRICE, s=30, zorder=5)
        ax.annotate(f"{last_v:,.2f}", xy=(q.index[-1], last_v), xytext=(6,0),
                    textcoords="offset points", color=C_PRICE, fontsize=10,
                    fontweight="bold", va="center")
        ax.set_title(title, fontsize=12, color=FG, fontweight="bold", pad=8)
        ax.legend(loc="upper left", fontsize=8.5, facecolor=PANEL, labelcolor=FG,
                  framealpha=0.85, edgecolor=GRID)
        locator = mdates.AutoDateLocator()
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        plt.tight_layout(pad=0.8)
        plt.savefig(out_path, dpi=125, facecolor=BG, bbox_inches="tight")
        plt.close(fig)
        return True
    except Exception as e:
        log(f"macro chart error {title}: {e}")
        return False

if yc_df is not None and not yc_df.empty:
    if plot_macro_3m(yc_df["close_use"], "Yield-kurve 2s10s - 3-maaneders", CHARTS/"macro_2s10s.png", zero_line=True):
        regime.setdefault("yield_curve",{})["chart"] = "charts/macro_2s10s.png"
if fed_df is not None and not fed_df.empty:
    if plot_macro_3m(fed_df["close_use"], "Fed-balanse (WALCL) - 3-maaneders", CHARTS/"macro_fed.png"):
        regime.setdefault("fed_liquidity",{})["chart"] = "charts/macro_fed.png"
if ten_df is not None and not ten_df.empty:
    if plot_macro_3m(ten_df["close_use"], "10yr yield - 3-maaneders", CHARTS/"macro_10yr.png"):
        regime.setdefault("yields",{})["chart"] = "charts/macro_10yr.png"

# Ratio charts + ratio scoring
log("Ratio charts...")
ratio_results = {}

def ratio_metrics(df_num, df_den):
    """Northstar-score for ratio (samme modell), + ukentlig score-historikk."""
    try:
        combined = pd.DataFrame({"num": df_num["close_use"], "den": df_den["close_use"]}).dropna()
        if len(combined) < 200:
            return None
        ratio = (combined["num"] / combined["den"])
        score, points, frames = score_synthetic_series(ratio)
        if score is None:
            return None
        w = frames.get("weekly", {})
        emoji, slabel = score_label(score)
        rcol = score_color(score)
        # ukentlig score-historikk (12 uker for rotasjon-sparkline)
        wk_hist = weekly_score_history(ratio, weeks=12)
        return {"score": score, "points": points, "label": slabel, "rcol": rcol,
                "dist_to_36MA": w.get("dist_to_36MA"),
                "dist_to_3yr_MA": w.get("dist_to_3yr_MA"),
                "score_series": wk_hist}
    except Exception as e:
        log(f"  ratio_metrics error: {e}")
        return None

for (num_id, den_id, label) in RATIO_PAIRS:
    if num_id in raw_cache and den_id in raw_cache:
        rid = f"RATIO_{num_id}_{den_id}"
        out_path = CHARTS / f"{rid}_weekly_compact.png"
        plot_ratio(raw_cache[num_id], raw_cache[den_id], label, out_path)
        rm = ratio_metrics(raw_cache[num_id], raw_cache[den_id])
        ratio_results[rid] = {"label": label, "numerator": num_id, "denominator": den_id,
                              "chart_weekly": f"charts/{rid}_weekly_compact.png",
                              "metrics": rm}

# News
log("News...")
news = {"nftrh": last_n_days_posts("https://nftrh.com/blog/feed/"),
        "northstar": last_n_days_posts("https://northstarbadcharts.com/feed/")}
with open(NEWS_DIR/"news.json","w",encoding="utf-8") as f:
    json.dump(news, f, ensure_ascii=False, indent=2)

# Portfolio brief
def build_portfolio_brief(assets_dict, sector_sum):
    buckets = {"lavrisiko":[], "noytral":[], "avvent":[], "unnga":[]}
    for iid, a in assets_dict.items():
        if a.get("missing_data") or a.get("northstar_score") is None: continue
        s  = a["northstar_score"]
        w_ = a.get("frames",{}).get("weekly")  or {}
        d_ = a.get("frames",{}).get("daily")   or {}
        m_ = a.get("frames",{}).get("monthly") or {}
        it = {"id":iid,"name":a.get("display_name",iid),"score":s,
              "label":a.get("northstar_score_label",""),"w":w_,"d":d_,"m":m_}
        if s>=75:   buckets["lavrisiko"].append(it)
        elif s>=55: buckets["noytral"].append(it)
        elif s>=35: buckets["avvent"].append(it)
        else:       buckets["unnga"].append(it)
    for k in buckets: buckets[k].sort(key=lambda x:-x["score"])

    def fr(v): return f"{v:.1f}" if isinstance(v,float) else "-"
    def fp(v): return f"{v*100:.1f}%" if isinstance(v,float) else "-"

    lines = [f"## Ukentlig Portfolio-Brief - {NOW.strftime('%d. %B %Y')}","",
             "### Sektorscore","","| Sektor | Score | Signal | n |","|---|---:|---|---:|"]
    for sec in sorted([s for s in ["Aksjer","Tech","Edelmetaller","Rawarer","Valuta","Crypto","Renter"] if s in sector_sum], key=lambda s:-sector_sum[s]["avg_score"]):
        ss = sector_sum[sec]
        lines.append(f"| {sec} | {ss['avg_score']} | {ss['label']} | {ss['n']} |")
    lines.append("")

    for key, title, desc in [
        ("lavrisiko","Lavrisiko entry","Near 3yr MA, RSI ok, momentum positivt."),
        ("noytral",  "Noytral - hold","Trend OK men ikke ideal entry."),
        ("avvent",   "Avvent",         "Stretched eller svak momentum."),
        ("unnga",    "Unnga/trim",     "Overbought, under MA, eller ingen bekreftelse."),
    ]:
        lines += [f"### {title}",f"_{desc}_","",
                  "| Instrument | Score | D-RSI | W-RSI | M-RSI | Dist 3yr | Dist 36W |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for it in buckets[key]:
            lines.append(
                f"| {it['name']} | **{it['score']}** | "
                f"{fr(it['d'].get('rsi14'))} | {fr(it['w'].get('rsi14'))} | {fr(it['m'].get('rsi14'))} | "
                f"{fp(it['w'].get('dist_to_3yr_MA'))} | {fp(it['w'].get('dist_to_36MA'))} |")
        if not buckets[key]: lines.append("_Ingen instrumenter._")
        lines.append("")
    return "\n".join(lines)

brief_md = build_portfolio_brief(summary["assets"], sector_summary)
with open(DOCS/"portfolio_brief.md","w",encoding="utf-8") as f: f.write(brief_md)

# ─── HISTORIKK & SCORE-ENDRING ─────────────────────────────────
# Arkiver dagens score per instrument, og les historikk for trend over tid.
# Historikk hentes fra live gh-pages slik at den overlever mellom kjoeringer
# (main-checkout har ikke docs/history fra forrige run).
HIST_DIR = DOCS / "history"
HIST_DIR.mkdir(exist_ok=True)

PAGES_HIST_BASE = "https://regg92s-hub.github.io/market-daily-report/history"

def bootstrap_history_from_pages():
    """Hent index over historikk-filer fra live site hvis lokal mappe er tom."""
    existing = list(HIST_DIR.glob("*.json"))
    if existing:
        return  # allerede lokal historikk
    try:
        # hent manifest hvis det finnes
        r = requests.get(f"{PAGES_HIST_BASE}/manifest.json", timeout=20)
        if r.status_code == 200:
            dates = r.json().get("dates", [])
            for d in dates[-42:]:
                rr = requests.get(f"{PAGES_HIST_BASE}/{d}.json", timeout=15)
                if rr.status_code == 200:
                    (HIST_DIR / f"{d}.json").write_bytes(rr.content)
            log(f"  bootstrapped {len(dates[-42:])} history files from pages")
    except Exception as e:
        log(f"  history bootstrap skipped: {e}")

bootstrap_history_from_pages()

today_snapshot = {
    "date": NOW.strftime("%Y-%m-%d"),
    "generated": NOW.isoformat(),
    "scores": {iid: a.get("northstar_score")
               for iid, a in summary["assets"].items()
               if not a.get("missing_data") and a.get("northstar_score") is not None},
    "sector_scores": {sec: ss["avg_score"] for sec, ss in sector_summary.items()},
}
with open(HIST_DIR / f"{NOW.strftime('%Y-%m-%d')}.json", "w", encoding="utf-8") as f:
    json.dump(today_snapshot, f, ensure_ascii=False, indent=2)

# Skriv manifest over alle historikk-datoer
all_dates = sorted([p.stem for p in HIST_DIR.glob("*.json") if p.stem != "manifest"])
with open(HIST_DIR / "manifest.json", "w", encoding="utf-8") as f:
    json.dump({"dates": all_dates}, f, ensure_ascii=False, indent=2)

# Les siste 42 dager (ca 6 uker) historikk
history_files = sorted(HIST_DIR.glob("*.json"))
history = []
for hf in history_files[-42:]:
    try:
        history.append(json.loads(hf.read_text(encoding="utf-8")))
    except Exception:
        pass

# Score-endring: naa vs ca 7 dager siden (forrige uke)
def score_delta(iid):
    cur = today_snapshot["scores"].get(iid)
    if cur is None or len(history) < 2:
        return None, None
    # finn snapshot naermest 7 dager tilbake
    week_ago = None
    for h in history[:-1]:
        if iid in h.get("scores", {}):
            week_ago = h["scores"][iid]
    if week_ago is None:
        return None, None
    return cur - week_ago, week_ago

for iid, a in summary["assets"].items():
    if a.get("missing_data"): continue
    delta, prev = score_delta(iid)
    a["score_delta"] = delta
    a["score_prev"]  = prev

# Sektor-trend sparkline-data (siste 6 ukers sektor-snitt)
sector_trend = {}
for sec in sector_summary:
    series = []
    seen_dates = set()
    for h in history:
        d = h.get("date")
        v = h.get("sector_scores", {}).get(sec)
        if v is not None and d not in seen_dates:
            series.append(v)
            seen_dates.add(d)
    sector_trend[sec] = series[-30:]   # opptil 30 datapunkter

# ─── SEKTOR-ROTASJON (ratio Northstar-score) ───────────────────
rotation = []
for rid, r in ratio_results.items():
    m = r.get("metrics")
    if m:
        rotation.append({"label": r["label"], "score": m["score"],
                         "rlabel": m["label"], "rcol": m["rcol"],
                         "dist36": m.get("dist_to_36MA"),
                         "score_series": m.get("score_series", [])})
rotation.sort(key=lambda x: -x["score"])

# ─── TREND-OVERSIKT: hent tickere, bygg ratioer, score + charts ──
log("Trend-oversikt: henter tickere...")
trend_price = {}
for key, candidates in TREND_TICKERS.items():
    df, resolved = yf_series_from_candidates(candidates)
    if df is not None and not df.empty:
        s = df["close_use"].copy()
        if key == "NOK" and NOK_INVERT:
            s = 1.0 / s
        trend_price[key] = s
        log(f"  trend ok: {key} ({resolved})")
    else:
        log(f"  trend MANGLER: {key}")

trend_ratios = []
for (num_key, den_key, label) in TREND_RATIOS:
    if num_key not in trend_price or den_key not in trend_price:
        log(f"  hopper over {label} (mangler data)")
        continue
    combined = pd.DataFrame({"num": trend_price[num_key], "den": trend_price[den_key]}).dropna()
    if len(combined) < 200:
        continue
    ratio = (combined["num"] / combined["den"]).dropna()
    score, points, frames = score_ratio_series(ratio)
    if score is None:
        continue
    emoji, slabel = score_label(score)
    rid = f"TREND_{num_key}_{den_key}"
    m_hist = monthly_ratio_score_history(ratio, months=6)
    # Tydelige charts (samme stil som Market Daily Report): bygg df og bruk plot_compact
    # MA-perioder tilpasset tidsrammen: maanedlig 12M(1aar)+36M(3aar), kvartal 4Q+12Q
    monthly_s = ratio.resample("ME").last().dropna()
    q_s       = ratio.resample("QE").last().dropna()
    mdf = pd.DataFrame({"close_use": monthly_s, "volume": np.nan})
    qdf = pd.DataFrame({"close_use": q_s,       "volume": np.nan})
    plot_compact(mdf.tail(180), f"{label} - maanedlig",
                 CHARTS / f"{rid}_monthly.png",
                 ma_short=12, ma_long=36, ma_short_label="SMA12 (1aar)", ma_label_long="SMA36 (3aar)")
    plot_compact(qdf.tail(120), f"{label} - 3-maaneders",
                 CHARTS / f"{rid}_quarterly.png",
                 ma_short=4, ma_long=12, ma_short_label="SMA4 (1aar)", ma_label_long="SMA12 (3aar)")
    m = frames.get("monthly", {}); q = frames.get("quarterly", {})
    trend_ratios.append({
        "rid": rid, "label": label, "score": score, "label_txt": slabel,
        "points": points, "score_series_monthly": m_hist,
        "chart_monthly": f"charts/{rid}_monthly.png",
        "chart_quarterly": f"charts/{rid}_quarterly.png",
        "mrsi": m.get("rsi14"), "qrsi": q.get("rsi14"),
        "dist36m": m.get("dist_to_36MA"), "dist36q": q.get("dist_to_36MA"),
        "macd_m": m.get("macd_hist"), "macd_q": q.get("macd_hist"),
    })
trend_ratios.sort(key=lambda x: -x["score"])
log(f"Trend-oversikt: {len(trend_ratios)} ratioer scoret")

# Index.json
index = {"generated_local": NOW.isoformat(), "version": VERSION, "summary": summary,
         "sector_summary": sector_summary, "sector_trend": sector_trend,
         "ratio_charts": ratio_results, "rotation": rotation,
         "trend_ratios": trend_ratios, "regime": regime,
         "notes": {"instrument_count": len(ALL_IDS)}}
with open(DOCS/"index.json","w",encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

files = sorted([f"charts/{fn.name}" for fn in CHARTS.glob("*.png")])
with open(DOCS/"filelist.json","w",encoding="utf-8") as f:
    json.dump({"charts":files}, f, ensure_ascii=False, indent=2)

# ─── HTML ──────────────────────────────────────────────────────
def fmt(v, d=1): return f"{v:.{d}f}" if isinstance(v,float) and not math.isnan(v) else "-"
def fmt_pct(v):  return f"{v*100:.1f}%" if isinstance(v,float) and not math.isnan(v) else "-"

def macd_html(v):
    if v is None: return "-"
    c = "#50c878" if v>0 else "#e05050"
    arr = "&#9650;" if v>0 else "&#9660;"
    return f'<span style="color:{c}">{arr} {abs(v):.4f}</span>'

def sparkline_svg(values, color="#7ec8e3", w=120, h=32):
    """Liten inline SVG trend-graf."""
    if not values or len(values) < 2:
        return '<svg class="sc-spark"></svg>'
    vmin, vmax = min(values), max(values)
    rng = (vmax - vmin) or 1
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        x = (i / (n - 1)) * w
        y = h - ((v - vmin) / rng) * (h - 4) - 2
        pts.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(pts)
    last_x, last_y = pts[-1].split(",")
    return (f'<svg class="sc-spark" viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
            f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="1.5"/>'
            f'<circle cx="{last_x}" cy="{last_y}" r="2" fill="{color}"/></svg>')

def delta_html(delta):
    if delta is None:
        return '<span class="delta-flat">–</span>'
    if delta > 0.5:
        return f'<span class="delta-up">&#9650; +{delta:.0f}</span>'
    if delta < -0.5:
        return f'<span class="delta-dn">&#9660; {delta:.0f}</span>'
    return '<span class="delta-flat">&#8226; 0</span>'

SECTOR_ANCHORS = {
    "Aksjer": "sec-aksjer", "Tech": "sec-tech", "Edelmetaller": "sec-edelmetaller",
    "Rawarer": "sec-rawarer", "Valuta": "sec-valuta", "Crypto": "sec-crypto",
    "Renter": "sec-renter",
}

def regime_stripe_html(regime):
    """Makro-regime stripe (NFTRH-stil): yield-kurve, Fed-likviditet, 10yr, rotasjon."""
    if not regime:
        return ""
    cards = [
        ("Yield-kurve (2s10s)", regime.get("yield_curve")),
        ("Fed-likviditet",      regime.get("fed_liquidity")),
        ("10yr yield",          regime.get("yields")),
        ("Aksjer vs gull",      regime.get("rotation")),
    ]
    out = ['<section class="section"><h2>&#127760; Makro-regime</h2>'
           '<p style="color:var(--muted);font-size:12px">NFTRH/Northstar makro-kontekst: '
           'renteregime, Fed-likviditet og kapitalrotasjon mot gull. Setter rammen for alt under.</p>'
           '<div class="sector-grid">']
    for name, r in cards:
        if not r:
            continue
        c = r.get("col", "#9aa7b5")
        out.append(
            f'<div class="sc" style="border-color:{c}50;cursor:default;text-align:left">'
            f'<div class="sc-name" style="min-height:auto">{html.escape(name)}</div>'
            f'<div style="font-size:15px;font-weight:700;color:{c};margin:3px 0">{html.escape(r.get("label",""))}</div>'
            f'<div style="font-size:11px;color:var(--muted);line-height:1.4">{html.escape(r.get("note",""))}</div>'
            f'</div>')
    out.append('</div>')
    # 3-maaneders charts under kortene
    chart_cards = [("Yield-kurve 2s10s", regime.get("yield_curve")),
                   ("Fed-balanse",       regime.get("fed_liquidity")),
                   ("10yr yield",        regime.get("yields"))]
    chart_figs = []
    for cname, r in chart_cards:
        if r and r.get("chart"):
            chart_figs.append(
                f'<figure><img src="{html.escape(r["chart"])}" alt="{html.escape(cname)}" loading="lazy">'
                f'<figcaption>{html.escape(cname)} (3-maaneders)</figcaption></figure>')
    if chart_figs:
        out.append('<div class="charts-grid" style="margin-top:12px">' + "".join(chart_figs) + '</div>')
    out.append('</section>')
    return "".join(out)

def build_homepage(index_data, filelist, brief_md_text):
    assets      = index_data.get("summary",{}).get("assets",{})
    categories  = index_data.get("summary",{}).get("categories",[])
    sec_sum     = index_data.get("sector_summary",{})
    sec_trend   = index_data.get("sector_trend",{})
    rotation    = index_data.get("rotation",[])
    ratios      = index_data.get("ratio_charts",{})
    regime      = index_data.get("regime",{})
    generated   = index_data.get("generated_local") or NOW.isoformat()
    file_set    = set(filelist)

    CSS = """:root{--bg:#0b0d10;--panel:#12161c;--panel2:#171c23;--text:#e7edf3;--muted:#9aa7b5;--border:#27313d}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.45}
.wrap{max-width:1600px;margin:0 auto;padding:20px 16px 40px}
h1{margin:0 0 4px;font-size:24px}h2{margin:0 0 6px;font-size:18px}
.topnote{color:var(--muted);margin:0 0 18px;font-size:13px}
.section{margin:0 0 22px;padding:14px 16px;border:1px solid var(--border);border-radius:14px;background:var(--panel)}
.sector-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-top:10px}
.sc{padding:10px 12px;border-radius:10px;border:1px solid var(--border);background:var(--panel2);text-align:center}
.sc-name{font-size:11px;color:var(--muted)}.sc-score{font-size:22px;font-weight:700;margin:2px 0}
.sc-label{font-size:10px}.sc-n{font-size:10px;color:var(--muted)}
.inst-table{width:100%;border-collapse:collapse;font-size:12px;margin-top:10px}
.inst-table th{background:var(--panel2);padding:5px 7px;text-align:left;border-bottom:1px solid var(--border);color:var(--muted);font-weight:600;white-space:nowrap}
.inst-table td{padding:4px 7px;border-bottom:1px solid #1e2530;vertical-align:top}
.inst-table tr:last-child td{border-bottom:none}.inst-table tr:hover td{background:#161b22}
.pill{display:inline-block;padding:2px 6px;border-radius:6px;font-size:11px;font-weight:700}
.pts-bar{display:flex;gap:2px;flex-wrap:wrap;margin-top:3px}
.pt{font-size:10px;padding:1px 4px;border-radius:3px;background:#1e2530;color:var(--muted)}
.pt.ok{background:#0d2a1a;color:#50c878}.pt.mid{background:#2a2000;color:#f0a500}.pt.bad{background:#2a0d0d;color:#e05050}
.charts-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:12px;margin-top:10px}
.inst-block{margin:0 0 18px;padding:14px;border:1px solid var(--border);border-radius:12px;background:var(--panel2)}
.inst-block:last-child{margin-bottom:0}
.inst-head{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:baseline;margin-bottom:6px}
.inst-head h3{margin:0;font-size:17px}
.ticker{color:var(--muted);font-weight:600;font-size:13px}
.delta{color:var(--muted);font-size:12px}
figure{margin:0;border:1px solid var(--border);border-radius:10px;overflow:hidden;background:#0f141a}
img{display:block;width:100%;height:auto}figcaption{padding:5px 10px;border-top:1px solid var(--border);color:var(--muted);font-size:12px}
.missing{padding:12px;border:1px dashed var(--border);border-radius:8px;color:var(--muted);font-size:12px}
details>summary{cursor:pointer;color:var(--muted);font-size:13px;padding:4px 0}
.brief-pre{white-space:pre-wrap;font-size:11px;color:var(--muted);font-family:monospace;margin-top:8px;background:var(--panel2);padding:10px;border-radius:8px;max-height:350px;overflow-y:auto}
.sc{cursor:pointer;transition:transform .1s,border-color .1s;text-decoration:none;display:block}
.sc:hover{transform:translateY(-2px)}
.sc-spark{margin-top:6px;height:32px;width:100%}
.sc-delta{font-size:11px;font-weight:700;margin-top:2px}
.rotation{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.rot-pill{padding:5px 10px;border-radius:8px;font-size:12px;border:1px solid var(--border)}
.trend-badge{display:inline-block;padding:1px 6px;border-radius:5px;font-size:10px;font-weight:600}
.delta-up{color:#50c878}.delta-dn{color:#e05050}.delta-flat{color:#9aa7b5}
html{scroll-behavior:smooth}
section[id]{scroll-margin-top:12px}
.tabs{display:flex;gap:8px;margin:0 0 18px;border-bottom:1px solid var(--border)}
.tab{padding:10px 18px;color:var(--muted);text-decoration:none;font-size:14px;font-weight:600;border-bottom:2px solid transparent;margin-bottom:-1px;transition:color .1s}
.tab:hover{color:var(--text)}
.tab.active{color:var(--text);border-bottom-color:#5aa9ff}
.legend{font-size:11px;color:var(--muted);margin-top:8px;line-height:1.7}
.legend code{background:var(--panel2);padding:1px 5px;border-radius:4px;color:var(--text)}
footer{margin-top:18px;color:var(--muted);font-size:12px}"""

    parts = [f"""<!doctype html><html lang="no"><head>
<meta charset="utf-8"><title>Market Daily Report</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}</style></head><body><div class="wrap">
<nav class="tabs">
  <a class="tab" href="index.html">&#128200; Trend-oversikt</a>
  <a class="tab active" href="report.html">&#128202; Market Daily Report</a>
  <a class="tab" href="portfolio.html">&#128188; Portef&oslash;lje</a>
</nav>
<h1>Market Daily Report</h1>
<p class="topnote">Generert: {html.escape(str(generated))} &nbsp;&bull;&nbsp; {VERSION}</p>"""]

    # Makro-regime stripe (NFTRH-stil) — setter rammen for alt
    parts.append(regime_stripe_html(regime))

    # Sector overview — klikkbare kort med sparkline + score-endring
    parts.append('<section class="section"><h2>&#128202; Sektorscore</h2>'
                 '<p style="color:var(--muted);font-size:12px">Snitt Northstar-score (hoeyere = lavrisiko entry). '
                 'Grafen viser <strong>sektor-score per uke</strong> &mdash; ett datapunkt per uke. '
                 'Pil = endring vs forrige uke. Klikk for aa hoppe til sektoren.</p>'
                 '<div class="sector-grid">')
    for sec in sorted([s for s in ["Aksjer","Tech","Edelmetaller","Rawarer","Valuta","Crypto","Renter"] if s in sec_sum],
                      key=lambda s:-sec_sum[s]["avg_score"]):
        ss = sec_sum[sec]; avg = ss["avg_score"]; c = score_color(avg)
        anchor = SECTOR_ANCHORS.get(sec, "")
        spark = sparkline_svg(sec_trend.get(sec, []), color=c)
        sec_display = "Råvarer" if sec == "Rawarer" else sec
        # sektor delta
        trend_vals = sec_trend.get(sec, [])
        sdelta = (trend_vals[-1] - trend_vals[0]) if len(trend_vals) >= 2 else None
        parts.append(
            f'<a class="sc" href="#{anchor}" style="border-color:{c}50">'
            f'<div class="sc-name">{html.escape(sec_display)}</div>'
            f'<div class="sc-score" style="color:{c}">{avg}</div>'
            f'<div class="sc-label" style="color:{c}">{html.escape(ss["label"])}</div>'
            f'<div class="sc-delta">{delta_html(sdelta)}</div>'
            f'{spark}'
            f'<div class="sc-n">{ss["n"]} instr.</div></a>')
    parts.append('</div></section>')

    # Instrument categories — sortert etter sektorscore (beste sektor foerst)
    def cat_sort_key(cat):
        sec = cat.get("sector", "")
        return -sec_sum.get(sec, {}).get("avg_score", -1)
    for category in sorted(categories, key=cat_sort_key):
        items = []
        for iid in category.get("instrument_ids",[]):
            a = assets.get(iid,{})
            score = a.get("northstar_score",-1) if not a.get("missing_data") else -1
            items.append((score, a.get("display_name") or iid, iid, a))
        items.sort(key=lambda x:-x[0])

        parts.append(f'<section class="section" id="{SECTOR_ANCHORS.get(category.get("sector",""),"")}">'
                     f'<h2>{html.escape(category.get("title",""))}</h2>'
                     f'<p style="color:var(--muted);font-size:12px">{html.escape(category.get("description",""))}</p>')

        for _, _, iid, a in items:
            if a.get("missing_data"):
                parts.append(f'<div class="inst-block"><div class="inst-head">'
                             f'<h3>{html.escape(a.get("display_name") or iid)}</h3>'
                             f'<span class="meta">ingen data</span></div></div>')
                continue
            d_ = (a.get("frames") or {}).get("daily")   or {}
            w_ = (a.get("frames") or {}).get("weekly")  or {}
            m_ = (a.get("frames") or {}).get("monthly") or {}
            sc = a.get("northstar_score", 0)
            slabel = a.get("northstar_score_label","")
            spoints = a.get("northstar_score_points",[])
            c = score_color(sc)

            # score point pills
            pills = '<div class="pts-bar" style="justify-content:flex-start">'
            for (plabel, pts, maxpts, pnote) in spoints:
                r = pts/maxpts if maxpts>0 else 0
                cls = "ok" if r>=0.8 else ("mid" if r>=0.4 else "bad")
                pills += f'<span class="pt {cls}" title="{html.escape(pnote)}">{html.escape(plabel)}: {pts}/{maxpts}</span>'
            pills += '</div>'

            tlabel, tcol = trend_label(w_)
            vc = w_.get("vol_confirm")
            if vc is None:           vol_s = "vol –"
            elif vc >= 1.3:          vol_s = f'<span style="color:#50c878">vol &#9650;{vc:.1f}x</span>'
            elif vc >= 0.8:          vol_s = f'vol {vc:.1f}x'
            else:                    vol_s = f'<span style="color:#e08030">vol {vc:.1f}x</span>'
            high52 = ' &bull; <span style="color:#f0a500">52u-topp</span>' if (a.get("52w_high") and d_.get("last") and d_["last"] >= a["52w_high"]*0.999) else ""

            vg = a.get("vs_gold")
            vg_badge = ""
            if vg:
                vg_dist = f' {vg["dist"]*100:+.0f}%' if isinstance(vg.get("dist"),(int,float)) else ""
                vg_badge = f' &bull; <span class="trend-badge" style="background:{vg["col"]}20;color:{vg["col"]}">{html.escape(vg["state"])}{vg_dist}</span>'
            meta = (f'<span class="trend-badge" style="background:{tcol}20;color:{tcol}">{html.escape(tlabel)}</span>{vg_badge} &bull; '
                    f'D-RSI {fmt(d_.get("rsi14"))} &bull; W-RSI {fmt(w_.get("rsi14"))} &bull; M-RSI {fmt(m_.get("rsi14"))} &bull; '
                    f'3yr MA {fmt_pct(w_.get("dist_to_3yr_MA"))} &bull; 36WMA {fmt_pct(w_.get("dist_to_36MA"))} &bull; '
                    f'MACD W {macd_html(w_.get("macd_hist"))} &bull; {vol_s}{high52}')

            parts.append(
                f'<div class="inst-block">'
                f'<div class="inst-head">'
                f'<h3>{html.escape(a.get("display_name") or iid)}</h3>'
                f'<span class="ticker">{html.escape(a.get("symbol_label") or iid)}</span>'
                f'<span class="pill" style="background:{c}20;color:{c};border:1px solid {c}40">Score {sc} &bull; {html.escape(slabel)}</span>'
                f'<span class="delta">{delta_html(a.get("score_delta"))} vs forrige uke</span>'
                f'</div>'
                f'<div class="meta">{meta}</div>'
                f'{pills}'
                f'<div class="charts-grid">')
            dname = a.get("display_name") or iid
            for suffix, cap in [("weekly_compact","weekly"),("monthly_compact","monthly")]:
                path = f"charts/{iid}_{suffix}.png"
                if path in file_set:
                    parts.append(f'<figure><img src="{html.escape(path)}" alt="{html.escape(dname)} {cap}" loading="lazy">'
                                  f'<figcaption>{html.escape(dname)} - {cap}</figcaption></figure>')
            parts.append('</div></div>')

        parts.append('</section>')

    # Ratio charts
    ratio_files = [(rid,r) for rid,r in ratios.items() if r.get("chart_weekly") in file_set]
    if ratio_files:
        parts.append('<section class="section"><h2>&#128200; Ratio Charts</h2>'
                     '<p style="color:var(--muted);font-size:12px">Over SMA36 = outperformer. Northstar sektor-screening.</p>'
                     '<div class="charts-grid">')
        for rid, r in ratio_files:
            m = r.get("metrics") or {}
            cap = html.escape(r["label"])
            if m.get("rlabel"):
                cap += f' &mdash; <span style="color:{m["rcol"]}">{html.escape(m["rlabel"])}</span>'
            parts.append(f'<figure><img src="{html.escape(r["chart_weekly"])}" alt="{html.escape(r["label"])}" loading="lazy">'
                          f'<figcaption>{cap}</figcaption></figure>')
        parts.append('</div></section>')

    # Legend / forklaring
    parts.append('<section class="section"><h2>&#8505;&#65039; Slik leser du rapporten</h2>'
                 '<div class="legend">'
                 '<code>Score 0-100</code> hoeyere = lavrisiko entry (naer/under MA, lav RSI, MACD snur opp).<br>'
                 '<code>&#916; uke</code> endring i score vs forrige uke &mdash; fanger sektorrotasjon foer den er aapenbar.<br>'
                 '<code>Trend</code> Opptrend = over stigende MA. Dip i trend = under MA men MA stiger (Northstar lavrisiko-dip). Nedtrend = fallende kniv, unngaa.<br>'
                 '<code>Dist 3yr MA</code> Northstar-filter: naer/under = potensiale, langt over = stretched.<br>'
                 '<code>Dist 36WMA</code> kortere MA-filter, samme logikk.<br>'
                 '<code>Vol</code> volum vs 20-snitt. &#9650;1.3x+ = breakout bekreftet av volum.<br>'
                 '<code>Sektor-rotasjon</code> hvilke sektorer kapital flyter inn i akkurat naa.'
                 '</div></section>')

    parts.append('<footer>Data: <a href="index.json" style="color:var(--muted)">index.json</a> &bull; '
                 '<a href="portfolio_brief.md" style="color:var(--muted)">portfolio_brief.md</a> &bull; '
                 '<a href="report.json" style="color:var(--muted)">report.json</a></footer>'
                 '</div></body></html>')
    return "".join(parts)

def build_trend_page(index_data, filelist):
    """Ny hovedside: trend-oversikt for makro-ratioer med Northstar-score."""
    trend_ratios = index_data.get("trend_ratios", [])
    regime       = index_data.get("regime", {})
    generated    = index_data.get("generated_local") or NOW.isoformat()
    file_set     = set(filelist)

    CSS = """:root{--bg:#0b0d10;--panel:#12161c;--panel2:#171c23;--text:#e7edf3;--muted:#9aa7b5;--border:#27313d}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.45}
.wrap{max-width:1600px;margin:0 auto;padding:20px 16px 40px}
h1{margin:0 0 4px;font-size:24px}h2{margin:0 0 6px;font-size:18px}
.topnote{color:var(--muted);margin:0 0 18px;font-size:13px}
.tabs{display:flex;gap:8px;margin:0 0 18px;border-bottom:1px solid var(--border)}
.tab{padding:10px 18px;color:var(--muted);text-decoration:none;font-size:14px;font-weight:600;border-bottom:2px solid transparent;margin-bottom:-1px;transition:color .1s}
.tab:hover{color:var(--text)}.tab.active{color:var(--text);border-bottom-color:#5aa9ff}
.section{margin:0 0 22px;padding:14px 16px;border:1px solid var(--border);border-radius:14px;background:var(--panel)}
.sector-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-top:10px}
.sc{cursor:pointer;text-decoration:none;display:block;padding:10px 12px;border-radius:10px;border:1px solid var(--border);background:var(--panel2);text-align:center;transition:transform .1s}
.sc:hover{transform:translateY(-2px)}
.sc-name{font-size:11px;color:var(--muted);min-height:26px;display:flex;align-items:center;justify-content:center}
.sc-score{font-size:24px;font-weight:700;margin:2px 0}.sc-label{font-size:10px}
.sc-spark{margin-top:6px;height:34px;width:100%}
.pts-bar{display:flex;gap:2px;flex-wrap:wrap;margin-top:6px;justify-content:center}
.pt{font-size:9px;padding:1px 4px;border-radius:3px;background:#1e2530;color:var(--muted)}
.pt.ok{background:#0d2a1a;color:#50c878}.pt.mid{background:#2a2000;color:#f0a500}.pt.bad{background:#2a0d0d;color:#e05050}
.charts-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:12px;margin-top:10px}
figure{margin:0;border:1px solid var(--border);border-radius:10px;overflow:hidden;background:#0f141a}
img{display:block;width:100%;height:auto}
figcaption{padding:6px 10px;border-top:1px solid var(--border);color:var(--muted);font-size:12px}
.ratio-block{margin:0 0 22px;padding:14px 16px;border:1px solid var(--border);border-radius:14px;background:var(--panel)}
.ratio-head{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:baseline;margin-bottom:6px}
.ratio-head h2{margin:0}.pill{display:inline-block;padding:2px 8px;border-radius:7px;font-size:13px;font-weight:700}
.meta{color:var(--muted);font-size:12px}
html{scroll-behavior:smooth}section[id]{scroll-margin-top:12px}
.legend{font-size:11px;color:var(--muted);margin-top:8px;line-height:1.7}
.legend code{background:var(--panel2);padding:1px 5px;border-radius:4px;color:var(--text)}
footer{margin-top:18px;color:var(--muted);font-size:12px}"""

    def anchor(rid): return f"r-{rid.lower()}"

    parts = [f"""<!doctype html><html lang="no"><head>
<meta charset="utf-8"><title>Trend-oversikt</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}</style></head><body><div class="wrap">
<nav class="tabs">
  <a class="tab active" href="index.html">&#128200; Trend-oversikt</a>
  <a class="tab" href="report.html">&#128202; Market Daily Report</a>
  <a class="tab" href="portfolio.html">&#128188; Portef&oslash;lje</a>
</nav>
<h1>Trend-oversikt</h1>
<p class="topnote">Generert: {html.escape(str(generated))} &nbsp;&bull;&nbsp; {VERSION} &nbsp;&bull;&nbsp; Makro-ratioer scoret med samme Northstar-modell</p>"""]

    parts.append(regime_stripe_html(regime))

    if not trend_ratios:
        parts.append('<section class="section"><p>Ingen trend-data ennaa. '
                     'Sjekk at tickerne er tilgjengelige.</p></section>')
    else:
        # Score-oversikt (kort med 6-mnd maanedlig score-graf)
        parts.append('<section class="section"><h2>&#128200; Ratio-score</h2>'
                     '<p style="color:var(--muted);font-size:12px">'
                     'Northstar-score (0-100, hoeyere = lavrisiko / teller-aktiva er sterkest). '
                     'Grafen viser <strong>score per maaned siste 6 mnd</strong>. '
                     'Klikk for aa hoppe til chartene.</p>'
                     '<div class="sector-grid">')
        for r in trend_ratios:
            sc = r["score"]; c = score_color(sc)
            spark = sparkline_svg(r.get("score_series_monthly", []), color=c)
            parts.append(
                f'<a class="sc" href="#{anchor(r["rid"])}" style="border-color:{c}50">'
                f'<div class="sc-name">{html.escape(r["label"])}</div>'
                f'<div class="sc-score" style="color:{c}">{sc}</div>'
                f'<div class="sc-label" style="color:{c}">{html.escape(r["label_txt"])}</div>'
                f'{spark}</a>')
        parts.append('</div></section>')

        # Per ratio: maanedlig + 3-maaneders chart, sortert etter score
        for r in trend_ratios:
            sc = r["score"]; c = score_color(sc)
            pills = '<div class="pts-bar" style="justify-content:flex-start">'
            for (plabel, pts, maxpts, pnote) in r.get("points", []):
                ratio_pt = pts/maxpts if maxpts>0 else 0
                cls = "ok" if ratio_pt>=0.8 else ("mid" if ratio_pt>=0.4 else "bad")
                pills += f'<span class="pt {cls}" title="{html.escape(pnote)}">{html.escape(plabel)}: {pts}/{maxpts}</span>'
            pills += '</div>'
            meta = (f'M-RSI {fmt(r.get("mrsi"))} &bull; 3M-RSI {fmt(r.get("qrsi"))} &bull; '
                    f'36M MA {fmt_pct(r.get("dist36m"))} &bull; 36Q MA {fmt_pct(r.get("dist36q"))} &bull; '
                    f'MACD M {macd_html(r.get("macd_m"))} &bull; MACD 3M {macd_html(r.get("macd_q"))}')
            parts.append(
                f'<section class="ratio-block" id="{anchor(r["rid"])}">'
                f'<div class="ratio-head"><h2>{html.escape(r["label"])}</h2>'
                f'<span class="pill" style="background:{c}20;color:{c};border:1px solid {c}40">Score {sc} &bull; {html.escape(r["label_txt"])}</span></div>'
                f'<div class="meta">{meta}</div>'
                f'{pills}'
                f'<div class="charts-grid">')
            for path, cap in [(r["chart_monthly"], "Maanedlig"),
                              (r["chart_quarterly"], "3-maaneders")]:
                if path in file_set:
                    parts.append(f'<figure><img src="{html.escape(path)}" alt="{html.escape(cap)}" loading="lazy">'
                                  f'<figcaption>{html.escape(cap)}</figcaption></figure>')
                else:
                    parts.append(f'<div style="padding:14px;color:var(--muted);font-size:12px">{html.escape(cap)} mangler</div>')
            parts.append('</div></section>')

    parts.append('<section class="section"><h2>&#8505;&#65039; Om denne siden</h2>'
                 '<div class="legend">'
                 '<code>Ratio-score</code> bruker samme 0-100 Northstar-modell som Market Daily Report: '
                 'RSI (daily/weekly/monthly), MACD + MACD14, avstand til 36-ukers og 3-aars MA, trend og volum.<br>'
                 '<code>Hoey score</code> = teller-aktivaet (f.eks. Gull i Gull/Olje) er i lavrisiko-sone og relativt sterkest.<br>'
                 '<code>Maanedsgraf</code> viser hvordan ratioens score har utviklet seg siste 6 maaneder.<br>'
                 '<code>Charts</code> maanedlig + 3-maaneders tidsramme med 36-MA, RSI og MACD.'
                 '</div></section>')

    parts.append('<footer>Data: <a href="index.json" style="color:var(--muted)">index.json</a> &bull; '
                 '<a href="report.html" style="color:var(--muted)">Market Daily Report</a></footer>'
                 '</div></body></html>')

    with open(DOCS/"index.html","w",encoding="utf-8") as f:
        f.write("".join(parts))
    log("Trend-side skrevet til index.html")

html_doc = build_homepage(index, files, brief_md)
with open(DOCS/"report.html","w",encoding="utf-8") as f: f.write(html_doc)

# ─── TREND-OVERSIKT (ny hovedside: index.html) ─────────────────
build_trend_page(index, files)

# ─── PORTEFOELJE (statisk side, leser index.json i nettleser) ──
try:
    _ptxt = _b64mod.b64decode(PORTFOLIO_HTML_B64).decode("utf-8")
    with open(DOCS/"portfolio.html","w",encoding="utf-8") as f:
        f.write(_ptxt)
    log("Portefoelje-side skrevet til portfolio.html")
except Exception as e:
    log(f"portfolio write error: {e}")

log(f"DONE - {len(summary['assets'])} instruments, {len(files)} charts, version={VERSION}")
flush_log()
print("Done.")
