from pathlib import Path

import fiona
import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.warp import Resampling, reproject, transform
from shapely import make_valid, union_all
from shapely.geometry import MultiPolygon, Point, mapping, shape


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INPUTS = ROOT / "data" / "inputs" / "analysis"
SCENE = "LC08_L2SP_123039_20250817_20250821_02_T1"
LAKE_SEEDS = {
    "shahu": ((114.332946, 30.569900), (114.321518, 30.564782)),
    "nanhu": ((114.358, 30.4906),),
}


def read_landsat(band):
    path = RAW / "landsat" / "wuhan" / f"{SCENE}_{band}.TIF"
    with rasterio.open(path) as dataset:
        return dataset.read(1), dataset.profile


def polygon_parts(geometry):
    if geometry.geom_type == "Polygon":
        return [geometry] if not geometry.is_empty else []
    return [part for child in getattr(geometry, "geoms", ()) for part in polygon_parts(child)]


def write_polygons(name, field, features, crs):
    with fiona.open(
        INPUTS / f"{name}.gpkg",
        "w",
        driver="GPKG",
        schema={"geometry": "MultiPolygon", "properties": {field: "str"}},
        crs_wkt=crs.to_wkt(),
    ) as output:
        for value, geometry in features:
            polygons = MultiPolygon(polygon_parts(geometry))
            if polygons.is_empty or not polygons.is_valid:
                raise ValueError(f"Invalid geometry for {value}")
            output.write({"geometry": mapping(polygons), "properties": {field: value}})


def main():
    INPUTS.mkdir(parents=True, exist_ok=True)
    temperature, raster = read_landsat("ST_B10")
    qa, qa_profile = read_landsat("QA_PIXEL")
    green, green_profile = read_landsat("SR_B3")
    swir, swir_profile = read_landsat("SR_B6")
    for profile in (qa_profile, green_profile, swir_profile):
        for key in ("width", "height", "crs", "transform"):
            if profile[key] != raster[key]:
                raise ValueError(f"Landsat grid mismatch on {key}")

    usable_temperature = (temperature != 0) & ((qa & 0x3F) == 0)
    lst = np.full(temperature.shape, -9999, dtype="float32")
    lst[usable_temperature] = temperature[usable_temperature] * 0.00341802 + 149.0 - 273.15
    with rasterio.open(
        INPUTS / "lst_c.tif", "w", **dict(raster, dtype="float32", nodata=-9999, compress="deflate")
    ) as output:
        output.write(lst, 1)
        output.set_band_description(1, "lst_c")
        output.update_tags(
            units="degC", value_kind="continuous", source_scene=SCENE, qa_excluded_bits="0,1,2,3,4,5"
        )

    # MNDWI > 0.1 on calibrated reflectance, retaining the component containing each lake seed.
    green_sr = green * 0.0000275 - 0.2
    swir_sr = swir * 0.0000275 - 0.2
    reflectance_sum = green_sr + swir_sr
    clear_optical = ((qa & 0x3F) == 0) & (green != 0) & (swir != 0)
    water = clear_optical & (reflectance_sum > 0) & ((green_sr - swir_sr) > 0.1 * reflectance_sum)
    components = [
        make_valid(shape(geometry))
        for geometry, value in shapes(water.astype("uint8"), mask=water, transform=raster["transform"])
        if value == 1
    ]
    lake_features = []
    for lake, seeds in LAKE_SEEDS.items():
        xs, ys = transform("EPSG:4326", raster["crs"], *zip(*seeds))
        patches = []
        for x, y in zip(xs, ys):
            (component,) = [area for area in components if area.covers(Point(x, y))]
            patches.append(component)
        lake_geometry = union_all(patches)
        if lake == "shahu":
            # Join the two lobes across the bridge without treating its deck as shoreline.
            east, west = patches
            under_bridge = west.buffer(45).intersection(east.buffer(45))
            lake_geometry = lake_geometry.union(under_bridge).buffer(0)
            if lake_geometry.geom_type != "Polygon":
                raise ValueError("The two Shahu lobes were not connected across the bridge")
        lake_features.append((lake, lake_geometry))
        print(f"{lake}: {lake_geometry.area / 1e6:.3f} km2")

    if lake_features[0][1].distance(lake_features[1][1]) <= 1800:
        raise ValueError("Lake 900 m buffers would overlap")
    write_polygons("lakes", "zone_id", lake_features, raster["crs"])

    tile = RAW / "worldcover" / "wuhan" / "ESA_WorldCover_10m_2021_v200_N30E114_Map.tif"
    landcover = np.zeros(temperature.shape, dtype="uint8")
    with rasterio.open(tile) as dataset:
        reproject(
            source=rasterio.band(dataset, 1),
            destination=landcover,
            dst_transform=raster["transform"],
            dst_crs=raster["crs"],
            dst_nodata=0,
            resampling=Resampling.nearest,
        )
    built = (landcover == 50) & ((qa & 0x80) == 0)
    fragments = [
        shape(geometry)
        for geometry, value in shapes(built.astype("uint8"), mask=built, transform=raster["transform"])
        if value == 1
    ]
    footprint = union_all([part for geometry in fragments for part in polygon_parts(make_valid(geometry))])
    write_polygons("built_up", "land_cover", [("50", footprint)], raster["crs"])
    print(f"Grid: {raster['width']} x {raster['height']}; valid temperature pixels: {int(usable_temperature.sum())}")
    print(f"WorldCover class 50 land cells: {int(built.sum())}")


if __name__ == "__main__":
    main()
