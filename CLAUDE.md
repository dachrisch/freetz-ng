# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Environment - Fritz!Box 3490 Test Router

**Current Test Device:** Fritz!Box 3490 (systemofhell.fritz.box)

This repository is being used to configure and develop firmware for a Fritz!Box 3490 home router that is accessible for testing.

### Router Specifications

**Hardware:**
- **Model:** Fritz!Box 3490
- **Hostname:** systemofhell.fritz.box
- **CPU:** MIPS 34Kc V5.6 (VR9 SoC)
- **Memory:** 240 MB RAM (MemTotal: 240224 kB)
- **Architecture:** MIPS big-endian
- **Flash Storage:** NAND + NOR (see MTD layout below)

**Current Firmware:**
- **Freetz-NG Version:** freetz-ng-30257M-3d18f7e7ff (flashed 2026-10-18, dnsmasq 2.93). Local DNSSEC validation is **off** as of 2026-11-01 (Quad9 validates upstream; `proxy-dnssec` keeps the `AD` flag) — see `history/2026-11-01_fritzbox-3490-dns-latency-dnssec.md`.
- **AVM Firmware Base:** 140.07.31 (FRITZ!OS 7.31)
- **Kernel:** Linux 3.10.107
- **Hardware Revision:** 212

**MTD Partitions:**
```
mtd0: reserved-kernel    (4 MB)
mtd1: reserved-filesystem (48 MB)
mtd2: kernel             (4 MB)
mtd3: filesystem         (48 MB)
mtd4: config             (8 MB)
mtd5: nand-filesystem    (400 MB) - Available for user data
mtd6: urlader            (256 KB) - Bootloader
mtd7: tffs (1)           (384 KB)
mtd8: tffs (2)           (384 KB)
```

**Installed Freetz Packages:**
- `addhole` - Block ads via DNS
- `authorized-keys` - SSH key management
- `ca-bundle` - CA certificates
- `dnsmasq` - DNS/DHCP server
- `dropbear` - SSH server (listening on port 22)
- `dtc` - Device Tree Compiler
- `haserl` - CGI scripting for web interface
- `inetd` - Internet super-server
- `juis_check` - Firmware update checker
- `mod` - Core Freetz modification package
- `modcgi` - Freetz web interface
- `syslogd` - System logging
- `wget` - File downloader

**Network Services:**
- **SSH:** Port 22 (dropbear) - Access via `ssh root@systemofhell.fritz.box`
- **AVM Web UI:** Port 80 (ctlmgr)
- **Freetz Web UI:** Port 81 (httpd-webcfg) - http://systemofhell.fritz.box:81/
- **DNS:** Port 53 (dnsmasq)
- **Content Filter:** Ports 8181, 8182, 8183, 8184

**Filesystem Usage:**
- Root filesystem: 29.6 MB (100% used - squashfs, read-only)
- Overlay: /var tmpfs (117.3 MB, 2% used)
- User data: /var/media/ftp (400 MB NAND, 2% used)

### Accessing the Test Router

**SSH Access:**
```bash
ssh root@systemofhell.fritz.box
```

**Web Interfaces:**
- Freetz web interface: http://systemofhell.fritz.box:81/
- AVM web interface: http://systemofhell.fritz.box/ (port 80)

**Default Credentials (if not changed):**
- Username: `root` (SSH)
- Username: `admin` (Freetz web UI)
- Password: `freetz` (default for Freetz installations)

### Development Workflow for This Device

When making changes for this Fritz!Box 3490:

1. **Configuration:**
   - Target hardware is already configured in `.config`
   - Model: FRITZ!Box 3490 (VR9 architecture)
   - Base firmware: 07.31

2. **Building:**
   ```bash
   make menuconfig  # Make configuration changes
   make             # Build modified firmware
   ```

3. **Testing:**
   - Flash via: `tools/push_firmware`
   - Or manually via SSH: `scp images/latest.image root@systemofhell.fritz.box:/var/tmp/`
   - Then flash from router: Use AVM recovery or Freetz update mechanism

