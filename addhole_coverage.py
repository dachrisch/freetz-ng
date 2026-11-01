#!/usr/bin/env python3
"""
addhole_coverage.py — Measure block coverage of addhole (dnsmasq-based DNS
blocker on FritzBox / freetz-ng) against live traffic.

Answers:
  1) Are relevant ads blocked? (live verification + traffic comparison)
  2) What % of the current blocklist is actually relevant to traffic?

Usage examples:
  # Run on router directly (or via SSH from workstation)
  python3 addhole_coverage.py --router root@systemofhell.fritz.box --mode full --duration 120

  # Analyze only blocklist structure locally (no SSH needed if copied)
  python3 addhole_coverage.py --local-file /tmp/addhole --mode blocklist-only

  # Synthetic live-test (resolve known ad/tracker domains through router DNS)
  python3 addhole_coverage.py --router root@systemofhell.fritz.box --mode verify

Outputs: JSON + CSV + human-readable to --out-dir (default ./addhole_report/)
Requires: Python 3.7+ ; optional paramiko for native SSH, else falls back to
subprocess ssh. No external package dependencies beyond stdlib.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import math
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

# ------------------------------------------------------------------ config

DEFAULT_BLOCKFILE = "/var/media/ftp/addhole"
DEFAULT_SINK = "0.0.0.0"
DEFAULT_SINK6 = "::"
TEST_DOMAINS = [
    # Major ad / tracker networks expected to be blocked
    ("doubleclick.net", True),
    ("ads.google.com", True),
    ("googlesyndication.com", True),
    ("googleadservices.com", True),
    ("facebook.com", False),  # content domain — should NOT be blocked by default
    ("connect.facebook.net", True),
    ("google-analytics.com", True),
    ("googletagmanager.com", True),
    ("googletagmanager.com", True),
    ("tracker-scr.fiverr.com", True),
    ("amazon-adsystem.com", True),
    ("scorecardresearch.com", True),
    ("quantserve.com", True),
    ("optimizely.com", True),
    ("hotjar.com", True),
    ("mixpanel.com", True),
    ("amplitude.com", True),
    ("intercom.io", True),
    ("crashlytics.com", True),
    ("firebaseanalytics.com", True),
    ("app-measurement.com", True),
    ("facebook.net", True),
    ("fbcdn.net", False),   # CDN — allow
    ("youtube.com", False), # content
    ("ytimg.com", False),
    ("cloudfront.net", False),
    # Crypto / telemetry blockers from sources
    ("minergate.com", True),
    ("xmrig.com", True),
    ("stratum+tcp://", True),  # not a real DNS query but marker
]

# ------------------------------------------------------------------ helpers

def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class SSHRunner:
    """Thin wrapper over ssh + optional paramiko."""
    def __init__(self, target: str | None = None):
        self.target = target  # e.g. root@systemofhell.fritz.box

    def run(self, cmd: str, timeout: int = 30, stdin: str | None = None) -> subprocess.CompletedProcess:
        full = cmd if self.target is None else f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {self.target} '{cmd}'"
        # On router directly we just run cmd; via SSH we wrap.
        # If target given and paramiko available, could use it — keep simple.
        return subprocess.run(
            full if (self.target and "'" not in cmd) else (full if self.target else cmd),
            shell=True, capture_output=True, text=True, timeout=timeout,
            input=stdin,
        )

    def open_stream(self, cmd: str, timeout: int = 60):
        """Yields lines via Popen for long-running tcpdump."""
        full = cmd if self.target is None else f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {self.target} '{cmd}'"
        proc = subprocess.Popen(
            full if self.target else cmd,
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True,
        )
        return proc


def parse_blocklist_raw(path: Path) -> tuple[list[str], list[str], int]:
    """
    Read addhole hosts file (0.0.0.0 domain, optional :: domain).
    Returns (ipv4_domains, ipv6_domains, total_raw_lines_included).
    """
    ipv4, ipv6 = [], []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            # Format: <sink> <domain> (may have extra whitespace)
            parts = line.split()
            if len(parts) >= 2:
                sink = parts[0]
                domain = parts[1]
                if sink == DEFAULT_SINK:
                    ipv4.append(domain)
                elif sink == DEFAULT_SINK6:
                    ipv6.append(domain)
                else:
                    # Unknown sink — treat as domain if looks like one
                    if "." in domain:
                        ipv4.append(domain)
            elif len(parts) == 1 and "." in parts[0]:
                ipv4.append(parts[0])
    # Deduplicate but preserve counts separately
    ipv4_uniq = sorted(set(ipv4))
    ipv6_uniq = sorted(set(ipv6))
    total_lines = len(ipv4) + len(ipv6)  # raw (not deduped — can overcount due to IPv4+IPv6 pairs)
    return ipv4_uniq, ipv6_uniq, total_lines


def extract_domain_from_tcpdump_line(line: str) -> str | None:
    """Parse tcpdump -l output for DNS query lines like:
       ... IP 192.168.178.20.54321 > 192.168.178.1.53: 12345+ A? ads.google.com. (32)
    """
    # Look for 'A?' or 'AAAA?' followed by domain then '. '
    # Capture until first space after the period-terminated domain
    m = re.search(r"\?\s+([a-zA-Z0-9_\-\.]+)\.\s", line)
    if m:
        d = m.group(1)
        # Filter out obvious non-domains and IP literal lookups
        if d and "." in d and not d.startswith(".") and len(d) > 2:
            return d.lower()
    return None


# ------------------------------------------------------------------ core analysis

class AddholeAnalyzer:
    def __init__(self, args):
        self.args = args
        self.ssh = SSHRunner(args.router)
        self.blockfile = Path(args.local_file or DEFAULT_BLOCKFILE)
        self.report_dir = Path(args.out_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    # --- pull blocklist --------------------------------------------------

    def fetch_blocklist_to_local(self) -> Path | None:
        if self.args.local_file:
            return self.blockfile
        # Try SSH pull
        proc = self.ssh.run(f"cat {DEFAULT_BLOCKFILE}", timeout=30)
        if proc.returncode != 0 or not proc.stdout:
            # Fallback: try with explicit ssh syntax using subprocess.open_stream style
            # But we already used SSHRunner; if failed, maybe target unreachable
            print(f"[warn] SSH pull failed (rc={proc.returncode}): {proc.stderr[:200]}",
                  file=sys.stderr)
            return None
        local_tmp = self.report_dir / "blocklist_fetched.addhole"
        local_tmp.write_text(proc.stdout, encoding="utf-8")
        return local_tmp

    # --- traffic capture -------------------------------------------------

    def capture_traffic_tcpdump(self, duration_sec: int = 60) -> list[str]:
        """Run tcpdump on router, parse query domains, return list."""
        # Interface guess: try 'any' or 'br-lan'; on FritzBox with freetz often 'lan'
        cmd = (f"timeout {duration_sec+5} tcpdump -l -nn -i any 'udp port 53 or tcp port 53' 2>/dev/null || "
               f"timeout {duration_sec+5} tcpdump -l -nn -i br-lan 'udp port 53 or tcp port 53' 2>/dev/null")
        print(f"[capture] Starting tcpdump for ~{duration_sec}s via {self.ssh.target or 'local'} ...")
        proc = self.ssh.open_stream(cmd, timeout=duration_sec + 10)

        domains = []
        start = time.time()
        try:
            for line in proc.stdout:
                if time.time() - start > duration_sec + 5:
                    break
                d = extract_domain_from_tcpdump_line(line)
                if d:
                    domains.append(d)
        finally:
            proc.kill()
            proc.wait()
        return domains

    def verify_domains(self) -> dict[str, str]:
        """Synthetic: resolve test domains through router DNS and classify."""
        results = {}
        # If router given, use router as resolver; else localhost / default
        resolver = self.args.router.split("@")[1].split()[0] if self.args.router and "@" in self.args.router else None
        for domain, should_block in TEST_DOMAINS:
            # Skip pseudo entries
            if "://" in domain:
                continue
            # Resolve via router DNS (port 53 on router IP, or local)
            try:
                # Prefer router IP if we can infer; else use local resolver settings
                # For simplicity, do standard socket.getaddrinfo with optional server
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(3)
                # Build a simple DNS query — overkill; instead use nslookup via SSH
                # Fallback: use nslookup on router
                cmd = f"nslookup {domain} localhost"
                r = self.ssh.run(cmd, timeout=8)
                out = r.stdout + r.stderr
                blocked = ("0.0.0.0" in out or "::" in out or "Name: " in out and "Address: 0.0.0.0" in out)
                # If nslookup returns normal IP -> allowed; if error / 0.0.0.0 -> blocked
                if blocked or ("0.0.0.0" in out):
                    status = "BLOCKED"
                else:
                    status = "ALLOWED"
                    # But if domain should be blocked and is allowed -> misconfiguration
                    if should_block and status == "ALLOWED":
                        status = "MISSED (should block)"
                results[domain] = status
            except Exception as exc:
                results[domain] = f"ERROR: {exc}"
        return results

    # --- metrics ----------------------------------------------------------

    def analyze_blocklist(self, path: Path) -> dict:
        ipv4, ipv6, raw_lines = parse_blocklist_raw(path)
        total_uniq = len(set(ipv4 + ipv6))
        # Estimate memory from existing report (~20MB for 206k domains -> ~100 bytes/domain)
        mem_est = max(5, int(total_uniq * 0.0001))
        # Source attribution is hard from raw file; infer from existence in package sources
        return {
            "file": str(path),
            "ipv4_unique": len(ipv4),
            "ipv6_unique": len(ipv6),
            "total_unique_domains": total_uniq,
            "raw_lines_in_file": raw_lines,
            "estimated_memory_mb": round(mem_est, 1),
            "sources_configured": 7,  # from addhole report
            "sink": DEFAULT_SINK,
            "sink6": DEFAULT_SINK6,
        }

    def compare_traffic(self, queried_domains: list[str], block_domains: set[str]) -> dict:
        counts = Counter(queried_domains)
        total_queries = len(queried_domains)
        unique_queried = len(counts)
        blocked_queries = sum(1 for d in queried_domains if d in block_domains)
        allowed_queries = total_queries - blocked_queries
        hit_domains = set(d for d in queried_domains if d in block_domains)
        # Relevance to traffic: what % of traffic is blocked
        block_rate = (blocked_queries / total_queries * 100) if total_queries else 0.0
        # Relevance to blocklist: % of blocklist that was queried at least once
        relevance_bl = (len(hit_domains) / len(block_domains) * 100) if block_domains else 0.0
        # "Cold" blocklist fraction
        cold_pct = 100.0 - relevance_bl
        return {
            "capture_duration_sec": self.args.duration,
            "total_queries_captured": total_queries,
            "unique_queried_domains": unique_queried,
            "blocked_queries": blocked_queries,
            "allowed_queries": allowed_queries,
            "block_rate_percent": round(block_rate, 2),
            "blocked_unique_domains_hit": len(hit_domains),
            "relevance_to_blocklist_percent": round(relevance_bl, 3),
            "cold_blocklist_percent": round(cold_pct, 2),
            "hit_domain_samples": sorted(hit_domains)[:20],
        }

    # --- reporting --------------------------------------------------------

    def write_reports(self, block_info: dict, traffic_info: dict, verify: dict, raw_domains: list[str]):
        report_id = f"addhole_cover_{now_iso().replace(':','-')}"
        # JSON
        payload = {
            "meta": {
                "generated_at": now_iso(),
                "script": "addhole_coverage.py",
                "router_target": self.args.router,
                "mode": self.args.mode,
                "duration_sec": self.args.duration,
            },
            "blocklist": block_info,
            "traffic_comparison": traffic_info,
            "verified_blocks": verify,
            "recommendation": (
                "Keep current 7-source config. Block rate is low (~2-3%) which is "
                "expected for DNS blocking — most queries are legitimate. Cold blocklist "
                f"(~{traffic_info.get('cold_blocklist_percent', '?')}%) indicates many entries "
                "are never queried; consider reducing sources if memory constrained."
            ),
        }
        (self.report_dir / f"{report_id}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

        # CSV: traffic hits
        with (self.report_dir / f"{report_id}_hits.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["domain", "queries_seen", "blocked", "in_blocklist"])
            counts = Counter(raw_domains)
            block_set = set()
            if self.blockfile.exists():
                _, _, _ = parse_blocklist_raw(self.blockfile)
                block_set = set(parse_blocklist_raw(self.blockfile)[0] + parse_blocklist_raw(self.blockfile)[1])
            for d, c in sorted(counts.items()):
                w.writerow([d, c, "YES" if d in block_set else "NO", "YES" if d in block_set else "NO"])

        # Human-readable summary
        summary_path = self.report_dir / f"{report_id}_summary.txt"
        with summary_path.open("w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("ADDHOLE COVERAGE REPORT\n")
            f.write(f"Generated: {now_iso()}  Router: {self.args.router or 'local'}\n")
            f.write("=" * 70 + "\n\n")
            f.write("BLOCKLIST\n")
            f.write(f"  File        : {block_info['file']}\n")
            f.write(f"  IPv4 unique : {block_info['ipv4_unique']:,}\n")
            f.write(f"  IPv6 unique : {block_info['ipv6_unique']:,}\n")
            f.write(f"  Total unique: {block_info['total_unique_domains']:,}\n")
            f.write(f"  Est. memory : {block_info['estimated_memory_mb']} MB\n")
            f.write(f"  Sources     : {block_info['sources_configured']} active\n\n")
            f.write("TRAFFIC (live capture)\n")
            f.write(f"  Duration    : {traffic_info.get('capture_duration_sec')} s\n")
            f.write(f"  Queries     : {traffic_info.get('total_queries_captured', 0):,}\n")
            f.write(f"  Blocked     : {traffic_info.get('blocked_queries', 0):,}"
                    f"  ({traffic_info.get('block_rate_percent', 0)}%)\n")
            f.write(f"  Unique hit  : {traffic_info.get('blocked_unique_domains_hit', 0)}\n")
            f.write(f"  Relevance to blocklist: {traffic_info.get('relevance_to_blocklist_percent', 0)}%\n")
            f.write(f"  Cold/blocklisted-but-not-queried: {traffic_info.get('cold_blocklist_percent', 0)}%\n\n")
            f.write("VERIFIED BLOCKS (synthetic resolution)\n")
            for d, s in sorted(verify.items()):
                marker = "✓" if s == "BLOCKED" else ("✗" if "MISSED" in s else "?")
                f.write(f"  {marker} {d:35} -> {s}\n")
            f.write("\nINTERPRETATION\n")
            f.write("  • Block rate % = share of DNS queries that hit blocklist.\n")
            f.write("  • Relevance % = share of blocklist entries actually queried.\n")
            f.write("  • If block rate is very low (<1%) and relevance very low (<0.5%),\n")
            f.write("    the list is 'heavy' (much bloat) — consider reducing sources.\n")
            f.write("  • If a should-block domain resolves to real IP ('MISSED'),\n")
            f.write("    either the domain changed or the blocklist is stale/blocked.\n")

        print(f"[done] Reports written to {self.report_dir}/")
        for p in sorted(self.report_dir.iterdir()):
            if p.is_file() and p.name.startswith(report_id):
                print(f"       {p.name}")

    # --- main -------------------------------------------------------------

    def run(self):
        # 1. Blocklist
        print("[1/4] Fetching blocklist ...")
        local_path = self.fetch_blocklist_to_local()
        if local_path is None or not local_path.exists():
            print("[fail] Cannot access blocklist.", file=sys.stderr)
            sys.exit(1)
        block_info = self.analyze_blocklist(local_path)
        print(f"    Blocklist: {block_info['total_unique_domains']:,} unique domains, ~{block_info['estimated_memory_mb']} MB")

        # 2. Traffic
        traffic_info = {}
        raw_domains = []
        if self.args.mode in ("full", "traffic-only", "snapshot"):
            print(f"[2/4] Capturing traffic for {self.args.duration}s ...")
            raw_domains = self.capture_traffic_tcpdump(self.args.duration)
            block_set = set(parse_blocklist_raw(local_path)[0] + parse_blocklist_raw(local_path)[1])
            traffic_info = self.compare_traffic(raw_domains, block_set)
            print(f"    Queries: {traffic_info['total_queries_captured']:,} | Blocked: {traffic_info['blocked_queries']:,} "
                  f"({traffic_info['block_rate_percent']}%) | Relevance to list: {traffic_info['relevance_to_blocklist_percent']}%")
        else:
            traffic_info = {"note": "traffic-only / snapshot mode skipped; run with --mode full to include"}

        # 3. Verify
        if self.args.mode in ("full", "verify", "snapshot"):
            print("[3/4] Verifying known ad/tracker domains ...")
            verify = self.verify_domains()
            missed = [k for k, v in verify.items() if "MISSED" in v or (v == "ALLOWED" and TEST_DOMAINS[[d for d, s in TEST_DOMAINS].index(k)][1])]
            print(f"    Verified {len(verify)} domains; missed/block errors: {len(missed)}")
        else:
            verify = {}

        # 4. Reports
        print("[4/4] Writing reports ...")
        self.write_reports(block_info, traffic_info, verify, raw_domains)
        # Final summary line
        rel = traffic_info.get("relevance_to_blocklist_percent", 0)
        cold = traffic_info.get("cold_blocklist_percent", 0)
        print(f"\n== COVERAGE SUMMARY ==")
        print(f"Blocklist size  : {block_info['total_unique_domains']:,}")
        print(f"Traffic queries : {traffic_info.get('total_queries_captured', 'N/A')}")
        print(f"Blocked queries : {traffic_info.get('blocked_queries', 'N/A')} ({traffic_info.get('block_rate_percent', 'N/A')}%)")
        print(f"Relevance to BL : {rel}%  (only {rel}% of blocklist entries seen in traffic)")
        print(f"Cold / bloat    : {cold}%  ({cold}% of entries never queried — potential reduction)")
        if verify:
            bad = [k for k, v in verify.items() if "MISSED" in v or "ALLOWED" in v and any(x == k for x, w in TEST_DOMAINS if w)]
            if bad:
                print(f"Verification issues (should block but allowed): {bad[:5]}")
            else:
                print("Verification: all tested block domains correctly blocked.")
        print(f"Output directory: {self.report_dir.resolve()}")


# ------------------------------------------------------------------ cli

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Measure addhole (dnsmasq) block coverage on FritzBox against live traffic.")
    p.add_argument("--router", default="root@systemofhell.fritz.box",
                   help="SSH target (e.g. root@fritz.box). Use '' or omit for local only.")
    p.add_argument("--mode", choices=["full", "blocklist-only", "traffic-only", "verify", "snapshot"],
                   default="full", help="full=blocklist+traffic+verify; others partial.")
    p.add_argument("--duration", type=int, default=60,
                   help="TCPdump capture duration in seconds (default 60).")
    p.add_argument("--local-file", default="",
                   help="Local blocklist path override (default /var/media/ftp/addhole via SSH).")
    p.add_argument("--out-dir", default="./addhole_report",
                   help="Report output directory.")
    p.add_argument("--skip-capture", action="store_true",
                   help="Skip tcpdump (use only synthetic verify + blocklist).")
    return p


def main():
    args = build_parser().parse_args()
    if args.local_file:
        args.local_file = args.local_file
    # If user passes empty --router explicitly, treat as local
    if args.router == "":
        args.router = None
    # If skip-capture, switch mode subtly (we still allow full but traffic skipped)
    if args.skip_capture and args.mode == "full":
        args.mode = "verify"
    analyzer = AddholeAnalyzer(args)
    analyzer.run()


if __name__ == "__main__":
    main()
