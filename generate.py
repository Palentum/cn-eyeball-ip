#!/usr/bin/env python3
"""从 CN IPv4 全量列表中剔除 IDC ASN 宣告的 IP 段，生成 CN Eyeball IPv4 列表。

数据源:
  - CN IPv4:  https://metowolf.github.io/iplist/data/special/china.txt
  - ASN 段:   https://iptoasn.com/data/ip2asn-v4.tsv.gz
输入:  idc-asn.txt (空白分隔的 ASN，兼容 "AS" 前缀与 "#" 注释)
输出:  cn-eyeball.txt (每行一个 CIDR)
"""
import gzip
import ipaddress
import sys
import urllib.request

CHINA_URL = "https://metowolf.github.io/iplist/data/special/china.txt"
IP2ASN_URL = "https://iptoasn.com/data/ip2asn-v4.tsv.gz"
ASN_FILE = "idc-asn.txt"
OUT_FILE = "cn-eyeball.txt"
MIN_CN_CIDRS = 3000  # china.txt 有效行低于此值视为上游异常


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "cn-eyeball-ip/1.0"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return resp.read()


def merge(intervals: list) -> list:
    """合并有序化后重叠或相邻的 [start, end] 闭区间。"""
    intervals.sort()
    out = []
    for s, e in intervals:
        if out and s <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def subtract(base: list, holes: list) -> list:
    """从互不重叠的有序 base 区间中挖去 holes 区间。"""
    out = []
    i = 0
    for s, e in base:
        while i < len(holes) and holes[i][1] < s:
            i += 1
        cur = s
        j = i
        while j < len(holes) and holes[j][0] <= e:
            hs, he = holes[j]
            if hs > cur:
                out.append((cur, hs - 1))
            cur = max(cur, he + 1)
            if cur > e:
                break
            j += 1
        if cur <= e:
            out.append((cur, e))
    return out


def load_cn_intervals() -> list:
    intervals = []
    for line in fetch(CHINA_URL).decode().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            net = ipaddress.ip_network(line, strict=False)
        except ValueError:
            continue
        if net.version != 4:
            continue
        intervals.append([int(net.network_address), int(net.broadcast_address)])
    if len(intervals) < MIN_CN_CIDRS:
        sys.exit(f"错误: china.txt 仅解析出 {len(intervals)} 个 CIDR (< {MIN_CN_CIDRS})，疑似上游异常，中止")
    return merge(intervals)


def load_idc_asns() -> set:
    asns = set()
    with open(ASN_FILE) as f:
        for line in f:
            for tok in line.split("#", 1)[0].split():
                if tok.upper().startswith("AS"):
                    tok = tok[2:]
                try:
                    asns.add(int(tok))
                except ValueError:
                    sys.exit(f"错误: idc-asn.txt 中存在无法解析的条目: {tok!r}")
    if not asns:
        sys.exit("错误: idc-asn.txt 为空，中止")
    return asns


def load_idc_intervals(asns: set) -> tuple:
    intervals = []
    matched = set()
    for line in gzip.decompress(fetch(IP2ASN_URL)).decode("utf-8", "replace").splitlines():
        fields = line.split("\t")
        if len(fields) < 3:
            continue
        try:
            asn = int(fields[2])
        except ValueError:
            continue
        if asn not in asns:
            continue
        intervals.append([int(ipaddress.IPv4Address(fields[0])), int(ipaddress.IPv4Address(fields[1]))])
        matched.add(asn)
    if not intervals:
        sys.exit("错误: ip2asn 数据中未命中任何 IDC ASN，疑似上游异常，中止")
    return merge(intervals), matched


def main():
    cn = load_cn_intervals()
    cn_total = sum(e - s + 1 for s, e in cn)
    print(f"CN IPv4: {len(cn)} 段 (合并后), {cn_total} 个地址")

    asns = load_idc_asns()
    idc, matched = load_idc_intervals(asns)
    print(f"IDC ASN: 输入 {len(asns)} 个, 在路由表中命中 {len(matched)} 个, 合并后 {len(idc)} 段")

    result = subtract(cn, idc)
    kept = sum(e - s + 1 for s, e in result)
    print(f"剔除 {cn_total - kept} 个地址, 保留 {kept} 个地址")

    count = 0
    with open(OUT_FILE, "w") as f:
        for s, e in result:
            for net in ipaddress.summarize_address_range(
                ipaddress.IPv4Address(s), ipaddress.IPv4Address(e)
            ):
                f.write(f"{net}\n")
                count += 1
    print(f"已写入 {OUT_FILE}: {count} 个 CIDR")


if __name__ == "__main__":
    main()
