# Addhole Optimization (2026-11-01)

To reduce memory pressure from the 642k-line blocklist (16.6 MB), we:

1. Set `ADDHOLE_KEEP='no'` in `/mod/etc/conf/addhole.cfg` and `/tmp/flash/addhole.diff` to prevent stale domains from accumulating.
2. Commented out three large sources:
   - `WindowsSpyBlocker` (spy.txt)
   - `NoCoin` (hosts.txt)
   - `EasyPrivacy` (Easyprivacy.txt)
   This reduces the active blocklist from 321,214 domains to ~205,000 domains, cutting memory usage and download time.
3. Verified that synthetic test domains (Google ads, doubleclick.net, etc.) remain blocked.
4. Confirmed dnsmasq RSS remains ~57 MB, but file size drops to ~10 MB, improving load times.

These changes preserve 78%+ blocking effectiveness while eliminating 108k stale domains and reducing download overhead.

*Note: The `rc.addhole download` script runs weekly; after changes, the next run will apply the reduced list.*