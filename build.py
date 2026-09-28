"""拉取 v2ray-rules-dat 广告明文 + AWAvenue geosite 明文，取并集去重，编译出 geoads.dat。

产物：
  - <out-dir>/geoads.dat  编译后的 geosite 数据（单一类别，默认 geosite:ads）
  - <out-dir>/geoads.txt  并集去重后的明文（GPL 要求可获得来源，同时便于审阅）

上游均为 GPL-3.0，本产物按 GPL-3.0 分发；来源见 README。
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

from geosite_pb import Entry, dump, load

# 每个来源给出主地址与镜像；按顺序尝试，全部失败则报错退出。
SOURCES: dict[str, list[str]] = {
    "v2ray-rules-dat (category-ads-all)": [
        "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release/reject-list.txt",
        "https://cdn.jsdelivr.net/gh/Loyalsoldier/v2ray-rules-dat@release/reject-list.txt",
        "https://fastly.jsdelivr.net/gh/Loyalsoldier/v2ray-rules-dat@release/reject-list.txt",
    ],
    "AWAvenue-Ads-Rule (geosite)": [
        "https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/main/Filters/AWAvenue-Ads-Rule-Geosite.txt",
        "https://cdn.jsdelivr.net/gh/TG-Twilight/AWAvenue-Ads-Rule@main/Filters/AWAvenue-Ads-Rule-Geosite.txt",
    ],
}

_KNOWN_PREFIX = {"full", "domain", "keyword", "regexp"}
_MIN_BYTES = 1024  # 下载结果小于此值视为异常，避免发布空表


def fetch(urls: list[str]) -> str:
    last_err: Exception | None = None
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "geoads-builder"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            if len(data) < _MIN_BYTES:
                raise ValueError(f"内容过小({len(data)}B)，疑似异常：{url}")
            return data.decode("utf-8")
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


def reduce_entries(entries: list[Entry]) -> list[Entry]:
    """按 geosite 匹配语义去冗余：

    - domain 条目若已被更短的父域 domain 覆盖，则删除；
    - full 条目若已被某个 domain 覆盖（相等或为其子域），则删除；
    - keyword / regexp 保持原样（无法安全归并）。
    """
    domains = {v for t, v in entries if t == "domain"}
    kept_domains = {d for d in domains if not _ancestor_in(d, domains, include_self=False)}

    out: list[Entry] = []
    seen: set[Entry] = set()
    for t, v in entries:
        if t == "domain":
            if v not in kept_domains:
                continue
        elif t == "full":
            if _ancestor_in(v, kept_domains, include_self=True):
                continue
        item = (t, v)
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def build(category: str, out_dir: Path) -> None:
    merged: list[Entry] = []
    for name, urls in SOURCES.items():
        print(f"拉取 {name} ...")
        entries = parse_list(fetch(urls))
        print(f"  {len(entries)} 条")
        merged.extend(entries)

    reduced = reduce_entries(merged)
    print(f"并集 {len(merged)} 条 -> 去冗余后 {len(reduced)} 条")

    out_dir.mkdir(parents=True, exist_ok=True)
    code = category.upper()
    dat = dump({code: reduced})
    dat_path = out_dir / "geoads.dat"
    dat_path.write_bytes(dat)

    txt_path = out_dir / "geoads.txt"
    lines = [(v if t == "domain" else f"{t}:{v}") for t, v in reduced]
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 回读校验：解析产物，确认类别与条数一致。
    reparsed = load(dat)
    got = len(reparsed.get(code, []))
    if got != len(reduced):
        raise RuntimeError(f"回读校验失败：写入 {len(reduced)} 条，读回 {got} 条")
    print(f"已写出 {dat_path} ({dat_path.stat().st_size} B) 与 {txt_path}")
    print(f"回读校验通过：geosite:{category.lower()} 共 {got} 条")


def main() -> None:
    ap = argparse.ArgumentParser(description="编译 AWAvenue + geosite 广告并集为 geoads.dat")
    ap.add_argument("--category", default="ads", help="类别名（客户端以 geosite:<category> 引用）")
    ap.add_argument("--out-dir", type=Path, default=Path("dist"), help="产物输出目录")
    args = ap.parse_args()
    # Windows 控制台默认非 UTF-8，重配输出流以正确显示中文进度
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    build(args.category, args.out_dir)


if __name__ == "__main__":
    main()
