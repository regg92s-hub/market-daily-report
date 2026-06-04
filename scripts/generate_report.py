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

VERSION = "2026-06-04-northstar-v6"
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
    "LnRyaW17Y29sb3I6I2YwYTUwMH0ucmVjLnNlbGx7Y29sb3I6I2UwNTA1MH0ucmVjLndlYWt7Y29sb3I6I2M5YTIyN30KLmdlbnJl"
    "LWdyaWR7ZGlzcGxheTpncmlkO2dyaWQtdGVtcGxhdGUtY29sdW1uczpyZXBlYXQoYXV0by1maXQsbWlubWF4KDE1MHB4LDFmcikp"
    "O2dhcDoxMHB4O21hcmdpbi10b3A6MTBweH0KLmdjYXJke2JhY2tncm91bmQ6dmFyKC0tcGFuZWwyKTtib3JkZXI6MXB4IHNvbGlk"
    "IHZhcigtLWJvcmRlcik7Ym9yZGVyLXJhZGl1czoxMHB4O3BhZGRpbmc6MTBweCAxMnB4fQoucG9zaW5wdXR7d2lkdGg6ODBweDti"
    "YWNrZ3JvdW5kOnZhcigtLXBhbmVsMik7Ym9yZGVyOjFweCBzb2xpZCB2YXIoLS1ib3JkZXIpO2JvcmRlci1yYWRpdXM6NnB4O2Nv"
    "bG9yOnZhcigtLXRleHQpO3BhZGRpbmc6NHB4IDZweDtmb250LXNpemU6MTJweH0KLmxlZ2VuZHtmb250LXNpemU6MTFweDtjb2xv"
    "cjp2YXIoLS1tdXRlZCk7bGluZS1oZWlnaHQ6MS43O21hcmdpbi10b3A6MTBweH0KLmxlZ2VuZCBjb2Rle2JhY2tncm91bmQ6dmFy"
    "KC0tcGFuZWwyKTtwYWRkaW5nOjFweCA1cHg7Ym9yZGVyLXJhZGl1czo0cHg7Y29sb3I6dmFyKC0tdGV4dCl9Ci5oaXN0e21heC1o"
    "ZWlnaHQ6MjgwcHg7b3ZlcmZsb3cteTphdXRvO21hcmdpbi10b3A6MTBweH0KLmhpc3QgLmh7cGFkZGluZzo4cHggMTBweDtib3Jk"
    "ZXItYm90dG9tOjFweCBzb2xpZCAjMWUyNTMwO2ZvbnQtc2l6ZToxMnB4fQouaGlzdCAuaCAudHtjb2xvcjp2YXIoLS1tdXRlZCk7"
    "Zm9udC1zaXplOjExcHh9Ci5tdXRlZHtjb2xvcjp2YXIoLS1tdXRlZCl9CnN2Zy5waWV7ZGlzcGxheTpibG9jazttYXJnaW46MCBh"
    "dXRvfQoubGVnZW5kLXBpZXtkaXNwbGF5OmZsZXg7ZmxleC1kaXJlY3Rpb246Y29sdW1uO2dhcDo1cHg7bWFyZ2luLXRvcDo4cHh9"
    "Ci5sZWdlbmQtcGllIC5saXtkaXNwbGF5OmZsZXg7YWxpZ24taXRlbXM6Y2VudGVyO2dhcDo4cHg7Zm9udC1zaXplOjEycHh9Ci5s"
    "ZWdlbmQtcGllIC5zd3t3aWR0aDoxMnB4O2hlaWdodDoxMnB4O2JvcmRlci1yYWRpdXM6M3B4O2ZsZXg6bm9uZX0KZm9vdGVye21h"
    "cmdpbi10b3A6MThweDtjb2xvcjp2YXIoLS1tdXRlZCk7Zm9udC1zaXplOjEycHh9Cjwvc3R5bGU+CjwvaGVhZD4KPGJvZHk+Cjxk"
    "aXYgY2xhc3M9IndyYXAiPgo8bmF2IGNsYXNzPSJ0YWJzIj4KICA8YSBjbGFzcz0idGFiIiBocmVmPSJpbmRleC5odG1sIj4mIzEy"
    "ODIwMDsgVHJlbmQtb3ZlcnNpa3Q8L2E+CiAgPGEgY2xhc3M9InRhYiIgaHJlZj0icmVwb3J0Lmh0bWwiPiYjMTI4MjAyOyBNYXJr"
    "ZXQgRGFpbHkgUmVwb3J0PC9hPgogIDxhIGNsYXNzPSJ0YWIgYWN0aXZlIiBocmVmPSJwb3J0Zm9saW8uaHRtbCI+JiMxMjgxODg7"
    "IFBvcnRlZiZvc2xhc2g7bGplPC9hPgo8L25hdj4KPGgxPlBvcnRlZiZvc2xhc2g7bGplPC9oMT4KPHAgY2xhc3M9InRvcG5vdGUi"
    "IGlkPSJ0b3Bub3RlIj5MYXN0ZXIgZGF0YSZoZWxsaXA7PC9wPgoKPGRpdiBjbGFzcz0iZGlzY2xhaW1lciI+CjxzdHJvbmc+RGl0"
    "dCBlZ2V0IHJhbW1ldmVyayAmbWRhc2g7IGlra2UgZmluYW5zciZhcmluZztkZ2l2bmluZy48L3N0cm9uZz4KRGV0dGUgdmVya3Qm"
    "b3NsYXNoO3lldCB2aXNlciBodmEgZGluIE5vcnRoc3Rhci1tZXRvZGlrayB0aWxzaWVyIGJhc2VydCBwJmFyaW5nOyB0cmVuZC1z"
    "Y29yZSwgaWtrZSBlbiBhbmJlZmFsaW5nLgpBbGwgZGF0YSBlciB0ZWtuaXNrIG9nIGthbiB2JmFlbGlnO3JlIGZlaWwgZWxsZXIg"
    "dXRkYXRlcnQuIER1IHRhciBhbGxlIGJlc2x1dG5pbmdlciBzZWx2Lgo8L2Rpdj4KCjxkaXYgY2xhc3M9InNlY3Rpb24iPgogIDxo"
    "Mj4mIzEyODE3NjsgS2FwaXRhbDwvaDI+CiAgPGRpdiBjbGFzcz0iY2FwLXJvdyI+CiAgICA8ZGl2IGNsYXNzPSJmaWVsZCI+CiAg"
    "ICAgIDxsYWJlbD5TdGFydGthcGl0YWwgKGtyKTwvbGFiZWw+CiAgICAgIDxpbnB1dCB0eXBlPSJudW1iZXIiIGlkPSJzdGFydENh"
    "cCIgcGxhY2Vob2xkZXI9IjEwMDAwMCIgc3RlcD0iMTAwMCI+CiAgICA8L2Rpdj4KICAgIDxkaXYgY2xhc3M9ImZpZWxkIj4KICAg"
    "ICAgPGxhYmVsPk55dHQgaW5uc2t1ZGQgKGtyKTwvbGFiZWw+CiAgICAgIDxpbnB1dCB0eXBlPSJudW1iZXIiIGlkPSJhZGRDYXAi"
    "IHBsYWNlaG9sZGVyPSIwIiBzdGVwPSIxMDAwIj4KICAgIDwvZGl2PgogICAgPGJ1dHRvbiBjbGFzcz0iYnRuIiBpZD0iYXBwbHlD"
    "YXAiPk9wcGRhdGVyIGthcGl0YWw8L2J1dHRvbj4KICAgIDxidXR0b24gY2xhc3M9ImJ0biBzZWNvbmRhcnkiIGlkPSJyZWJhbGFu"
    "Y2UiPk9tZm9yZGVsIG4mYXJpbmc7ICh1a2VudGxpZyk8L2J1dHRvbj4KICA8L2Rpdj4KICA8ZGl2IGNsYXNzPSJrcGkiPgogICAg"
    "PGRpdiBjbGFzcz0iayI+PGRpdiBjbGFzcz0ibGJsIj5Ub3RhbCBrYXBpdGFsPC9kaXY+PGRpdiBjbGFzcz0idmFsIiBpZD0ia1Rv"
    "dGFsIj4mbmRhc2g7PC9kaXY+PC9kaXY+CiAgICA8ZGl2IGNsYXNzPSJrIj48ZGl2IGNsYXNzPSJsYmwiPkludmVzdGVydDwvZGl2"
    "PjxkaXYgY2xhc3M9InZhbCIgaWQ9ImtJbnZlc3RlZCI+Jm5kYXNoOzwvZGl2PjwvZGl2PgogICAgPGRpdiBjbGFzcz0iayI+PGRp"
    "diBjbGFzcz0ibGJsIj5DYXNoPC9kaXY+PGRpdiBjbGFzcz0idmFsIiBpZD0ia0Nhc2giPiZuZGFzaDs8L2Rpdj48L2Rpdj4KICAg"
    "IDxkaXYgY2xhc3M9ImsiPjxkaXYgY2xhc3M9ImxibCI+Q2FzaCAlPC9kaXY+PGRpdiBjbGFzcz0idmFsIiBpZD0ia0Nhc2hQY3Qi"
    "PiZuZGFzaDs8L2Rpdj48L2Rpdj4KICAgIDxkaXYgY2xhc3M9ImsiPjxkaXYgY2xhc3M9ImxibCI+UG9ydGVmJm9zbGFzaDtsamUt"
    "dHJlbmQgKHZla3RldCBzY29yZSk8L2Rpdj48ZGl2IGNsYXNzPSJ2YWwiIGlkPSJrVHJlbmQiPiZuZGFzaDs8L2Rpdj48L2Rpdj4K"
    "ICAgIDxkaXYgY2xhc3M9ImsiPjxkaXYgY2xhc3M9ImxibCI+QW5kZWwgaSBtZWR2aW5kPC9kaXY+PGRpdiBjbGFzcz0idmFsIiBp"
    "ZD0ia01lZHZpbmQiPiZuZGFzaDs8L2Rpdj48L2Rpdj4KICA8L2Rpdj4KICA8ZGl2IGNsYXNzPSJjYXAtcm93IiBzdHlsZT0ibWFy"
    "Z2luLXRvcDoxNHB4Ij4KICAgIDxkaXYgY2xhc3M9ImZpZWxkIj4KICAgICAgPGxhYmVsPk0mYXJpbmc7bCBjYXNoLWJ1ZmZlciAo"
    "JSk8L2xhYmVsPgogICAgICA8aW5wdXQgdHlwZT0ibnVtYmVyIiBpZD0iY2FzaFRhcmdldCIgdmFsdWU9IjE1IiBtaW49IjAiIG1h"
    "eD0iMTAwIiBzdGVwPSI1Ij4KICAgIDwvZGl2PgogICAgPGRpdiBjbGFzcz0iZmllbGQiPgogICAgICA8bGFiZWw+TWFrcyB2ZWt0"
    "IHBlciBwb3Npc2pvbiAoJSk8L2xhYmVsPgogICAgICA8aW5wdXQgdHlwZT0ibnVtYmVyIiBpZD0ibWF4UG9zIiB2YWx1ZT0iMjUi"
    "IG1pbj0iNSIgbWF4PSIxMDAiIHN0ZXA9IjUiPgogICAgPC9kaXY+CiAgPC9kaXY+CjwvZGl2PgoKPGRpdiBjbGFzcz0ic2VjdGlv"
    "biI+CiAgPGgyPiYjMTI3OTQyOyBUcmlubiAxOiBTamFuZ2VyLXJhbmdlcmluZzwvaDI+CiAgPHAgY2xhc3M9Im11dGVkIiBzdHls"
    "ZT0iZm9udC1zaXplOjEycHgiPlJlbGF0aXYgc3R5cmtlIHBlciBha3RpdmFrbGFzc2UgKG0mYXJpbmc7bmVkbGlnICsgMy1tJmFy"
    "aW5nO25lZGxpZyB0cmVuZCB2cyBndWxsIG9nIG1vbWVudHVtKS4gU2phbmdyZXIgc29tIDxzdHJvbmc+c2wmYXJpbmc7ciBndWxs"
    "ID0gaSBtZWR2aW5kPC9zdHJvbmc+ICZtZGFzaDsgZGV0IGVyIGhlciB2aSBsZXRlciBldHRlciBsYXZyaXNpa28tZW50cnktaW5z"
    "dHJ1bWVudGVyLjwvcD4KICA8ZGl2IGNsYXNzPSJnZW5yZS1ncmlkIiBpZD0iZ2VucmVCb3giPjwvZGl2Pgo8L2Rpdj4KCjxkaXYg"
    "Y2xhc3M9ImdyaWQyIj4KICA8ZGl2IGNsYXNzPSJzZWN0aW9uIj4KICAgIDxoMj4mIzEyOTUxODsgQW5iZWZhbHQgZm9yZGVsaW5n"
    "PC9oMj4KICAgIDxwIGNsYXNzPSJtdXRlZCIgc3R5bGU9ImZvbnQtc2l6ZToxMnB4Ij5WZWt0ZXQgZXR0ZXIgc2NvcmUsIGt1biBp"
    "bnN0cnVtZW50ZXIgaSBtZWR2aW5kLXNqYW5nZXIgKHNsJmFyaW5nO3IgZ3VsbCkuIENhc2gtYnVmZmVyIGhvbGRlcyBpZ2plbi48"
    "L3A+CiAgICA8ZGl2IGlkPSJwaWVXcmFwIj48L2Rpdj4KICAgIDxkaXYgY2xhc3M9ImxlZ2VuZC1waWUiIGlkPSJwaWVMZWdlbmQi"
    "PjwvZGl2PgogIDwvZGl2PgogIDxkaXYgY2xhc3M9InNlY3Rpb24iPgogICAgPGgyPiYjMTI4MjIxOyBUcmlubiAyOiBQb3Npc2pv"
    "bmVyICZhbXA7IGFuYmVmYWxpbmc8L2gyPgogICAgPHAgY2xhc3M9Im11dGVkIiBzdHlsZT0iZm9udC1zaXplOjEycHgiPkFsbGUg"
    "aW5zdHJ1bWVudGVyIHZpc2VzLiBLSiZPc2xhc2g7UC9MRUdHIFRJTCBnamVsZGVyIGt1biBsYXZyaXNpa28tZW50cnkgaSBtZWR2"
    "aW5kLXNqYW5ncmVyLiBFaWRlIHBvc2lzam9uZXIgYmVob2xkZXMgKGZsYWdnZXMgaHZpcyBzamFuZ2VyZW4gbWlzdGV0IG1lZHZp"
    "bmQpLiBTa3JpdiBpbm4gbiZhcmluZzt2JmFlbGlnO3JlbmRlIHZla3QgKCUpIGR1IGVpZXIuPC9wPgogICAgPHRhYmxlIGlkPSJw"
    "b3NUYWJsZSI+PHRoZWFkPjx0cj4KICAgICAgPHRoPkluc3RydW1lbnQ8L3RoPjx0aD5TamFuZ2VyPC90aD48dGg+U2NvcmU8L3Ro"
    "Pjx0aD5FaWVyICU8L3RoPjx0aD5NJmFyaW5nO2wgJTwvdGg+PHRoPkFuYmVmYWxpbmc8L3RoPgogICAgPC90cj48L3RoZWFkPjx0"
    "Ym9keSBpZD0icG9zQm9keSI+PC90Ym9keT48L3RhYmxlPgogIDwvZGl2Pgo8L2Rpdj4KCjxkaXYgY2xhc3M9InNlY3Rpb24iPgog"
    "IDxoMj4mIzEyODIwMjsgRW5kcmluZ3Nsb2dnPC9oMj4KICA8cCBjbGFzcz0ibXV0ZWQiIHN0eWxlPSJmb250LXNpemU6MTJweCI+"
    "SHZlciBvbWZvcmRlbGluZyBvZyBrYXBpdGFsZW5kcmluZyBsb2dnZXMgaGVyIChsYWdyZXQgbG9rYWx0IGkgbmV0dGxlc2VyZW4p"
    "LjwvcD4KICA8ZGl2IGNsYXNzPSJoaXN0IiBpZD0iaGlzdEJveCI+PC9kaXY+CiAgPGJ1dHRvbiBjbGFzcz0iYnRuIHNlY29uZGFy"
    "eSIgaWQ9ImNsZWFySGlzdCIgc3R5bGU9Im1hcmdpbi10b3A6MTBweCI+VCZvc2xhc2g7bSBsb2dnPC9idXR0b24+CjwvZGl2PgoK"
    "PGRpdiBjbGFzcz0ic2VjdGlvbiI+CiAgPGgyPiYjODUwNTsmIzY1MDM5OyBTbGlrIGZ1bmdlcmVyIG1vZGVsbGVuPC9oMj4KICA8"
    "ZGl2IGNsYXNzPSJsZWdlbmQiPgogIDxjb2RlPk0mYXJpbmc7bCAlPC9jb2RlPiBiZXJlZ25lcyBmcmEgdHJlbmQtc2NvcmUgcCZh"
    "cmluZzsgdG9wcCAxMCBpbnN0cnVtZW50ZXI6IGt1biBkZSBtZWQgc2NvcmUgJmdlOyA1NSBmJmFyaW5nO3IgdGlsZGVsdCB2ZWt0"
    "LiBWZWt0IGVyIHByb3BvcnNqb25hbCBtZWQgc2NvcmUgb3ZlciB0ZXJza2VsZW4uPGJyPgogIDxjb2RlPkNhc2gtYnVmZmVyPC9j"
    "b2RlPiAoc3RhbmRhcmQgMTUlKSBob2xkZXMgYWxsdGlkIGlnamVuIGYmb3NsYXNoO3IgZm9yZGVsaW5nICZtZGFzaDsgZHUgdGFy"
    "IGt1biBwb3Npc2pvbmVyIG4mYXJpbmc7ciBub2Ugc2VyIGxvdmVuZGUgdXQuPGJyPgogIDxjb2RlPk1ha3MgdmVrdDwvY29kZT4g"
    "cGVyIHBvc2lzam9uIGhpbmRyZXIgYXQgYWx0IHNhbWxlcyBpICZlYWN1dGU7biBpZCZlYWN1dGU7LiA8Y29kZT5NYWtzIDcgcG9z"
    "aXNqb25lcjwvY29kZT4gb20gZ2FuZ2VuICZtZGFzaDsgZWlkZSBwb3Npc2pvbmVyIHByaW9yaXRlcmVzLCBvZyBueWUga3ZhbGlm"
    "aXNlcnRlIHZlbnRlciBwJmFyaW5nOyBsZWRpZyBwbGFzcy48YnI+CiAgPGNvZGU+S0omT3NsYXNoO1A8L2NvZGU+OiBzY29yZSAm"
    "Z2U7IDU1IG9nIGR1IGVpZXIgbWluZHJlIGVubiBtJmFyaW5nO2wuIDxjb2RlPkxFR0cgVElMPC9jb2RlPjogZ29kIHNjb3JlLCBs"
    "aXR0IHVuZGVyIG0mYXJpbmc7bC48YnI+CiAgPGNvZGU+SE9MRDwvY29kZT46IHBvc2lzam9uIHRhdHQsIGlra2Ugb3ZlcmtqJm9z"
    "bGFzaDtwdCBlbm4mYXJpbmc7ICZtZGFzaDsgYmVob2xkZXMgc2VsdiBvbSBzY29yZSBmYWxsZXIsIHRpbCBkZW4gYmxpciA8ZW0+"
    "dmVsZGlnPC9lbT4gb3ZlcmtqJm9zbGFzaDtwdC48YnI+CiAgPGNvZGU+U0tBTEVSIEFWPC9jb2RlPjoga3VuIG4mYXJpbmc7ciBS"
    "U0kgJmdlOyA2NSBPRyBNQUNELWhpc3QgJmdlOyAyIE9HIHN0cnVra2V0IGxhbmd0IG92ZXIgMzZXTUEvM3lyIE1BICZtZGFzaDsg"
    "ZWxsZXIgbiZhcmluZztyIGR1IHRyZW5nZXIgY2FzaCB0aWwga2xhcnQgYmVkcmUgbXVsaWdoZXRlci48YnI+CiAgPGNvZGU+RnVs"
    "bCBwb3J0ZWYmb3NsYXNoO2xqZTwvY29kZT46IGh2aXMgYWx0IGVyIGZ1bGx0IG9nIGNhc2ggZXIgdW5kZXIgbSZhcmluZztsLCBm"
    "b3Jlc2wmYXJpbmc7cyBrdW4gc2tpZnRlIG4mYXJpbmc7ciBlbiBzdmFrZXJlIHBvc2lzam9uIGthbiB2aWtlIGZvciBlbiBrbGFy"
    "dCBzdGVya2VyZS4KICA8L2Rpdj4KPC9kaXY+Cgo8Zm9vdGVyPkRhdGE6IDxhIGhyZWY9ImluZGV4Lmpzb24iIHN0eWxlPSJjb2xv"
    "cjp2YXIoLS1tdXRlZCkiPmluZGV4Lmpzb248L2E+ICZidWxsOyBMYWdyZXMgbG9rYWx0IGkgZGluIG5ldHRsZXNlciAobG9jYWxT"
    "dG9yYWdlKTwvZm9vdGVyPgo8L2Rpdj4KCjxzY3JpcHQ+CmNvbnN0IExTX0tFWSA9ICJuc19wb3J0Zm9saW9fdjEiOwpjb25zdCBD"
    "QVNIX1RIUkVTSE9MRCA9IDU1OyAgICAgLy8gbWluIHNjb3JlIGZvciDDpSBmw6UgdGlsZGVsdCB2ZWt0CmNvbnN0IE1BWF9QT1NJ"
    "VElPTlMgPSA3OyAgICAgICAvLyBtYWtzIGFudGFsbCBwb3Npc2pvbmVyIG9tIGdhbmdlbgpjb25zdCBPVkVSQk9VR0hUX1JTSSA9"
    "IDY1Owpjb25zdCBPVkVSQk9VR0hUX01BQ0QgPSAyOwpjb25zdCBTVFJFVENIXzM2ID0gMC4yMDsgICAgICAgLy8gMjAlIG92ZXIg"
    "MzZNQQpjb25zdCBTVFJFVENIXzNZUiA9IDAuMzA7ICAgICAgLy8gMzAlIG92ZXIgM3lyCgpsZXQgU1RBVEUgPSBsb2FkU3RhdGUo"
    "KTsKbGV0IERBVEEgPSBudWxsOwoKZnVuY3Rpb24gbG9hZFN0YXRlKCl7CiAgdHJ5eyBjb25zdCBzID0gSlNPTi5wYXJzZShsb2Nh"
    "bFN0b3JhZ2UuZ2V0SXRlbShMU19LRVkpKTsgaWYocykgcmV0dXJuIHM7IH1jYXRjaChlKXt9CiAgcmV0dXJuIHsgc3RhcnRDYXA6"
    "IDEwMDAwMCwgY2FzaDogMTAwMDAwLCBpbnZlc3RlZDogMCwgcG9zaXRpb25zOiB7fSwgaGlzdG9yeTogW10sIGNhc2hUYXJnZXQ6"
    "IDE1LCBtYXhQb3M6IDI1IH07Cn0KZnVuY3Rpb24gc2F2ZVN0YXRlKCl7IGxvY2FsU3RvcmFnZS5zZXRJdGVtKExTX0tFWSwgSlNP"
    "Ti5zdHJpbmdpZnkoU1RBVEUpKTsgfQpmdW5jdGlvbiBrcihuKXsgcmV0dXJuIChNYXRoLnJvdW5kKG4pKS50b0xvY2FsZVN0cmlu"
    "Zygibm8tTk8iKSArICIga3IiOyB9CmZ1bmN0aW9uIHBjdChuKXsgcmV0dXJuIChuKS50b0ZpeGVkKDEpICsgIiUiOyB9CmZ1bmN0"
    "aW9uIG5vdygpeyByZXR1cm4gbmV3IERhdGUoKS50b0xvY2FsZVN0cmluZygibm8tTk8iKTsgfQoKZnVuY3Rpb24gbG9nSGlzdCht"
    "c2cpewogIFNUQVRFLmhpc3RvcnkudW5zaGlmdCh7IHQ6IG5vdygpLCBtc2cgfSk7CiAgaWYoU1RBVEUuaGlzdG9yeS5sZW5ndGgg"
    "PiAyMDApIFNUQVRFLmhpc3RvcnkucG9wKCk7Cn0KCmFzeW5jIGZ1bmN0aW9uIGluaXQoKXsKICB0cnl7CiAgICBjb25zdCByID0g"
    "YXdhaXQgZmV0Y2goImluZGV4Lmpzb24iLCB7Y2FjaGU6Im5vLXN0b3JlIn0pOwogICAgREFUQSA9IGF3YWl0IHIuanNvbigpOwog"
    "ICAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInRvcG5vdGUiKS5pbm5lckhUTUwgPQogICAgICAiVHJlbmQtZGF0YSBnZW5lcmVy"
    "dDogIiArIChEQVRBLmdlbmVyYXRlZF9sb2NhbHx8IiIpICsgIiAmYnVsbDsgIiArIChEQVRBLnZlcnNpb258fCIiKTsKICB9Y2F0"
    "Y2goZSl7CiAgICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgidG9wbm90ZSIpLnRleHRDb250ZW50ID0gIkt1bm5lIGlra2UgbGFz"
    "dGUgaW5kZXguanNvbjogIiArIGU7CiAgICByZXR1cm47CiAgfQogIC8vIGluaXQgY2FwaXRhbCBpbnB1dHMKICBkb2N1bWVudC5n"
    "ZXRFbGVtZW50QnlJZCgic3RhcnRDYXAiKS52YWx1ZSA9IFNUQVRFLnN0YXJ0Q2FwOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlk"
    "KCJjYXNoVGFyZ2V0IikudmFsdWUgPSBTVEFURS5jYXNoVGFyZ2V0OwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJtYXhQb3Mi"
    "KS52YWx1ZSA9IFNUQVRFLm1heFBvczsKICByZW5kZXIoKTsKfQoKLy8gVHJpbm4gQTogc2phbmdlci1zdHlya2UgZnJhIGluZGV4"
    "Lmpzb24gKGJlcmVnbmV0IGkgZ2VuZXJhdG9yZW4pCmZ1bmN0aW9uIGdlbnJlcygpewogIHJldHVybiAoREFUQS5nZW5yZV9zdHJl"
    "bmd0aCB8fCBbXSk7Cn0KLy8gTWVkdmluZCA9IHNqYW5ncmVyIHNvbSBmYWt0aXNrIHNsw6VyIGd1bGwgKGlra2Uga3VuIHRvcHAg"
    "MykuCmZ1bmN0aW9uIG1lZHZpbmRHZW5yZU5hbWVzKCl7CiAgcmV0dXJuIG5ldyBTZXQoZ2VucmVzKCkuZmlsdGVyKGc9PmcubWVk"
    "dmluZCkubWFwKGc9PmcuZ2VucmUpKTsKfQoKLy8gVHJpbm4gQjogYnlnZyBrYW5kaWRhdGxpc3RlLiBBbGxlIGluc3RydW1lbnRl"
    "ciB2dXJkZXJlcywgbWVuIHZpIG1lcmtlcgovLyBodmlsa2Ugc29tIGxpZ2dlciBpIGVuIG1lZHZpbmQtc2phbmdlciAoc2zDpXIg"
    "Z3VsbCkuIERlIGJlc3RlIGxhdnJpc2lrby0KLy8gZW50cnktaW5zdHJ1bWVudGVuZSBJTk5FTkZPUiBtZWR2aW5kLXNqYW5ncmVu"
    "ZSBhbmJlZmFsZXMga2rDuHB0LgpmdW5jdGlvbiBjYW5kaWRhdGVzKCl7CiAgY29uc3QgYXNzZXRzID0gKERBVEEuc3VtbWFyeSAm"
    "JiBEQVRBLnN1bW1hcnkuYXNzZXRzKSB8fCB7fTsKICBjb25zdCBtZWR2aW5kID0gbWVkdmluZEdlbnJlTmFtZXMoKTsKICBjb25z"
    "dCBhcnIgPSBbXTsKICBPYmplY3Qua2V5cyhhc3NldHMpLmZvckVhY2goaWlkPT57CiAgICBjb25zdCBhID0gYXNzZXRzW2lpZF07"
    "CiAgICBpZihhLm1pc3NpbmdfZGF0YSB8fCBhLm5vcnRoc3Rhcl9zY29yZSA9PSBudWxsKSByZXR1cm47CiAgICBjb25zdCB3ID0g"
    "KGEuZnJhbWVzICYmIGEuZnJhbWVzLndlZWtseSkgfHwge307CiAgICBjb25zdCBtID0gKGEuZnJhbWVzICYmIGEuZnJhbWVzLm1v"
    "bnRobHkpIHx8IHt9OwogICAgY29uc3QgcSA9IChhLmZyYW1lcyAmJiBhLmZyYW1lcy5xdWFydGVybHkpIHx8IHt9OwogICAgY29u"
    "c3Qgc3ViID0gYS5zdWJjbGFzcyB8fCAiIjsKICAgIGFyci5wdXNoKHsKICAgICAgaWQ6IGlpZCwKICAgICAgbGFiZWw6IChhLmRp"
    "c3BsYXlfbmFtZSB8fCBpaWQpICsgIiAoIiArIChhLnN5bWJvbF9sYWJlbCB8fCBpaWQpICsgIikiLAogICAgICB0aWNrZXI6IChh"
    "LnN5bWJvbF9sYWJlbCB8fCBpaWQpLAogICAgICBzY29yZTogYS5ub3J0aHN0YXJfc2NvcmUsCiAgICAgIHJzaTogcS5yc2kxNCA/"
    "PyBtLnJzaTE0ID8/IHcucnNpMTQsCiAgICAgIG1hY2Q6IHEubWFjZF9oaXN0ID8/IG0ubWFjZF9oaXN0ID8/IHcubWFjZF9oaXN0"
    "LAogICAgICBkMzY6IHEuZGlzdF90b18zNk1BID8/IG0uZGlzdF90b18zNk1BID8/IHcuZGlzdF90b18zNk1BLAogICAgICBzZWN0"
    "b3I6IGEuc2VjdG9yIHx8ICIiLAogICAgICBzdWJjbGFzczogc3ViLAogICAgICBpbk1lZHZpbmQ6IG1lZHZpbmQuaGFzKHN1Yiks"
    "CiAgICAgIGtpbmQ6ICJpbnN0cnVtZW50IgogICAgfSk7CiAgfSk7CiAgYXJyLnNvcnQoKGEsYik9PmIuc2NvcmUtYS5zY29yZSk7"
    "CiAgcmV0dXJuIGFycjsKfQoKLy8gTcOlbC12ZWt0ZXI6IGt1biBpbnN0cnVtZW50ZXIgaSBtZWR2aW5kLXNqYW5nZXIgT0cgc2Nv"
    "cmU+PXRlcnNrZWwgZXIKLy8ga2FuZGlkYXRlciBmb3IgTllFIGtqw7hwLiBNYWtzIDcgcG9zaXNqb25lciwgZWlkZSBwcmlvcml0"
    "ZXJlcy4KZnVuY3Rpb24gdGFyZ2V0V2VpZ2h0cyhjYW5kcyl7CiAgY29uc3QgY2FzaFRhcmdldCA9IGNsYW1wKHBhcnNlRmxvYXQo"
    "ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImNhc2hUYXJnZXQiKS52YWx1ZSl8fDE1LCAwLCAxMDApOwogIGNvbnN0IG1heFBvcyA9"
    "IGNsYW1wKHBhcnNlRmxvYXQoZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm1heFBvcyIpLnZhbHVlKXx8MjUsIDUsIDEwMCk7CiAg"
    "Y29uc3QgaW52ZXN0YWJsZSA9IDEwMCAtIGNhc2hUYXJnZXQ7CgogIC8vIEt2YWxpZmlzZXJ0IGZvciBueXR0IGtqw7hwOiBzY29y"
    "ZT49dGVyc2tlbCBPRyBpIG1lZHZpbmQtc2phbmdlci4KICBjb25zdCBlbGlnQWxsID0gY2FuZHMuZmlsdGVyKGMgPT4gYy5zY29y"
    "ZSA+PSBDQVNIX1RIUkVTSE9MRCAmJiBjLmluTWVkdmluZCkKICAgICAgICAgICAgICAgICAgICAgICAuc29ydCgoYSxiKT0+Yi5z"
    "Y29yZS1hLnNjb3JlKTsKICBjb25zdCBoZWxkID0gZWxpZ0FsbC5maWx0ZXIoYyA9PiAoU1RBVEUucG9zaXRpb25zW2MuaWRdfHww"
    "KSA+IDApOwogIGNvbnN0IGZyZXNoID0gZWxpZ0FsbC5maWx0ZXIoYyA9PiAhKChTVEFURS5wb3NpdGlvbnNbYy5pZF18fDApID4g"
    "MCkpOwogIGxldCBlbGlnID0gaGVsZC5zbGljZSgwLCBNQVhfUE9TSVRJT05TKTsKICBmb3IoY29uc3QgYyBvZiBmcmVzaCl7IGlm"
    "KGVsaWcubGVuZ3RoID49IE1BWF9QT1NJVElPTlMpIGJyZWFrOyBlbGlnLnB1c2goYyk7IH0KCiAgY29uc3Qgc3VtRXhjZXNzID0g"
    "ZWxpZy5yZWR1Y2UoKGEsYyk9PmErKGMuc2NvcmUtQ0FTSF9USFJFU0hPTEQpLDApOwogIGNvbnN0IHdlaWdodHMgPSB7fTsKICBp"
    "ZihzdW1FeGNlc3MgPiAwKXsKICAgIGVsaWcuZm9yRWFjaChjPT57CiAgICAgIGxldCB3ID0gaW52ZXN0YWJsZSAqIChjLnNjb3Jl"
    "LUNBU0hfVEhSRVNIT0xEKS9zdW1FeGNlc3M7CiAgICAgIHdlaWdodHNbYy5pZF0gPSBNYXRoLm1pbih3LCBtYXhQb3MpOwogICAg"
    "fSk7CiAgICBsZXQgdG90ID0gT2JqZWN0LnZhbHVlcyh3ZWlnaHRzKS5yZWR1Y2UoKGEsYik9PmErYiwwKTsKICAgIGlmKHRvdD4w"
    "ICYmIHRvdCA8IGludmVzdGFibGUpewogICAgICBsZXQgcm9vbSA9IGVsaWcuZmlsdGVyKGM9PndlaWdodHNbYy5pZF0gPCBtYXhQ"
    "b3MpOwogICAgICBsZXQgZGVmaWNpdCA9IGludmVzdGFibGUgLSB0b3Q7CiAgICAgIGxldCByb29tU3VtID0gcm9vbS5yZWR1Y2Uo"
    "KGEsYyk9PmErKG1heFBvcy13ZWlnaHRzW2MuaWRdKSwwKTsKICAgICAgaWYocm9vbVN1bT4wKSByb29tLmZvckVhY2goYz0+eyB3"
    "ZWlnaHRzW2MuaWRdKz0gZGVmaWNpdCoobWF4UG9zLXdlaWdodHNbYy5pZF0pL3Jvb21TdW07IH0pOwogICAgfQogIH0KICByZXR1"
    "cm4geyB3ZWlnaHRzLCBjYXNoVGFyZ2V0LCBtYXhQb3MsIGVsaWdJZHM6IG5ldyBTZXQoZWxpZy5tYXAoYz0+Yy5pZCkpIH07Cn0K"
    "CmZ1bmN0aW9uIGNsYW1wKHYsYSxiKXsgcmV0dXJuIE1hdGgubWF4KGEsIE1hdGgubWluKGIsIHYpKTsgfQoKLy8gRGVsdGEtYW5i"
    "ZWZhbGluZzogdGFyIGhlbnN5biB0aWwgaHZhIGR1IGVpZXIgKyBzamFuZ2VyLW1lZHZpbmQgKyBzY29yZS4KZnVuY3Rpb24gcmVj"
    "b21tZW5kYXRpb24oYywgb3duUGN0LCB0YXJnZXRQY3QsIGluRWxpZyl7CiAgY29uc3QgcnNpID0gYy5yc2kgPz8gNTA7CiAgY29u"
    "c3QgbWFjZCA9IGMubWFjZCA/PyAwOwogIGNvbnN0IGQzNiA9IGMuZDM2ID8/IDA7CiAgY29uc3QgdmVyeU92ZXJib3VnaHQgPSAo"
    "cnNpID49IE9WRVJCT1VHSFRfUlNJKSAmJiAobWFjZCA+PSBPVkVSQk9VR0hUX01BQ0QpICYmIChkMzYgPj0gU1RSRVRDSF8zNik7"
    "CiAgaWYob3duUGN0ID4gMCl7CiAgICAvLyBFaWQgcG9zaXNqb24KICAgIGlmKHZlcnlPdmVyYm91Z2h0KSByZXR1cm4ge2NvZGU6"
    "IlNDQUxFIiwgbGFiZWw6IlNLQUxFUiBBViIsIGNsczoic2VsbCIsIHdoeTpgVmVsZGlnIG92ZXJraiZvc2xhc2g7cHQgKFJTSSAk"
    "e01hdGgucm91bmQocnNpKX0sIE1BQ0QgaCZvc2xhc2g7eSwgc3RydWtrZXQgJHsoZDM2KjEwMCkudG9GaXhlZCgwKX0lKWB9Owog"
    "ICAgaWYoYy5zY29yZSA8IDM1KSByZXR1cm4ge2NvZGU6IlNDQUxFIiwgbGFiZWw6IlNLQUxFUiBBViIsIGNsczoidHJpbSIsIHdo"
    "eToiU2NvcmUgYnJ1dHQgbmVkIGkgbmVnYXRpdiBzb25lIn07CiAgICBpZighYy5pbk1lZHZpbmQpIHJldHVybiB7Y29kZToiSE9M"
    "RF9XRUFLIiwgbGFiZWw6IkhPTEQgKHN2ZWtrZXQgc2phbmdlcikiLCBjbHM6IndlYWsiLCB3aHk6YCR7Yy5zdWJjbGFzc30gc2wm"
    "YXJpbmc7ciBpa2tlIGd1bGwgbGVuZ2VyICZtZGFzaDsgdGVrbmlzayBzdW50LCBtZW4gbWlzdGV0IG1lZHZpbmRgfTsKICAgIGlm"
    "KG93blBjdCA8IHRhcmdldFBjdCAtIDMpIHJldHVybiB7Y29kZToiQUREIiwgbGFiZWw6IkxFR0cgVElMIiwgY2xzOiJhZGQiLCB3"
    "aHk6IkkgbWVkdmluZC1zamFuZ2VyLCB1bmRlciBtJmFyaW5nO2x2ZWt0In07CiAgICByZXR1cm4ge2NvZGU6IkhPTEQiLCBsYWJl"
    "bDoiSE9MRCIsIGNsczoiaG9sZCIsIHdoeToiSSBtZWR2aW5kLXNqYW5nZXIsIGlra2Ugb3ZlcmtqJm9zbGFzaDtwdCAmbWRhc2g7"
    "IGJlaG9sZCJ9OwogIH0gZWxzZSB7CiAgICAvLyBJa2tlIGVpZAogICAgaWYoIWMuaW5NZWR2aW5kKSByZXR1cm4ge2NvZGU6IldB"
    "SVQiLCBsYWJlbDoiQVZWRU5UIiwgY2xzOiJob2xkIiwgd2h5OmAke2Muc3ViY2xhc3N9IHNsJmFyaW5nO3IgaWtrZSBndWxsIChp"
    "a2tlIGkgbWVkdmluZClgfTsKICAgIGlmKGMuc2NvcmUgPj0gQ0FTSF9USFJFU0hPTEQgJiYgdGFyZ2V0UGN0ID4gMCkgcmV0dXJu"
    "IHtjb2RlOiJCVVkiLCBsYWJlbDoiS0omT3NsYXNoO1AiLCBjbHM6ImJ1eSIsIHdoeTpgTWVkdmluZC1zamFuZ2VyICsgc2NvcmUg"
    "JHtjLnNjb3JlfSAmZ2U7ICR7Q0FTSF9USFJFU0hPTER9LCBsYXZyaXNpa28gZW50cnlgfTsKICAgIGlmKGMuc2NvcmUgPj0gQ0FT"
    "SF9USFJFU0hPTEQgJiYgIWluRWxpZykgcmV0dXJuIHtjb2RlOiJXQUlUIiwgbGFiZWw6IkFWVkVOVCIsIGNsczoiaG9sZCIsIHdo"
    "eTpgS3ZhbGlmaXNlcnQsIG1lbiBtYWtzICR7TUFYX1BPU0lUSU9OU30gcG9zaXNqb25lciBmeWx0ICZtZGFzaDsgdmVudGVyIHAm"
    "YXJpbmc7IHBsYXNzYH07CiAgICByZXR1cm4ge2NvZGU6IldBSVQiLCBsYWJlbDoiQVZWRU5UIiwgY2xzOiJob2xkIiwgd2h5OmBT"
    "Y29yZSAke2Muc2NvcmV9IHVuZGVyIHRlcnNrZWwgJHtDQVNIX1RIUkVTSE9MRH1gfTsKICB9Cn0KCmZ1bmN0aW9uIHJlbmRlcigp"
    "ewogIGNvbnN0IGNhbmRzID0gY2FuZGlkYXRlcygpOwogIGNvbnN0IHsgd2VpZ2h0cywgY2FzaFRhcmdldCwgZWxpZ0lkcyB9ID0g"
    "dGFyZ2V0V2VpZ2h0cyhjYW5kcyk7CgogIC8vIFRyaW5uIEE6IHNqYW5nZXItcmFuZ2VyaW5nIChrdW4gdmlzbmluZykKICByZW5k"
    "ZXJHZW5yZXMoKTsKCiAgLy8gS1BJcwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJrVG90YWwiKS50ZXh0Q29udGVudCA9IGty"
    "KFNUQVRFLmNhc2ggKyBTVEFURS5pbnZlc3RlZCk7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImtJbnZlc3RlZCIpLnRleHRD"
    "b250ZW50ID0ga3IoU1RBVEUuaW52ZXN0ZWQpOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJrQ2FzaCIpLnRleHRDb250ZW50"
    "ID0ga3IoU1RBVEUuY2FzaCk7CiAgY29uc3QgdG90YWwgPSBTVEFURS5jYXNoICsgU1RBVEUuaW52ZXN0ZWQ7CiAgZG9jdW1lbnQu"
    "Z2V0RWxlbWVudEJ5SWQoImtDYXNoUGN0IikudGV4dENvbnRlbnQgPSB0b3RhbD4wID8gcGN0KFNUQVRFLmNhc2gvdG90YWwqMTAw"
    "KSA6ICLigJMiOwoKICAvLyBQb3J0ZWbDuGxqZW5zIHZla3RlZGUgdHJlbmQ6IHNuaXR0IGF2IGVpZGUgcG9zaXNqb25lcnMgc2Nv"
    "cmUsIHZla3RldAogIC8vIGV0dGVyIGVpZXJhbmRlbC4gSG9leWVyZSBzY29yZSA9IGJlZHJlIGxhdnJpc2lrby1wb3Npc2pvbmVy"
    "aW5nLgogIGNvbnN0IGJ5SWQgPSB7fTsgY2FuZHMuZm9yRWFjaChjPT5ieUlkW2MuaWRdPWMpOwogIGxldCB3c3VtID0gMCwgdHcg"
    "PSAwLCBtZWR2aW5kU2hhcmUgPSAwOwogIE9iamVjdC5rZXlzKFNUQVRFLnBvc2l0aW9ucykuZm9yRWFjaChpZD0+ewogICAgY29u"
    "c3Qgb3duID0gU1RBVEUucG9zaXRpb25zW2lkXSB8fCAwOwogICAgY29uc3QgYyA9IGJ5SWRbaWRdOwogICAgaWYob3duPjAgJiYg"
    "Yyl7CiAgICAgIHdzdW0gKz0gYy5zY29yZSAqIG93bjsgdHcgKz0gb3duOwogICAgICBpZihjLmluTWVkdmluZCkgbWVkdmluZFNo"
    "YXJlICs9IG93bjsKICAgIH0KICB9KTsKICBjb25zdCBwb3J0U2NvcmUgPSB0dz4wID8gTWF0aC5yb3VuZCh3c3VtL3R3KSA6IG51"
    "bGw7CiAgY29uc3QgbWVkdmluZFBjdCA9IHR3PjAgPyAobWVkdmluZFNoYXJlL3R3KjEwMCkgOiAwOwogIGNvbnN0IHB0RWwgPSBk"
    "b2N1bWVudC5nZXRFbGVtZW50QnlJZCgia1RyZW5kIik7CiAgaWYocHRFbCl7CiAgICBpZihwb3J0U2NvcmU9PW51bGwpeyBwdEVs"
    "LnRleHRDb250ZW50ID0gIuKAkyI7IHB0RWwuc3R5bGUuY29sb3IgPSAidmFyKC0tdGV4dCkiOyB9CiAgICBlbHNlIHsKICAgICAg"
    "Y29uc3QgY29sID0gcG9ydFNjb3JlPj02Nj8iIzUwYzg3OCI6cG9ydFNjb3JlPj00NT8iI2YwYTUwMCI6IiNlMDUwNTAiOwogICAg"
    "ICBwdEVsLmlubmVySFRNTCA9IGAke3BvcnRTY29yZX08c3BhbiBzdHlsZT0iZm9udC1zaXplOjEycHg7Y29sb3I6dmFyKC0tbXV0"
    "ZWQpIj4gLyAxMDA8L3NwYW4+YDsKICAgICAgcHRFbC5zdHlsZS5jb2xvciA9IGNvbDsKICAgIH0KICB9CiAgY29uc3QgbXZFbCA9"
    "IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJrTWVkdmluZCIpOwogIGlmKG12RWwpewogICAgY29uc3QgY29sID0gbWVkdmluZFBj"
    "dD49NjY/IiM1MGM4NzgiOm1lZHZpbmRQY3Q+PTQwPyIjZjBhNTAwIjoiI2UwNTA1MCI7CiAgICBtdkVsLnRleHRDb250ZW50ID0g"
    "dHc+MCA/IHBjdChtZWR2aW5kUGN0KSA6ICLigJMiOwogICAgbXZFbC5zdHlsZS5jb2xvciA9IHR3PjAgPyBjb2wgOiAidmFyKC0t"
    "dGV4dCkiOwogIH0KCiAgLy8gUG9zaXNqb25zdGFiZWxsOiBzb3J0ZXIgZXR0ZXIgS0rDmFAtdHJpZ2dldCBmb2Vyc3QsIGRlcmV0"
    "dGVyIHNjb3JlLgogIGNvbnN0IGJvZHkgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgicG9zQm9keSIpOwogIGJvZHkuaW5uZXJI"
    "VE1MID0gIiI7CiAgY29uc3QgcmFua2VkID0gY2FuZHMubWFwKGM9PnsKICAgIGNvbnN0IG93biA9IFNUQVRFLnBvc2l0aW9uc1tj"
    "LmlkXSB8fCAwOwogICAgY29uc3QgdGd0ID0gd2VpZ2h0c1tjLmlkXSB8fCAwOwogICAgY29uc3QgcmVjID0gcmVjb21tZW5kYXRp"
    "b24oYywgb3duLCB0Z3QsIGVsaWdJZHMuaGFzKGMuaWQpKTsKICAgIHJldHVybiB7Yywgb3duLCB0Z3QsIHJlY307CiAgfSk7CiAg"
    "Y29uc3QgcmVjUmFuayA9IHtCVVk6MCwgQUREOjEsIEhPTEQ6MiwgSE9MRF9XRUFLOjMsIFNDQUxFOjQsIFdBSVQ6NX07CiAgcmFu"
    "a2VkLnNvcnQoKGEsYik9PnsKICAgIGNvbnN0IHJhID0gcmVjUmFua1thLnJlYy5jb2RlXSA/PyA5LCByYiA9IHJlY1JhbmtbYi5y"
    "ZWMuY29kZV0gPz8gOTsKICAgIGlmKHJhICE9PSByYikgcmV0dXJuIHJhIC0gcmI7ICAgICAgIC8vIGtqw7hwLXRyaWdnZXQgZm9l"
    "cnN0CiAgICByZXR1cm4gYi5jLnNjb3JlIC0gYS5jLnNjb3JlOyAgICAgICAvLyBkZXJldHRlciBob2V5ZXN0IHNjb3JlCiAgfSk7"
    "CiAgcmFua2VkLmZvckVhY2goKHtjLCBvd24sIHRndCwgcmVjfSk9PnsKICAgIGNvbnN0IHNjID0gc2NvcmVDb2xvcihjLnNjb3Jl"
    "KTsKICAgIGNvbnN0IHR2ID0gYGh0dHBzOi8vd3d3LnRyYWRpbmd2aWV3LmNvbS9jaGFydC8/c3ltYm9sPSR7ZW5jb2RlVVJJQ29t"
    "cG9uZW50KGMudGlja2VyKX1gOwogICAgY29uc3QgdHIgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KCJ0ciIpOwogICAgdHIuaW5u"
    "ZXJIVE1MID0KICAgICAgYDx0ZD48c3Ryb25nPiR7Yy5sYWJlbH08L3N0cm9uZz4ke2MuaW5NZWR2aW5kPycgPHNwYW4gc3R5bGU9"
    "ImNvbG9yOiM1MGM4Nzg7Zm9udC1zaXplOjEwcHgiPiYjOTY1MDsgbWVkdmluZDwvc3Bhbj4nOicnfSBgKwogICAgICAgIGA8YSBo"
    "cmVmPSIke3R2fSIgdGFyZ2V0PSJfYmxhbmsiIHJlbD0ibm9vcGVuZXIiIHRpdGxlPSLDhXBuZSBpIFRyYWRpbmdWaWV3IiBzdHls"
    "ZT0iY29sb3I6IzVhYTlmZjtmb250LXNpemU6MTFweDt0ZXh0LWRlY29yYXRpb246bm9uZSI+JiMxMjgyMDI7IFRWPC9hPjwvdGQ+"
    "YCsKICAgICAgYDx0ZD48c3BhbiBjbGFzcz0ibXV0ZWQiIHN0eWxlPSJmb250LXNpemU6MTFweCI+JHtjLnN1YmNsYXNzfTwvc3Bh"
    "bj48L3RkPmArCiAgICAgIGA8dGQ+PHNwYW4gY2xhc3M9InBpbGwiIHN0eWxlPSJiYWNrZ3JvdW5kOiR7c2N9MjA7Y29sb3I6JHtz"
    "Y307Ym9yZGVyOjFweCBzb2xpZCAke3NjfTQwIj4ke2Muc2NvcmV9PC9zcGFuPjwvdGQ+YCsKICAgICAgYDx0ZD48aW5wdXQgY2xh"
    "c3M9InBvc2lucHV0IiB0eXBlPSJudW1iZXIiIG1pbj0iMCIgbWF4PSIxMDAiIHN0ZXA9IjEiIHZhbHVlPSIke293bn0iIGRhdGEt"
    "aWQ9IiR7Yy5pZH0iPjwvdGQ+YCsKICAgICAgYDx0ZD4ke3RndD4wP3RndC50b0ZpeGVkKDEpKyIlIjoiJm5kYXNoOyJ9PC90ZD5g"
    "KwogICAgICBgPHRkPjxzcGFuIGNsYXNzPSJyZWMgJHtyZWMuY2xzfSI+JHtyZWMubGFiZWx9PC9zcGFuPjxicj48c3BhbiBjbGFz"
    "cz0ibXV0ZWQiIHN0eWxlPSJmb250LXNpemU6MTFweCI+JHtyZWMud2h5fTwvc3Bhbj48L3RkPmA7CiAgICBib2R5LmFwcGVuZENo"
    "aWxkKHRyKTsKICB9KTsKICBib2R5LnF1ZXJ5U2VsZWN0b3JBbGwoIi5wb3NpbnB1dCIpLmZvckVhY2goaW5wPT57CiAgICBpbnAu"
    "YWRkRXZlbnRMaXN0ZW5lcigiY2hhbmdlIiwgZT0+ewogICAgICBjb25zdCBpZCA9IGUudGFyZ2V0LmRhdGFzZXQuaWQ7CiAgICAg"
    "IGNvbnN0IHYgPSBjbGFtcChwYXJzZUZsb2F0KGUudGFyZ2V0LnZhbHVlKXx8MCwgMCwgMTAwKTsKICAgICAgU1RBVEUucG9zaXRp"
    "b25zW2lkXSA9IHY7CiAgICAgIHJlY2FsY0ludmVzdGVkKCk7CiAgICAgIHNhdmVTdGF0ZSgpOyByZW5kZXIoKTsKICAgIH0pOwog"
    "IH0pOwoKICAvLyBQaWU6IGZha3Rpc2sgZm9yZGVsaW5nIChlaWRlIHBvc2lzam9uZXIgKyBjYXNoKQogIGRyYXdQaWUoY2FuZHMp"
    "OwoKICAvLyBIaXN0b3Jpa2sKICByZW5kZXJIaXN0KCk7CiAgc2F2ZVN0YXRlKCk7Cn0KCmZ1bmN0aW9uIHJlY2FsY0ludmVzdGVk"
    "KCl7CiAgY29uc3QgdG90YWwgPSBTVEFURS5jYXNoICsgU1RBVEUuaW52ZXN0ZWQ7CiAgY29uc3Qgb3duU3VtID0gT2JqZWN0LnZh"
    "bHVlcyhTVEFURS5wb3NpdGlvbnMpLnJlZHVjZSgoYSxiKT0+YStiLDApOwogIFNUQVRFLmludmVzdGVkID0gdG90YWwgKiBNYXRo"
    "Lm1pbihvd25TdW0sMTAwKS8xMDA7CiAgU1RBVEUuY2FzaCA9IHRvdGFsIC0gU1RBVEUuaW52ZXN0ZWQ7Cn0KCmZ1bmN0aW9uIHNj"
    "b3JlQ29sb3Iocyl7CiAgaWYocz49NzUpIHJldHVybiAiIzUwYzg3OCI7IGlmKHM+PTU1KSByZXR1cm4gIiNmMGE1MDAiOwogIGlm"
    "KHM+PTM1KSByZXR1cm4gIiNlMDgwMzAiOyByZXR1cm4gIiNlMDUwNTAiOwp9CgpmdW5jdGlvbiBkcmF3UGllKGNhbmRzKXsKICBj"
    "b25zdCB0b3RhbCA9IFNUQVRFLmNhc2ggKyBTVEFURS5pbnZlc3RlZDsKICBjb25zdCBzbGljZXMgPSBbXTsKICBjYW5kcy5mb3JF"
    "YWNoKGM9PnsKICAgIGNvbnN0IG93biA9IFNUQVRFLnBvc2l0aW9uc1tjLmlkXXx8MDsKICAgIGlmKG93bj4wKSBzbGljZXMucHVz"
    "aCh7bGFiZWw6Yy5sYWJlbCwgcGN0Om93biwgdmFsOiB0b3RhbCpvd24vMTAwLCBjb2w6IHNjb3JlQ29sb3IoYy5zY29yZSl9KTsK"
    "ICB9KTsKICBjb25zdCBjYXNoUGN0ID0gdG90YWw+MCA/IFNUQVRFLmNhc2gvdG90YWwqMTAwIDogMTAwOwogIHNsaWNlcy5wdXNo"
    "KHtsYWJlbDoiQ2FzaCIsIHBjdDpjYXNoUGN0LCB2YWw6U1RBVEUuY2FzaCwgY29sOiIjM2E0NDUyIn0pOwoKICBjb25zdCBzaXpl"
    "PTI0MCwgcj0xMTAsIGN4PXNpemUvMiwgY3k9c2l6ZS8yOwogIGxldCBhbmc9LU1hdGguUEkvMjsKICBsZXQgcGF0aHM9IiI7CiAg"
    "c2xpY2VzLmZvckVhY2gocz0+ewogICAgY29uc3QgYTIgPSBhbmcgKyAocy5wY3QvMTAwKSpNYXRoLlBJKjI7CiAgICBjb25zdCB4"
    "MT1jeCtyKk1hdGguY29zKGFuZyksIHkxPWN5K3IqTWF0aC5zaW4oYW5nKTsKICAgIGNvbnN0IHgyPWN4K3IqTWF0aC5jb3MoYTIp"
    "LCB5Mj1jeStyKk1hdGguc2luKGEyKTsKICAgIGNvbnN0IGxhcmdlID0gKGEyLWFuZyk+TWF0aC5QST8xOjA7CiAgICBpZihzLnBj"
    "dD4wLjAxKSBwYXRocyArPSBgPHBhdGggZD0iTSR7Y3h9LCR7Y3l9IEwke3gxfSwke3kxfSBBJHtyfSwke3J9IDAgJHtsYXJnZX0s"
    "MSAke3gyfSwke3kyfSBaIiBmaWxsPSIke3MuY29sfSIgc3Ryb2tlPSIjMGIwZDEwIiBzdHJva2Utd2lkdGg9IjIiPjwvcGF0aD5g"
    "OwogICAgYW5nPWEyOwogIH0pOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJwaWVXcmFwIikuaW5uZXJIVE1MID0KICAgIGA8"
    "c3ZnIGNsYXNzPSJwaWUiIHdpZHRoPSIke3NpemV9IiBoZWlnaHQ9IiR7c2l6ZX0iIHZpZXdCb3g9IjAgMCAke3NpemV9ICR7c2l6"
    "ZX0iPiR7cGF0aHN9PC9zdmc+YDsKICBjb25zdCBsZWcgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgicGllTGVnZW5kIik7CiAg"
    "bGVnLmlubmVySFRNTCA9ICIiOwogIHNsaWNlcy5maWx0ZXIocz0+cy5wY3Q+MC4wMSkuZm9yRWFjaChzPT57CiAgICBjb25zdCBk"
    "PWRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoImRpdiIpOyBkLmNsYXNzTmFtZT0ibGkiOwogICAgZC5pbm5lckhUTUw9YDxzcGFuIGNs"
    "YXNzPSJzdyIgc3R5bGU9ImJhY2tncm91bmQ6JHtzLmNvbH0iPjwvc3Bhbj5gKwogICAgICBgPHNwYW4+JHtzLmxhYmVsfTogPHN0"
    "cm9uZz4ke3MucGN0LnRvRml4ZWQoMSl9JTwvc3Ryb25nPiA8c3BhbiBjbGFzcz0ibXV0ZWQiPigke2tyKHMudmFsKX0pPC9zcGFu"
    "Pjwvc3Bhbj5gOwogICAgbGVnLmFwcGVuZENoaWxkKGQpOwogIH0pOwp9CgpmdW5jdGlvbiByZW5kZXJHZW5yZXMoKXsKICBjb25z"
    "dCBib3ggPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZ2VucmVCb3giKTsKICBpZighYm94KSByZXR1cm47CiAgY29uc3QgZ3Mg"
    "PSBnZW5yZXMoKTsKICBpZighZ3MubGVuZ3RoKXsgYm94LmlubmVySFRNTCA9ICc8ZGl2IGNsYXNzPSJtdXRlZCIgc3R5bGU9ImZv"
    "bnQtc2l6ZToxMnB4Ij5JbmdlbiBzamFuZ2VyLWRhdGEuPC9kaXY+JzsgcmV0dXJuOyB9CiAgYm94LmlubmVySFRNTCA9IGdzLm1h"
    "cChnPT57CiAgICBjb25zdCBjb2wgPSBnLm1lZHZpbmQgPyAiIzUwYzg3OCIgOiAoZy5zdHJlbmd0aD49NDAgPyAiI2YwYTUwMCIg"
    "OiAiI2UwNTA1MCIpOwogICAgY29uc3QgbWVkdmluZCA9IGcubWVkdmluZCA/ICc8c3BhbiBzdHlsZT0iY29sb3I6IzUwYzg3ODtm"
    "b250LXdlaWdodDo3MDA7Zm9udC1zaXplOjExcHgiPiYjOTY1MDsgSSBNRURWSU5EIChzbCZhcmluZztyIGd1bGwpPC9zcGFuPicg"
    "OiAnPHNwYW4gY2xhc3M9Im11dGVkIiBzdHlsZT0iZm9udC1zaXplOjExcHgiPmlra2UgbWVkdmluZDwvc3Bhbj4nOwogICAgcmV0"
    "dXJuIGA8ZGl2IGNsYXNzPSJnY2FyZCIgc3R5bGU9ImJvcmRlci1jb2xvcjoke2NvbH01MCI+CiAgICAgIDxkaXYgc3R5bGU9ImRp"
    "c3BsYXk6ZmxleDtqdXN0aWZ5LWNvbnRlbnQ6c3BhY2UtYmV0d2VlbjthbGlnbi1pdGVtczpiYXNlbGluZSI+CiAgICAgICAgPHNw"
    "YW4gc3R5bGU9ImZvbnQtd2VpZ2h0OjcwMCI+JHtnLnJhbmt9LiAke2cuZ2VucmV9PC9zcGFuPgogICAgICAgICR7bWVkdmluZH0K"
    "ICAgICAgPC9kaXY+CiAgICAgIDxkaXYgc3R5bGU9ImZvbnQtc2l6ZToyMnB4O2ZvbnQtd2VpZ2h0OjcwMDtjb2xvcjoke2NvbH07"
    "bWFyZ2luOjJweCAwIj4ke2cuc3RyZW5ndGh9PC9kaXY+CiAgICAgIDxkaXYgY2xhc3M9Im11dGVkIiBzdHlsZT0iZm9udC1zaXpl"
    "OjExcHgiPiR7Zy5ufSBpbnN0cjogJHtnLm1lbWJlcnMuam9pbigiLCAiKX08L2Rpdj4KICAgIDwvZGl2PmA7CiAgfSkuam9pbigi"
    "Iik7Cn0KCmZ1bmN0aW9uIHJlbmRlckhpc3QoKXsKICBjb25zdCBib3g9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImhpc3RCb3gi"
    "KTsKICBpZighU1RBVEUuaGlzdG9yeS5sZW5ndGgpeyBib3guaW5uZXJIVE1MPSc8ZGl2IGNsYXNzPSJtdXRlZCIgc3R5bGU9ImZv"
    "bnQtc2l6ZToxMnB4Ij5JbmdlbiBlbmRyaW5nZXIgZW5uJmFyaW5nOy48L2Rpdj4nOyByZXR1cm47IH0KICBib3guaW5uZXJIVE1M"
    "ID0gU1RBVEUuaGlzdG9yeS5tYXAoaD0+YDxkaXYgY2xhc3M9ImgiPjxkaXYgY2xhc3M9InQiPiR7aC50fTwvZGl2PiR7aC5tc2d9"
    "PC9kaXY+YCkuam9pbigiIik7Cn0KCi8vIC0tLSBLYXBpdGFsLWhhbmRsaW5nZXIgLS0tCmRvY3VtZW50LmdldEVsZW1lbnRCeUlk"
    "KCJhcHBseUNhcCIpLmFkZEV2ZW50TGlzdGVuZXIoImNsaWNrIiwgKCk9PnsKICBjb25zdCBzdGFydCA9IHBhcnNlRmxvYXQoZG9j"
    "dW1lbnQuZ2V0RWxlbWVudEJ5SWQoInN0YXJ0Q2FwIikudmFsdWUpfHwwOwogIGNvbnN0IGFkZCA9IHBhcnNlRmxvYXQoZG9jdW1l"
    "bnQuZ2V0RWxlbWVudEJ5SWQoImFkZENhcCIpLnZhbHVlKXx8MDsKICBjb25zdCBvbGRUb3RhbCA9IFNUQVRFLmNhc2ggKyBTVEFU"
    "RS5pbnZlc3RlZDsKICBpZihzdGFydCAhPT0gU1RBVEUuc3RhcnRDYXAgJiYgb2xkVG90YWwgPT09IFNUQVRFLnN0YXJ0Q2FwKXsK"
    "ICAgIC8vIGbDuHJzdGUgZ2FuZyAvIGp1c3RlcmluZyBhdiBzdGFydGthcGl0YWwKICAgIFNUQVRFLnN0YXJ0Q2FwID0gc3RhcnQ7"
    "IFNUQVRFLmNhc2ggPSBzdGFydCAtIFNUQVRFLmludmVzdGVkOwogICAgbG9nSGlzdChgU3RhcnRrYXBpdGFsIHNhdHQgdGlsICR7"
    "a3Ioc3RhcnQpfWApOwogIH0KICBpZihhZGQ+MCl7CiAgICBTVEFURS5jYXNoICs9IGFkZDsKICAgIGxvZ0hpc3QoYE55dHQgaW5u"
    "c2t1ZGQ6ICR7a3IoYWRkKX0gKHRvdGFsOiAke2tyKFNUQVRFLmNhc2grU1RBVEUuaW52ZXN0ZWQpfSlgKTsKICAgIGRvY3VtZW50"
    "LmdldEVsZW1lbnRCeUlkKCJhZGRDYXAiKS52YWx1ZT0iIjsKICB9CiAgU1RBVEUuY2FzaFRhcmdldCA9IGNsYW1wKHBhcnNlRmxv"
    "YXQoZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImNhc2hUYXJnZXQiKS52YWx1ZSl8fDE1LDAsMTAwKTsKICBTVEFURS5tYXhQb3Mg"
    "PSBjbGFtcChwYXJzZUZsb2F0KGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJtYXhQb3MiKS52YWx1ZSl8fDI1LDUsMTAwKTsKICBz"
    "YXZlU3RhdGUoKTsgcmVuZGVyKCk7Cn0pOwoKZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInJlYmFsYW5jZSIpLmFkZEV2ZW50TGlz"
    "dGVuZXIoImNsaWNrIiwgKCk9PnsKICBjb25zdCBjYW5kcyA9IGNhbmRpZGF0ZXMoKTsKICBjb25zdCB7IHdlaWdodHMsIGVsaWdJ"
    "ZHMgfSA9IHRhcmdldFdlaWdodHMoY2FuZHMpOwogIGxldCBjaGFuZ2VzPVtdOwogIGNhbmRzLmZvckVhY2goYz0+ewogICAgY29u"
    "c3Qgb3duID0gU1RBVEUucG9zaXRpb25zW2MuaWRdfHwwOwogICAgY29uc3QgdGd0ID0gd2VpZ2h0c1tjLmlkXXx8MDsKICAgIGNv"
    "bnN0IHJlYyA9IHJlY29tbWVuZGF0aW9uKGMsIG93biwgdGd0LCBlbGlnSWRzLmhhcyhjLmlkKSk7CiAgICBpZihyZWMuY29kZT09"
    "PSJCVVkiKXsgaWYodGd0PjAgJiYgb3duPHRndCl7IFNUQVRFLnBvc2l0aW9uc1tjLmlkXT1wYXJzZUZsb2F0KHRndC50b0ZpeGVk"
    "KDEpKTsgY2hhbmdlcy5wdXNoKGBLSiZPc2xhc2g7UCAke2MubGFiZWx9ICZyYXJyOyAke3RndC50b0ZpeGVkKDEpfSVgKTt9IH0K"
    "ICAgIGVsc2UgaWYocmVjLmNvZGU9PT0iQUREIil7IFNUQVRFLnBvc2l0aW9uc1tjLmlkXT1wYXJzZUZsb2F0KHRndC50b0ZpeGVk"
    "KDEpKTsgY2hhbmdlcy5wdXNoKGBMRUdHIFRJTCAke2MubGFiZWx9ICZyYXJyOyAke3RndC50b0ZpeGVkKDEpfSVgKTsgfQogICAg"
    "ZWxzZSBpZihyZWMuY29kZT09PSJTQ0FMRSIpeyBpZihvd24+MCl7IFNUQVRFLnBvc2l0aW9uc1tjLmlkXT0wOyBjaGFuZ2VzLnB1"
    "c2goYFNLQUxFUiBBViAke2MubGFiZWx9IChmcmEgJHtvd259JSlgKTt9IH0KICB9KTsKICByZWNhbGNJbnZlc3RlZCgpOwogIGlm"
    "KGNoYW5nZXMubGVuZ3RoKSBsb2dIaXN0KCJPbWZvcmRlbGluZzogIiArIGNoYW5nZXMuam9pbigiLCAiKSk7CiAgZWxzZSBsb2dI"
    "aXN0KCJPbWZvcmRlbGluZzogaW5nZW4gZW5kcmluZ2VyIGFuYmVmYWx0Iik7CiAgc2F2ZVN0YXRlKCk7IHJlbmRlcigpOwp9KTsK"
    "CmRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJjbGVhckhpc3QiKS5hZGRFdmVudExpc3RlbmVyKCJjbGljayIsICgpPT57CiAgaWYo"
    "Y29uZmlybSgiVCZvc2xhc2g7bW1lIGhlbGUgZW5kcmluZ3Nsb2dnZW4/IikpeyBTVEFURS5oaXN0b3J5PVtdOyBzYXZlU3RhdGUo"
    "KTsgcmVuZGVySGlzdCgpOyB9Cn0pOwoKaW5pdCgpOwo8L3NjcmlwdD4KPC9ib2R5Pgo8L2h0bWw+Cg=="
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
        "key": "renter_valuta", "title": "0. Renter & Valuta", "sector": "Renter & Valuta",
        "description": "Lange renter, kreditt og dollar-regimet. Northstar Milkshake Arc: bearish USD langsiktig.",
        "instruments": [
            {"id": "TLT",   "label": "20yr UST",        "symbol_label": "TLT",   "source": "yf", "candidates": ["TLT"]},
            {"id": "HYG",   "label": "High Yield",      "symbol_label": "HYG",   "source": "yf", "candidates": ["HYG", "JNK"]},
            {"id": "UUP",   "label": "DXY",             "symbol_label": "UUP",   "source": "yf", "candidates": ["UUP","USDU"]},
            {"id": "FXE",   "label": "EUR/USD",         "symbol_label": "FXE",   "source": "yf", "candidates": ["FXE"]},
            {"id": "CEW",   "label": "EM Currencies",   "symbol_label": "CEW",   "source": "yf", "candidates": ["CEW"]},
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
        ],
    },
    {
        "key": "tech", "title": "2. Tech & Halvledere", "sector": "Tech",
        "description": "Teknologilederskap og AI-infrastruktur.",
        "instruments": [
            {"id": "SOXQ", "label": "Semiconductors",   "symbol_label": "SOXQ",  "source": "yf", "candidates": ["SOXQ","SOXX"]},
            {"id": "HACK", "label": "Cybersecurity",    "symbol_label": "HACK",  "source": "yf", "candidates": ["HACK","CIBR"]},
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
        ],
    },
    {
        "key": "crypto", "title": "6. Crypto", "sector": "Crypto",
        "description": "Risiko-on spekulasjon og likviditetsindikator.",
        "instruments": [
            {"id": "BTC",  "label": "BTC",               "symbol_label": "BTC",   "source": "yf", "candidates": ["BTC-USD","BITO","IBIT"]},
            {"id": "ETHA", "label": "ETH",               "symbol_label": "ETH",   "source": "yf", "candidates": ["ETH-USD","ETHA"]},
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

# DPM-stil aktivaklasse per instrument (underklasse-henvisning).
# Brukes for Trinn A sjanger-rangering og som merke per instrument.
ASSET_SUBCLASS = {
    "SPY":"Stocks","QQQ":"Stocks","IWM":"Stocks","ACWI":"Stocks","EXSA":"Stocks","EEM":"Stocks","VNQ":"Stocks",
    "SOXQ":"Tech","HACK":"Tech","BOTZ":"Tech",
    "TLT":"Bonds","HYG":"Bonds","UUP":"Cash","FXE":"Cash","CEW":"Cash",
    "GLD":"Edelmetaller","SLV":"Edelmetaller","GDX":"Edelmetaller","GDXJ":"Edelmetaller",
    "SIL":"Edelmetaller","SILJ":"Edelmetaller","PPLT":"Edelmetaller","PALL":"Edelmetaller",
    "BCOM":"Commodity","USO":"Commodity","UNG":"Commodity","COPX":"Commodity",
    "XME":"Commodity","XLE":"Commodity","DBA":"Commodity","URA":"Commodity","URNM":"Commodity",
    "BTC":"Crypto","ETHA":"Crypto",
}

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
    daily     = with_indicators(base_df)
    weekly    = with_indicators(base_df.resample("W-FRI").last().dropna(how="all"))
    monthly   = with_indicators(base_df.resample("ME").last().dropna(how="all"))
    quarterly = with_indicators(base_df.resample("QE").last().dropna(how="all"))
    return daily, weekly, monthly, quarterly

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
    return ("Nøytral", "#9aa7b5")

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
    Tre like tidsrammer (hver 33.3%): weekly, monthly, 3-maaneders (kvartal).
    Hver tidsramme bidrar med RSI + MACD + avstand til 36-periode MA,
    likt vektet innen tidsrammen. Alle delscorer er dynamiske (ikke boetter).

    Avstand til MA bruker 36-periode paa hver tidsramme:
      weekly -> 36WMA, monthly -> 36MMA, 3M -> 36Q MA.
    """
    w = entry.get("frames",{}).get("weekly")    or {}
    m = entry.get("frames",{}).get("monthly")   or {}
    q = entry.get("frames",{}).get("quarterly") or {}

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

    # 33.3% per tidsramme, delt likt paa RSI/MACD/MA = 11.1% hver
    W = 100.0 / 9.0   # ~11.11

    for fr, tag in [(w, "W"), (m, "M"), (q, "3M")]:
        rsi = fr.get("rsi14")
        add(f"RSI {tag}", _rsi_subscore(rsi), W,
            f"{rsi:.1f} ({_fmt_sub(_rsi_subscore(rsi))})" if rsi is not None else "ingen data")
        mh = fr.get("macd_hist"); ml = fr.get("macd")
        add(f"MACD {tag}", _macd_subscore(mh, ml), W,
            f"hist {mh:.4f} ({_fmt_sub(_macd_subscore(mh, ml))})" if mh is not None else "ingen data")
        d36 = fr.get("dist_to_36MA")
        add(f"36MA {tag}", _ma_subscore(d36), W,
            f"{d36*100:+.1f}% ({_fmt_sub(_ma_subscore(d36))})" if d36 is not None else "ingen data")

    score = round(total / maxtot * 100) if maxtot > 0 else 0
    return min(score, 100), points

def score_synthetic_series(price_series):
    """
    Beregn Northstar-score for en syntetisk prisserie (f.eks. en ratio).
    Bruker EKSAKT samme scoremodell som northstar_score (W/M/3M, 33% hver).
    Returnerer (score, points, frames-dict).
    """
    df = pd.DataFrame({"close_use": price_series, "volume": np.nan}).dropna(subset=["close_use"])
    if len(df) < 200:
        return None, None, None
    daily, weekly, monthly, quarterly = resample_frames(df)
    entry = {"frames": {
        "daily":     frame_summary(daily,     is_weekly=False),
        "weekly":    frame_summary(weekly,    is_weekly=True),
        "monthly":   frame_summary(monthly,   is_weekly=False),
        "quarterly": frame_summary(quarterly, is_weekly=False),
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
            "subclass": ASSET_SUBCLASS.get(iid, ""),
            "frames": {"daily":{}, "weekly":{}, "monthly":{}},
            "missing_data": df is None or getattr(df,"empty",True),
        }
        if entry["missing_data"]:
            summary["assets"][iid] = entry; log(f"  MISSING: {iid}"); continue

        raw_cache[iid] = df
        daily, weekly, monthly, quarterly = resample_frames(df)
        entry["frames"]["daily"]     = frame_summary(daily,     is_weekly=False)
        entry["frames"]["weekly"]    = frame_summary(weekly,    is_weekly=True)
        entry["frames"]["monthly"]   = frame_summary(monthly,   is_weekly=False)
        entry["frames"]["quarterly"] = frame_summary(quarterly, is_weekly=False)

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
            plot_compact(monthly.tail(240), f"{inst['label']} ({inst['symbol_label']}) - monthly",
                         CHARTS / f"{iid}_monthly_compact.png",
                         ma_short=12, ma_long=36, ma_short_label="SMA12 (1aar)", ma_label_long="SMA36 (3aar)")
        if not quarterly.empty and len(quarterly) >= 8:
            plot_compact(quarterly.tail(120), f"{inst['label']} ({inst['symbol_label']}) - 3-maaneders",
                         CHARTS / f"{iid}_quarterly_compact.png",
                         ma_short=4, ma_long=12, ma_short_label="SMA4 (1aar)", ma_label_long="SMA12 (3aar)")

        summary["assets"][iid] = entry
        log(f"  OK: {iid} score={score}")

# ─── VS GULL: relativ styrke mot gull per instrument ───────────
# Northstar: vurder alt mot gull, ikke bare egen MA. Beregner hver
# instrument-ratio mot GLD over stigende 36-periode MA, paa flere
# tidsrammer (ukentlig for badge, maanedlig + kvartal for rotasjon).
def _vs_gold_state(ratio, ma_window=36, lookback=9):
    if ratio is None or len(ratio) < ma_window + 4:
        return None
    ma = ratio.rolling(ma_window).mean()
    last = float(ratio.iloc[-1])
    ma_now = float(ma.iloc[-1]) if pd.notna(ma.iloc[-1]) else None
    ma_prev = float(ma.iloc[-lookback]) if (len(ma) >= lookback and pd.notna(ma.iloc[-lookback])) else None
    if ma_now is None:
        return None
    above = last > ma_now
    rising = (ma_now > ma_prev) if ma_prev is not None else None
    dist = (last-ma_now)/ma_now
    if above and rising:   vstate, vcol = "Slaar gull", "#50c878"
    elif above:            vstate, vcol = "Over gull-MA", "#7ec88a"
    elif rising:           vstate, vcol = "Snur vs gull", "#f0a500"
    else:                  vstate, vcol = "Taper mot gull", "#e05050"
    return {"state": vstate, "col": vcol, "dist": dist, "beats": bool(above and rising)}

gold_df = raw_cache.get("GLD")
for iid, a in summary["assets"].items():
    if a.get("missing_data") or iid == "GLD" or gold_df is None:
        a["vs_gold"] = None; a["vs_gold_m"] = None; a["vs_gold_q"] = None
        continue
    inst_df = raw_cache.get(iid)
    if inst_df is None:
        a["vs_gold"] = None; a["vs_gold_m"] = None; a["vs_gold_q"] = None
        continue
    try:
        comb = pd.DataFrame({"i": inst_df["close_use"], "g": gold_df["close_use"]}).dropna()
        if len(comb) < 60:
            a["vs_gold"] = None; a["vs_gold_m"] = None; a["vs_gold_q"] = None
            continue
        rW = (comb["i"]/comb["g"]).resample("W-FRI").last().dropna()
        rM = (comb["i"]/comb["g"]).resample("ME").last().dropna()
        rQ = (comb["i"]/comb["g"]).resample("QE").last().dropna()
        a["vs_gold"]   = _vs_gold_state(rW, 36, 9)   # ukentlig (badge)
        a["vs_gold_m"] = _vs_gold_state(rM, 12, 3)    # maanedlig (1aar MA)
        a["vs_gold_q"] = _vs_gold_state(rQ, 4, 2)     # kvartal (1aar MA)
    except Exception:
        a["vs_gold"] = None; a["vs_gold_m"] = None; a["vs_gold_q"] = None

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

# Hent regime-serier dedikert (disse vises ikke lenger som instrumenter,
# men trengs for regime-kort og makro-charts).
yc_df, _yc_src = fred_2s10s_series()
if yc_df is None:
    log("  regime: 2s10s utilgjengelig (FRED-noekkel mangler?)")
ten_df, _ten_src = yf_series_from_candidates(["UTEN", "^TNX", "IEF"])
if ten_df is None:
    log("  regime: 10yr UST utilgjengelig")

# 1) Yield-kurve 2s10s: invertert (< 0) vs un-invertert (> 0)
if yc_df is not None and not yc_df.empty:
    yc_last = float(yc_df["close_use"].iloc[-1])
    yc_3m_ago = float(yc_df["close_use"].iloc[-63]) if len(yc_df) >= 63 else yc_last
    yc_dir = "stiler" if yc_last > yc_3m_ago else "flater"
    if yc_last < 0:
        regime["yield_curve"] = {"label": f"Invertert ({yc_last:.2f})", "col": "#e05050",
                                 "note": f"Resesjonsvarsel aktivt, {yc_dir}"}
    elif yc_last < 0.5:
        regime["yield_curve"] = {"label": f"Un-invertering ({yc_last:.2f})", "col": "#f0a500",
                                 "note": f"Høy resesjonsrisiko etter un-invertering, {yc_dir}"}
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
                                   "note": "Stimulativ fase - likviditet inn (NFTRH: QE-nær)"}
    elif fed_last > fed_12m * 0.98:
        regime["fed_liquidity"] = {"label": f"Baser seg ({chg_3m:+.1f}% 3m)", "col": "#f0a500",
                                   "note": "Balanse baser seg - mulig vending mot stimulering"}
    else:
        regime["fed_liquidity"] = {"label": f"Fallende ({chg_3m:+.1f}% 3m)", "col": "#e05050",
                                   "note": "QT pågår - likviditet ut"}
else:
    regime["fed_liquidity"] = {"label": "ingen data", "col": "#9aa7b5", "note": "FRED-noekkel mangler?"}

# 3) 10yr yield-retning (Continuum): over/under stigende?
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

# Kapitalrotasjon (Northstar): hovedinstrumenter vs gull paa maanedlig + 3M.
# Disse er valgt for aa fange store trender paa tvers av aktivaklasser.
ROTATION_MAIN = ["SPY","EEM","USO","URNM","XLE","SLV","BTC","NOK","DBA","ACWI","VNQ"]
def _count_beats(field):
    beats, loses = [], []
    for iid in ROTATION_MAIN:
        a = summary["assets"].get(iid, {})
        vg = a.get(field)
        if not vg:
            continue
        sym = a.get("symbol_label", iid)
        (beats if vg.get("beats") else loses).append(sym)
    return beats, loses

beats_m, loses_m = _count_beats("vs_gold_m")
beats_q, loses_q = _count_beats("vs_gold_q")
tot_m = len(beats_m) + len(loses_m)
tot_q = len(beats_q) + len(loses_q)
if tot_m > 0 or tot_q > 0:
    nb = len(beats_m)  # bruk maanedlig for farge/label
    frac = nb / tot_m if tot_m else 0
    if frac == 0:       rcol = "#e05050"; rnote = "Alle hovedinstrumenter i bear vs gull - kraftig rotasjon mot hard assets."
    elif frac < 0.5:    rcol = "#f0a500"; rnote = "Få hovedinstrumenter slår gull - rotasjon mot hard assets pågår."
    else:               rcol = "#50c878"; rnote = "Flertallet slår gull - risk-on holder følge."
    detail = (f"Maanedlig - slår gull: {', '.join(beats_m) or 'ingen'}; taper: {', '.join(loses_m) or 'ingen'}. "
              f"3M - slår gull: {', '.join(beats_q) or 'ingen'}; taper: {', '.join(loses_q) or 'ingen'}.")
    regime["rotation"] = {
        "label": f"M: {len(beats_m)}/{tot_m} | 3M: {len(beats_q)}/{tot_q} slår gull",
        "col": rcol, "note": f"{rnote} {detail}"}

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

# Kapitalrotasjon-chart: GLD/ACWI (Northstar sin kjerne-ratio) M + 3M
acwi_df = raw_cache.get("ACWI")
if gold_df is not None and acwi_df is not None:
    try:
        rc = pd.DataFrame({"g": gold_df["close_use"], "a": acwi_df["close_use"]}).dropna()
        if len(rc) > 200:
            rot_ratio = (rc["g"]/rc["a"])
            mdf = pd.DataFrame({"close_use": rot_ratio.resample("ME").last().dropna(), "volume": np.nan})
            qdf = pd.DataFrame({"close_use": rot_ratio.resample("QE").last().dropna(), "volume": np.nan})
            plot_compact(mdf.tail(180), "GLD/ACWI - maanedlig", CHARTS/"rotation_gld_acwi_m.png",
                         ma_short=12, ma_long=36, ma_short_label="SMA12 (1aar)", ma_label_long="SMA36 (3aar)")
            plot_compact(qdf.tail(120), "GLD/ACWI - 3-maaneders", CHARTS/"rotation_gld_acwi_q.png",
                         ma_short=4, ma_long=12, ma_short_label="SMA4 (1aar)", ma_label_long="SMA12 (3aar)")
            regime.setdefault("rotation",{})["chart_m"] = "charts/rotation_gld_acwi_m.png"
            regime.setdefault("rotation",{})["chart_q"] = "charts/rotation_gld_acwi_q.png"
    except Exception as e:
        log(f"rotation chart error: {e}")

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
    # Charts droppet: ratio-score-seksjonen vises ikke lenger paa trend-siden.
    m = frames.get("monthly", {}); q = frames.get("quarterly", {})
    trend_ratios.append({
        "rid": rid, "label": label, "score": score, "label_txt": slabel,
        "points": points, "score_series_monthly": m_hist,
        "mrsi": m.get("rsi14"), "qrsi": q.get("rsi14"),
        "dist36m": m.get("dist_to_36MA"), "dist36q": q.get("dist_to_36MA"),
        "macd_m": m.get("macd_hist"), "macd_q": q.get("macd_hist"),
    })
trend_ratios.sort(key=lambda x: -x["score"])
log(f"Trend-oversikt: {len(trend_ratios)} ratioer scoret")

# ─── LEADERSHIP RANKING (Trend-oversikt lag 1+2+4) ─────────────
# Kjerneprinsipp: all analyse relativt til gull (baseline), og til DXY.
# Vi rangerer sykliske instrumenter etter relativ styrke vs gull og vs DXY
# paa 1M og 3M. I tillegg sykliske par (instrument vs instrument).
log("Leadership ranking (vs gull, vs DXY, sykliske par)...")

# Sykliske instrumenter: aksjer, raavarer, energi, krypto, uran.
# (Edelmetaller utelatt fra "vs gull"-ranking siden de ER gull-komplekset.)
CYCLICAL_IDS = [
    "SPY","QQQ","IWM","ACWI","EXSA","EEM","VNQ",      # aksjer
    "SOXQ","HACK","BOTZ",                              # tech
    "BCOM","USO","UNG","COPX","XME","XLE","DBA",       # raavarer/energi
    "URA","URNM",                                      # uran
    "BTC","ETHA",                                      # krypto
]

def _rel_perf(num_id, den_df):
    """Relativ performance num/den: 1M og 3M % endring + retning vs MA.
    Returnerer dict med pct-endringer og en samlet styrke-score 0..100."""
    num_df = raw_cache.get(num_id)
    if num_df is None or den_df is None:
        return None
    comb = pd.DataFrame({"n": num_df["close_use"], "d": den_df["close_use"]}).dropna()
    if len(comb) < 80:
        return None
    ratio = (comb["n"]/comb["d"])
    m = ratio.resample("ME").last().dropna()
    if len(m) < 6:
        return None
    last = float(m.iloc[-1])
    # 1M og 3M prosentendring i ratioen (relativ performance)
    chg_1m = (last/float(m.iloc[-2]) - 1.0)*100 if len(m) >= 2 else None
    chg_3m = (last/float(m.iloc[-4]) - 1.0)*100 if len(m) >= 4 else None
    # Over stigende 12M-MA = relativ opptrend
    ma = m.rolling(12).mean()
    ma_now = float(ma.iloc[-1]) if pd.notna(ma.iloc[-1]) else None
    ma_prev = float(ma.iloc[-4]) if (len(ma) >= 4 and pd.notna(ma.iloc[-4])) else None
    above = (last > ma_now) if ma_now else False
    rising = (ma_now > ma_prev) if (ma_now and ma_prev) else False
    dist = ((last-ma_now)/ma_now*100) if ma_now else 0.0
    # Styrke-score: momentum (1M+3M) + trend (over/stigende MA)
    s = 50.0
    if chg_1m is not None: s += max(-20, min(20, chg_1m*1.5))
    if chg_3m is not None: s += max(-20, min(20, chg_3m*0.8))
    if above:  s += 5
    if rising: s += 5
    return {"chg_1m": chg_1m, "chg_3m": chg_3m, "dist": dist,
            "above": above, "rising": rising, "strength": round(max(0, min(100, s)))}

def _build_ranking(den_df, den_label):
    rows = []
    for iid in CYCLICAL_IDS:
        rp = _rel_perf(iid, den_df)
        if rp is None:
            continue
        a = summary["assets"].get(iid, {})
        rows.append({
            "id": iid, "label": a.get("symbol_label", iid),
            "name": a.get("display_name", iid),
            "subclass": ASSET_SUBCLASS.get(iid, ""),
            **rp,
        })
    rows.sort(key=lambda x: -(x.get("chg_3m") if x.get("chg_3m") is not None else -999))
    return {"den": den_label, "rows": rows}

ranking_gold = _build_ranking(raw_cache.get("GLD"), "Gull (GLD)")
ranking_dxy  = _build_ranking(raw_cache.get("UUP"), "DXY (UUP)")
log(f"  ranking vs gull: {len(ranking_gold['rows'])} | vs DXY: {len(ranking_dxy['rows'])}")

# Sykliske par (lag 4): intern rotasjon mellom sykliske aktiva.
# Høyere ratio-endring = først-nevnte leder.
CYCLICAL_PAIRS = [
    ("XLE","URNM","Energi vs Uran"),
    ("USO","XLE","Olje vs Energi-aksjer"),
    ("EEM","SPY","EM vs US"),
    ("IWM","SPY","Small-cap vs Large-cap"),
    ("SOXQ","QQQ","Halvledere vs Nasdaq"),
    ("COPX","XME","Kobber vs Metaller"),
    ("BTC","QQQ","Krypto vs Tech"),
    ("DBA","BCOM","Agri vs Bred raavare"),
    ("URNM","SPY","Uran vs US-aksjer"),
]
cyclical_pairs = []
for (a_id, b_id, plabel) in CYCLICAL_PAIRS:
    bdf = raw_cache.get(b_id)
    rp = _rel_perf(a_id, bdf) if bdf is not None else None
    if rp is None:
        continue
    cyclical_pairs.append({
        "label": plabel, "a": a_id, "b": b_id,
        "chg_1m": rp["chg_1m"], "chg_3m": rp["chg_3m"],
        "strength": rp["strength"], "above": rp["above"], "rising": rp["rising"],
    })
cyclical_pairs.sort(key=lambda x: -(x.get("chg_3m") if x.get("chg_3m") is not None else -999))
log(f"  sykliske par: {len(cyclical_pairs)}")

# ─── MONEY FLOW / LIKVIDITET (lag 3) ───────────────────────────
# Fed-likviditet finnes i regime. Legg til risk-appetitt: HYG/TLT
# (kreditt-spread proxy) og kobber/gull (vekst vs frykt).
money_flow = []
def _flow_signal(num_id, den_id, label, note):
    nd = raw_cache.get(num_id); dd = raw_cache.get(den_id)
    if nd is None or dd is None:
        return
    comb = pd.DataFrame({"n": nd["close_use"], "d": dd["close_use"]}).dropna()
    if len(comb) < 80:
        return
    r = (comb["n"]/comb["d"]).resample("ME").last().dropna()
    if len(r) < 4:
        return
    chg_3m = (float(r.iloc[-1])/float(r.iloc[-4]) - 1.0)*100
    ma = r.rolling(12).mean()
    rising = pd.notna(ma.iloc[-1]) and pd.notna(ma.iloc[-4]) and ma.iloc[-1] > ma.iloc[-4]
    risk_on = chg_3m > 0 and rising
    money_flow.append({
        "label": label, "chg_3m": round(chg_3m, 1),
        "state": "Risk-on" if risk_on else ("Nøytral" if chg_3m > -2 else "Risk-off"),
        "col": "#50c878" if risk_on else ("#f0a500" if chg_3m > -2 else "#e05050"),
        "note": note,
    })
_flow_signal("HYG","TLT","Kreditt-appetitt (HYG/TLT)", "Høy = risikovillig kapital søker yield")
_flow_signal("COPX","GLD","Vekst vs frykt (kobber/gull)", "Høy = vekstforventning over sikkerhet")
_flow_signal("EEM","ACWI","EM-ledelse (EM/verden)", "Høy = risk-on, likviditet til periferien")

# Index.json
# ─── SJANGER-STYRKE (Trinn A): relativ styrke per aktivaklasse ──
# Aggregerer hvert instrument sin styrke til sjanger-nivaa. Metode:
# snitt av (maanedlig + kvartal) trend-signal pr medlem. Trend-signal =
# kombinasjon av "slår gull" (M+Q) og positiv MACD-retning (M+Q),
# normalisert 0..1. Dette svarer paa "hvilke sjangrer er i medvind".
genre_members = {}
for iid, a in summary["assets"].items():
    if a.get("missing_data"):
        continue
    g = ASSET_SUBCLASS.get(iid)
    if not g:
        continue
    genre_members.setdefault(g, []).append(iid)

def _genre_strength(iids):
    """Returner 0..100 styrke-score for en sjanger basert paa medlemmene."""
    vals = []
    for iid in iids:
        a = summary["assets"].get(iid, {})
        parts = []
        # vs gull paa M og Q (1.0 hvis slår gull, 0.5 hvis over MA, 0 ellers)
        for fld in ("vs_gold_m", "vs_gold_q"):
            vg = a.get(fld)
            if vg:
                if vg.get("beats"):                 parts.append(1.0)
                elif vg.get("state") == "Over gull-MA": parts.append(0.6)
                elif vg.get("state") == "Snur vs gull": parts.append(0.4)
                else:                                parts.append(0.0)
        # MACD-retning paa M og Q (positiv hist = momentum opp)
        fr = a.get("frames") or {}
        for tf in ("monthly", "quarterly"):
            h = (fr.get(tf) or {}).get("macd_hist")
            if h is not None:
                parts.append(1.0 if h > 0 else 0.0)
        if parts:
            vals.append(sum(parts)/len(parts))
    return round(sum(vals)/len(vals)*100) if vals else 0

def _genre_beats_gold(iids):
    """Sjanger er 'i medvind' hvis flertallet av medlemmene slår gull (M og Q).
    Cash regnes aldri som medvind (defensiv). Edelmetaller = gull selv -> medvind
    hvis de slår sin egen MA-trend (bruker strength-terskel)."""
    beat = 0; total = 0
    for iid in iids:
        a = summary["assets"].get(iid, {})
        for fld in ("vs_gold_m", "vs_gold_q"):
            vg = a.get(fld)
            if vg is not None:
                total += 1
                if vg.get("beats"):
                    beat += 1
    if total == 0:
        return False
    return beat / total >= 0.5

genre_strength = []
for g, iids in genre_members.items():
    bg = _genre_beats_gold(iids)
    # Edelmetaller maales mot egen styrke (de ER gull), Cash aldri medvind
    if g == "Cash":
        medvind = False
    elif g == "Edelmetaller":
        medvind = _genre_strength(iids) >= 55
    else:
        medvind = bg
    genre_strength.append({
        "genre": g, "strength": _genre_strength(iids),
        "members": [summary["assets"][i].get("symbol_label", i) for i in iids],
        "member_ids": iids, "n": len(iids), "medvind": medvind,
    })
genre_strength.sort(key=lambda x: -x["strength"])
# Behold topp3 for visning, men 'medvind' er den styrende definisjonen.
for rank, gs in enumerate(genre_strength):
    gs["rank"] = rank + 1
    gs["top3"] = rank < 3

index = {"generated_local": NOW.isoformat(), "version": VERSION, "summary": summary,
         "sector_summary": sector_summary, "sector_trend": sector_trend,
         "ratio_charts": ratio_results, "rotation": rotation,
         "trend_ratios": trend_ratios, "regime": regime,
         "ranking_gold": ranking_gold, "ranking_dxy": ranking_dxy,
         "cyclical_pairs": cyclical_pairs, "money_flow": money_flow,
         "genre_strength": genre_strength,
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
    "Rawarer": "sec-rawarer", "Crypto": "sec-crypto",
    "Renter & Valuta": "sec-renter-valuta",
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
                   ("Fed-balanse",       regime.get("fed_liquidity"))]
    chart_figs = []
    for cname, r in chart_cards:
        if r and r.get("chart"):
            chart_figs.append(
                f'<figure><img src="{html.escape(r["chart"])}" alt="{html.escape(cname)}" loading="lazy">'
                f'<figcaption>{html.escape(cname)} (3-maaneders)</figcaption></figure>')
    if chart_figs:
        out.append('<div class="charts-grid" style="margin-top:12px">' + "".join(chart_figs) + '</div>')
    # Kapitalrotasjon GLD/ACWI (Northstar kjerne-ratio) - maanedlig + 3M
    rot = regime.get("rotation") or {}
    rot_figs = []
    if rot.get("chart_m"):
        rot_figs.append(f'<figure><img src="{html.escape(rot["chart_m"])}" alt="GLD/ACWI maanedlig" loading="lazy">'
                        f'<figcaption>GLD / ACWI - maanedlig (kapitalrotasjon)</figcaption></figure>')
    if rot.get("chart_q"):
        rot_figs.append(f'<figure><img src="{html.escape(rot["chart_q"])}" alt="GLD/ACWI 3-maaneders" loading="lazy">'
                        f'<figcaption>GLD / ACWI - 3-maaneders (kapitalrotasjon)</figcaption></figure>')
    if rot_figs:
        out.append('<p style="color:var(--muted);font-size:12px;margin-top:14px">'
                   '<strong>Kapitalrotasjon</strong> (Northstar kjerne-ratio): naar GLD/ACWI bryter opp = rotasjon mot hard assets bekreftet.</p>')
        out.append('<div class="charts-grid">' + "".join(rot_figs) + '</div>')
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

    # Topp performers — topp 10 instrumenter etter score
    ranked = []
    for iid, a in assets.items():
        if a.get("missing_data") or a.get("northstar_score") is None:
            continue
        ranked.append((a["northstar_score"], iid, a))
    ranked.sort(key=lambda x: -x[0])
    top10 = ranked[:10]
    if top10:
        parts.append('<section class="section"><h2>&#127942; Topp performers</h2>'
                     '<p style="color:var(--muted);font-size:12px">De 10 instrumentene med h&oslash;yest Northstar-score n&aring; '
                     '(lavrisiko entry / sterkest teknisk). Klikk for &aring; hoppe til sektoren.</p>'
                     '<table class="inst-table" style="margin-top:10px"><thead><tr>'
                     '<th>#</th><th>Instrument</th><th>Sektor</th><th>Score</th><th>Trend</th>'
                     '<th>Vs gull</th><th>&#916; uke</th></tr></thead><tbody>')
        for rank, (sc, iid, a) in enumerate(top10, 1):
            c = score_color(sc)
            w_ = (a.get("frames") or {}).get("weekly") or {}
            tlabel, tcol = trend_label(w_)
            vg = a.get("vs_gold")
            vg_s = f'<span style="color:{vg["col"]}">{html.escape(vg["state"])}</span>' if vg else "&ndash;"
            sec = a.get("sector","")
            anchor = SECTOR_ANCHORS.get(sec, "")
            parts.append(
                f'<tr>'
                f'<td style="color:var(--muted)">{rank}</td>'
                f'<td><a href="#{anchor}" style="color:var(--text);text-decoration:none"><strong>{html.escape(a.get("display_name") or iid)}</strong> '
                f'<span class="muted" style="font-size:11px">{html.escape(a.get("symbol_label") or iid)}</span></a></td>'
                f'<td class="muted">{html.escape("Råvarer" if sec=="Rawarer" else sec)}</td>'
                f'<td><span class="pill" style="background:{c}20;color:{c};border:1px solid {c}40">{sc}</span></td>'
                f'<td><span class="trend-badge" style="background:{tcol}20;color:{tcol}">{html.escape(tlabel)}</span></td>'
                f'<td style="font-size:12px">{vg_s}</td>'
                f'<td>{delta_html(a.get("score_delta"))}</td>'
                f'</tr>')
        parts.append('</tbody></table></section>')

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
            d_ = (a.get("frames") or {}).get("daily")     or {}
            w_ = (a.get("frames") or {}).get("weekly")    or {}
            m_ = (a.get("frames") or {}).get("monthly")   or {}
            q_ = (a.get("frames") or {}).get("quarterly") or {}
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
            meta = (f'<span class="trend-badge" style="background:{tcol}20;color:{tcol}">{html.escape(tlabel)}</span>{vg_badge} &bull; {vol_s}{high52}<br>'
                    f'<span class="muted">RSI:</span> W {fmt(w_.get("rsi14"))} / M {fmt(m_.get("rsi14"))} / 3M {fmt(q_.get("rsi14"))} &bull; '
                    f'<span class="muted">MACD:</span> W {macd_html(w_.get("macd_hist"))} / M {macd_html(m_.get("macd_hist"))} / 3M {macd_html(q_.get("macd_hist"))} &bull; '
                    f'<span class="muted">36-MA:</span> W {fmt_pct(w_.get("dist_to_36MA"))} / M {fmt_pct(m_.get("dist_to_36MA"))} / 3M {fmt_pct(q_.get("dist_to_36MA"))}')

            parts.append(
                f'<div class="inst-block">'
                f'<div class="inst-head">'
                f'<h3>{html.escape(a.get("display_name") or iid)}</h3>'
                f'<span class="ticker">{html.escape(a.get("symbol_label") or iid)}</span>'
                f'<span class="ticker" style="color:#5aa9ff;font-weight:600">{html.escape(ASSET_SUBCLASS.get(iid,""))}</span>'
                f'<span class="pill" style="background:{c}20;color:{c};border:1px solid {c}40">Score {sc} &bull; {html.escape(slabel)}</span>'
                f'<span class="delta">{delta_html(a.get("score_delta"))} vs forrige uke</span>'
                f'</div>'
                f'<div class="meta">{meta}</div>'
                f'{pills}'
                f'<div class="charts-grid">')
            dname = a.get("display_name") or iid
            for suffix, cap in [("weekly_compact","weekly"),("monthly_compact","monthly"),("quarterly_compact","3-maaneders")]:
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
table.rank{width:100%;border-collapse:collapse;font-size:13px;margin-top:4px}
table.rank th{background:var(--panel2);padding:6px 8px;text-align:left;border-bottom:1px solid var(--border);color:var(--muted);font-weight:600;font-size:11px}
table.rank td{padding:5px 8px;border-bottom:1px solid #1e2530}
table.rank tr:last-child td{border-bottom:none}
.muted{color:var(--muted)}
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

    # ─── LEADERSHIP RANKING (lag 1+2): vs gull og vs DXY ─────────
    rgold = index_data.get("ranking_gold", {})
    rdxy  = index_data.get("ranking_dxy", {})
    mflow = index_data.get("money_flow", [])
    cpairs = index_data.get("cyclical_pairs", [])

    def _chg_cell(v):
        if v is None: return '<td class="muted">&ndash;</td>'
        col = "#50c878" if v > 0 else "#e05050"
        return f'<td style="color:{col};text-align:right">{v:+.1f}%</td>'

    def _ranking_table(rk, title, baseline_note):
        rows = rk.get("rows", [])
        if not rows:
            return ""
        out = [f'<div style="flex:1;min-width:340px"><h3 style="margin:0 0 4px;font-size:15px">{html.escape(title)}</h3>'
               f'<p style="color:var(--muted);font-size:11px;margin:0 0 8px">{html.escape(baseline_note)}</p>'
               '<table class="rank"><thead><tr><th>#</th><th>Instr</th><th>Sjanger</th>'
               '<th style="text-align:right">1M</th><th style="text-align:right">3M</th><th>Trend</th></tr></thead><tbody>']
        for i, r in enumerate(rows, 1):
            tcol = "#50c878" if (r.get("above") and r.get("rising")) else ("#f0a500" if r.get("above") else "#e05050")
            tlab = "Leder" if (r.get("above") and r.get("rising")) else ("Over MA" if r.get("above") else "Svak")
            out.append(
                f'<tr><td class="muted">{i}</td>'
                f'<td><strong>{html.escape(r["label"])}</strong></td>'
                f'<td class="muted" style="font-size:11px">{html.escape(r.get("subclass",""))}</td>'
                f'{_chg_cell(r.get("chg_1m"))}{_chg_cell(r.get("chg_3m"))}'
                f'<td><span style="color:{tcol};font-size:11px;font-weight:600">{tlab}</span></td></tr>')
        out.append('</tbody></table></div>')
        return "".join(out)

    if rgold.get("rows") or rdxy.get("rows"):
        parts.append('<section class="section"><h2>&#127942; Leadership ranking (relativ styrke)</h2>'
                     '<p style="color:var(--muted);font-size:12px">Kjerneprinsipp: all analyse er <strong>relativ til gull</strong> '
                     '(baseline for likviditet, realrenter og monetaer politikk), og til <strong>DXY</strong>. '
                     'Sykliske instrumenter rangert etter relativ performance &mdash; hva outperformer naa, paa 1M og 3M.</p>'
                     '<div style="display:flex;flex-wrap:wrap;gap:24px;margin-top:10px">')
        parts.append(_ranking_table(rgold, "&#129351; vs Gull (XAU baseline)", "Positiv = slår gull. Dette er hovedlinsa for kapitalrotasjon."))
        parts.append(_ranking_table(rdxy,  "&#128181; vs DXY (dollar)", "Positiv = slår dollaren. Bekrefter ekte styrke vs valutaeffekt."))
        parts.append('</div></section>')

    # ─── MONEY FLOW (lag 3) ──────────────────────────────────────
    if mflow:
        parts.append('<section class="section"><h2>&#128167; Money flow &amp; likviditet</h2>'
                     '<p style="color:var(--muted);font-size:12px">Hvor kapital flyter: risikoappetitt og vekstforventning. '
                     'Kompletterer Fed-likviditet i makro-regimet over.</p>'
                     '<div class="sector-grid">')
        for f in mflow:
            parts.append(
                f'<div class="sc" style="border-color:{f["col"]}50;cursor:default;text-align:left">'
                f'<div class="sc-name" style="min-height:auto">{html.escape(f["label"])}</div>'
                f'<div style="font-size:16px;font-weight:700;color:{f["col"]};margin:3px 0">{html.escape(f["state"])} ({f["chg_3m"]:+.1f}% 3M)</div>'
                f'<div style="font-size:11px;color:var(--muted)">{html.escape(f["note"])}</div></div>')
        parts.append('</div></section>')

    # ─── SYKLISKE PAR (lag 4): intern rotasjon ───────────────────
    if cpairs:
        parts.append('<section class="section"><h2>&#9878;&#65039; Sykliske par (intern rotasjon)</h2>'
                     '<p style="color:var(--muted);font-size:12px">Instrument vs instrument &mdash; hvem leder innad blant sykliske aktiva. '
                     'Positiv = først leder.</p>'
                     '<table class="rank"><thead><tr><th>Par</th>'
                     '<th style="text-align:right">1M</th><th style="text-align:right">3M</th><th>Leder</th></tr></thead><tbody>')
        for p in cpairs:
            leader = p["a"] if (p.get("chg_3m") or 0) > 0 else p["b"]
            lcol = "#50c878" if (p.get("chg_3m") or 0) > 0 else "#e05050"
            parts.append(
                f'<tr><td><strong>{html.escape(p["label"])}</strong> '
                f'<span class="muted" style="font-size:11px">{html.escape(p["a"])}/{html.escape(p["b"])}</span></td>'
                f'{_chg_cell(p.get("chg_1m"))}{_chg_cell(p.get("chg_3m"))}'
                f'<td style="color:{lcol};font-weight:600">{html.escape(leader)}</td></tr>')
        parts.append('</tbody></table></section>')


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
