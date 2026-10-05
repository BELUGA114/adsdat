# geoads

将 [v2ray-rules-dat](https://github.com/Loyalsoldier/v2ray-rules-dat) 的广告域名（`category-ads-all`，以国际广告表为主）与 [AWAvenue-Ads-Rule](https://github.com/TG-Twilight/AWAvenue-Ads-Rule)（以国内 App 广告/SDK 为主）合并，通过 GitHub Actions 每 7 天自动构建

产出两份数据文件：

- **`geoads.dat`** —— 仅含单一类别 `ads`（合并后的广告并集），体积小
- **`geosite.dat`** —— 完整的 v2ray-rules-dat geosite（全部类别、属性原样保留），仅把 AWAvenue 并入其 `category-ads-all`

## 下载

Release 直链：

- geoads.dat：`https://github.com/BELUGA114/adsdat/releases/latest/download/geoads.dat`
- geosite.dat：`https://github.com/BELUGA114/adsdat/releases/latest/download/geosite.dat`

jsdelivr CDN：

- geoads.dat：`https://cdn.jsdelivr.net/gh/BELUGA114/adsdat@release/geoads.dat`
- geosite.dat：`https://cdn.jsdelivr.net/gh/BELUGA114/adsdat@release/geosite.dat`

另发布明文 `geoads.txt` 与校验和 `SHA256SUMS`

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

1. 拉取 AWAvenue geosite 明文与 v2ray-rules-dat 完整 `geosite.dat`（有 jsdelivr / fastly 镜像回退，下载异常或过小即报错）
2. 解析完整 geosite（运行期构建的 protobuf schema，含 `Domain.attribute`，避免往返丢属性），把 AWAvenue 条目并入 `category-ads-all`，跳过已被现有父域覆盖或重复者，其余类别与全部属性原样不动
3. 序列化出完整 `geosite.dat`；同时把合并后的广告类别单独导出为 `geoads.dat`（类别名 `ads`）与明文 `geoads.txt`，全程无需 protoc / Go 工具链

## 数据来源与许可

本项目产物为上述两个上游的派生作品，二者均为 **GPL-3.0**，故本仓库同样以 **GPL-3.0** 分发（见 [LICENSE](./LICENSE)）

- [Loyalsoldier/v2ray-rules-dat](https://github.com/Loyalsoldier/v2ray-rules-dat)（GPL-3.0）。其 `category-ads-all` 进一步聚合自：EasyList、EasyListChina、AdGuard DNS Filter、[Peter Lowe's adservers](https://pgl.yoyo.org/adservers/)、[Dan Pollock's hosts](https://someonewhocares.org/hosts/)
- [TG-Twilight/AWAvenue-Ads-Rule](https://github.com/TG-Twilight/AWAvenue-Ads-Rule)（GPL-3.0）

Peter Lowe 列表为 CC BY-NC-SA 4.0，Dan Pollock 列表要求署名。

**本项目仅供个人、非商业使用**，并保留上述全部来源署名。这些说明不构成法律意见
