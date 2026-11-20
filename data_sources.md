# 武汉沙湖与南湖地表温度项目数据

归档日期为 2026-11-19（北京时间）。Landsat 8 Collection 2 Level-2 原始景号为 `LC08_L2SP_123039_20250817_20250821_02_T1`，采集时间为 2025-08-17 10:56:21（北京时间）。[USGS 温度目录](https://landsatlook.usgs.gov/stac-server/collections/landsat-c2l2-st/items/LC08_L2SP_123039_20250817_20250821_02_T1_ST) · [USGS 反射率目录](https://landsatlook.usgs.gov/stac-server/collections/landsat-c2l2-sr/items/LC08_L2SP_123039_20250817_20250821_02_T1_SR)

## 数据范围与用途

- Landsat 分析文件位于 `data/raw/landsat/wuhan/`。从 Microsoft Planetary Computer 托管的同一景原始 GeoTIFF 读取武汉窗口。五个波段均为 EPSG:32649、30 米网格、678 × 741 像元，并通过像元网格一致性检查。窗口保留原始 DN。父目录还保存整景 QA_PIXEL 与三份 STAC 目录记录、产品 MTL。 [Landsat 镜像目录](https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2)
- WorldCover 2021 v200 分析文件位于 `data/raw/worldcover/wuhan/`。从 ESA 的 `N30E114` 瓦片读取同一经纬度范围，保留 EPSG:4326 和原始类别，窗口为 2460 × 2341 像元。已确认窗口内存在建成区类别 50。 [ESA 数据说明](https://esa-worldcover.org/en/data-access) · [原始瓦片](https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N30E114_Map.tif)
- 请求区域为东经 114.250–114.455°、北纬 30.430–30.625°，覆盖沙湖、南湖和分析缓冲带。截取时向外取整到原始网格，各文件保留对应的 `SOURCE_WINDOW` 标签。未进行重采样、温度换算或云掩膜。
- 像元窗口按「列偏移、行偏移、列数、行数」记录。Landsat 为 `5102,2596,678,741`，WorldCover 为 `3000,28500,2460,2341`。

`ST_B10` 用于地表温度换算，`QA_PIXEL` 用于质量掩膜，`SR_B3`、`SR_B5`、`SR_B6` 用于判读湖岸。湖岸矢量和温度分析输入由实施方案的预处理步骤生成。

## 本地文件校验

| 项目相对路径 | 字节 | SHA-256 |
| --- | ---: | --- |
| `data/raw/landsat/wuhan/LC08_L2SP_123039_20250817_20250821_02_T1_ST_B10.TIF` | 862,623 | `c240b97cd8affe77592dbdaadb8870abb4fc0c948c73e4c603810e010621c96f` |
| `data/raw/landsat/wuhan/LC08_L2SP_123039_20250817_20250821_02_T1_QA_PIXEL.TIF` | 22,767 | `ffcd1c815dfc0cce72375e43b58d8ba63112c4c1599dc41283b56b3ca11c541c` |
| `data/raw/landsat/wuhan/LC08_L2SP_123039_20250817_20250821_02_T1_SR_B3.TIF` | 869,456 | `927b10b10f07ef7605821622912a00e4b6c9648a7b19b4546d8d3422e6075878` |
| `data/raw/landsat/wuhan/LC08_L2SP_123039_20250817_20250821_02_T1_SR_B5.TIF` | 928,696 | `d69cb3aff600d5aae0a33b88dda2d8581b93cb69e6c12ea5122442d48f4de294` |
| `data/raw/landsat/wuhan/LC08_L2SP_123039_20250817_20250821_02_T1_SR_B6.TIF` | 905,580 | `0d642296750ac2e4587769cf9b521312394a78d4d704e4954c7265d6588200d2` |
| `data/raw/worldcover/wuhan/ESA_WorldCover_10m_2021_v200_N30E114_Map.tif` | 586,159 | `6538137cd1934e70ea566c7ba65c8262eea6003400d7e361c169a12b225b5bc5` |
| `data/raw/landsat/LC08_L2SP_123039_20250817_20250821_02_T1_QA_PIXEL.TIF` | 2,340,613 | `b578777d313c8f33700f6e2177ffc6bb289472e4b350739f6eabb71bee65e742` |
| `data/raw/landsat/LC08_L2SP_123039_20250817_20250821_02_T1_MTL.json` | 14,568 | `e9d4a42ff506c7ae8d9a02e621dfae2fec25279453c915efd62ec6c43cd4ba76` |
| `data/raw/landsat/LC08_L2SP_123039_20250817_20250821_02_T1_ST.stac.json` | 22,759 | `05b100c4551eaf6e13d077e0e667eeb363afc4048120356a86d1928be54b7dbf` |
| `data/raw/landsat/LC08_L2SP_123039_20250817_20250821_02_T1_SR.stac.json` | 23,965 | `8ff238cbccac548018dbdc99fe9a530ff996817b11f7add0874632a91985993d` |
| `data/raw/landsat/LC08_L2SP_123039_20250817_02_T1.planetary-computer.stac.json` | 23,211 | `be1a5d8023a1965f4ecc83551777da93d044d8ff148f00c5ee98fe7899a29bae` |
