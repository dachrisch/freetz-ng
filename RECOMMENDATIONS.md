# Fritz!Box 3490 Package Recommendations
**Based on current setup analysis - 2025-11-27**

---

## Current Setup Summary

### ✅ Already Installed (Good Choices)
- **addhole** - DNS ad blocker (206K domains blocked)
- **authorized-keys** - SSH key management
- **bash** - Better shell than busybox ash
- **ca-bundle** - SSL certificate bundle
- **curl** - HTTP/HTTPS downloads with SSL support
- **dehydrated** - Let's Encrypt ACME client (SSL certificates)
- **dnsmasq** - DNS/DHCP server (local DNSSEC validation disabled 2026-11-01; Quad9 validates upstream and the `AD` flag is proxied)
- **dropbear** - SSH server
- **haserl** - CGI for web interface
- **inetd** - Internet super-server
- **juis_check** - Firmware update checker
- **mod** - Core Freetz package
- **modcgi** - Freetz web interface
- **openssl** - SSL/TLS library (v3.0)
- **syslogd** - System logging
- **wget** - File downloader with SSL

### 📊 Available Resources
- **RAM:** 240 MB total, ~38 MB free (~77 MB used, ~125 MB cache)
- **NAND Storage:** 400 MB total, 391 MB free
- **CPU:** MIPS 34Kc @ 331 BogoMIPS
- **Uptime:** 31+ days (very stable)

---

## 🌟 Highly Recommended Additions

### 1. **htop** - Interactive Process Viewer
**Why:** Much better than basic `top` for monitoring your router
- Interactive, colorful display
- See memory/CPU usage per process
- Kill processes easily
- Sort by CPU, memory, etc.

**Memory:** ~2 MB
**Command:** Add to menuconfig → Packages → htop

```bash
# Usage after installation:
htop
```

### 2. **nano** - Simple Text Editor
**Why:** `vi` is installed but nano is much easier for quick edits
- User-friendly (Ctrl+X to exit, shows shortcuts at bottom)
- Syntax highlighting
- Better for config file editing

**Memory:** ~500 KB
**Command:** Add to menuconfig → Packages → nano

```bash
# Usage:
nano /mod/etc/conf/addhole.cfg
```

### 3. **screen** or **tmux** - Terminal Multiplexer
**Why:** Essential for long-running tasks over SSH
- Keep sessions alive if SSH disconnects
- Multiple windows in one connection
- Run background tasks

**Memory:** screen ~300 KB, tmux ~1 MB
**Recommendation:** Use `screen` (lighter)

```bash
# Usage:
screen              # Start new session
# Ctrl+A then D to detach
screen -r           # Reattach to session
```

### 4. **vnstat** - Network Traffic Monitor
**Why:** Track bandwidth usage over time
- See hourly, daily, monthly traffic
- Minimal CPU/memory overhead
- Stored on NAND (persistent)

**Memory:** ~1 MB + database storage
**Note:** Package marked DEPRECATED but still works fine

```bash
# Usage:
vnstat -l           # Live traffic
vnstat -h           # Hourly stats
vnstat -d           # Daily stats
```

---

## 🔧 Useful Additions

### 5. **stunnel** - SSL/TLS Tunnel
**Why:** Secure non-SSL services or create VPN-like tunnels
- Encrypt any TCP connection
- Useful for securing services
- Works with your existing OpenSSL

**Memory:** ~1 MB
**Use case:** Secure HTTP, SMTP, etc.

### 6. **rrdtool** - Data Logging and Graphing
**Why:** Create graphs of router performance over time
- CPU usage graphs
- Memory usage graphs
- Network traffic visualization
- Works with many monitoring tools

**Memory:** ~2-3 MB + database
**Note:** Requires some setup, but powerful

### 7. **wol** - Wake-on-LAN Tool
**Why:** Wake up computers on your network remotely
- Tiny utility
- Very handy for home setups

**Memory:** ~50 KB

```bash
# Usage:
wol -i 192.168.178.255 00:11:22:33:44:55
```

### 8. **smartmontools** - Hard Drive Monitoring
**Why:** If you connect USB drives for storage
- Monitor drive health (SMART data)
- Get warnings before drive fails
- Essential for NAS-like usage

**Memory:** ~1 MB
**Only if:** You use USB storage regularly

### 9. **e2fsprogs** - ext2/ext3/ext4 Tools
**Why:** Better support for Linux filesystems on USB drives
- fsck, tune2fs, etc.
- Essential if using ext4 USB drives

**Memory:** ~3 MB
**Only if:** You use USB storage with ext filesystems

### 10. **usbutils** - USB Device Info
**Why:** Identify USB devices connected to router
- `lsusb` command
- Helpful for troubleshooting

**Memory:** ~500 KB

---

## 🚀 Advanced Options (Consider Carefully)