4. **Debugging:**
   - Check logs: `ssh root@systemofhell.fritz.box 'logread'`
   - Monitor during boot: `ssh root@systemofhell.fritz.box 'dmesg'`
   - Non-interactive SSH has `PATH=/usr/bin:/bin:/var/bin` — call `/sbin/reboot` etc. with full path
   - Check services: `ssh root@systemofhell.fritz.box 'ps'`

5. **Rollback:**
   - Fritz!Box 3490 has dual-boot (reserved-kernel/reserved-filesystem partitions)
   - Can switch between firmware versions via bootloader
   - Bootloader accessible via FTP during boot (adam2/adam2)

### Important Notes for Fritz!Box 3490

- **Generation:** "Gen 1" - NOR flash, single-boot initially, but 3490 has dual-boot
- **Architecture:** MIPS 34Kc (big-endian) requires MIPS toolchain
- **Flash Method:** Use `tools/push_firmware` (supports this model)
- **Memory Constraints:** Only 240 MB RAM - be conservative with package selection
- **NAND Storage:** 400 MB available on mtd5 for persistent user data

### Addhole Ad Blocker Status

The router has addhole (DNS-based ad blocker) actively running:
- **Blocked Domains:** 315,338 (as of 2026-10-21; each domain has an IPv4 `0.0.0.0` and an IPv6 `::` entry, status count is lines/2)
- **Memory Usage:** ~20 MB (8.5% of total RAM)
- **Blocklist Location:** `/var/media/ftp/addhole` (~16 MB)
- **Update Schedule:** Weekly on Monday at 02:01 AM via crond (`MOD_CROND=yes`, enabled 2026-10-21 — before that cron was off and the list never updated)
- **Side effect of updates:** download takes ~13 min, RAM gets tight, and DNS drops briefly while dnsmasq reloads the list
- **Performance Report:** See `addhole_performance_report.md` for detailed analysis

**Quick Commands:**
```bash
# Check addhole status
ssh root@systemofhell.fritz.box "/mod/etc/init.d/rc.addhole status"

# Test domain blocking
ssh root@systemofhell.fritz.box "nslookup ads.google.com localhost"

# Update blocklist manually
ssh root@systemofhell.fritz.box "/mod/etc/init.d/rc.addhole download"
```

### Package Recommendations

For recommendations on additional packages to install based on this hardware:
- **See:** `RECOMMENDATIONS.md` - Comprehensive analysis of 316 available packages
- **Tier 1 (Recommended):** htop, nano, screen, wol (~3 MB total)
- **Tier 2 (Useful):** vnstat, rrdtool, usbutils (~4.5 MB total)
- **Tier 3 (Advanced):** wireguard, transmission, samba (memory intensive)
- **Memory Budget:** Keep free RAM above 30 MB for stability

## Project Overview

Freetz-NG is a firmware modification framework for AVM FRITZ!Box routers and other AVM devices. It allows users to customize their router firmware by adding packages, removing unwanted components, and applying patches to the original AVM firmware images.

**Key Concepts:**
- **Firmware Modification Pipeline**: Download original AVM firmware → Unpack → Modify (add packages/apply patches) → Repack → Flash to device
- **Cross-compilation**: All target code is compiled for MIPS/ARM architectures using custom toolchains
- **Package-based System**: Modular design with 300+ packages (applications/libraries) that can be selectively included
- **Configuration-driven**: Uses Linux kernel's `kconfig` menuconfig system for build configuration

## Build System Architecture

### Main Build Flow

```
make menuconfig    # Configure what to build (.config file)
make              # Full build process:
                  #  1. Build/download toolchain
                  #  2. Build host tools
                  #  3. Download original firmware
                  #  4. Build selected packages/libraries
                  #  5. Run fwmod to modify firmware
```

