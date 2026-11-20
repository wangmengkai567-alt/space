import argparse
import csv
import hashlib
import json
from pathlib import Path
from shutil import copy2
from zipfile import ZipFile

import fiona
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely import intersects_xy, points, shortest_line
from shapely.geometry import Point, shape

from geoharness.mcp.trace import verify_bundle
from prepare_inputs import INPUTS, ROOT, read_landsat


NAMES = {"shahu": "外沙湖", "nanhu": "南湖"}
BANDS = {"near": "150–450 m", "far": "600–900 m"}
RESULTS = ROOT / "results"


def read_zones(path):
    with fiona.open(path) as source:
        return {item.properties["zone_id"]: shape(item.geometry) for item in source}


def read_stats(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        return {
            row["zone_id"]: (float(row["lst_mean"]), int(float(row["lst_count"])), float(row["lst_valid_fraction"]))
            for row in csv.DictReader(source)
        }


def write_csv(name, header, rows):
    with (RESULTS / name).open("w", encoding="utf-8", newline="") as destination:
        writer = csv.writer(destination, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def draw_boundary(ax, geometry, **style):
    for line in getattr(geometry.boundary, "geoms", (geometry.boundary,)):
        ax.plot(*line.xy, **style)


def representative_pair(lake, near_mask, far_mask, x, y, temperature, means):
    near_indices, far_indices = np.flatnonzero(near_mask), np.flatnonzero(far_mask)
    flat_temperature = temperature.ravel()
    near_indices = near_indices[np.argsort(np.abs(flat_temperature[near_indices] - means[0]))[:80]]
    flat_x, flat_y = x.ravel(), y.ravel()
    near_points = points(flat_x[near_indices], flat_y[near_indices])
    far_points = points(flat_x[far_indices], flat_y[far_indices])
    near_shore = [line.coords[-1] for line in shortest_line(near_points, lake.boundary)]
    far_shore = np.asarray([line.coords[-1] for line in shortest_line(far_points, lake.boundary)])
    candidates = []
    for index, shore in zip(near_indices, near_shore):
        separations = np.hypot(flat_x[far_indices] - flat_x[index], flat_y[far_indices] - flat_y[index])
        shore_gaps = np.linalg.norm(far_shore - shore, axis=1)
        same_bank = (shore_gaps <= 180) & (separations >= 250) & (separations <= 750)
        for distant in far_indices[same_bank]:
            error = abs(flat_temperature[index] - means[0]) + abs(flat_temperature[distant] - means[1])
            candidates.append((error, index, distant))
    _, near, far = min(candidates)
    return [(flat_x[index], flat_y[index], float(flat_temperature[index])) for index in (near, far)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    args = parser.parse_args()
    verified_bundle = verify_bundle(args.trace)
    if not verified_bundle["passed"]:
        raise ValueError(verified_bundle["diagnoses"])
    with ZipFile(args.trace) as bundle:
        manifest = json.loads(bundle.read("manifest.json"))
        ledger = [json.loads(line) for line in bundle.read("ledger.jsonl").splitlines()]
        runs = json.loads(bundle.read("outputs.json"))["runs"]
        (run,) = [item for item in runs if item["ok"] and item["l4"]["passed"]]
        (verification,) = [
            item for item in ledger
            if item["tool"] == "verify_dag" and item["response"].get("verified_hash") == run["verified_hash"]
        ]
        report = f"reports/{verification['seq']:04d}-verify_dag.json"
        assert report in bundle.namelist()
        dag = json.loads(bundle.read(f"dags/{run['dag_sha256']}.json"))

    results = {}
    for item in run["outputs"]:
        path = ROOT / item["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        results[item["name"]] = path
    zones = {band: read_zones(results[f"{band}_zones"]) for band in BANDS}
    stats = {band: read_stats(results[f"{band}_stats"]) for band in BANDS}
    assert all(set(data) == set(NAMES) for data in (*stats.values(), *zones.values()))
    lakes = read_zones(INPUTS / "lakes.gpkg")
    raw, profile = read_landsat("ST_B10")
    qa, _ = read_landsat("QA_PIXEL")
    valid = (raw != 0) & ((qa & 0xBF) == 0)
    raw_celsius = raw * 0.00341802 + 149.0 - 273.15
    transform = profile["transform"]
    rows, columns = np.indices(raw.shape)
    x, y = transform * (columns + 0.5, rows + 0.5)

    audit_rows, masks = [], {}
    for lake in NAMES:
        for band in BANDS:
            mean, count, fraction = stats[band][lake]
            inside = intersects_xy(zones[band][lake], x, y)
            usable = inside & valid
            masks[band, lake] = usable
            independent_mean = float(raw_celsius[usable].mean())
            independent_count = int(usable.sum())
            independent_fraction = independent_count / int(inside.sum())
            assert count == independent_count and abs(fraction - independent_fraction) < 1e-10
            assert abs(independent_mean - mean) < 0.0001 and fraction >= 0.95
            audit_rows.append((lake, BANDS[band], count, independent_count, f"{mean:.9f}",
                               f"{independent_mean:.9f}", f"{independent_mean - mean:.9f}", f"{fraction:.6f}"))

    differences = {lake: stats["far"][lake][0] - stats["near"][lake][0] for lake in NAMES}
    illustrative_lake = "shahu"
    evidence = representative_pair(
        lakes[illustrative_lake], masks["near", illustrative_lake], masks["far", illustrative_lake],
        x, y, raw_celsius, [stats[band][illustrative_lake][0] for band in BANDS],
    )
    RESULTS.mkdir(exist_ok=True)
    write_csv("lake_temperature_summary.csv", ["湖泊", "距离带", "平均地表温度 °C", "有效像元数", "有效比例", "远岸减近岸 °C"],
              [(NAMES[lake], BANDS[band], *stats[band][lake], differences[lake] if band == "far" else "")
               for lake in NAMES for band in BANDS])
    write_csv("spot_check.csv", ["湖泊编号", "距离带", "GeoHarness 像元数", "复算像元数", "GeoHarness 均值 °C",
                                  "复算均值 °C", "均值差 °C", "有效比例"], audit_rows)
    evidence_rows = []
    for band, (ex, ey, temp) in zip(BANDS, evidence):
        row, column = rasterio.transform.rowcol(transform, ex, ey)
        distance = lakes[illustrative_lake].boundary.distance(Point(ex, ey))
        evidence_rows.append((illustrative_lake, BANDS[band], ex, ey, round(distance, 3), round(temp, 6),
                              int(raw[row, column]), int(qa[row, column])))
    write_csv("map_evidence.csv", ["湖泊编号", "距离带", "东向坐标 EPSG:32649", "北向坐标 EPSG:32649",
                                   "距岸 m", "地表温度 °C", "原始 DN", "QA_PIXEL"], evidence_rows)

    for name, source in results.items():
        copy2(source, RESULTS / f"{name}{source.suffix}")
    copy2(args.trace, RESULTS / "geoharness_trace.zip")
    for name, content in (("dag.json", dag), ("task.json", run["task"])):
        (RESULTS / name).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    plot(zones, stats, lakes, differences, illustrative_lake, evidence)

    details = {"run_id": run["run_id"], "verified_hash": run["verified_hash"], "verification_report": report,
               "execution_seq": run["seq"], "coverage": manifest["coverage"], "zip_record_count": verified_bundle["record_count"],
               "l4": run["l4"], "temperature_differences": differences, "evidence_lake": illustrative_lake}
    print(json.dumps(details, ensure_ascii=True, indent=2))


def plot(zones, stats, lakes, differences, illustrative_lake, evidence):
    font = Path("C:/Windows/Fonts/msyh.ttc")
    font_manager.fontManager.addfont(font)
    plt.rcParams.update({"font.family": font_manager.FontProperties(fname=font).get_name(), "svg.fonttype": "path"})
    qa, _ = read_landsat("QA_PIXEL")
    with rasterio.open(INPUTS / "lst_c.tif") as raster:
        data = raster.read(1, masked=True)
        extent = (raster.bounds.left, raster.bounds.right, raster.bounds.bottom, raster.bounds.top)
    data = np.ma.masked_where((qa & 0x80) != 0, data)
    vmin, vmax = np.percentile(data.compressed(), [3, 97])
    colors = {"near": "#007C9B", "far": "#653478"}
    styles = {"near": "-", "far": "--"}
    fig = plt.figure(figsize=(11.2, 8.0), facecolor="white")
    grid = fig.add_gridspec(2, 2, height_ratios=[1, 0.046], left=0.075, right=0.93, top=0.80,
                            bottom=0.17, hspace=0.28, wspace=0.14)
    fig.text(0.075, 0.935, "武汉湖岸建成区地表温度", fontsize=24, weight="bold", color="#132833")
    fig.text(0.075, 0.878, "2025 年 8 月 17 日 10:56（北京时间）  |  Landsat 8 单次过境", fontsize=11, color="#425665")
    cmap = plt.get_cmap("inferno").copy()
    cmap.set_bad("#F1F3F3")
    for index, (lake, name) in enumerate(NAMES.items()):
        ax = fig.add_subplot(grid[0, index])
        image = ax.imshow(data, extent=extent, cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest")
        for band in BANDS:
            draw_boundary(ax, zones[band][lake], color="white", linewidth=1.0, linestyle=styles[band], alpha=0.82)
            draw_boundary(ax, zones[band][lake], color=colors[band], linewidth=0.55, linestyle=styles[band])
        draw_boundary(ax, lakes[lake], color="#2C5962", linewidth=1.0)
        xmin, ymin, xmax, ymax = lakes[lake].bounds
        cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
        half = max(xmax - xmin, ymax - ymin) / 2 + 1040
        ax.set(xlim=(cx - half, cx + half), ylim=(cy - half, cy + half), xticks=[], yticks=[])
        ax.set_title(name, loc="left", fontsize=16, weight="bold", pad=12)
        for spine in ax.spines.values():
            spine.set_color("#AFBDC1")
        ax.annotate("N", xy=(0.94, 0.95), xytext=(0.94, 0.86), xycoords="axes fraction", ha="center",
                    color="white", weight="bold", arrowprops={"arrowstyle": "-|>", "color": "white"})
        start, level = cx - half + (half * 0.12), cy - half + (half * 0.14)
        ax.plot([start, start + 1000], [level, level], color="white", linewidth=3.1)
        ax.plot([start, start + 1000], [level, level], color="#263238", linewidth=1.2)
        ax.text(start + 500, level + half * 0.03, "1 km", ha="center", fontsize=8, color="#17242B",
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8, "pad": 1.5})
        if lake == illustrative_lake:
            for marker, (ex, ey, temp) in zip(("A", "B"), evidence):
                ax.scatter(ex, ey, s=22, facecolor="white", edgecolor="#132833", linewidth=0.8, zorder=8)
                offset = (-9, -16) if marker == "A" else (9, 11)
                ax.annotate(f"{marker} {temp:.1f}°", (ex, ey), xytext=offset, textcoords="offset points",
                            ha="right" if marker == "A" else "left", fontsize=8, color="#132833", weight="bold",
                            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9, "pad": 1.5})
        near_mean, near_n, _ = stats["near"][lake]
        far_mean, far_n, _ = stats["far"][lake]
        ax.text(0.5, -0.075,
                f"近岸 {near_mean:.2f} °C（{near_n:,}）  ·  远岸 {far_mean:.2f} °C（{far_n:,}）  ·  温差 {differences[lake]:+.2f} °C",
                transform=ax.transAxes, ha="center", va="top", fontsize=9, color="#263C48")
    cax = fig.add_subplot(grid[1, :])
    colorbar = fig.colorbar(image, cax=cax, orientation="horizontal", extend="both")
    colorbar.set_label("地表温度（°C）", fontsize=9)
    colorbar.ax.tick_params(labelsize=8)
    handles = [Line2D([0], [0], color=colors[band], lw=1.5, linestyle=styles[band], label=f"{distance} 建成区")
               for band, distance in BANDS.items()]
    handles.append(Patch(facecolor="#F1F3F3", edgecolor="#AFBDC1", label="水面或无有效值"))
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.075), ncol=3, frameon=False, fontsize=9)
    fig.text(0.075, 0.045, "括号为有效像元数。温差为远岸减近岸。A、B 为同一岸段近岸与远岸的示例像元。", fontsize=8, color="#425665")
    fig.text(0.075, 0.022, "数据：USGS Landsat Collection 2 Level-2、ESA WorldCover 2021。分析网格：30 m，EPSG:32649。",
             fontsize=8, color="#425665")
    for suffix in ("svg", "png"):
        fig.savefig(RESULTS / f"wuhan_lake_temperature.{suffix}", dpi=300, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