### 11. **openvpn** - VPN Server/Client
**Why:** Access home network remotely or route traffic through VPN
- Full-featured VPN
- Industry standard

**Memory:** ~5-8 MB
**⚠️ Warning:** Complex setup, moderate CPU usage
**Alternative:** Consider WireGuard instead (lighter)

### 12. **wireguard** - Modern VPN (Lighter than OpenVPN)
**Why:** Faster, lighter VPN alternative
- Less CPU overhead
- Simpler configuration
- Modern cryptography

**Memory:** ~2-3 MB
**Recommendation:** Preferred over OpenVPN for home use
**Note:** Requires kernel module support

### 13. **transmission** - BitTorrent Client
**Why:** Download torrents directly on router
- Web interface
- Uses USB storage for downloads

**Memory:** ~5-10 MB + downloads
**⚠️ Warning:** CPU intensive, consider memory constraints
**Only if:** You have USB storage and need torrent downloads

### 14. **samba** - Windows File Sharing
**Why:** Share USB drives with Windows computers
- Network Attached Storage (NAS) functionality
- Access files from any Windows PC

**Memory:** ~10-15 MB
**⚠️ Warning:** Heavy memory usage for 240 MB device
**Recommendation:** Only if NAS is primary use case

### 15. **lighttpd** or **nginx** - Web Server
**Why:** Host simple websites or web apps
- Lighter than Apache
- Can run web dashboards

**Memory:** lighttpd ~2 MB, nginx ~3 MB
**Use case:** Custom web interfaces or services

### 16. **privoxy** or **tinyproxy** - HTTP Proxy
**Why:** Advanced content filtering beyond DNS
- Filter ads at HTTP level (better than addhole)
- Modify web traffic
- Privacy enhancement

**Memory:** privoxy ~3 MB, tinyproxy ~1 MB
**Note:** Requires client configuration, addhole is simpler

### 17. **tor** - Anonymity Network
**Why:** Anonymous browsing, access .onion sites
- Privacy focused

**Memory:** ~10-15 MB
**⚠️ Warning:** High memory usage, moderate CPU
**Recommendation:** Too heavy for 240 MB device

---

## ❌ NOT Recommended (Memory Constraints)

These packages are interesting but too heavy for 240 MB RAM:

- **apache2** - Too heavy (~20-30 MB), use lighttpd instead
- **mysql** - Database server (~30+ MB), use sqlite if needed
- **asterisk** - PBX system (~40+ MB)
- **bind** - Full DNS server (dnsmasq is sufficient)
- **collectd** - Monitoring (rrdtool is lighter)
- **samba (full)** - If you don't need NAS functionality

---

## 🎯 Recommended Package Priority

Based on your setup and memory constraints:

### Tier 1: Install Now (Low Memory, High Value)
1. ✅ **htop** (2 MB) - Better system monitoring
2. ✅ **nano** (500 KB) - Easier text editing
3. ✅ **screen** (300 KB) - Session management
4. ✅ **wol** (50 KB) - Wake-on-LAN utility

**Total:** ~3 MB
**Impact:** Quality of life improvements, minimal overhead

### Tier 2: Useful Additions (If You Need Them)
5. ⭐ **vnstat** (1 MB) - If you want traffic statistics
6. ⭐ **rrdtool** (3 MB) - If you want performance graphs
7. ⭐ **usbutils** (500 KB) - If you use USB devices

**Total:** ~4.5 MB
**Impact:** Monitoring and diagnostics

### Tier 3: Specific Use Cases
8. 🔐 **wireguard** (3 MB) - Only if you need VPN access
9. 💾 **smartmontools** (1 MB) - Only if using USB storage
10. 💾 **e2fsprogs** (3 MB) - Only if using ext4 USB drives
11. 🌐 **stunnel** (1 MB) - Only if you need SSL tunneling

**Total:** Variable based on needs
**Impact:** Depends on use case

### Tier 4: Advanced (Memory Intensive)
12. ⚠️ **transmission** (10 MB) - Torrent client
13. ⚠️ **samba** (15 MB) - NAS functionality
14. ⚠️ **openvpn** (8 MB) - VPN (use wireguard instead)

**Total:** Heavy memory usage
**Recommendation:** Only one of these at most

---

## 📋 My Specific Recommendations for Your Setup

### Immediate Additions (Safe to install now)
```
Recommended to add:
✅ htop        - Much better than top
✅ nano        - Easier editing than vi
✅ screen      - Keep SSH sessions alive
✅ wol         - Handy network utility
```

**Total Impact:** ~3 MB RAM
**Remaining Free:** ~35 MB (still safe)

### Consider Based on Usage

**If you want network statistics:**
- Add `vnstat` - Track bandwidth usage

**If you access router remotely:**
- Add `wireguard` - Modern VPN (better than OpenVPN)

