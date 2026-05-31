name: Daily Market Report

on:
  schedule:
    - cron: '50 17 * * *'  # 19:50 Oslo (sommer, UTC+2)
    - cron: '50 18 * * *'  # 19:50 Oslo (vinter, UTC+1)
  workflow_dispatch:
    inputs:
      force:
        description: 'Force full run'
        required: false
        default: 'false'

permissions:
  contents: write

concurrency:
  group: market-daily-report
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install deps
        shell: bash
        run: |
          set -e
          python -m pip install --upgrade pip
          pip install requests pandas matplotlib yfinance beautifulsoup4 feedparser pytz lxml numpy

      - name: Backfill score history (one-time, idempotent)
        if: ${{ hashFiles('scripts/backfill_history.py') != '' }}
        env:
          MPLBACKEND: Agg
          FORCE_RUN: 'true'
        run: |
          # Rekonstruerer ~8 ukers score-historikk fra pris.
          # Idempotent: ekte (ikke-backfilled) snapshots roeres ikke.
          python scripts/backfill_history.py || true

      - name: Run generator
        env:
          MPLBACKEND: Agg
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
          FORCE_RUN: ${{ github.event.inputs.force }}
        shell: bash
        run: |
          set -e
          python scripts/generate_report.py

      - name: Postprocess -> report.json / report.md / report_table.html
        env:
          POSTPROC_SOFT_FAIL: 'true'
        run: python scripts/postprocess_report.py || true

      - name: Export ChatGPT/Claude feed
        env:
          RUN_ID: ${{ github.run_id }}
        run: python scripts/export_for_chatgpt.py

      - name: Fetch NFTRH & Northstar news (optional)
        if: ${{ hashFiles('scripts/fetch_nftrh_northstar.py') != '' }}
        run: python scripts/fetch_nftrh_northstar.py || true

      - name: List generated files
        shell: bash
        run: |
          echo "=== docs/ ===" && ls -l docs/ || true
          echo "=== charts ===" && ls -1 docs/charts/*.png 2>/dev/null | wc -l || true

      - name: Upload artifacts
        if: ${{ always() }}
        uses: actions/upload-artifact@v4
        with:
          name: generator-logs
          path: |
            docs/run_log.txt
            docs/index.json
            docs/index.html
            docs/portfolio_brief.md
            docs/report.json
            docs/report.md
            docs/report_table.html
            docs/chatgpt_feed.json
            docs/charts/**

      - name: Sanity check before deploy
        shell: bash
        run: |
          set -e
          COUNT=$(ls -1 docs/charts/*.png 2>/dev/null | wc -l | tr -d ' ')
          echo "charts count: ${COUNT:-0}"
          if [ "${COUNT:-0}" -lt 8 ]; then
            echo "::warning::For få grafer; hopper over deploy"
            echo "SKIP_DEPLOY=1" >> $GITHUB_ENV
          fi

      - name: Deploy to gh-pages
        if: env.SKIP_DEPLOY != '1'
        uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./docs
          publish_branch: gh-pages
          user_name: github-actions[bot]
          user_email: 41898282+github-actions[bot]@users.noreply.github.com
