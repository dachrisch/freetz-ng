# Slow internet on the 3490 — local DNSSEC validation + 150-entry cache; fixed by delegating validation to Quad9 — 2026-11-01

**Target:** Fritz!Box 3490 `systemofhell.fritz.box` (Freetz-NG `freetz-ng-30257M-3d18f7e7ff`, AVM 140.07.31, dnsmasq 2.93, VR9/MIPS 34Kc)
**Symptom:** "internet is very slow", suspected DNS.

## Problem

Page loads and fresh connections felt slow and occasionally stalled for several
seconds, while bulk transfers were fine. DNS through the router was the suspect.

## Diagnosis

The WAN line, Wi-Fi link and upstream resolvers were healthy; the cost was
inside dnsmasq on the router.

| Layer | Measurement | Verdict |
|---|---|---|
| WAN line | laptop 20 MB download in 4.45 s ≈ **36 Mbit/s**, ping 1.1.1.1 7–8 ms | fine |
| Router → WAN | ping 1.1.1.1 **6 ms**, 20 MB wget 15 s (TLS/CPU-bound) | fine |
| Wi-Fi | 5 GHz ch 116 (DFS), **-76 dBm**, VHT-MCS2, 97/176 Mbit/s | usable, marginal |
| DNS via router, 10 cold names | **1287 ms total** (avg 129 ms, max 211 ms) | slow |
| DNS direct to 9.9.9.9, same count | **175 ms total** (avg 17.5 ms) | baseline |
| DNS cache hit via router | 11–45 ms | okay |
| dnsmasq CPU during a lookup burst | **45–49 % of the 2-core box = one full core**, loadavg **4.5**, free RAM briefly **3 MB** | CPU-bound |
| IPv6 upstream `2620:fe::fe` | reachable, 12–14 ms | not a factor |
| addhole list | **642,428 lines / 16.6 MB**, dnsmasq RSS **57.8 MB (24 % RAM)** | memory hog, not latency cause |
| syslog | no `/dev/log`, no syslogd | `log-queries` did nothing useful |

Live dnsmasq config (`/tmp/flash/dnsmasq.diff`):

```sh
export DNSMASQ_DNSSEC='yes'
export DNSMASQ_LOG_QUERIES='yes'
export DNSMASQ_UPSTREAM='9.9.9.9 2620:fe::fe'
```

`/mod/etc/dnsmasq.conf` had `dnssec`, `log-queries` and `addn-hosts`, but **no
`cache-size`** — so dnsmasq used its default of **150 entries**.

## Root cause

Local DNSSEC validation makes dnsmasq perform 6–12 extra upstream round trips
per cold name (`DS` + `DNSKEY` at every label) plus ECDSA/RSA verification on a
331 BogoMIPS MIPS CPU. With a 150-entry cache almost nothing stays warm, so a
normal page load (dozens of domains) triggers that cost repeatedly.

Quad9 already validates DNSSEC and sets the `AD` flag, so the local validation
was largely redundant work on the weakest CPU in the path.

## Solution

Config only — no firmware rebuild, no reboot:

1. `/tmp/flash/dnsmasq.diff`:
   ```sh
   export DNSMASQ_DNSSEC='no'
   export DNSMASQ_LOG_QUERIES='no'
   # unchanged: DNSMASQ_UPSTREAM='9.9.9.9 2620:fe::fe'
   ```
2. `/tmp/flash/dnsmasq/dnsmasq.extra` (appended verbatim to
   `/mod/etc/dnsmasq.conf` by `modlib_config`):
   ```
   cache-size=2000
   proxy-dnssec
   ```
   `proxy-dnssec` passes the upstream `AD` bit through, so clients can still see
   that the answer was validated.
3. Same two values set in `/mod/etc/conf/dnsmasq.cfg` so a save from the Freetz
   web UI cannot silently re-enable them.
4. `/mod/etc/init.d/rc.dnsmasq restart` and `modsave flash`.

Backups on NAND:

- `/var/media/ftp/dnsmasq.diff.2026-11-01.bak`
- `/var/media/ftp/dnsmasq.cfg.2026-11-01.bak`

## Verification

| Measurement | Before | After |
|---|---|---|
| 10 cold names via router | 1287 ms (avg 129) | **227 ms (avg 23, max 39)** |
| 20 cold names via router vs direct Quad9 | — | **587 ms vs 470 ms** |
| Cache hit | 11–45 ms | **3 ms** |
| Page load DNS (spiegel/github/google) | 92–212 ms | **1–16 ms** |
| Page load total | — | 0.17–0.37 s |
| dnsmasq during burst | one core pinned, loadavg 4.5 | **no system-load entries, loadavg < 0.9** |
| Free RAM | briefly 3 MB | 66 MB |

Security is unchanged in practice: `dig dnssec-failed.org` still returns
`SERVFAIL` (Quad9 validates) and signed answers still carry `ad`
(`proxy-dnssec`).

Persistence checked by reading the config back from the flash device:
`tar -xOf /var/flash/freetz flash/dnsmasq.diff` and
`.../flash/dnsmasq/dnsmasq.extra` contain the new values; `modsave flash` is
idempotent; `modconf load dnsmasq` (the boot path) yields `DNSSEC='no'`,
`LOG_QUERIES='no'`.

## Impact

- No firmware image, package or Wi-Fi change; no reboot.
- Config lives in TFFS (`/var/flash/freetz`) and survives reboots.
- A firmware reflash rebuilds `/tmp/flash` and will lose the override (expected).

## Rollback

```sh
cp /var/media/ftp/dnsmasq.diff.2026-11-01.bak /tmp/flash/dnsmasq.diff
cp /var/media/ftp/dnsmasq.cfg.2026-11-01.bak /mod/etc/conf/dnsmasq.cfg
rm -f /tmp/flash/dnsmasq/dnsmasq.extra
/mod/etc/init.d/rc.dnsmasq restart
modsave flash
```

## Next Steps

- **addhole:** the list grew from ~206k domains / 5.5 MB (Nov 2025) to
  **642k lines / 16.6 MB**, costing ~58 MB RSS (24 % of RAM). Prune sources or
  drop the largest lists if memory pressure returns.
- **Wi-Fi:** 5 GHz sits at -76 dBm on DFS ch 116 (VHT-MCS2). Moving to a
  non-DFS 36–48 channel or repositioning would improve the fallback path.
- **Build level:** consider emitting a sane `cache-size` default (e.g. 1000) in
  `make/pkgs/dnsmasq/files/root/etc/default.dnsmasq/dnsmasq_conf` for future
  images.
- `myfreetz.config` in the repo is a stale July-2024 copy (dnsmasq marked off);
  `.config` is the real build config.
