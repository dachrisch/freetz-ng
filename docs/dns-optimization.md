# DNS Configuration Optimization

## Issue: Dead DNS Servers from AVM Configuration

### Problem Description

By default, Freetz-NG's dnsmasq package is configured with `DNSMASQ_AVM_DNS='yes'`, which instructs dnsmasq to use DNS servers from AVM's original firmware configuration. These DNS servers are retrieved using:

```sh
echo 'servercfg.dns1' | ar7cfgctl -s
echo 'servercfg.dns2' | ar7cfgctl -s
```

However, these DNS servers can be:
- **Outdated** - from old ISP configurations
- **Unreachable** - from previous VPN or cascaded router setups
- **Invalid** - pointing to non-existent networks

### Example Issue

In one case, AVM firmware configuration contained:
- `servercfg.dns1` = 192.168.180.1
- `servercfg.dns2` = 192.168.180.2

These servers were completely unreachable (100% packet loss), causing:
- DNS query timeouts of 400-500ms per query
- First ping delays of multiple seconds
- Overall slow internet experience

### Root Cause

The dnsmasq configuration generator (`/mod/etc/default.dnsmasq/dnsmasq_conf`) adds these servers when `DNSMASQ_AVM_DNS=yes`:

```sh
if [ "$DNSMASQ_AVM_DNS" = yes ]; then
    echo "server=$(echo 'servercfg.dns1' | ar7cfgctl -s)"
    echo "server=$(echo 'servercfg.dns2' | ar7cfgctl -s)"
fi
```

These dead servers are queried **before** the working upstream servers defined in `DNSMASQ_UPSTREAM`.

## Solution

### Change Default Configuration

Modified `/make/pkgs/dnsmasq/files/root/etc/default.dnsmasq/dnsmasq.cfg`:

```diff
-export DNSMASQ_AVM_DNS='yes'
+export DNSMASQ_AVM_DNS='no'
```

### Rationale

1. **User Control**: Users should explicitly configure their upstream DNS servers via `DNSMASQ_UPSTREAM`
2. **Reliability**: AVM's DNS configuration is often stale or incorrect
3. **Modern Practice**: Explicit DNS configuration is more maintainable than relying on firmware settings
4. **Performance**: Eliminates timeout delays from unreachable servers

### Recommended Configuration

Users should explicitly set their preferred DNS servers in Freetz web UI or via `/tmp/flash/dnsmasq.diff`:

```sh
export DNSMASQ_UPSTREAM='9.9.9.9 2620:fe::fe'        # Quad9
# Or
export DNSMASQ_UPSTREAM='8.8.8.8 8.8.4.4'            # Google DNS
# Or
export DNSMASQ_UPSTREAM='1.1.1.1 1.0.0.1'            # Cloudflare
```

## For Existing Installations

### Check if You're Affected

SSH into your router and check:

```sh
echo 'servercfg.dns1' | ar7cfgctl -s
echo 'servercfg.dns2' | ar7cfgctl -s
```

If these return invalid or unreachable addresses, you're affected.

### Fix for Existing Installations

Add to `/tmp/flash/dnsmasq.diff`:

```sh
export DNSMASQ_AVM_DNS='no'
```

Save configuration to flash storage (required for persistence across reboots):

```sh
modsave flash
```

Then restart dnsmasq:

```sh
/mod/etc/init.d/rc.dnsmasq restart
```

### Verify Fix

Check that `/mod/etc/dnsmasq.conf` no longer contains the problematic servers:

```sh
cat /mod/etc/dnsmasq.conf | grep "^server="
```

Should only show your `DNSMASQ_UPSTREAM` servers.

## Testing

After applying this fix:

1. **DNS Resolution Speed**: Should be <200ms for uncached queries
   ```sh
   time nslookup google.com localhost
   ```

2. **No Timeouts**: Check for DNS timeout errors
   ```sh
   grep -i timeout /var/log/messages
   ```

3. **Working DNS**: Verify DNS queries succeed
   ```sh
   nslookup wikipedia.org localhost
   ```

## Configuration Persistence

### Freetz Configuration Storage

Freetz uses a two-layer configuration system:

1. **Working Directory:** `/tmp/flash/` (in-memory, lost on reboot)
   - User edits configuration here (e.g., `dnsmasq.diff`)
   - Changes take effect immediately when daemon restarts

2. **Flash Storage:** `/var/flash/freetz` (persistent flash device)
   - Character device storing compressed tar of `/tmp/flash/`
   - Survives reboots

### Making Changes Persistent

After editing `/tmp/flash/dnsmasq.diff`, you **must** save to flash:

```bash
modsave flash
```

Without this command, changes will be lost on reboot.

### What `modsave flash` Does

1. Creates tar archive of entire `/tmp/flash/` directory
2. Compresses it (max 32KB)
3. Writes to `/var/flash/freetz`
4. Verifies write succeeded

### On Boot

When router boots:
1. Reads `/var/flash/freetz`
2. Extracts to `/tmp/flash/`
3. Applies configuration from `.diff` files

## Related Files

- **Build-time Default:** `/make/pkgs/dnsmasq/files/root/etc/default.dnsmasq/dnsmasq.cfg`
- **Generator Script:** `/make/pkgs/dnsmasq/files/root/etc/default.dnsmasq/dnsmasq_conf`
- **Runtime Config:** `/mod/etc/conf/dnsmasq.cfg`
- **User Overrides (working):** `/tmp/flash/dnsmasq.diff`
- **User Overrides (persistent):** `/var/flash/freetz` (contains `/tmp/flash/dnsmasq.diff`)
- **Active Config:** `/mod/etc/dnsmasq.conf`

## See Also

- [Dnsmasq Package Documentation](make/dnsmasq.md)
- [Freetz DNS Configuration Guide](https://freetz-ng.github.io/freetz-ng/)
