# geoads

将 [Xray-rules-dat](https://github.com/XTLS/Xray-rules-dat) 的广告域名（`category-ads-all`）与 [AWAvenue-Ads-Rule](https://github.com/TG-Twilight/AWAvenue-Ads-Rule)（以国内 App 广告/SDK 为主）合并，通过 GitHub Actions 每天北京时间 11:30 自动构建

上游[构建计划](https://github.com/XTLS/Xray-rules-dat/blob/main/.github/workflows/release.yml)为每天 18:00 UTC（北京时间次日 02:00），实际发布可能因 GitHub Actions 排队延迟数小时。本项目计划在每天 03:30 UTC（北京时间 11:30）同步，较上游计划时间延后 9 小时 30 分钟；实际执行时间以 Actions 调度为准。

产出两份数据文件：

- **`geoads.dat`** —— 仅含单一类别 `ads`（合并后的广告并集），体积小
- **`geosite.dat`** —— 完整的 Xray-rules-dat geosite（全部类别、属性原样保留），仅把 AWAvenue 并入其 `category-ads-all`

## 下载

Release 直链：

- geoads.dat：`https://github.com/BELUGA114/adsdat/releases/latest/download/geoads.dat`
- geosite.dat：`https://github.com/BELUGA114/adsdat/releases/latest/download/geosite.dat`

jsdelivr CDN：

- geoads.dat：`https://cdn.jsdelivr.net/gh/BELUGA114/adsdat@release/geoads.dat`
- geosite.dat：`https://cdn.jsdelivr.net/gh/BELUGA114/adsdat@release/geosite.dat`

另发布压缩附件 `geoads.dat.gz` / `geosite.dat.gz`、明文 `geoads.txt`、校验和 `SHA256SUMS` 与来源记录 `SOURCES`

> `release` 分支只同步 `geosite.dat` / `geoads.dat` / `SHA256SUMS` / `SOURCES` 供 jsDelivr 取用；
> 压缩包和 `geoads.txt` 只在 Release 附件中提供，其中 `geoads.txt` 仅供审阅

## 溯源与校验

每次构建都会为三份数据文件及两份压缩包生成 [SLSA 构建溯源证明](https://docs.github.com/actions/security-for-github-actions/using-artifact-attestations)（Sigstore 签名），可用 GitHub CLI 核验产物确实来自本仓库该次工作流：

```bash
gh attestation verify geosite.dat --repo BELUGA114/adsdat
```

- **`SHA256SUMS`** —— 三份数据文件、两份压缩包及 `SOURCES` 的校验和
- **`SOURCES`** —— 本次构建实际取用的上游地址及其内容摘要（`sha256` / ETag / Last-Modified），以及产出该版本的源码提交。上游按分支或「最新发布」地址取用、内容随时间变化，故 `sha256` 才是本次所用内容的唯一标识

> `SHA256SUMS` 与产物同源发布，只能防传输损坏；要确认产物来源可信，请用上面的溯源证明核验

## 使用

**geoads.dat：**

- Xray / v2ray：路由规则写 `ext:geoads.dat:ads`
- mihomo（Clash.Meta）：把 geosite 库指向本文件，规则写 `GEOSITE,ads,REJECT`

**geosite.dat：**

- 用本 `geosite.dat` 覆盖资源目录里的官方同名文件，照常写 `geosite:category-ads-all`，其它类别不受影响


## 本地构建

依赖使用 [uv](https://docs.astral.sh/uv/) 管理：

```bash
uv sync
uv run python build.py --out-dir dist
```

产物写入 `dist/`，构建末尾回读校验类别数与属性数不变、`category-ads-all` = 原值 + 新增、`geoads.dat` 条数一致

## 构建逻辑

1. 拉取 AWAvenue geosite 明文（支持 jsDelivr 镜像回退）与 Xray-rules-dat 最新 Release 的完整 [`geosite.dat`](https://github.com/XTLS/Xray-rules-dat/releases/latest/download/geosite.dat)（下载异常或过小即报错）
2. 解析完整 geosite（运行期构建的 protobuf schema，含 `Domain.attribute`，避免往返丢属性），把 AWAvenue 条目并入 `category-ads-all`，跳过已被现有父域覆盖或重复者，其余类别与全部属性原样不动
3. 序列化出完整 `geosite.dat`；同时把合并后的广告类别单独导出为 `geoads.dat`（类别名 `ads`）与明文 `geoads.txt`，全程无需 protoc / Go 工具链

## 数据来源与许可

本项目产物为上述两个上游的派生作品，二者均为 **GPL-3.0**，故本仓库同样以 **GPL-3.0** 分发（见 [LICENSE](./LICENSE)）

- [XTLS/Xray-rules-dat](https://github.com/XTLS/Xray-rules-dat)（GPL-3.0）。其 GeoSite 基于 [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community)
- [TG-Twilight/AWAvenue-Ads-Rule](https://github.com/TG-Twilight/AWAvenue-Ads-Rule)（GPL-3.0）

**本项目仅供个人、非商业使用**，并保留上述全部来源署名。这些说明不构成法律意见
