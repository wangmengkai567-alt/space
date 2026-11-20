# 武汉湖泊近岸与远岸地表温度分析

本项目使用 Landsat 8 地表温度和 ESA WorldCover 土地覆盖数据，比较武汉外沙湖、南湖周边近岸（150–450 米）和远岸（600–900 米）建成区的地表温度。DeepSeek Harness 启动本地工作流，GeoHarness 验证并执行空间分析，随后由 Python 脚本独立复算并生成图表。

直接查看现有成果，可打开 [项目汇报](results/项目汇报.md)、[温度对照图](results/wuhan_lake_temperature.png)或[统计汇总表](results/lake_temperature_summary.csv)。

## 在 Windows 上运行

在项目根目录 `work2` 打开 PowerShell。准备 `uv`、Node.js 24.9.0 或更高版本，以及 `deepseek-harness/package.json` 指定的 pnpm 版本。Python 3.12 由 `uv` 管理。以下步骤使用 `data/raw/` 已归档的影像，程序化工作流无需 DeepSeek API Key。

### 1. 安装依赖并生成输入

```powershell
uv sync --project geoharness --locked --python 3.12 --extra mcp --extra geo
pnpm --dir deepseek-harness install --frozen-lockfile
uv run --project geoharness --locked --python 3.12 --extra mcp --extra geo -- python workflow/prepare_inputs.py
```

预处理在 `data/inputs/analysis/` 生成 `lakes.gpkg`、`built_up.gpkg` 和 `lst_c.tif`。原始文件及校验值见[数据来源](data_sources.md)。

### 2. 启动分析

如果项目移到了其他路径，将 [deepseek-programmatic.patch.yml](workflow/deepseek-programmatic.patch.yml) 中 `wuhan-lake-geoharness` 的 `name` 改为本机 `workflow/run-geoharness.mjs` 的绝对路径，路径用 `/` 分隔。当前配置对应 `D:/My_workspace/project/work2`。

```powershell
$dsh = (Resolve-Path deepseek-harness).Path
$env:TSX_TSCONFIG_PATH = Join-Path $dsh 'tsconfig.json'
$tsx = [uri](Join-Path $dsh 'node_modules/tsx/dist/esm/index.mjs')
node --import $tsx.AbsoluteUri (Join-Path $dsh 'apps/cli/src/bin.ts') --profile headless --patch workflow/deepseek-geoharness.patch.yml --patch workflow/deepseek-programmatic.patch.yml 'Run the configured Wuhan GeoHarness workflow.'
```

这条命令在终端运行。成功时会打印带有 `run_id` 和 `trace.path` 的 JSON，并将分区和统计数据写入 `outputs/`。如有报错，查看终端信息和 `results/deepseek_mcp_calls.jsonl` 的末尾。

### 3. 复算并生成成果

在分析成功后，从调用日志读取本次 `export_trace` 返回的 ZIP 路径，再运行汇总脚本。

```powershell
$trace = (Get-Content -Encoding utf8 results/deepseek_mcp_calls.jsonl -Tail 1 | ConvertFrom-Json).output.path
uv run --project geoharness --locked --python 3.12 --extra mcp --extra geo --with matplotlib -- python workflow/finalize_results.py $trace
```

汇总脚本校验溯源包并独立复算四个分区，更新 `results/` 下的同名 CSV、GeoPackage、地图和溯源 ZIP。分析命令会重写 `results/deepseek_mcp_calls.jsonl`。

## 结果文件

| 文件 | 内容 |
| --- | --- |
| [lake_temperature_summary.csv](results/lake_temperature_summary.csv) | 两湖近岸和远岸的均值、像元数与温差 |
| [wuhan_lake_temperature.png](results/wuhan_lake_temperature.png) | 近岸和远岸的温度对照图 |
| [spot_check.csv](results/spot_check.csv) | 从原始影像独立复算的核对结果 |
| [geoharness_trace.zip](results/geoharness_trace.zip) | DAG 验证、执行和溯源记录 |

研究口径和结果解读见[项目汇报](results/项目汇报.md)。
