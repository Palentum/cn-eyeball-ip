# cn-eyeball-ip

中国大陆眼球网络（家宽 / 移动等真实用户）IPv4 列表：从 CN 全量 IPv4 段中剔除 IDC ASN 宣告的 IP 段后生成。

## 使用

```
https://raw.githubusercontent.com/Palentum/cn-eyeball-ip/main/cn-eyeball.txt
```

每行一个 CIDR。GitHub Actions 每日自动更新（UTC 02:30），有变化时提交回 `main`。

## 数据来源

| 数据 | 来源 |
| --- | --- |
| CN IPv4 全量 | [metowolf/iplist](https://github.com/metowolf/iplist) `data/special/china.txt` |
| ASN → IP 段 | [iptoasn.com](https://iptoasn.com/) `ip2asn-v4.tsv.gz` |
| IDC ASN 列表 | 本仓库 [`idc-asn.txt`](idc-asn.txt) |

## 维护 idc-asn.txt

空白分隔的 ASN 号码，兼容 `AS` 前缀与 `#` 注释。修改后下一次定时任务生效，或手动触发 `daily` workflow 立即重新生成。

## 本地生成

```bash
python3 generate.py
```

仅依赖 Python 3 标准库。
