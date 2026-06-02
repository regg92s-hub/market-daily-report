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

VERSION = "2026-06-02-northstar-v5"
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
    "PiZuZGFzaDs8L2Rpdj48L2Rpdj4KICA8L2Rpdj4KICA8ZGl2IGNsYXNzPSJjYXAtcm93IiBzdHlsZT0ibWFyZ2luLXRvcDoxNHB4"
    "Ij4KICAgIDxkaXYgY2xhc3M9ImZpZWxkIj4KICAgICAgPGxhYmVsPk0mYXJpbmc7bCBjYXNoLWJ1ZmZlciAoJSk8L2xhYmVsPgog"
    "ICAgICA8aW5wdXQgdHlwZT0ibnVtYmVyIiBpZD0iY2FzaFRhcmdldCIgdmFsdWU9IjE1IiBtaW49IjAiIG1heD0iMTAwIiBzdGVw"
    "PSI1Ij4KICAgIDwvZGl2PgogICAgPGRpdiBjbGFzcz0iZmllbGQiPgogICAgICA8bGFiZWw+TWFrcyB2ZWt0IHBlciBwb3Npc2pv"
    "biAoJSk8L2xhYmVsPgogICAgICA8aW5wdXQgdHlwZT0ibnVtYmVyIiBpZD0ibWF4UG9zIiB2YWx1ZT0iMjUiIG1pbj0iNSIgbWF4"
    "PSIxMDAiIHN0ZXA9IjUiPgogICAgPC9kaXY+CiAgPC9kaXY+CjwvZGl2PgoKPGRpdiBjbGFzcz0ic2VjdGlvbiI+CiAgPGgyPiYj"
    "MTI3OTQyOyBUcmlubiAxOiBTamFuZ2VyLXJhbmdlcmluZzwvaDI+CiAgPHAgY2xhc3M9Im11dGVkIiBzdHlsZT0iZm9udC1zaXpl"
    "OjEycHgiPlJlbGF0aXYgc3R5cmtlIHBlciBha3RpdmFrbGFzc2UgKG0mYXJpbmc7bmVkbGlnICsgMy1tJmFyaW5nO25lZGxpZyB0"
    "cmVuZCB2cyBndWxsIG9nIG1vbWVudHVtKS4gVG9wcCAzIGVyIDxzdHJvbmc+aSBtZWR2aW5kPC9zdHJvbmc+ICZtZGFzaDsgZGV0"
    "IGVyIGhlciB2aSBsZXRlciBldHRlciBsYXZyaXNpa28tZW50cnktaW5zdHJ1bWVudGVyLjwvcD4KICA8ZGl2IGNsYXNzPSJnZW5y"
    "ZS1ncmlkIiBpZD0iZ2VucmVCb3giPjwvZGl2Pgo8L2Rpdj4KCjxkaXYgY2xhc3M9ImdyaWQyIj4KICA8ZGl2IGNsYXNzPSJzZWN0"
    "aW9uIj4KICAgIDxoMj4mIzEyOTUxODsgQW5iZWZhbHQgZm9yZGVsaW5nPC9oMj4KICAgIDxwIGNsYXNzPSJtdXRlZCIgc3R5bGU9"
    "ImZvbnQtc2l6ZToxMnB4Ij5WZWt0ZXQgZXR0ZXIgc2NvcmUsIGt1biBpbnN0cnVtZW50ZXIgaSB0b3BwLTMtc2phbmdlci4gQ2Fz"
    "aC1idWZmZXIgaG9sZGVzIGlnamVuLjwvcD4KICAgIDxkaXYgaWQ9InBpZVdyYXAiPjwvZGl2PgogICAgPGRpdiBjbGFzcz0ibGVn"
    "ZW5kLXBpZSIgaWQ9InBpZUxlZ2VuZCI+PC9kaXY+CiAgPC9kaXY+CiAgPGRpdiBjbGFzcz0ic2VjdGlvbiI+CiAgICA8aDI+JiMx"
    "MjgyMjE7IFRyaW5uIDI6IFBvc2lzam9uZXIgJmFtcDsgYW5iZWZhbGluZzwvaDI+CiAgICA8cCBjbGFzcz0ibXV0ZWQiIHN0eWxl"
    "PSJmb250LXNpemU6MTJweCI+QWxsZSBpbnN0cnVtZW50ZXIgdmlzZXMuIEtKJk9zbGFzaDtQL0xFR0cgVElMIGdqZWxkZXIga3Vu"
    "IGxhdnJpc2lrby1lbnRyeSBpIG1lZHZpbmQtc2phbmdyZXIuIEVpZGUgcG9zaXNqb25lciBiZWhvbGRlcyAoZmxhZ2dlcyBodmlz"
    "IHNqYW5nZXJlbiBtaXN0ZXQgbWVkdmluZCkuIFNrcml2IGlubiBuJmFyaW5nO3YmYWVsaWc7cmVuZGUgdmVrdCAoJSkgZHUgZWll"
    "ci48L3A+CiAgICA8dGFibGUgaWQ9InBvc1RhYmxlIj48dGhlYWQ+PHRyPgogICAgICA8dGg+SW5zdHJ1bWVudDwvdGg+PHRoPlNq"
    "YW5nZXI8L3RoPjx0aD5TY29yZTwvdGg+PHRoPkVpZXIgJTwvdGg+PHRoPk0mYXJpbmc7bCAlPC90aD48dGg+QW5iZWZhbGluZzwv"
    "dGg+CiAgICA8L3RyPjwvdGhlYWQ+PHRib2R5IGlkPSJwb3NCb2R5Ij48L3Rib2R5PjwvdGFibGU+CiAgPC9kaXY+CjwvZGl2PgoK"
    "PGRpdiBjbGFzcz0ic2VjdGlvbiI+CiAgPGgyPiYjMTI4MjAyOyBFbmRyaW5nc2xvZ2c8L2gyPgogIDxwIGNsYXNzPSJtdXRlZCIg"
    "c3R5bGU9ImZvbnQtc2l6ZToxMnB4Ij5IdmVyIG9tZm9yZGVsaW5nIG9nIGthcGl0YWxlbmRyaW5nIGxvZ2dlcyBoZXIgKGxhZ3Jl"
    "dCBsb2thbHQgaSBuZXR0bGVzZXJlbikuPC9wPgogIDxkaXYgY2xhc3M9Imhpc3QiIGlkPSJoaXN0Qm94Ij48L2Rpdj4KICA8YnV0"
    "dG9uIGNsYXNzPSJidG4gc2Vjb25kYXJ5IiBpZD0iY2xlYXJIaXN0IiBzdHlsZT0ibWFyZ2luLXRvcDoxMHB4Ij5UJm9zbGFzaDtt"
    "IGxvZ2c8L2J1dHRvbj4KPC9kaXY+Cgo8ZGl2IGNsYXNzPSJzZWN0aW9uIj4KICA8aDI+JiM4NTA1OyYjNjUwMzk7IFNsaWsgZnVu"
    "Z2VyZXIgbW9kZWxsZW48L2gyPgogIDxkaXYgY2xhc3M9ImxlZ2VuZCI+CiAgPGNvZGU+TSZhcmluZztsICU8L2NvZGU+IGJlcmVn"
    "bmVzIGZyYSB0cmVuZC1zY29yZSBwJmFyaW5nOyB0b3BwIDEwIGluc3RydW1lbnRlcjoga3VuIGRlIG1lZCBzY29yZSAmZ2U7IDU1"
    "IGYmYXJpbmc7ciB0aWxkZWx0IHZla3QuIFZla3QgZXIgcHJvcG9yc2pvbmFsIG1lZCBzY29yZSBvdmVyIHRlcnNrZWxlbi48YnI+"
    "CiAgPGNvZGU+Q2FzaC1idWZmZXI8L2NvZGU+IChzdGFuZGFyZCAxNSUpIGhvbGRlcyBhbGx0aWQgaWdqZW4gZiZvc2xhc2g7ciBm"
    "b3JkZWxpbmcgJm1kYXNoOyBkdSB0YXIga3VuIHBvc2lzam9uZXIgbiZhcmluZztyIG5vZSBzZXIgbG92ZW5kZSB1dC48YnI+CiAg"
    "PGNvZGU+TWFrcyB2ZWt0PC9jb2RlPiBwZXIgcG9zaXNqb24gaGluZHJlciBhdCBhbHQgc2FtbGVzIGkgJmVhY3V0ZTtuIGlkJmVh"
    "Y3V0ZTsuIDxjb2RlPk1ha3MgNyBwb3Npc2pvbmVyPC9jb2RlPiBvbSBnYW5nZW4gJm1kYXNoOyBlaWRlIHBvc2lzam9uZXIgcHJp"
    "b3JpdGVyZXMsIG9nIG55ZSBrdmFsaWZpc2VydGUgdmVudGVyIHAmYXJpbmc7IGxlZGlnIHBsYXNzLjxicj4KICA8Y29kZT5LSiZP"
    "c2xhc2g7UDwvY29kZT46IHNjb3JlICZnZTsgNTUgb2cgZHUgZWllciBtaW5kcmUgZW5uIG0mYXJpbmc7bC4gPGNvZGU+TEVHRyBU"
    "SUw8L2NvZGU+OiBnb2Qgc2NvcmUsIGxpdHQgdW5kZXIgbSZhcmluZztsLjxicj4KICA8Y29kZT5IT0xEPC9jb2RlPjogcG9zaXNq"
    "b24gdGF0dCwgaWtrZSBvdmVya2omb3NsYXNoO3B0IGVubiZhcmluZzsgJm1kYXNoOyBiZWhvbGRlcyBzZWx2IG9tIHNjb3JlIGZh"
    "bGxlciwgdGlsIGRlbiBibGlyIDxlbT52ZWxkaWc8L2VtPiBvdmVya2omb3NsYXNoO3B0Ljxicj4KICA8Y29kZT5TS0FMRVIgQVY8"
    "L2NvZGU+OiBrdW4gbiZhcmluZztyIFJTSSAmZ2U7IDY1IE9HIE1BQ0QtaGlzdCAmZ2U7IDIgT0cgc3RydWtrZXQgbGFuZ3Qgb3Zl"
    "ciAzNldNQS8zeXIgTUEgJm1kYXNoOyBlbGxlciBuJmFyaW5nO3IgZHUgdHJlbmdlciBjYXNoIHRpbCBrbGFydCBiZWRyZSBtdWxp"
    "Z2hldGVyLjxicj4KICA8Y29kZT5GdWxsIHBvcnRlZiZvc2xhc2g7bGplPC9jb2RlPjogaHZpcyBhbHQgZXIgZnVsbHQgb2cgY2Fz"
    "aCBlciB1bmRlciBtJmFyaW5nO2wsIGZvcmVzbCZhcmluZztzIGt1biBza2lmdGUgbiZhcmluZztyIGVuIHN2YWtlcmUgcG9zaXNq"
    "b24ga2FuIHZpa2UgZm9yIGVuIGtsYXJ0IHN0ZXJrZXJlLgogIDwvZGl2Pgo8L2Rpdj4KCjxmb290ZXI+RGF0YTogPGEgaHJlZj0i"
    "aW5kZXguanNvbiIgc3R5bGU9ImNvbG9yOnZhcigtLW11dGVkKSI+aW5kZXguanNvbjwvYT4gJmJ1bGw7IExhZ3JlcyBsb2thbHQg"
    "aSBkaW4gbmV0dGxlc2VyIChsb2NhbFN0b3JhZ2UpPC9mb290ZXI+CjwvZGl2PgoKPHNjcmlwdD4KY29uc3QgTFNfS0VZID0gIm5z"
    "X3BvcnRmb2xpb192MSI7CmNvbnN0IENBU0hfVEhSRVNIT0xEID0gNTU7ICAgICAvLyBtaW4gc2NvcmUgZm9yIMOlIGbDpSB0aWxk"
    "ZWx0IHZla3QKY29uc3QgTUFYX1BPU0lUSU9OUyA9IDc7ICAgICAgIC8vIG1ha3MgYW50YWxsIHBvc2lzam9uZXIgb20gZ2FuZ2Vu"
    "CmNvbnN0IE9WRVJCT1VHSFRfUlNJID0gNjU7CmNvbnN0IE9WRVJCT1VHSFRfTUFDRCA9IDI7CmNvbnN0IFNUUkVUQ0hfMzYgPSAw"
    "LjIwOyAgICAgICAvLyAyMCUgb3ZlciAzNk1BCmNvbnN0IFNUUkVUQ0hfM1lSID0gMC4zMDsgICAgICAvLyAzMCUgb3ZlciAzeXIK"
    "CmxldCBTVEFURSA9IGxvYWRTdGF0ZSgpOwpsZXQgREFUQSA9IG51bGw7CgpmdW5jdGlvbiBsb2FkU3RhdGUoKXsKICB0cnl7IGNv"
    "bnN0IHMgPSBKU09OLnBhcnNlKGxvY2FsU3RvcmFnZS5nZXRJdGVtKExTX0tFWSkpOyBpZihzKSByZXR1cm4gczsgfWNhdGNoKGUp"
    "e30KICByZXR1cm4geyBzdGFydENhcDogMTAwMDAwLCBjYXNoOiAxMDAwMDAsIGludmVzdGVkOiAwLCBwb3NpdGlvbnM6IHt9LCBo"
    "aXN0b3J5OiBbXSwgY2FzaFRhcmdldDogMTUsIG1heFBvczogMjUgfTsKfQpmdW5jdGlvbiBzYXZlU3RhdGUoKXsgbG9jYWxTdG9y"
    "YWdlLnNldEl0ZW0oTFNfS0VZLCBKU09OLnN0cmluZ2lmeShTVEFURSkpOyB9CmZ1bmN0aW9uIGtyKG4peyByZXR1cm4gKE1hdGgu"
    "cm91bmQobikpLnRvTG9jYWxlU3RyaW5nKCJuby1OTyIpICsgIiBrciI7IH0KZnVuY3Rpb24gcGN0KG4peyByZXR1cm4gKG4pLnRv"
    "Rml4ZWQoMSkgKyAiJSI7IH0KZnVuY3Rpb24gbm93KCl7IHJldHVybiBuZXcgRGF0ZSgpLnRvTG9jYWxlU3RyaW5nKCJuby1OTyIp"
    "OyB9CgpmdW5jdGlvbiBsb2dIaXN0KG1zZyl7CiAgU1RBVEUuaGlzdG9yeS51bnNoaWZ0KHsgdDogbm93KCksIG1zZyB9KTsKICBp"
    "ZihTVEFURS5oaXN0b3J5Lmxlbmd0aCA+IDIwMCkgU1RBVEUuaGlzdG9yeS5wb3AoKTsKfQoKYXN5bmMgZnVuY3Rpb24gaW5pdCgp"
    "ewogIHRyeXsKICAgIGNvbnN0IHIgPSBhd2FpdCBmZXRjaCgiaW5kZXguanNvbiIsIHtjYWNoZToibm8tc3RvcmUifSk7CiAgICBE"
    "QVRBID0gYXdhaXQgci5qc29uKCk7CiAgICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgidG9wbm90ZSIpLmlubmVySFRNTCA9CiAg"
    "ICAgICJUcmVuZC1kYXRhIGdlbmVyZXJ0OiAiICsgKERBVEEuZ2VuZXJhdGVkX2xvY2FsfHwiIikgKyAiICZidWxsOyAiICsgKERB"
    "VEEudmVyc2lvbnx8IiIpOwogIH1jYXRjaChlKXsKICAgIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJ0b3Bub3RlIikudGV4dENv"
    "bnRlbnQgPSAiS3VubmUgaWtrZSBsYXN0ZSBpbmRleC5qc29uOiAiICsgZTsKICAgIHJldHVybjsKICB9CiAgLy8gaW5pdCBjYXBp"
    "dGFsIGlucHV0cwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJzdGFydENhcCIpLnZhbHVlID0gU1RBVEUuc3RhcnRDYXA7CiAg"
    "ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImNhc2hUYXJnZXQiKS52YWx1ZSA9IFNUQVRFLmNhc2hUYXJnZXQ7CiAgZG9jdW1lbnQu"
    "Z2V0RWxlbWVudEJ5SWQoIm1heFBvcyIpLnZhbHVlID0gU1RBVEUubWF4UG9zOwogIHJlbmRlcigpOwp9CgovLyBUcmlubiBBOiBz"
    "amFuZ2VyLXN0eXJrZSBmcmEgaW5kZXguanNvbiAoYmVyZWduZXQgaSBnZW5lcmF0b3JlbikKZnVuY3Rpb24gZ2VucmVzKCl7CiAg"
    "cmV0dXJuIChEQVRBLmdlbnJlX3N0cmVuZ3RoIHx8IFtdKTsKfQpmdW5jdGlvbiB0b3AzR2VucmVOYW1lcygpewogIHJldHVybiBu"
    "ZXcgU2V0KGdlbnJlcygpLmZpbHRlcihnPT5nLnRvcDMpLm1hcChnPT5nLmdlbnJlKSk7Cn0KCi8vIFRyaW5uIEI6IGJ5Z2cga2Fu"
    "ZGlkYXRsaXN0ZS4gQWxsZSBpbnN0cnVtZW50ZXIgdnVyZGVyZXMsIG1lbiB2aSBtZXJrZXIKLy8gaHZpbGtlIHNvbSBsaWdnZXIg"
    "aSBlbiB0b3BwLTMtc2phbmdlciAoaSBtZWR2aW5kKS4gRGUgNyBiZXN0ZSBsYXZyaXNpa28tCi8vIGVudHJ5LWluc3RydW1lbnRl"
    "bmUgSU5ORU5GT1IgdG9wcC0zLXNqYW5ncmVuZSBlciBkZSBzb20gYW5iZWZhbGVzIGtqb2VwdC4KZnVuY3Rpb24gY2FuZGlkYXRl"
    "cygpewogIGNvbnN0IGFzc2V0cyA9IChEQVRBLnN1bW1hcnkgJiYgREFUQS5zdW1tYXJ5LmFzc2V0cykgfHwge307CiAgY29uc3Qg"
    "dG9wMyA9IHRvcDNHZW5yZU5hbWVzKCk7CiAgY29uc3QgYXJyID0gW107CiAgT2JqZWN0LmtleXMoYXNzZXRzKS5mb3JFYWNoKGlp"
    "ZD0+ewogICAgY29uc3QgYSA9IGFzc2V0c1tpaWRdOwogICAgaWYoYS5taXNzaW5nX2RhdGEgfHwgYS5ub3J0aHN0YXJfc2NvcmUg"
    "PT0gbnVsbCkgcmV0dXJuOwogICAgY29uc3QgdyA9IChhLmZyYW1lcyAmJiBhLmZyYW1lcy53ZWVrbHkpIHx8IHt9OwogICAgY29u"
    "c3QgbSA9IChhLmZyYW1lcyAmJiBhLmZyYW1lcy5tb250aGx5KSB8fCB7fTsKICAgIGNvbnN0IHEgPSAoYS5mcmFtZXMgJiYgYS5m"
    "cmFtZXMucXVhcnRlcmx5KSB8fCB7fTsKICAgIGNvbnN0IHN1YiA9IGEuc3ViY2xhc3MgfHwgIiI7CiAgICBhcnIucHVzaCh7CiAg"
    "ICAgIGlkOiBpaWQsCiAgICAgIGxhYmVsOiAoYS5kaXNwbGF5X25hbWUgfHwgaWlkKSArICIgKCIgKyAoYS5zeW1ib2xfbGFiZWwg"
    "fHwgaWlkKSArICIpIiwKICAgICAgc2NvcmU6IGEubm9ydGhzdGFyX3Njb3JlLAogICAgICByc2k6IHEucnNpMTQgPz8gbS5yc2kx"
    "NCA/PyB3LnJzaTE0LAogICAgICBtYWNkOiBxLm1hY2RfaGlzdCA/PyBtLm1hY2RfaGlzdCA/PyB3Lm1hY2RfaGlzdCwKICAgICAg"
    "ZDM2OiBxLmRpc3RfdG9fMzZNQSA/PyBtLmRpc3RfdG9fMzZNQSA/PyB3LmRpc3RfdG9fMzZNQSwKICAgICAgc2VjdG9yOiBhLnNl"
    "Y3RvciB8fCAiIiwKICAgICAgc3ViY2xhc3M6IHN1YiwKICAgICAgaW5Ub3AzOiB0b3AzLmhhcyhzdWIpLAogICAgICBraW5kOiAi"
    "aW5zdHJ1bWVudCIKICAgIH0pOwogIH0pOwogIGFyci5zb3J0KChhLGIpPT5iLnNjb3JlLWEuc2NvcmUpOwogIHJldHVybiBhcnI7"
    "Cn0KCi8vIE3DpWwtdmVrdGVyOiBrdW4gaW5zdHJ1bWVudGVyIGkgdG9wcC0zLXNqYW5nZXIgT0cgc2NvcmU+PXRlcnNrZWwgZXIK"
    "Ly8ga2FuZGlkYXRlciBmb3IgTllFIGtqb2VwLiBNYWtzIDcgcG9zaXNqb25lciwgZWlkZSBwcmlvcml0ZXJlcy4KZnVuY3Rpb24g"
    "dGFyZ2V0V2VpZ2h0cyhjYW5kcyl7CiAgY29uc3QgY2FzaFRhcmdldCA9IGNsYW1wKHBhcnNlRmxvYXQoZG9jdW1lbnQuZ2V0RWxl"
    "bWVudEJ5SWQoImNhc2hUYXJnZXQiKS52YWx1ZSl8fDE1LCAwLCAxMDApOwogIGNvbnN0IG1heFBvcyA9IGNsYW1wKHBhcnNlRmxv"
    "YXQoZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm1heFBvcyIpLnZhbHVlKXx8MjUsIDUsIDEwMCk7CiAgY29uc3QgaW52ZXN0YWJs"
    "ZSA9IDEwMCAtIGNhc2hUYXJnZXQ7CgogIC8vIEt2YWxpZmlzZXJ0IGZvciBueXR0IGtqb2VwOiBzY29yZT49dGVyc2tlbCBPRyBp"
    "IHRvcHAtMy1zamFuZ2VyLgogIGNvbnN0IGVsaWdBbGwgPSBjYW5kcy5maWx0ZXIoYyA9PiBjLnNjb3JlID49IENBU0hfVEhSRVNI"
    "T0xEICYmIGMuaW5Ub3AzKQogICAgICAgICAgICAgICAgICAgICAgIC5zb3J0KChhLGIpPT5iLnNjb3JlLWEuc2NvcmUpOwogIGNv"
    "bnN0IGhlbGQgPSBlbGlnQWxsLmZpbHRlcihjID0+IChTVEFURS5wb3NpdGlvbnNbYy5pZF18fDApID4gMCk7CiAgY29uc3QgZnJl"
    "c2ggPSBlbGlnQWxsLmZpbHRlcihjID0+ICEoKFNUQVRFLnBvc2l0aW9uc1tjLmlkXXx8MCkgPiAwKSk7CiAgbGV0IGVsaWcgPSBo"
    "ZWxkLnNsaWNlKDAsIE1BWF9QT1NJVElPTlMpOwogIGZvcihjb25zdCBjIG9mIGZyZXNoKXsgaWYoZWxpZy5sZW5ndGggPj0gTUFY"
    "X1BPU0lUSU9OUykgYnJlYWs7IGVsaWcucHVzaChjKTsgfQoKICBjb25zdCBzdW1FeGNlc3MgPSBlbGlnLnJlZHVjZSgoYSxjKT0+"
    "YSsoYy5zY29yZS1DQVNIX1RIUkVTSE9MRCksMCk7CiAgY29uc3Qgd2VpZ2h0cyA9IHt9OwogIGlmKHN1bUV4Y2VzcyA+IDApewog"
    "ICAgZWxpZy5mb3JFYWNoKGM9PnsKICAgICAgbGV0IHcgPSBpbnZlc3RhYmxlICogKGMuc2NvcmUtQ0FTSF9USFJFU0hPTEQpL3N1"
    "bUV4Y2VzczsKICAgICAgd2VpZ2h0c1tjLmlkXSA9IE1hdGgubWluKHcsIG1heFBvcyk7CiAgICB9KTsKICAgIGxldCB0b3QgPSBP"
    "YmplY3QudmFsdWVzKHdlaWdodHMpLnJlZHVjZSgoYSxiKT0+YStiLDApOwogICAgaWYodG90PjAgJiYgdG90IDwgaW52ZXN0YWJs"
    "ZSl7CiAgICAgIGxldCByb29tID0gZWxpZy5maWx0ZXIoYz0+d2VpZ2h0c1tjLmlkXSA8IG1heFBvcyk7CiAgICAgIGxldCBkZWZp"
    "Y2l0ID0gaW52ZXN0YWJsZSAtIHRvdDsKICAgICAgbGV0IHJvb21TdW0gPSByb29tLnJlZHVjZSgoYSxjKT0+YSsobWF4UG9zLXdl"
    "aWdodHNbYy5pZF0pLDApOwogICAgICBpZihyb29tU3VtPjApIHJvb20uZm9yRWFjaChjPT57IHdlaWdodHNbYy5pZF0rPSBkZWZp"
    "Y2l0KihtYXhQb3Mtd2VpZ2h0c1tjLmlkXSkvcm9vbVN1bTsgfSk7CiAgICB9CiAgfQogIHJldHVybiB7IHdlaWdodHMsIGNhc2hU"
    "YXJnZXQsIG1heFBvcywgZWxpZ0lkczogbmV3IFNldChlbGlnLm1hcChjPT5jLmlkKSkgfTsKfQoKZnVuY3Rpb24gY2xhbXAodixh"
    "LGIpeyByZXR1cm4gTWF0aC5tYXgoYSwgTWF0aC5taW4oYiwgdikpOyB9CgovLyBEZWx0YS1hbmJlZmFsaW5nOiB0YXIgaGVuc3lu"
    "IHRpbCBodmEgZHUgZWllciArIHNqYW5nZXItbWVkdmluZCArIHNjb3JlLgpmdW5jdGlvbiByZWNvbW1lbmRhdGlvbihjLCBvd25Q"
    "Y3QsIHRhcmdldFBjdCwgaW5FbGlnKXsKICBjb25zdCByc2kgPSBjLnJzaSA/PyA1MDsKICBjb25zdCBtYWNkID0gYy5tYWNkID8/"
    "IDA7CiAgY29uc3QgZDM2ID0gYy5kMzYgPz8gMDsKICBjb25zdCB2ZXJ5T3ZlcmJvdWdodCA9IChyc2kgPj0gT1ZFUkJPVUdIVF9S"
    "U0kpICYmIChtYWNkID49IE9WRVJCT1VHSFRfTUFDRCkgJiYgKGQzNiA+PSBTVFJFVENIXzM2KTsKICBpZihvd25QY3QgPiAwKXsK"
    "ICAgIC8vIEVpZCBwb3Npc2pvbgogICAgaWYodmVyeU92ZXJib3VnaHQpIHJldHVybiB7Y29kZToiU0NBTEUiLCBsYWJlbDoiU0tB"
    "TEVSIEFWIiwgY2xzOiJzZWxsIiwgd2h5OmBWZWxkaWcgb3ZlcmtqJm9zbGFzaDtwdCAoUlNJICR7TWF0aC5yb3VuZChyc2kpfSwg"
    "TUFDRCBoJm9zbGFzaDt5LCBzdHJ1a2tldCAkeyhkMzYqMTAwKS50b0ZpeGVkKDApfSUpYH07CiAgICBpZihjLnNjb3JlIDwgMzUp"
    "IHJldHVybiB7Y29kZToiU0NBTEUiLCBsYWJlbDoiU0tBTEVSIEFWIiwgY2xzOiJ0cmltIiwgd2h5OiJTY29yZSBicnV0dCBuZWQg"
    "aSBuZWdhdGl2IHNvbmUifTsKICAgIGlmKCFjLmluVG9wMykgcmV0dXJuIHtjb2RlOiJIT0xEX1dFQUsiLCBsYWJlbDoiSE9MRCAo"
    "c3Zla2tldCBzamFuZ2VyKSIsIGNsczoid2VhayIsIHdoeTpgJHtjLnN1YmNsYXNzfSBmYWx0IHV0IGF2IHRvcHAgMyAmbWRhc2g7"
    "IHRla25pc2sgc3VudCwgbWVuIG1pc3RldCBtZWR2aW5kYH07CiAgICBpZihvd25QY3QgPCB0YXJnZXRQY3QgLSAzKSByZXR1cm4g"
    "e2NvZGU6IkFERCIsIGxhYmVsOiJMRUdHIFRJTCIsIGNsczoiYWRkIiwgd2h5OiJJIG1lZHZpbmQtc2phbmdlciwgdW5kZXIgbSZh"
    "cmluZztsdmVrdCJ9OwogICAgcmV0dXJuIHtjb2RlOiJIT0xEIiwgbGFiZWw6IkhPTEQiLCBjbHM6ImhvbGQiLCB3aHk6IkkgbWVk"
    "dmluZC1zamFuZ2VyLCBpa2tlIG92ZXJraiZvc2xhc2g7cHQgJm1kYXNoOyBiZWhvbGQifTsKICB9IGVsc2UgewogICAgLy8gSWtr"
    "ZSBlaWQKICAgIGlmKCFjLmluVG9wMykgcmV0dXJuIHtjb2RlOiJXQUlUIiwgbGFiZWw6IkFWVkVOVCIsIGNsczoiaG9sZCIsIHdo"
    "eTpgJHtjLnN1YmNsYXNzfSBlciBpa2tlIGkgdG9wcCAzIHNqYW5ncmVyYH07CiAgICBpZihjLnNjb3JlID49IENBU0hfVEhSRVNI"
    "T0xEICYmIHRhcmdldFBjdCA+IDApIHJldHVybiB7Y29kZToiQlVZIiwgbGFiZWw6IktKJk9zbGFzaDtQIiwgY2xzOiJidXkiLCB3"
    "aHk6YE1lZHZpbmQtc2phbmdlciArIHNjb3JlICR7Yy5zY29yZX0gJmdlOyAke0NBU0hfVEhSRVNIT0xEfSwgbGF2cmlzaWtvIGVu"
    "dHJ5YH07CiAgICBpZihjLnNjb3JlID49IENBU0hfVEhSRVNIT0xEICYmICFpbkVsaWcpIHJldHVybiB7Y29kZToiV0FJVCIsIGxh"
    "YmVsOiJBVlZFTlQiLCBjbHM6ImhvbGQiLCB3aHk6YEt2YWxpZmlzZXJ0LCBtZW4gbWFrcyAke01BWF9QT1NJVElPTlN9IHBvc2lz"
    "am9uZXIgZnlsdCAmbWRhc2g7IHZlbnRlciBwJmFyaW5nOyBwbGFzc2B9OwogICAgcmV0dXJuIHtjb2RlOiJXQUlUIiwgbGFiZWw6"
    "IkFWVkVOVCIsIGNsczoiaG9sZCIsIHdoeTpgU2NvcmUgJHtjLnNjb3JlfSB1bmRlciB0ZXJza2VsICR7Q0FTSF9USFJFU0hPTER9"
    "YH07CiAgfQp9CgpmdW5jdGlvbiByZW5kZXIoKXsKICBjb25zdCBjYW5kcyA9IGNhbmRpZGF0ZXMoKTsKICBjb25zdCB7IHdlaWdo"
    "dHMsIGNhc2hUYXJnZXQsIGVsaWdJZHMgfSA9IHRhcmdldFdlaWdodHMoY2FuZHMpOwoKICAvLyBUcmlubiBBOiBzamFuZ2VyLXJh"
    "bmdlcmluZyAoa3VuIHZpc25pbmcpCiAgcmVuZGVyR2VucmVzKCk7CgogIC8vIEtQSXMKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJ"
    "ZCgia1RvdGFsIikudGV4dENvbnRlbnQgPSBrcihTVEFURS5jYXNoICsgU1RBVEUuaW52ZXN0ZWQpOwogIGRvY3VtZW50LmdldEVs"
    "ZW1lbnRCeUlkKCJrSW52ZXN0ZWQiKS50ZXh0Q29udGVudCA9IGtyKFNUQVRFLmludmVzdGVkKTsKICBkb2N1bWVudC5nZXRFbGVt"
    "ZW50QnlJZCgia0Nhc2giKS50ZXh0Q29udGVudCA9IGtyKFNUQVRFLmNhc2gpOwogIGNvbnN0IHRvdGFsID0gU1RBVEUuY2FzaCAr"
    "IFNUQVRFLmludmVzdGVkOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJrQ2FzaFBjdCIpLnRleHRDb250ZW50ID0gdG90YWw+"
    "MCA/IHBjdChTVEFURS5jYXNoL3RvdGFsKjEwMCkgOiAi4oCTIjsKCiAgLy8gUG9zaXNqb25zdGFiZWxsCiAgY29uc3QgYm9keSA9"
    "IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJwb3NCb2R5Iik7CiAgYm9keS5pbm5lckhUTUwgPSAiIjsKICBjYW5kcy5zb3J0KChh"
    "LGIpPT5iLnNjb3JlLWEuc2NvcmUpLmZvckVhY2goYz0+ewogICAgY29uc3Qgb3duID0gU1RBVEUucG9zaXRpb25zW2MuaWRdIHx8"
    "IDA7CiAgICBjb25zdCB0Z3QgPSB3ZWlnaHRzW2MuaWRdIHx8IDA7CiAgICBjb25zdCByZWMgPSByZWNvbW1lbmRhdGlvbihjLCBv"
    "d24sIHRndCwgZWxpZ0lkcy5oYXMoYy5pZCkpOwogICAgY29uc3Qgc2MgPSBzY29yZUNvbG9yKGMuc2NvcmUpOwogICAgY29uc3Qg"
    "dHIgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KCJ0ciIpOwogICAgdHIuaW5uZXJIVE1MID0KICAgICAgYDx0ZD48c3Ryb25nPiR7"
    "Yy5sYWJlbH08L3N0cm9uZz4ke2MuaW5Ub3AzPycgPHNwYW4gc3R5bGU9ImNvbG9yOiM1MGM4Nzg7Zm9udC1zaXplOjEwcHgiPiYj"
    "OTY1MDsgbWVkdmluZDwvc3Bhbj4nOicnfTwvdGQ+YCsKICAgICAgYDx0ZD48c3BhbiBjbGFzcz0ibXV0ZWQiIHN0eWxlPSJmb250"
    "LXNpemU6MTFweCI+JHtjLnN1YmNsYXNzfTwvc3Bhbj48L3RkPmArCiAgICAgIGA8dGQ+PHNwYW4gY2xhc3M9InBpbGwiIHN0eWxl"
    "PSJiYWNrZ3JvdW5kOiR7c2N9MjA7Y29sb3I6JHtzY307Ym9yZGVyOjFweCBzb2xpZCAke3NjfTQwIj4ke2Muc2NvcmV9PC9zcGFu"
    "PjwvdGQ+YCsKICAgICAgYDx0ZD48aW5wdXQgY2xhc3M9InBvc2lucHV0IiB0eXBlPSJudW1iZXIiIG1pbj0iMCIgbWF4PSIxMDAi"
    "IHN0ZXA9IjEiIHZhbHVlPSIke293bn0iIGRhdGEtaWQ9IiR7Yy5pZH0iPjwvdGQ+YCsKICAgICAgYDx0ZD4ke3RndD4wP3RndC50"
    "b0ZpeGVkKDEpKyIlIjoiJm5kYXNoOyJ9PC90ZD5gKwogICAgICBgPHRkPjxzcGFuIGNsYXNzPSJyZWMgJHtyZWMuY2xzfSI+JHty"
    "ZWMubGFiZWx9PC9zcGFuPjxicj48c3BhbiBjbGFzcz0ibXV0ZWQiIHN0eWxlPSJmb250LXNpemU6MTFweCI+JHtyZWMud2h5fTwv"
    "c3Bhbj48L3RkPmA7CiAgICBib2R5LmFwcGVuZENoaWxkKHRyKTsKICB9KTsKICBib2R5LnF1ZXJ5U2VsZWN0b3JBbGwoIi5wb3Np"
    "bnB1dCIpLmZvckVhY2goaW5wPT57CiAgICBpbnAuYWRkRXZlbnRMaXN0ZW5lcigiY2hhbmdlIiwgZT0+ewogICAgICBjb25zdCBp"
    "ZCA9IGUudGFyZ2V0LmRhdGFzZXQuaWQ7CiAgICAgIGNvbnN0IHYgPSBjbGFtcChwYXJzZUZsb2F0KGUudGFyZ2V0LnZhbHVlKXx8"
    "MCwgMCwgMTAwKTsKICAgICAgU1RBVEUucG9zaXRpb25zW2lkXSA9IHY7CiAgICAgIHJlY2FsY0ludmVzdGVkKCk7CiAgICAgIHNh"
    "dmVTdGF0ZSgpOyByZW5kZXIoKTsKICAgIH0pOwogIH0pOwoKICAvLyBQaWU6IGZha3Rpc2sgZm9yZGVsaW5nIChlaWRlIHBvc2lz"
    "am9uZXIgKyBjYXNoKQogIGRyYXdQaWUoY2FuZHMpOwoKICAvLyBIaXN0b3Jpa2sKICByZW5kZXJIaXN0KCk7CiAgc2F2ZVN0YXRl"
    "KCk7Cn0KCmZ1bmN0aW9uIHJlY2FsY0ludmVzdGVkKCl7CiAgY29uc3QgdG90YWwgPSBTVEFURS5jYXNoICsgU1RBVEUuaW52ZXN0"
    "ZWQ7CiAgY29uc3Qgb3duU3VtID0gT2JqZWN0LnZhbHVlcyhTVEFURS5wb3NpdGlvbnMpLnJlZHVjZSgoYSxiKT0+YStiLDApOwog"
    "IFNUQVRFLmludmVzdGVkID0gdG90YWwgKiBNYXRoLm1pbihvd25TdW0sMTAwKS8xMDA7CiAgU1RBVEUuY2FzaCA9IHRvdGFsIC0g"
    "U1RBVEUuaW52ZXN0ZWQ7Cn0KCmZ1bmN0aW9uIHNjb3JlQ29sb3Iocyl7CiAgaWYocz49NzUpIHJldHVybiAiIzUwYzg3OCI7IGlm"
    "KHM+PTU1KSByZXR1cm4gIiNmMGE1MDAiOwogIGlmKHM+PTM1KSByZXR1cm4gIiNlMDgwMzAiOyByZXR1cm4gIiNlMDUwNTAiOwp9"
    "CgpmdW5jdGlvbiBkcmF3UGllKGNhbmRzKXsKICBjb25zdCB0b3RhbCA9IFNUQVRFLmNhc2ggKyBTVEFURS5pbnZlc3RlZDsKICBj"
    "b25zdCBzbGljZXMgPSBbXTsKICBjYW5kcy5mb3JFYWNoKGM9PnsKICAgIGNvbnN0IG93biA9IFNUQVRFLnBvc2l0aW9uc1tjLmlk"
    "XXx8MDsKICAgIGlmKG93bj4wKSBzbGljZXMucHVzaCh7bGFiZWw6Yy5sYWJlbCwgcGN0Om93biwgdmFsOiB0b3RhbCpvd24vMTAw"
    "LCBjb2w6IHNjb3JlQ29sb3IoYy5zY29yZSl9KTsKICB9KTsKICBjb25zdCBjYXNoUGN0ID0gdG90YWw+MCA/IFNUQVRFLmNhc2gv"
    "dG90YWwqMTAwIDogMTAwOwogIHNsaWNlcy5wdXNoKHtsYWJlbDoiQ2FzaCIsIHBjdDpjYXNoUGN0LCB2YWw6U1RBVEUuY2FzaCwg"
    "Y29sOiIjM2E0NDUyIn0pOwoKICBjb25zdCBzaXplPTI0MCwgcj0xMTAsIGN4PXNpemUvMiwgY3k9c2l6ZS8yOwogIGxldCBhbmc9"
    "LU1hdGguUEkvMjsKICBsZXQgcGF0aHM9IiI7CiAgc2xpY2VzLmZvckVhY2gocz0+ewogICAgY29uc3QgYTIgPSBhbmcgKyAocy5w"
    "Y3QvMTAwKSpNYXRoLlBJKjI7CiAgICBjb25zdCB4MT1jeCtyKk1hdGguY29zKGFuZyksIHkxPWN5K3IqTWF0aC5zaW4oYW5nKTsK"
    "ICAgIGNvbnN0IHgyPWN4K3IqTWF0aC5jb3MoYTIpLCB5Mj1jeStyKk1hdGguc2luKGEyKTsKICAgIGNvbnN0IGxhcmdlID0gKGEy"
    "LWFuZyk+TWF0aC5QST8xOjA7CiAgICBpZihzLnBjdD4wLjAxKSBwYXRocyArPSBgPHBhdGggZD0iTSR7Y3h9LCR7Y3l9IEwke3gx"
    "fSwke3kxfSBBJHtyfSwke3J9IDAgJHtsYXJnZX0sMSAke3gyfSwke3kyfSBaIiBmaWxsPSIke3MuY29sfSIgc3Ryb2tlPSIjMGIw"
    "ZDEwIiBzdHJva2Utd2lkdGg9IjIiPjwvcGF0aD5gOwogICAgYW5nPWEyOwogIH0pOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlk"
    "KCJwaWVXcmFwIikuaW5uZXJIVE1MID0KICAgIGA8c3ZnIGNsYXNzPSJwaWUiIHdpZHRoPSIke3NpemV9IiBoZWlnaHQ9IiR7c2l6"
    "ZX0iIHZpZXdCb3g9IjAgMCAke3NpemV9ICR7c2l6ZX0iPiR7cGF0aHN9PC9zdmc+YDsKICBjb25zdCBsZWcgPSBkb2N1bWVudC5n"
    "ZXRFbGVtZW50QnlJZCgicGllTGVnZW5kIik7CiAgbGVnLmlubmVySFRNTCA9ICIiOwogIHNsaWNlcy5maWx0ZXIocz0+cy5wY3Q+"
    "MC4wMSkuZm9yRWFjaChzPT57CiAgICBjb25zdCBkPWRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoImRpdiIpOyBkLmNsYXNzTmFtZT0i"
    "bGkiOwogICAgZC5pbm5lckhUTUw9YDxzcGFuIGNsYXNzPSJzdyIgc3R5bGU9ImJhY2tncm91bmQ6JHtzLmNvbH0iPjwvc3Bhbj5g"
    "KwogICAgICBgPHNwYW4+JHtzLmxhYmVsfTogPHN0cm9uZz4ke3MucGN0LnRvRml4ZWQoMSl9JTwvc3Ryb25nPiA8c3BhbiBjbGFz"
    "cz0ibXV0ZWQiPigke2tyKHMudmFsKX0pPC9zcGFuPjwvc3Bhbj5gOwogICAgbGVnLmFwcGVuZENoaWxkKGQpOwogIH0pOwp9Cgpm"
    "dW5jdGlvbiByZW5kZXJHZW5yZXMoKXsKICBjb25zdCBib3ggPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZ2VucmVCb3giKTsK"
    "ICBpZighYm94KSByZXR1cm47CiAgY29uc3QgZ3MgPSBnZW5yZXMoKTsKICBpZighZ3MubGVuZ3RoKXsgYm94LmlubmVySFRNTCA9"
    "ICc8ZGl2IGNsYXNzPSJtdXRlZCIgc3R5bGU9ImZvbnQtc2l6ZToxMnB4Ij5JbmdlbiBzamFuZ2VyLWRhdGEuPC9kaXY+JzsgcmV0"
    "dXJuOyB9CiAgYm94LmlubmVySFRNTCA9IGdzLm1hcChnPT57CiAgICBjb25zdCBjb2wgPSBnLnN0cmVuZ3RoPj02NiA/ICIjNTBj"
    "ODc4IiA6IGcuc3RyZW5ndGg+PTQwID8gIiNmMGE1MDAiIDogIiNlMDUwNTAiOwogICAgY29uc3QgbWVkdmluZCA9IGcudG9wMyA/"
    "ICc8c3BhbiBzdHlsZT0iY29sb3I6IzUwYzg3ODtmb250LXdlaWdodDo3MDA7Zm9udC1zaXplOjExcHgiPiYjOTY1MDsgSSBNRURW"
    "SU5EPC9zcGFuPicgOiAnPHNwYW4gY2xhc3M9Im11dGVkIiBzdHlsZT0iZm9udC1zaXplOjExcHgiPiZuZGFzaDs8L3NwYW4+JzsK"
    "ICAgIHJldHVybiBgPGRpdiBjbGFzcz0iZ2NhcmQiIHN0eWxlPSJib3JkZXItY29sb3I6JHtjb2x9NTAiPgogICAgICA8ZGl2IHN0"
    "eWxlPSJkaXNwbGF5OmZsZXg7anVzdGlmeS1jb250ZW50OnNwYWNlLWJldHdlZW47YWxpZ24taXRlbXM6YmFzZWxpbmUiPgogICAg"
    "ICAgIDxzcGFuIHN0eWxlPSJmb250LXdlaWdodDo3MDAiPiR7Zy5yYW5rfS4gJHtnLmdlbnJlfTwvc3Bhbj4KICAgICAgICAke21l"
    "ZHZpbmR9CiAgICAgIDwvZGl2PgogICAgICA8ZGl2IHN0eWxlPSJmb250LXNpemU6MjJweDtmb250LXdlaWdodDo3MDA7Y29sb3I6"
    "JHtjb2x9O21hcmdpbjoycHggMCI+JHtnLnN0cmVuZ3RofTwvZGl2PgogICAgICA8ZGl2IGNsYXNzPSJtdXRlZCIgc3R5bGU9ImZv"
    "bnQtc2l6ZToxMXB4Ij4ke2cubn0gaW5zdHI6ICR7Zy5tZW1iZXJzLmpvaW4oIiwgIil9PC9kaXY+CiAgICA8L2Rpdj5gOwogIH0p"
    "LmpvaW4oIiIpOwp9CgpmdW5jdGlvbiByZW5kZXJIaXN0KCl7CiAgY29uc3QgYm94PWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJo"
    "aXN0Qm94Iik7CiAgaWYoIVNUQVRFLmhpc3RvcnkubGVuZ3RoKXsgYm94LmlubmVySFRNTD0nPGRpdiBjbGFzcz0ibXV0ZWQiIHN0"
    "eWxlPSJmb250LXNpemU6MTJweCI+SW5nZW4gZW5kcmluZ2VyIGVubiZhcmluZzsuPC9kaXY+JzsgcmV0dXJuOyB9CiAgYm94Lmlu"
    "bmVySFRNTCA9IFNUQVRFLmhpc3RvcnkubWFwKGg9PmA8ZGl2IGNsYXNzPSJoIj48ZGl2IGNsYXNzPSJ0Ij4ke2gudH08L2Rpdj4k"
    "e2gubXNnfTwvZGl2PmApLmpvaW4oIiIpOwp9CgovLyAtLS0gS2FwaXRhbC1oYW5kbGluZ2VyIC0tLQpkb2N1bWVudC5nZXRFbGVt"
    "ZW50QnlJZCgiYXBwbHlDYXAiKS5hZGRFdmVudExpc3RlbmVyKCJjbGljayIsICgpPT57CiAgY29uc3Qgc3RhcnQgPSBwYXJzZUZs"
    "b2F0KGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJzdGFydENhcCIpLnZhbHVlKXx8MDsKICBjb25zdCBhZGQgPSBwYXJzZUZsb2F0"
    "KGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJhZGRDYXAiKS52YWx1ZSl8fDA7CiAgY29uc3Qgb2xkVG90YWwgPSBTVEFURS5jYXNo"
    "ICsgU1RBVEUuaW52ZXN0ZWQ7CiAgaWYoc3RhcnQgIT09IFNUQVRFLnN0YXJ0Q2FwICYmIG9sZFRvdGFsID09PSBTVEFURS5zdGFy"
    "dENhcCl7CiAgICAvLyBmw7hyc3RlIGdhbmcgLyBqdXN0ZXJpbmcgYXYgc3RhcnRrYXBpdGFsCiAgICBTVEFURS5zdGFydENhcCA9"
    "IHN0YXJ0OyBTVEFURS5jYXNoID0gc3RhcnQgLSBTVEFURS5pbnZlc3RlZDsKICAgIGxvZ0hpc3QoYFN0YXJ0a2FwaXRhbCBzYXR0"
    "IHRpbCAke2tyKHN0YXJ0KX1gKTsKICB9CiAgaWYoYWRkPjApewogICAgU1RBVEUuY2FzaCArPSBhZGQ7CiAgICBsb2dIaXN0KGBO"
    "eXR0IGlubnNrdWRkOiAke2tyKGFkZCl9ICh0b3RhbDogJHtrcihTVEFURS5jYXNoK1NUQVRFLmludmVzdGVkKX0pYCk7CiAgICBk"
    "b2N1bWVudC5nZXRFbGVtZW50QnlJZCgiYWRkQ2FwIikudmFsdWU9IiI7CiAgfQogIFNUQVRFLmNhc2hUYXJnZXQgPSBjbGFtcChw"
    "YXJzZUZsb2F0KGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJjYXNoVGFyZ2V0IikudmFsdWUpfHwxNSwwLDEwMCk7CiAgU1RBVEUu"
    "bWF4UG9zID0gY2xhbXAocGFyc2VGbG9hdChkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgibWF4UG9zIikudmFsdWUpfHwyNSw1LDEw"
    "MCk7CiAgc2F2ZVN0YXRlKCk7IHJlbmRlcigpOwp9KTsKCmRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJyZWJhbGFuY2UiKS5hZGRF"
    "dmVudExpc3RlbmVyKCJjbGljayIsICgpPT57CiAgY29uc3QgY2FuZHMgPSBjYW5kaWRhdGVzKCk7CiAgY29uc3QgeyB3ZWlnaHRz"
    "LCBlbGlnSWRzIH0gPSB0YXJnZXRXZWlnaHRzKGNhbmRzKTsKICBsZXQgY2hhbmdlcz1bXTsKICBjYW5kcy5mb3JFYWNoKGM9PnsK"
    "ICAgIGNvbnN0IG93biA9IFNUQVRFLnBvc2l0aW9uc1tjLmlkXXx8MDsKICAgIGNvbnN0IHRndCA9IHdlaWdodHNbYy5pZF18fDA7"
    "CiAgICBjb25zdCByZWMgPSByZWNvbW1lbmRhdGlvbihjLCBvd24sIHRndCwgZWxpZ0lkcy5oYXMoYy5pZCkpOwogICAgaWYocmVj"
    "LmNvZGU9PT0iQlVZIil7IGlmKHRndD4wICYmIG93bjx0Z3QpeyBTVEFURS5wb3NpdGlvbnNbYy5pZF09cGFyc2VGbG9hdCh0Z3Qu"
    "dG9GaXhlZCgxKSk7IGNoYW5nZXMucHVzaChgS0omT3NsYXNoO1AgJHtjLmxhYmVsfSAmcmFycjsgJHt0Z3QudG9GaXhlZCgxKX0l"
    "YCk7fSB9CiAgICBlbHNlIGlmKHJlYy5jb2RlPT09IkFERCIpeyBTVEFURS5wb3NpdGlvbnNbYy5pZF09cGFyc2VGbG9hdCh0Z3Qu"
    "dG9GaXhlZCgxKSk7IGNoYW5nZXMucHVzaChgTEVHRyBUSUwgJHtjLmxhYmVsfSAmcmFycjsgJHt0Z3QudG9GaXhlZCgxKX0lYCk7"
    "IH0KICAgIGVsc2UgaWYocmVjLmNvZGU9PT0iU0NBTEUiKXsgaWYob3duPjApeyBTVEFURS5wb3NpdGlvbnNbYy5pZF09MDsgY2hh"
    "bmdlcy5wdXNoKGBTS0FMRVIgQVYgJHtjLmxhYmVsfSAoZnJhICR7b3dufSUpYCk7fSB9CiAgfSk7CiAgcmVjYWxjSW52ZXN0ZWQo"
    "KTsKICBpZihjaGFuZ2VzLmxlbmd0aCkgbG9nSGlzdCgiT21mb3JkZWxpbmc6ICIgKyBjaGFuZ2VzLmpvaW4oIiwgIikpOwogIGVs"
    "c2UgbG9nSGlzdCgiT21mb3JkZWxpbmc6IGluZ2VuIGVuZHJpbmdlciBhbmJlZmFsdCIpOwogIHNhdmVTdGF0ZSgpOyByZW5kZXIo"
    "KTsKfSk7Cgpkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiY2xlYXJIaXN0IikuYWRkRXZlbnRMaXN0ZW5lcigiY2xpY2siLCAoKT0+"
    "ewogIGlmKGNvbmZpcm0oIlQmb3NsYXNoO21tZSBoZWxlIGVuZHJpbmdzbG9nZ2VuPyIpKXsgU1RBVEUuaGlzdG9yeT1bXTsgc2F2"
    "ZVN0YXRlKCk7IHJlbmRlckhpc3QoKTsgfQp9KTsKCmluaXQoKTsKPC9zY3JpcHQ+CjwvYm9keT4KPC9odG1sPgo="
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
    elif frac < 0.5:    rcol = "#f0a500"; rnote = "Faa hovedinstrumenter slaar gull - rotasjon mot hard assets paagaar."
    else:               rcol = "#50c878"; rnote = "Flertallet slaar gull - risk-on holder foelge."
    detail = (f"Maanedlig - slaar gull: {', '.join(beats_m) or 'ingen'}; taper: {', '.join(loses_m) or 'ingen'}. "
              f"3M - slaar gull: {', '.join(beats_q) or 'ingen'}; taper: {', '.join(loses_q) or 'ingen'}.")
    regime["rotation"] = {
        "label": f"M: {len(beats_m)}/{tot_m} | 3M: {len(beats_q)}/{tot_q} slaar gull",
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
if ten_df is not None and not ten_df.empty:
    if plot_macro_3m(ten_df["close_use"], "10yr yield - 3-maaneders", CHARTS/"macro_10yr.png"):
        regime.setdefault("yields",{})["chart"] = "charts/macro_10yr.png"

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
# ─── SJANGER-STYRKE (Trinn A): relativ styrke per aktivaklasse ──
# Aggregerer hvert instrument sin styrke til sjanger-nivaa. Metode:
# snitt av (maanedlig + kvartal) trend-signal pr medlem. Trend-signal =
# kombinasjon av "slaar gull" (M+Q) og positiv MACD-retning (M+Q),
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
        # vs gull paa M og Q (1.0 hvis slaar gull, 0.5 hvis over MA, 0 ellers)
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

genre_strength = []
for g, iids in genre_members.items():
    genre_strength.append({
        "genre": g, "strength": _genre_strength(iids),
        "members": [summary["assets"][i].get("symbol_label", i) for i in iids],
        "member_ids": iids, "n": len(iids),
    })
# Cash er alltid tilgjengelig som defensiv sjanger (UUP/FXE/CEW representerer den)
genre_strength.sort(key=lambda x: -x["strength"])
# Marker topp 3 som "i medvind"
for rank, gs in enumerate(genre_strength):
    gs["rank"] = rank + 1
    gs["top3"] = rank < 3

index = {"generated_local": NOW.isoformat(), "version": VERSION, "summary": summary,
         "sector_summary": sector_summary, "sector_trend": sector_trend,
         "ratio_charts": ratio_results, "rotation": rotation,
         "trend_ratios": trend_ratios, "regime": regime,
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