### Critical Build Commands

**Configuration:**
- `make menuconfig` - Interactive configuration (ncurses TUI)
- `make olddefconfig` - Update .config after git pull or config changes
- `make config-compress` - Create compressed config (.config.compressed)

**Building:**
- `make` - Full build (calls `./fwmod` internally)
- `make firmware` - Build firmware image only
- `make firmware-nocompile` - Repack firmware without recompiling packages
- `make tools` - Build host tools only
- `make toolchain` - Build cross-compilation toolchain

**Package-specific:**
- `make <package>-recompile` - Clean and rebuild a package
- `make <package>-dirclean` - Remove package build directory
- `make <package>-autofix` - Auto-update patches after version bump

**Cleaning:**
- `make clean` - Remove build artifacts, keep toolchain
- `make dirclean` - Remove everything except downloads
- `make distclean` - Complete clean (keeps .config)

**Flashing:**
- `tools/push_firmware` - Flash firmware via bootloader (FTP/EVA)
- `make push_firmware` - Same as above

### Directory Structure

**Core directories:**
- `make/` - Build system makefiles
  - `make/pkgs/` - Package definitions (300+ packages)
  - `make/libs/` - Shared library definitions (100+ libraries)
  - `make/busybox/` - BusyBox configuration
  - `make/kernel/` - Kernel modules
  - `make/toolchain/` - Toolchain build rules
  - `make/host-tools/` - Host tool build definitions
  - `make/include/` - Core makefile includes
- `config/` - Kconfig configuration files
  - `config/ui/` - User-visible menuconfig menus
  - `config/avm/` - AVM firmware variant definitions
- `patches/` - Patches applied to firmware
  - `patches/cond/` - Conditional patches
  - `patches/scripts/` - Patch application scripts
- `tools/` - Host scripts and prebuilt binaries
- `addon/` - User addons (avoid using third-party addons - see docs/ADDONS.md)

**Generated directories (not in git):**
- `build/` - Unpacked/modified firmware
- `source/` - Package source code
- `packages/` - Compiled packages
- `toolchain/` - Cross-compilation toolchains
- `images/` - Output firmware images
- `dl/` - Downloaded files (usually symlinked to ~/.freetz-dl)

### Package System

**Package Structure (make/pkgs/\<package\>/):**
- `Config.in` - Kconfig menu entries (dependencies, options)
- `<package>.mk` - Build rules (download, compile, install)
- `patches/` - Source code patches
- `files/` - Files to include in firmware (configs, init scripts, web UI)

**Package .mk File Variables:**
- `$(PKG)_VERSION` - Package version
- `$(PKG)_SOURCE` - Source tarball filename
- `$(PKG)_HASH` - SHA256 checksum
- `$(PKG)_SITE` - Download URL(s)
- `$(PKG)_DEPENDS_ON` - Build dependencies
- `$(PKG)_STARTLEVEL` - Init script priority (10-99)

**Common Package Patterns:**
```make
$(call PKG_INIT_BIN, <version>)           # Binary package
$(call PKG_INIT_LIB, <version>)           # Library package
$(PKG)_CONFIGURE_OPTIONS += --enable-foo  # Configure flags
$(PKG)_MAKE_OPTIONS += TARGET=bar         # Make flags
```

## Firmware Modification Process

The `fwmod` script (in repository root) orchestrates firmware modification:

**Main Actions:**
- `-u` - Unpack firmware image
- `-m` - Modify unpacked image (add packages, apply patches)
- `-p` - Pack modified image
- `-a` - All of the above (default when running `make`)

**fwmod Workflow:**
1. Download original firmware from AVM (or use local file)
2. Unpack firmware image (extract kernel, filesystem)
3. Apply patches to filesystem
4. Install selected packages to filesystem
5. Remove excluded AVM components
6. Repack filesystem (squashfs) and kernel
7. Create flashable image with proper headers/signatures

## Important Development Notes

### Prerequisites

