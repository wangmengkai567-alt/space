# 武汉外沙湖、南湖地表温度比较

请用已配置的 GeoHarness MCP 完成空间分析。比较 2025 年 8 月 17 日 Landsat 8 过境时，武汉外沙湖和南湖各自距岸 150–450 米与 600–900 米的建成区地表温度。

项目已准备 `data/inputs/analysis/` 下的 `lakes.gpkg`、`built_up.gpkg` 和 `lst_c.tif`。湖泊 ID 为 `shahu` 和 `nanhu`。三项资产须使用 EPSG:32649，温度须使用 30 米网格、连续值和 `lst_c` 波段。

1. 通过 MCP 登记三项资产，查看可用算子和契约，再根据任务组织完整 DAG。用平面距离划出两条环带，只统计环带内的建成区。按 `zone_id` 和像元中心统计均温、有效像元数及有效比例。
2. 把两个分区面命名为 `near_zones`、`far_zones`，两个统计表命名为 `near_stats`、`far_stats`。统计列前缀使用 `lst`，供后续复算脚本读取。
3. 将数据约束传给 `verify_dag`。通过后在同一个 MCP 会话中把原 DAG 与返回的 `verified_hash` 传给 `execute_dag`，输出到 `outputs/`。核对执行状态、L4 检查、两湖 ID 和每个分区至少 95% 的有效比例。如失败，报告原始诊断。
4. 导出 `full` 溯源包并记录路径、链校验状态和 `run_id`。成功后，用 `workflow/finalize_results.py` 独立复算并生成成果。以远岸减近岸报告两湖的温差，注明这是一次卫星过境的地表温度比较。
