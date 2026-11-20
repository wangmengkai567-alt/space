# 武汉湖边的凉意，走出几条街还看得见吗？

**GeoHarness 空间分析实施方案｜武汉沙湖与南湖｜2026 年 11 月 23 日 24:00 截止**

## 1. 研究问题

夏天从武汉湖边向城里走，地表温度会变多少？用 **2025 年 8 月 17 日约 10:56（北京时间）** 同一次 Landsat 8 过境，比较**沙湖和南湖各自距岸 150–450 米与 600–900 米的建成区，哪座湖的近岸与远岸地表温差更大？** 用地图展示一个典型岸段，再用四个分区的统计值比较两座湖。

每座湖形成两条向陆侧延伸的同宽距离带。主指标为 **远岸平均地表温度 − 近岸平均地表温度**，单位 °C。只比较土地覆盖图标为建成区的像元，以减少把湖面、树林和屋顶混在一起的影响。近岸的前 150 米留空，以减少热红外像元混入湖水。这个比较反映单次过境时的地表温度差异，可受绿化、建筑遮阴和地表材料影响。它衡量地表温度，人体体感与近地气温需要其他观测。 [武汉市水生态环境保护规划](https://hbj.wuhan.gov.cn/fbjd_19/zc/sthjjwj/xgwj/202301/t20230118_2135854.html) · [USGS 地表温度产品说明](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature)

## 2. 数据与准备

| 实际数据 | 取数与用途 |
| --- | --- |
| Landsat 8 Collection 2 Level-2 同一景 | 已在 USGS 查到景号 `LC08_L2SP_123039_20250817_20250821_02_T1`，目录记录整景云量 0.8%。下载 `ST_B10`、`QA_PIXEL`，以及同景的 `SR_B3`、`SR_B5`、`SR_B6` 供湖岸判读。整景云量用于选景，实际分析检查两湖周围的有效像元。 [温度资产清单](https://landsatlook.usgs.gov/stac-server/collections/landsat-c2l2-st/items/LC08_L2SP_123039_20250817_20250821_02_T1_ST) · [反射率资产清单](https://landsatlook.usgs.gov/stac-server/collections/landsat-c2l2-sr/items/LC08_L2SP_123039_20250817_20250821_02_T1_SR) |
| ESA WorldCover 2021 v200 | 武汉所在的 `N30E114` 瓦片可以直接下载。使用建成区类别 50。它是 2021 年底图，汇报保留与 2025 年影像的时间差说明。 [产品与下载说明](https://esa-worldcover.org/en/data-access) · [武汉所在瓦片](https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N30E114_Map.tif) |
| 沙湖、南湖的水面边界 | 在 QGIS 用同景 `SR_B6/B5/B3`（红／绿／蓝）假彩色组合识别水陆边界，勾画并保存两湖范围。武汉市水务局湖泊名录用于核对名称，实际几何来自当日影像。 [武汉市水务局湖泊名录](https://swj.wuhan.gov.cn/xxgk/new_zc/new_qtzdgkwj/202412/t20241226_2508785.html) |

1. 登录 USGS EarthExplorer 免费下载对应景号的 Level-2 波段，下载需要 USGS 的 ERS 账号。归档原始波段、WorldCover 瓦片和 STAC 元数据。把下载日期、输入路径、场景 ID、温度系数及预处理参数记入 `data_sources.md`。景号及资产列表已核实，执行时检查两湖四个分区的有效像元。 [下载入口](https://earthexplorer.usgs.gov/) · [USGS 账户与下载帮助](https://www.usgs.gov/centers/eros/science/earthexplorer-help-index)
2. 在 QGIS 或使用 `uv` 管理的 Python 环境准备资产。取覆盖两湖与全部 900 米分析带的矩形窗口，保持 Landsat 原始 30 米输出网格和米制投影 `EPSG:32649`。所有波段使用同一像元窗口，温度栅格保持原网格，不插值。
3. 温度栅格排除 `ST_B10=0` 和 `QA_PIXEL` 位 0–5 标记的像元。有效像元按 `°C = DN × 0.00341802 + 149.0 − 273.15` 转换，保存单波段 Float32 GeoTIFF `data/inputs/analysis/lst_c.tif`，波段名为 `lst_c`，`NoData=-9999`。 [USGS 温度换算](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature) · [USGS QA 位定义](https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands)
4. 将 WorldCover 以最近邻对齐到温度窗口，保留类别 50 并按 `QA_PIXEL` 位 7 排除水面。建成区转换并融合成一条多部件记录，保存为 `data/inputs/analysis/built_up.gpkg`。两湖主水面保存为 `data/inputs/analysis/lakes.gpkg`，每湖一条有效面记录，`zone_id` 设为 `shahu` 和 `nanhu`。两者与温度数据同投影。检查两湖的 900 米外扩范围互不重叠。 [预处理脚本](workflow/prepare_inputs.py)

## 3. Codex 连接 GeoHarness

在项目根目录使用已登录的 Codex，按 README 安装 GeoHarness 并生成分析输入。项目配置通过 `uv` 启动本地 stdio MCP 服务。从根目录打开新的 Codex 会话，提交自然语言任务提示。 [启动说明](README.md) · [MCP 配置](.codex/config.toml) · [Codex MCP 文档](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

Codex 登记三项分析资产，再通过 `list_operators` 读取可用算子契约，依据任务约束组织 DAG。 [Codex 任务提示](workflow/codex-task.md)

## 4. GeoHarness 核心分析与地图

1. **登记资产。** Codex 在同一 MCP 会话调用 `ingest_asset` 登记三个输入，标记 `task_tag="wuhan_lake_lst"`。温度输入登记时传 `bands=["lst_c"]`。核对三个实际 `asset_id`、CRS、几何类型、栅格边界、30 米网格和 NoData。如工具提示需确认数值类型，以产品说明确认温度为连续量，再登记经确认的元数据。
2. **构建完整 DAG。** 用 `buffer(vector=lakes)` 生成 150、450、600、900 米的向外平面缓冲（`geodesic=false`）。用 `overlay(operation="difference")` 计算 `B450 − B150` 和 `B900 − B600`，分别用 `clip_vector` 保留与建成区重叠的面，输出 `near_zones` 和 `far_zones`。保留左侧的 `zone_id`，每个环带应各有沙湖、南湖两条记录。
3. **分区统计。** 每个环带接一个 `zonal_stats`。插槽 `raster` 使用 `lst_c`，`zones` 使用该环带建成区，参数 `input_band="lst_c"`、`zone_id_field="zone_id"`、`column_prefix="lst"`、`stats=["mean","count","valid_fraction"]`。输出 `near_stats` 和 `far_stats`。分析要求温度输入 CRS 为 `EPSG:32649`、分辨率为 30 米，可在 `task` 中使用温度输入的 `asset_id` 声明 `crs EQ` 和 `resolution EQ`。 [DAG 格式](https://github.com/GeoZcx/geoharness/blob/main/geoharness/mcp/catalog_data.py) · [内置契约](https://github.com/GeoZcx/geoharness/blob/main/geoharness/contracts/builtins.py) · [分区统计实现](https://github.com/GeoZcx/geoharness/blob/main/geoharness/operators/zonal.py)
4. **验证与执行。** 用 `verify_dag(dag, task)` 验证。遇到可修复诊断时按原因修正，原样传回 `task` 重新验证。通过后在同一 MCP 会话用同一 DAG 和最新的 `verified_hash` 调用 `execute_dag`。检查 `ok`、`l4.passed`、运行时诊断、输出文件及两张表的湖泊 ID。分区检查有效像元比例至少 95%，四个分区均有有效像元才报告比较值。记录每个分区的像元数与有效比例。 [GeoHarness 运行时检查](https://github.com/GeoZcx/geoharness/blob/main/geoharness/verification/checker.py)
5. **汇总并解释证据。** 对两湖分别算 `ΔT = 远岸 lst_mean − 近岸 lst_mean`，输出 `lake_temperature_summary.csv`。两图共用同一温度色标，叠加湖岸和两种环带轮廓，用 QGIS 布局输出 `wuhan_lake_temperature.svg`。根据结果挑一个清晰的岸段，标出相邻近岸和远岸的空间位置及温度，说明这处图上证据如何对应分区统计。比较使用未四舍五入的数值，展示保留 1 位小数。温差很小时报告幅度，不强行给出有实质差别的排名。 [QGIS SVG 导出](https://docs.qgis.org/3.44/en/docs/user_manual/print_layout/create_output.html#export-as-svg)

本次 Codex 执行所用的 DAG 和校验记录随成果归档。 [DAG](results/dag.json) · [正式运行与溯源](results/项目汇报.md#codex-运行与溯源)

## 5. 独立抽查与溯源

抽查 **沙湖近岸建成区平均地表温度**。从 GeoHarness 出图的 `near_zones` 取 `zone_id=shahu` 的面。在 QGIS 用「栅格像元转点」取得温度像元中心，空间筛出落入该面的点，排除 NoData，再单独统计有效点数和均值。核对边界上的像元中心，并以同一取样口径比较 GeoHarness 的像元数和均值。把数值、差值及差异原因写入 `spot_check.csv`。再任选一个被计入的像元，回查原始 DN 和 QA，记录其换算值与掩膜判定。 [GeoHarness 像元中心取样实现](https://github.com/GeoZcx/geoharness/blob/main/geoharness/operators/zonal.py#L155-L195)

在正式会话调用 `export_trace(profile="full")`，查验链校验结果并保留导出的 ZIP。在汇报中用同一个 `verified_hash` 对照验证与执行。 [GeoHarness 溯源包实现](https://github.com/GeoZcx/geoharness/blob/main/geoharness/mcp/bundle.py#L519-L595)

| 溯源包位置 | 汇报中指出 |
| --- | --- |
| `reports/<序号>-verify_dag.json` | 验证是否通过、签发的 `verified_hash`、诊断与运行时检查项。 |
| `ledger.jsonl` 和 `outputs.json` | 对应 `execute_dag` 的执行序号、`run_id`、L4 状态、文件路径与校验值。 |
| `dags/`、`inputs.json`、`manifest.json` | 最终 DAG、登记资产和溯源覆盖范围。覆盖范围为 `ledger-only` 时，调用端的规划与工具发起过程可结合 Codex 会话核对。 |

原始数据、预处理输入和成果文件随项目归档，便于根据 ZIP 中的清单核验。遇到工具问题时，记录发生步骤、真实返回、处理方式及重跑结果。

## 6. 提交安排

| 日期 | 可验收产物 |
| --- | --- |
| 11 月 19–20 日 | 下载数据，完成两湖边界、建成区掩膜、温度栅格及 MCP 连通检查。 |
| 11 月 21 日 | 用 Codex 调用 GeoHarness 完成验证、执行和溯源导出，提交分区面与原始统计表。 |
| 11 月 22 日 | 复算沙湖近岸均值，完成对照 SVG 地图与抽查记录。 |
| 11 月 23 日 | 核对地图、统计表和溯源 ZIP，用地图标出支撑结论的岸段，24:00 前提交。 |
