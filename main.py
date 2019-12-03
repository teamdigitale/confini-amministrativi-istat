import json, topojson, geobuf
from pathlib import Path
from simpledbf import Dbf5
import geopandas as gpd
import pandas as pd
from io import BytesIO
from urllib.request import urlopen
from zipfile import ZipFile

with open("sources.json") as f:
    sources = json.load(f)

for source in sources[0:2]:

    print("Processing %s..." % source["name"])

    source["divisions"] = { division["name"]: division for division in source["divisions"] }

    # SHP - Shapefile
    output_shp = Path(source["name"], "shp")
    if not output_shp.exists():
        output_shp.mkdir(parents=True, exist_ok=True) 
        with urlopen(source["url"]) as res:
            with ZipFile(BytesIO(res.read())) as zfile:
                zip_root_dir = next(dir for dir in zfile.namelist() if dir.count('/') == 1)
                for zip_info in zfile.infolist():
                    zip_info.filename = zip_info.filename.replace(zip_root_dir, "")
                    for division in source["divisions"].values():
                        zip_info.filename = zip_info.filename.replace(division["dirname"]+"/", division["name"]+"/").replace(division["filename"]+".", division["name"]+".")
                    if zip_info.filename:
                        zfile.extract(zip_info, output_shp)

    # CSV - Comma Separated Values
    output_csv = Path(source["name"], "csv")
    if not output_csv.exists():
        output_csv.mkdir(parents=True, exist_ok=True) 
        for dbf_filename in output_shp.glob("**/*.dbf"):
            csv_filename = Path(output_csv, *dbf_filename.parts[2:]).with_suffix('.csv')
            csv_filename.parent.mkdir(parents=True, exist_ok=True)
            dbf = Dbf5(dbf_filename)
            dbf.to_csv(csv_filename)
        for csv_filename in output_csv.glob("**/*.csv"):
            df = pd.read_csv(csv_filename)
            for parent in (source["divisions"][division_id] for division_id in source["divisions"][csv_filename.stem].get("parents",[])):
                jdf = pd.read_csv(Path(output_csv, parent["name"]+"/", parent["name"]+".csv"))
                df = pd.merge(df, jdf[[parent["key"]] + parent["fields"]], on=parent["key"])
            df.to_csv(csv_filename, index = False, columns = [col for col in df.columns if "shape_" not in col.lower()])

    # Geojson + Topojson + Geobuf
    output_geojson = Path(source["name"], "geojson")
    output_topojson = Path(source["name"], "topojson")
    output_geobuf = Path(source["name"], "geobuf")

    output_geojson.mkdir(parents=True, exist_ok=True)
    output_topojson.mkdir(parents=True, exist_ok=True)
    output_geobuf.mkdir(parents=True, exist_ok=True)

    for shp_filename in output_shp.glob("**/*.shp"):

        gdf = gpd.read_file(shp_filename)

        # Geojson - https://geojson.org/
        geojson_filename = Path(output_geojson, *shp_filename.parts[2:]).with_suffix('.json')
        if not geojson_filename.exists():
            geojson_filename.parent.mkdir(parents=True, exist_ok=True)
            gdf.to_file(geojson_filename, driver="GeoJSON")

        # Topojson - https://github.com/topojson/topojson
        # topojson_filename = Path(output_topojson, *shp_filename.parts[2:]).with_suffix('.json')
        # if not topojson_filename.exists():
        #     topojson_filename.parent.mkdir(parents=True, exist_ok=True)
        #     tj = topojson.Topology(gdf, prequantize=False, topology=True)
        #     with open(topojson_filename, 'w') as f:
        #         f.write(tj.to_json())

        # Geobuf - https://github.com/pygeobuf/pygeobuf
        #geobuf_filename = Path(output_geobuf, *shp_filename.parts[2:]).with_suffix('.pbf')
        #if not geobuf_filename.exists() and geojson_filename.exists():
        #    geobuf_filename.parent.mkdir(parents=True, exist_ok=True)
        #    with open(geojson_filename) as f:
        #        pbf = geobuf.encode(json.load(f))
        #    with open(geobuf_filename, 'wb') as f:
        #        f.write(pbf)
