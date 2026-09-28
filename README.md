# geoads.dat

将 [v2ray-rules-dat](https://github.com/Loyalsoldier/v2ray-rules-dat) 的广告域名（`category-ads-all`，以国际广告表为主）与 [AWAvenue-Ads-Rule](https://github.com/TG-Twilight/AWAvenue-Ads-Rule)（以国内 App 广告/SDK 为主）**取并集**，编译成一个 geosite 数据文件 `geoads.dat`，通过 GitHub Actions 每日自动构建。

单独使用任一上游都有缺口：v2ray-rules-dat 覆盖的国内 App 广告有限，AWAvenue 又不含国际广告。合并后两头兼顾。

## 使用

`geoads.dat` 是标准的 v2ray/Xray geosite 数据文件，内部只含一个类别，名为 `ads`：

- Release 直链：`https://github.com/BELUGA114/adsdat/releases/latest/download/geoads.dat`
- jsdelivr CDN：`https://cdn.jsdelivr.net/gh/BELUGA114/adsdat@release/geoads.dat`

引用方式：

- **Xray / v2ray（推荐）**：把 `geoads.dat` 放进资源目录（`XRAY_LOCATION_ASSET` 指向、与 geoip.dat/geosite.dat 同处的目录），路由规则用外部文件语法 `ext:geoads.dat:ads`。保留自定义文件名，且与官方 `geosite.dat` 并存
- **替换默认库**：把它改名为 `geosite.dat` 覆盖官方资源文件，再用 `geosite:ads`。但这样会丢掉官方库里的其它类别（`geosite:cn`、`geosite:google` 等），一般不推荐
- **mihomo（Clash.Meta）**：geodata 模式下把 geosite 数据库指向本文件（本地放为 `geosite.dat`，或用 `geox-url.geosite` 指到上面的直链），规则写 `GEOSITE,ads,REJECT`

同时发布并集明文 `geoads.txt`，便于审阅与二次加工。

## 本地构建

依赖用 [uv](https://docs.astral.sh/uv/) 管理：

```bash
uv sync
uv run python build.py --category ads --out-dir dist
```

产物写入 `dist/geoads.dat` 与 `dist/geoads.txt`，构建末尾会回读 `.dat` 校验类别与条数一致。

## 构建逻辑

1. 拉取两个上游明文列表（各自带 jsdelivr / fastly 镜像回退，下载异常或过小即报错，不发布空表）。
2. 合并后按 geosite 匹配语义去冗余：被父域 `domain` 覆盖的 `domain` / `full` 条目删除，`keyword` / `regexp` 保留。
3. 用运行期构建的 protobuf schema 序列化为 `geoads.dat`（无需 protoc / Go 工具链），再回读校验。

## 数据来源与许可

本项目产物为上述两个上游的派生作品，二者均为 **GPL-3.0**，故本仓库同样以 **GPL-3.0** 分发（见 [LICENSE](./LICENSE)）。

- [Loyalsoldier/v2ray-rules-dat](https://github.com/Loyalsoldier/v2ray-rules-dat)（GPL-3.0）。其 `category-ads-all` 进一步聚合自：EasyList、EasyListChina、AdGuard DNS Filter、[Peter Lowe's adservers](https://pgl.yoyo.org/adservers/)、[Dan Pollock's hosts](https://someonewhocares.org/hosts/)。
- [TG-Twilight/AWAvenue-Ads-Rule](https://github.com/TG-Twilight/AWAvenue-Ads-Rule)（GPL-3.0）。

注意传递性条款：Peter Lowe 列表为 CC BY-NC-SA 4.0（非商业、相同方式共享），Dan Pollock 列表要求署名。为规避风险，**本项目仅供个人、非商业使用**，并保留上述全部来源署名。这些说明不构成法律意见。
