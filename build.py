"""拉取 AWAvenue geosite 明文与 v2ray-rules-dat 完整 geosite.dat，产出下列文件：

  - geosite.dat  完整 geosite（保留全部类别与属性），AWAvenue 并入 category-ads-all
  - geoads.dat   仅含单一类别 ads（= 合并后的 category-ads-all），便于用 ext: 单独引用
  - geoads.txt   ads 类别明文，便于审阅
  - SOURCES      本次构建实际取用的上游地址与内容摘要，供审计与复现

上游 v2ray-rules-dat 与 AWAvenue 均为 GPL-3.0，本产物按 GPL-3.0 分发；来源见 README。
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from geosite_pb import Entry, GeoSiteList, NAME_TO_TYPE, TYPE_TO_NAME, dump, load

AWAVENUE_URLS = [
    "https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/main/Filters/AWAvenue-Ads-Rule-Geosite.txt",
    "https://cdn.jsdelivr.net/gh/TG-Twilight/AWAvenue-Ads-Rule@main/Filters/AWAvenue-Ads-Rule-Geosite.txt",
]
GEOSITE_URLS = [
    "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat",
    "https://cdn.jsdelivr.net/gh/Loyalsoldier/v2ray-rules-dat@release/geosite.dat",
    "https://fastly.jsdelivr.net/gh/Loyalsoldier/v2ray-rules-dat@release/geosite.dat",
]
ADS_ALL = "CATEGORY-ADS-ALL"

_KNOWN_PREFIX = {"full", "domain", "keyword", "regexp"}
_MIN_BYTES = 1024  # 下载结果小于此值视为异常，避免发布空表


@dataclass(frozen=True)
class Source:
    """一次成功的上游下载，连同其来源信息，用于写入 SOURCES。"""

    url: str
    data: bytes
    etag: str
    last_modified: str


def fetch_bytes(urls: list[str]) -> Source:
    last_err: Exception | None = None
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "geoads-builder"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
                etag = resp.headers.get("ETag") or ""
                last_modified = resp.headers.get("Last-Modified") or ""
            if len(data) < _MIN_BYTES:
                raise ValueError(f"内容过小({len(data)}B)，疑似异常：{url}")
            return Source(url=url, data=data, etag=etag, last_modified=last_modified)
        except Exception as exc:  # 记录并回退到下一个镜像
            last_err = exc
            print(f"  [warn] {url} 失败：{exc}", file=sys.stderr)
    raise RuntimeError(f"全部地址均失败，最后错误：{last_err}")


def parse_list(text: str) -> list[Entry]:
    entries: list[Entry] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line[0] in "#!":
            continue
        token = line.split()[0]  # 丢弃可能的行内属性/注释
        if ":" in token:
            prefix, value = token.split(":", 1)
            if prefix not in _KNOWN_PREFIX:
                prefix, value = "domain", token
        else:
            prefix, value = "domain", token
        if prefix in ("domain", "full"):
            value = value.lower()
        entries.append((prefix, value))
    return entries


def _ancestor_in(host: str, dset: set[str], *, include_self: bool) -> bool:
    parts = host.split(".")
    start = 0 if include_self else 1
    for i in range(start, len(parts)):
        if ".".join(parts[i:]) in dset:
            return True
    return False


def merge_into_ads_all(lst: GeoSiteList, awavenue: list[Entry]) -> tuple[int, list[Entry]]:
    """把 AWAvenue 条目并入 category-ads-all，跳过已被现有域覆盖或重复者。

    直接在消息上追加，其余类别与全部属性保持不动。
    返回 (新增条数, 合并后 category-ads-all 的 (type,value) 列表)。
    """
    target = next((e for e in lst.entry if e.country_code.upper() == ADS_ALL), None)
    if target is None:
        raise RuntimeError(f"上游 geosite.dat 未找到类别 {ADS_ALL}")

    dom_type = NAME_TO_TYPE["domain"]
    existing_domains = {d.value for d in target.domain if d.type == dom_type}
    existing_pairs = {(d.type, d.value) for d in target.domain}

    added = 0
    for tname, value in awavenue:
        t = NAME_TO_TYPE[tname]
        if tname in ("domain", "full") and _ancestor_in(value, existing_domains, include_self=True):
            continue
        if (t, value) in existing_pairs:
            continue
        d = target.domain.add()
        d.type, d.value = t, value
        existing_pairs.add((t, value))
        if tname == "domain":
            existing_domains.add(value)
        added += 1

    merged = [(TYPE_TO_NAME.get(d.type, str(d.type)), d.value) for d in target.domain]
    return added, merged


def _verify(geosite_bytes: bytes, cats_before: int, attrs_before: int,
            ads_before: int, added: int, ads_dat: bytes, merged: list[Entry]) -> None:
    chk = GeoSiteList()
    chk.ParseFromString(geosite_bytes)
    cats_after = len(chk.entry)
    attrs_after = sum(len(d.attribute) for e in chk.entry for d in e.domain)
    ads_after = len(next(e for e in chk.entry if e.country_code.upper() == ADS_ALL).domain)
    if cats_after != cats_before:
        raise RuntimeError(f"类别数变化：{cats_before} -> {cats_after}")
    if attrs_after != attrs_before:
        raise RuntimeError(f"属性丢失：{attrs_before} -> {attrs_after}")
    if ads_after != ads_before + added:
        raise RuntimeError(f"category-ads-all 计数异常：{ads_after} != {ads_before}+{added}")
    if len(load(ads_dat).get("ADS", [])) != len(merged):
        raise RuntimeError("geoads.dat 回读条数不一致")


def _write_sources(out_dir: Path, sources: dict[str, Source], source_revision: str | None) -> None:
    """写出上游来源记录。

    上游按分支或「最新发布」地址取用，内容随时间变化，故 sha256 才是本次构建所用
    内容的唯一标识；ETag / Last-Modified 仅作辅助参考。
    """
    lines = [
        "# 本次构建实际取用的上游地址与内容摘要，供审计与复现",
        f"generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"source_revision: {source_revision or 'unknown'}",
    ]
    for label, src in sources.items():
        lines += [
            "",
            f"[{label}]",
            f"url: {src.url}",
            f"sha256: {hashlib.sha256(src.data).hexdigest()}",
            f"bytes: {len(src.data)}",
            f"etag: {src.etag}",
            f"last_modified: {src.last_modified}",
        ]
    (out_dir / "SOURCES").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(out_dir: Path, source_revision: str | None = None) -> None:
    print("拉取 AWAvenue geosite 明文 ...")
    awavenue_src = fetch_bytes(AWAVENUE_URLS)
    awavenue = parse_list(awavenue_src.data.decode("utf-8"))
    print(f"  {len(awavenue)} 条")

    print("拉取 v2ray-rules-dat 完整 geosite.dat ...")
    geosite_src = fetch_bytes(GEOSITE_URLS)
    lst = GeoSiteList()
    lst.ParseFromString(geosite_src.data)
    cats_before = len(lst.entry)
    attrs_before = sum(len(d.attribute) for e in lst.entry for d in e.domain)
    ads_before = len(next(e for e in lst.entry if e.country_code.upper() == ADS_ALL).domain)
    print(f"  {cats_before} 个类别，category-ads-all {ads_before} 条，属性 {attrs_before} 个")

    added, merged = merge_into_ads_all(lst, awavenue)
    print(f"AWAvenue 并入 category-ads-all：新增 {added} 条，合并后 {len(merged)} 条")

    out_dir.mkdir(parents=True, exist_ok=True)
    geosite_bytes = lst.SerializeToString()
    (out_dir / "geosite.dat").write_bytes(geosite_bytes)

    ads_dat = dump({"ADS": merged})
    (out_dir / "geoads.dat").write_bytes(ads_dat)
    lines = [(v if t == "domain" else f"{t}:{v}") for t, v in merged]
    # 显式固定换行符：放任 Windows 把 \n 转成 \r\n，会让本地构建的 geoads.txt
    # 与 CI 产物字节不同，SHA256SUMS 无法跨平台比对
    (out_dir / "geoads.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    _verify(geosite_bytes, cats_before, attrs_before, ads_before, added, ads_dat, merged)
    _write_sources(out_dir, {"awa-ads": awavenue_src, "geosite": geosite_src}, source_revision)
    print(f"已写出 geosite.dat / geoads.dat / geoads.txt / SOURCES 到 {out_dir}，校验通过")


def main() -> None:
    ap = argparse.ArgumentParser(description="合并 AWAvenue 与 v2ray-rules-dat 广告规则")
    ap.add_argument("--out-dir", type=Path, default=Path("dist"), help="产物输出目录")
    ap.add_argument("--source-revision", default=None,
                    help="写入 SOURCES 的源码版本，CI 传 github.sha；本地构建可省略")
    args = ap.parse_args()
    # Windows 控制台默认非 UTF-8，重配输出流以正确显示中文进度
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    build(args.out_dir, args.source_revision)


if __name__ == "__main__":
    main()