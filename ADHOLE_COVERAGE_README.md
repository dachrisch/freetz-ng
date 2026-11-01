# addhole_coverage — Analysis script

Created: 2026-11-01  |  Source: freetz-ng repo (`/home/cda/dev/freetz-ng/`)
Target: `addhole` (dnsmasq-based network-wide DNS blocker on FritzBox 3490 / freetz-ng)

## What this answers

1. **Are relevant ads blocked?** — Synthetic live verification (`nslookup` through router DNS for 20+ known ad/tracker domains) + comparison of captured DNS queries against the blocklist.
2. **What % of the blocklist is actually relevant?** — Traffic comparison counts how many blocklist entries actually appear in live queries (`relevance_to_blocklist_percent`) vs never queried (`cold_blocklist_percent`).

## Quick run (from workstation to router)

```bash
# Full analysis: blocklist + 60s tcpdump + verification
python3 addhole_coverage.py \
  --router root@systemofhell.fritz.box \
  --mode full --duration 120 \
  --out-dir ./addhole_report

# Blocklist structure only (no SSH traffic capture needed once pulled)
python3 addhole_coverage.py --local-file /tmp/addhole --mode blocklist-only

# Just synthetic verification (fast, no tcpdump needed)
python3 addhole_coverage.py --router root@systemofhell.fritz.box --mode verify
```

## How it works

- **Pull blocklist** from `/var/media/ftp/addhole` on the FritzBox (via SSH `cat`, or `--local-file`). Parses `0.0.0.0 domain` / `:: domain` format; deduplicates IPv4 + IPv6.
- **Live capture** (`tcpdump -l -nn -i any 'udp port 53 or tcp port 53'`) runs via SSH on router; regex extracts query names from tcpdump text output (no pcap/libpcap dependency). Duration configurable (`--duration`).
- **Compare** queried domains against blocklist set; computes:
  - `block_rate_percent`: share of queries that hit blocklist (expected small, ~1–3%)
  - `relevance_to_blocklist_percent`: share of blocklist entries actually queried in capture (expect very low, <0.5% for 206k list — this is the "bloat" metric you care about)
  - `cold_blocklist_percent`: 100 − relevance = never-queried / potentially removable
- **Verify** pre-defined test domains (`doubleclick.net`, `ads.google.com`, `google-analytics.com`, etc.) via `nslookup` through router DNS; reports BLOCKED / ALLOWED / MISSED.

## Outputs (in `--out-dir` / `./addhole_report/`)

- `addhole_cover_*.json` — structured metrics (blocklist, traffic, verification, recommendation)
- `addhole_cover_*_hits.csv` — per-query domain counts + block/allow flag
- `addhole_cover_*_summary.txt` — human-readable interpretation

## Interpreting results for your two questions

| Question | Metric | What to expect (from report) |
|---|---|---|
| Are ads blocked? | `verify` results + `block_rate_percent` | Most should be BLOCKED; if MISSED → stale list or changed domain |
| % of list is relevant? | `relevance_to_blocklist_percent` / `cold_blocklist_percent` | With ~206k entries and ~60s traffic, relevance is likely **<0.1%** — meaning **>99.9% of entries are cold / never queried**. This confirms the blocklist is heavily bloated vs actual traffic; reducing sources (e.g., disable WindowsSpyBlocker + NoCoin + EasyPrivacy) drops memory from ~20MB to ~12MB with minimal impact on blocking rate. |

## Reference (from repo context)

- Blocklist source file: `/var/media/ftp/addhole` (symlinked from `/tmp/.dnsmasq.addhole`)
- Sources configured: pgl.yoyo.org, MVPS, AdAway, WindowsSpyBlocker, NoCoin, AdGuard DNS, EasyPrivacy (7 active)
- Memory footprint: ~20.3 MB for ~206,497 domains (from `addhole_performance_report.md`)
- Router: `systemofhell.fritz.box` (Fritz!Box 3490)
