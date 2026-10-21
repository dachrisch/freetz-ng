# Slow downloads on the 3490 — root cause was the 2.4 GHz link, fixed by moving the client to 5 GHz — 2026-10-22

**Target:** Fritz!Box 3490 `systemofhell.fritz.box` (Freetz-NG `freetz-ng-30257M-3d18f7e7ff`, AVM 140.07.31, VR9/MIPS 34Kc)
**Affected client:** laptop `wlp0s20f3` (Intel Wi-Fi 6 AX201, `iwlwifi`)

## Problem

Downloads from the laptop capped at **27–154 kB/s (0.2–1.2 Mbit/s)**, independent of the
source, with RTT to the gateway swinging between 1.6 ms and 600 ms. The suspicion was the
router (Freetz + addhole + dnsmasq) or the DSL line.

## Diagnosis

Everything on the router tested clean; the bottleneck was the Wi-Fi link itself.

| Layer | Measurement | Verdict |
|---|---|---|
| Router CPU/RAM | `load average 0.12 0.16 0.20`, 48 MB free of 240 MB | idle, not the cause |
| WAN line | 50 MB `wget` from Cloudflare **on the router** → 10 s ≈ **40 Mbit/s** | line is fine |
| 2.4 GHz link | ch 6, **20 MHz**, -68…-71 dBm, PHY **MCS2–4 (19–39 Mbit/s)** | poor |
| Cell load (AP BSS Load IE) | **162/255 = 63 % channel utilisation**, 12 stations, legacy 1/2/5.5/11 Mbit/s rates advertised | congested |
| Latency | gateway: 1.6 ms best, 90–600 ms typical, occasional 100 % loss bursts; symmetric (router→laptop 29 ms best / 300 ms avg) | link, not router |
| Throughput | 27–154 kB/s; ~**15.3 MB of air traffic for 5.2 MB payload (~3× overhead)** | retry-bound |
| DNS | 200–400 ms via router **and** 300–380 ms straight to 1.1.1.1 | symptom of link latency, not addhole/dnsmasq |
| Laptop shaping/VPN | `tc qdisc` = `noqueue`, no mangle rules, no VPN | not the cause |
| Laptop power save | forced `power_save off` → RTT got **worse** (458–856 ms) | not the cause (reverted to `on`) |

The 5 GHz radio was already up (`systemofhell`, ch 52, 80 MHz, 802.11ac) but only
**-83 dBm** at the laptop, and AVM band steering never moved the client there.

## Solution

Client-side only — no firmware, package or router config change. A 5 GHz-pinned
NetworkManager profile was added and given priority, with the 2.4 GHz profile kept as a
deliberate fallback:

```bash
# same SSID + PSK, 5 GHz only, preferred
nmcli connection add type wifi con-name systemofhell-5ghz ssid systemofhell ifname wlp0s20f3
nmcli connection modify systemofhell-5ghz 802-11-wireless.band a \
    802-11-wireless-security.key-mgmt wpa-psk 802-11-wireless-security.psk '<psk>' \
    connection.autoconnect yes connection.autoconnect-priority 100

# existing profile demoted and pinned to 2.4 GHz so it can never win over 5 GHz
nmcli connection modify systemofhell 802-11-wireless.band bg
nmcli connection modify systemofhell connection.autoconnect-priority 50
```

## Verification

- 5 GHz association: ch 52, **80 MHz**, -72…-80 dBm, **VHT-MCS 3–5**, 117–234 Mbit/s PHY.
- Gateway RTT **1.0–2.6 ms** (was 90–600 ms); 1.1.1.1 **6–9 ms** (was 300–2700 ms, 20 % loss).
- `curl` 20 MB from Cloudflare: **8.6 MB/s ≈ 68 Mbit/s** (was <0.15 MB/s).
- `speedtest-cli` (Hivane, 684 km): **35.89 Mbit/s down / 32.35 Mbit/s up**.
- Router-side WAN re-test: 50 MB in 10 s ≈ **40 Mbit/s** → the client now runs at line rate,
  the Wi-Fi is no longer the bottleneck.
- Failover: bringing `systemofhell-5ghz` down reconnects to a 5 GHz SSID of the same box
  (`systemofheaven`, prio 0) and restoring the profile returns to `systemofhell-5ghz`.

## Impact

- No change to the firmware image, `dl/`, `myfreetz.config` or any Freetz package.
- No router reboot, no WLAN settings touched; only the laptop's NetworkManager profiles.
- 2.4 GHz remains available for IoT/legacy clients that cannot use 5 GHz.

## Rollback

```bash
sudo nmcli connection delete systemofhell-5ghz
sudo nmcli connection modify systemofhell 802-11-wireless.band ''
sudo nmcli connection modify systemofhell connection.autoconnect-priority 0
```

## Next Steps

- 5 GHz sits at -72…-80 dBm at the laptop's position — usable, but near the edge. If it
  degrades, reposition the box/laptop or add an AVM 5 GHz mesh repeater.
- 5 GHz runs on **DFS channel 52**; radar detection causes a channel hop for ~1 min.
  Channels 36–48 (non-DFS) avoid that.
- The 2.4 GHz cell is still 63 % airtime-busy with legacy rates enabled — set the WLAN
  standard to **802.11n only** and move to channel **13** to fix the fallback/IoT path.
- AVM band steering did not move an 802.11ac client with a 12 dB weaker 5 GHz signal;
  per-band SSIDs or a client-side preference (as done here) remain necessary.
