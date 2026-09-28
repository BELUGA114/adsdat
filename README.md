# geoads.dat

将 [v2ray-rules-dat](https://github.com/Loyalsoldier/v2ray-rules-dat) 的广告域名（`category-ads-all`，以国际广告表为主）与 [AWAvenue-Ads-Rule](https://github.com/TG-Twilight/AWAvenue-Ads-Rule)（以国内 App 广告/SDK 为主）**取并集**，编译成一个 geosite 数据文件 `geoads.dat`，通过 GitHub Actions 每日自动构建。

单独使用任一上游都有缺口：v2ray-rules-dat 覆盖的国内 App 广告有限，AWAvenue 又不含国际广告。合并后两头兼顾。

## 使用

客户端（v2ray / Xray / mihomo / sing-box 等）将 geosite 数据源指向本仓库产物，并按类别 `geosite:ads` 引用：

- Release 直链：`https://github.com/<owner>/<repo>/releases/latest/download/geoads.dat`
- jsdelivr CDN：`https://cdn.jsdelivr.net/gh/<owner>/<repo>@release/geoads.dat`

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
