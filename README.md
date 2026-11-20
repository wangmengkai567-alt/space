# 武汉湖泊近岸与远岸地表温度分析

本项目使用 Landsat 8 地表温度和 ESA WorldCover 土地覆盖数据，比较武汉外沙湖、南湖周边近岸（150–450 米）和远岸（600–900 米）建成区的地表温度。Codex 根据自然语言任务规划 DAG 并调用 GeoHarness MCP。GeoHarness 验证计划、执行空间分析和导出溯源包，随后由 Python 脚本独立复算并生成图表。

直接查看现有成果，可打开 [项目汇报](results/项目汇报.md)、[温度对照图](results/wuhan_lake_temperature.png)或[统计汇总表](results/lake_temperature_summary.csv)。

## 在 Windows 上运行

在项目根目录打开 PowerShell。准备已登录的 Codex 和 `uv`。Python 3.12 由 `uv` 管理，原始影像已归档在 `data/raw/`。

### 1. 安装依赖并生成输入

首次运行时，将已验证的 GeoHarness 版本检出到项目根目录的 `geoharness/`。

```powershell
git clone https://github.com/GeoZcx/geoharness.git geoharness
git -C geoharness checkout --detach b6b871a9d60e04d6cf494e430a60380c14e282bb
```

```powershell
uv sync --project geoharness --locked --python 3.12 --extra mcp --extra geo
uv run --project geoharness --locked --python 3.12 --extra mcp --extra geo -- python workflow/prepare_inputs.py
```

预处理在 `data/inputs/analysis/` 生成 `lakes.gpkg`、`built_up.gpkg` 和 `lst_c.tif`。原始文件及校验值见[数据来源](data_sources.md)。

### 2. 在 Codex 中运行任务

[项目 MCP 配置](.codex/config.toml)使用 `uv` 启动本地 GeoHarness。用 Codex 打开并信任项目，从根目录启动一个新会话。使用 CLI 时，可先查看已加载的服务器配置。

```powershell
codex mcp get geoharness
codex
```

向 Codex 发送「读取 `workflow/codex-task.md`，使用 GeoHarness MCP 完成分析」。[任务说明](workflow/codex-task.md)给出研究问题、数据约束和交付要求。Codex 根据算子契约组织 DAG，使用 GeoHarness 签发的 `verified_hash` 在同一 MCP 会话内执行。

### 3. 查看成果或手动复算

任务会要求 Codex 使用 `export_trace` 返回的 ZIP 生成成果。也可以用本次工具返回的实际路径手动复算。

```powershell
uv run --project geoharness --locked --python 3.12 --extra mcp --extra geo --with matplotlib -- python workflow/finalize_results.py "<本次 export_trace 返回的 ZIP 路径>"
```

汇总脚本核对溯源包和执行文件的校验值，独立复算四个分区，并更新 `results/` 下的统计、分区、地图与溯源 ZIP。

## 结果文件

| 文件 | 内容 |
| --- | --- |
| [lake_temperature_summary.csv](results/lake_temperature_summary.csv) | 两湖近岸和远岸的均值、像元数与温差 |
| [wuhan_lake_temperature.png](results/wuhan_lake_temperature.png) | 近岸和远岸的温度对照图 |
| [spot_check.csv](results/spot_check.csv) | 从原始影像独立复算的核对结果 |
| [geoharness_trace.zip](results/geoharness_trace.zip) | DAG 验证、执行和溯源记录 |

研究口径和结果解读见[项目汇报](results/项目汇报.md)。