**If you connect USB drives:**
- Add `smartmontools` - Monitor drive health
- Add `e2fsprogs` - ext4 filesystem support
- Add `usbutils` - Identify USB devices

**If you want performance graphs:**
- Add `rrdtool` - Graph CPU, memory, traffic over time

**If you need file sharing:**
- Add `samba` - BUT this is heavy (15 MB)
- **Warning:** Would use 12% of your RAM alone

---

## 🚫 Things to Avoid

### Don't Install
1. **Third-party addons** from "Digital Elite" - See docs/ADDONS.md
2. **tor** - Too memory intensive (15 MB+ on 240 MB device)
3. **apache2** - Too heavy, use lighttpd if you need web server
4. **bind** - dnsmasq is already excellent
5. **Multiple VPN solutions** - Pick one: wireguard OR openvpn, not both

### Don't Enable
1. **Too many blocklist sources** in addhole - You already have good coverage
2. **Auto-compile toolchain** - Download precompiled (faster, less disk space)

---

## 🔄 Optimization Ideas

### Current Config Optimizations

1. **Consider Disabling DNSSEC** (if you don't use it)
   - Saves ~2-3 MB RAM
   - Only needed if you validate DNS signatures
   - Check: `cat .config | grep DNSSEC`

2. **Reduce Addhole Sources** (if memory gets tight)
   - See `addhole_performance_report.md`
   - Currently 7 sources = 20 MB RAM
   - Could reduce to 4 sources = ~12 MB RAM

3. **Review Busybox Applets**
   - You have bash, wget, curl installed separately
   - Could disable busybox versions to save space
   - Check: `make menuconfig` → Busybox

---

## 📊 Memory Budget Projection

### Current Usage
- System: ~77 MB
- Cache: ~125 MB
- Free: ~38 MB

### After Tier 1 Additions (+3 MB)
- System: ~80 MB
- Cache: ~122 MB
- Free: ~35 MB
**Status:** ✅ Safe

### After Tier 2 Additions (+7.5 MB total)
- System: ~84 MB
- Cache: ~118 MB
- Free: ~31 MB
**Status:** ✅ Still safe, good buffer

### If Adding Tier 3 (Variable)
- WireGuard: ~87 MB used, 28 MB free ✅ OK
- Transmission: ~94 MB used, 21 MB free ⚠️ Tight
- Samba: ~99 MB used, 16 MB free ❌ Too tight

**Recommended Maximum:** ~90 MB total system usage
**Safety Margin:** Keep 30+ MB free for cache/buffers

---

## 🎮 How to Add Packages

### Method 1: Menuconfig (Recommended)
```bash
cd ~/freetz-ng
make menuconfig

# Navigate to:
# → Packages → [Select packages]

# Save and exit, then:
make
tools/push_firmware  # Flash to router
```

### Method 2: Edit .config Directly
```bash
# Add lines like:
echo "FREETZ_PACKAGE_HTOP=y" >> .config
echo "FREETZ_PACKAGE_NANO=y" >> .config
echo "FREETZ_PACKAGE_SCREEN=y" >> .config

make olddefconfig  # Update config
make              # Build
```

### Method 3: Use Existing Config Template
```bash
# Save current working config:
make config-compress
cp .config.compressed myconfig-3490-enhanced

# Later restore:
cp myconfig-3490-enhanced .config
make olddefconfig
make
```

---

## 🔍 Monitoring After Changes

After adding packages, monitor:

```bash
# Check memory usage:
ssh root@systemofhell.fritz.box "free -m"

# Check process memory:
ssh root@systemofhell.fritz.box "ps w"

# Check NAND usage:
ssh root@systemofhell.fritz.box "df -h"

# Check system load:
ssh root@systemofhell.fritz.box "uptime"

# If you installed htop:
ssh root@systemofhell.fritz.box "htop"
```

---

## 💡 Final Recommendations

### Conservative Approach (Recommended)
**Add only Tier 1 packages** - maximum reliability, minimal impact

### Moderate Approach
**Add Tier 1 + Tier 2** - good monitoring, still plenty of headroom

### Aggressive Approach
**Add Tier 1 + Tier 2 + VPN** - Full featured, but watch memory closely

### When to Stop Adding Packages
- If free memory drops below 25 MB
- If system becomes sluggish
- If OOM (Out of Memory) errors appear in logs

---

## 📚 Related Documentation

- Main docs: `CLAUDE.md`
- Addhole analysis: `addhole_performance_report.md`
- Package support: `docs/SUPPORT.md`
- Available packages: `make/pkgs/`

---

**Last Updated:** 2025-11-27
**For:** Fritz!Box 3490 (240 MB RAM, 400 MB NAND)
**Current Freetz:** freetz-ng-24211M-3acc2a51b