Install required packages first:
```bash
tools/prerequisites install
```

Check prerequisites are met:
```bash
tools/prerequisites check
```

### Environment Requirements

- **Must NOT run as root** - Build system enforces this
- **umask must be 0022** - Build system checks this
- **x86_64 Linux required** - Precompiled toolchains only work on x86_64
- **AVX2 CPU required** - For precompiled toolchains (or build toolchain yourself)
- Filesystem must support Unix permissions (not FAT/NTFS)

### Configuration Files

- `.config` - Main build configuration (generated by menuconfig)
- `.config.compressed` - Minimal config (only non-default values)
- `myfreetz.config` - Example/backup config in repository root

### Patching Workflow

When modifying package source code:
1. Make changes to source in `source/<package>-<version>/`
2. Test compilation: `make <package>-recompile`
3. Generate patches: `make <package>-autofix`
4. Patches are saved to `make/pkgs/<package>/patches/`

### Version Bumps (See docs/SUPPORT.md)

To update a package version:
1. Update `docs/CHANGELOG.md`
2. Update version in `make/pkgs/<package>/Config.in`
3. Update version in `make/pkgs/<package>/<package>.mk`
4. Update hash in `make/pkgs/<package>/<package>.mk`
5. Update `make/pkgs/<package>/external.*` if filename includes version
6. Run `make <package>-autofix` to update patches
7. Test: `make <package>-recompile`

### Toolchain System

Freetz uses two separate toolchains:
- **Kernel toolchain** - Compiles kernel and kernel modules (often older GCC)
- **Target toolchain** - Compiles userspace packages (newer GCC, uClibc)

Toolchain options (in menuconfig):
- `FREETZ_BUILD_TOOLCHAIN=y` - Build from source (slow, works on any x64 CPU)
- `FREETZ_DOWNLOAD_TOOLCHAIN=y` - Download prebuilt (fast, requires x86_64 + AVX2)

### Web Interface

Modified firmware includes a web interface on port 81:
- Default URL: http://fritz.box:81/
- Default credentials: admin/freetz
- Configured via `make/pkgs/mod/` package

## Common Pitfalls

1. **Don't use third-party addons** - See docs/ADDONS.md for why
2. **Always run `make olddefconfig`** after git pull
3. **Parallel make is automatic** - Don't use `make -j` manually
4. **Source downloads** - First build downloads a lot, use `make sources` to pre-download
5. **Disk space** - Full build needs 10-20 GB
6. **Build time** - Initial toolchain build: 30-60 min; subsequent builds: 5-15 min

## Testing

- `make test` - Currently no tests defined
- Manual testing required: Flash to device and verify functionality

## Documentation

- `docs/` - Documentation in markdown (served via mkdocs at freetz-ng.github.io)
- `docs/wiki/` - Wiki pages (many are outdated - see docs/SUPPORT.md)
- `README.md` - Quick start guide

## Key Scripts and Tools

**Build System:**
- `fwmod` - Main firmware modification script
- `fmake` - Make wrapper (legacy)
- `tools/freetz_download` - Download helper with mirror support
- `tools/freetz_patch` - Patch application helper
- `tools/genin` - Generates Config.in.generated files

**Flashing:**
- `tools/push_firmware` - Universal firmware flashing tool (works with all device generations)
- `tools/recover-eva` - Recovery via FTP bootloader

**Image Tools:**
- `tools/fwdu` - Firmware unpacker
- `tools/mksquashfs*` - Create squashfs filesystems (multiple versions for different AVM firmware)
- `tools/unsquashfs*` - Extract squashfs filesystems

**Development:**
- `tools/prerequisites` - Check/install build prerequisites
- `tools/freetz_revision` - Git revision info

## Git Workflow

Standard git workflow applies:
- Main branch: `master`
- Fork → feature branch → pull request
- Commit messages should be descriptive
- See docs/SUPPORT.md for detailed pull request instructions
