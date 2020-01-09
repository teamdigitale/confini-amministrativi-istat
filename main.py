import os, subprocess, json, re, topojson, geobuf
from pathlib import Path
from simpledbf import Dbf5
import geopandas as gpd
import pandas as pd
from io import BytesIO, StringIO
from urllib.request import urlopen
from urllib.parse import urlparse
from zipfile import ZipFile

## Apro il file con tutte le risorse
with open("sources.json") as f:
    ## Carico le risorse (JSON)
    sources = json.load(f)
    ## Ciclo su tutte le risorse ISTAT
    for source in sources["istat"]:
        ## Trasforma la lista di divisioni amministrative (comuni, province, ecc.) in un dizionario indicizzato
        source["divisions"] = { division["name"]: division for division in source.get("divisions",[]) }
    ## Trasforma la lista di divisioni amministrative (comuni, province, ecc.) in un dizionario indicizzato
    sources["ontopia"]["divisions"] = { division["name"]: division for division in sources["ontopia"].get("divisions",[]) }

# ISTAT - Unità territoriali originali
print("+++ ISTAT +++")
## Ciclo su tutte le risorse ISTAT
for source in sources["istat"][0:2]:

    print("Processing %s..." % source["name"])

    # ZIP - Zip of original shapefile
    ## Cartella di output
    output_zip = Path(source["name"], "zip")
    ## Se non esiste...
    if not output_zip.exists():
        print("-- zip")
        ## ... la crea
        output_zip.mkdir(parents=True, exist_ok=True)
        ## Scarico il file dal sito ISTAT
        with urlopen(source["url"]) as res:
            ## Lo leggo come archivio zip
            with ZipFile(BytesIO(res.read())) as zfile:
                ## Individuo il nome della cartella root dell'archivio
                zip_root_dir = next(dir for dir in zfile.namelist() if dir.count('/') == 1)
                ## Ciclo su ogni file e cartella nell'archivio
                for zip_info in zfile.infolist():
                    ## Elimino la cartella root dal percorso di ogni file e cartella
                    zip_info.filename = zip_info.filename.replace(zip_root_dir, "")
                    ## Ciclo sulle divisioni amministrative
                    for division in source["divisions"].values():
                        ## Rinomino le sottocartelle con il nome normalizzato delle divisioni
                        zip_info.filename = zip_info.filename.replace(division["dirname"]+"/", division["name"]+"/").replace(division["filename"]+".", division["name"]+".")
                    ## Estraggo file e cartelle con un percorso non vuoto
                    if zip_info.filename:
                        zfile.extract(zip_info, output_zip)

    # SHP - Corrected shapefile
    ## Cartella di output
    output_shp = Path(source["name"], "shp")
    ## Se non esiste...
    if not output_shp.exists():
        print("-- shp")
        ## ... la crea
        output_shp.mkdir(parents=True, exist_ok=True)
        ## Ciclo su ogni suddivisione amministrativa
        for division in source["divisions"]:
            ## Creazione cartella
            output_div = Path(output_shp, division)
            output_div.mkdir(parents=True, exist_ok=True)
            ## Database spaziale temporaneo
            output_sqlite = output_div.with_suffix('.sqlite')
            ## Crea il db sqlite e poi lo inizializza come db spaziale
            subprocess.run([
                "sqlite3",
                output_sqlite,
                "\n".join([
                    "SELECT load_extension('mod_spatialite');",
                    "SELECT InitSpatialMetadata(1);"
                ])
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ## Analisi dello shp originale
            subprocess.run([
                "sqlite3",
                output_sqlite,
                "\n".join([
                    "SELECT load_extension('mod_spatialite');",
                    #"-- importa shp come tabella virtuale",
                    "CREATE VIRTUAL TABLE \"%s\" USING VirtualShape('%s', UTF-8, 32632);" % (division, Path(output_zip, division, division)),
                    #"-- crea tabella con output check geometrico",
                    "CREATE TABLE \"%s_check\" AS SELECT PKUID,GEOS_GetLastWarningMsg() msg,ST_AsText(GEOS_GetCriticalPointFromMsg()) punto FROM \"%s\" WHERE ST_IsValid(geometry) <> 1;" % (division, division)
                ])
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ## Conteggio degli errori rilevati
            errori = subprocess.check_output([
                "sqlite3",
                output_sqlite,
                "\n".join([
                    "SELECT count(*) FROM \"%s_check\"" % division
                ])
            ], stderr=subprocess.DEVNULL)
            ## Se ci sono errori crea nuova tabella con geometrie corrette
            print("Errori %s: %d geometrie corrette" % (division, int(errori)))
            if int(errori) > 0:
                subprocess.run([
                    "sqlite3",
                    output_sqlite,
                    "\n".join([
                        "SELECT load_extension('mod_spatialite');",
                        "CREATE table \"%s_clean\" AS SELECT * FROM \"%s\";" % (division, division),
                        "SELECT RecoverGeometryColumn('%s_clean','geometry',32632,'MULTIPOLYGON','XY');" % division,
                        "UPDATE \"%s_clean\" SET geometry = MakeValid(geometry) WHERE ST_IsValid(geometry) <> 1;" % division
                    ])
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ## Creazione shapefile con geometrie corrette
            subprocess.run([
                "ogr2ogr",
                Path(output_div, division).with_suffix(".shp"),
                output_sqlite,
                "%s_clean" % division
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ## Pulizia file temporanei
            os.remove(output_sqlite)

    # CSV - Comma Separated Values
    ## Cartella di output
    output_csv = Path(source["name"], "csv")
    ## Se non esiste...
    if not output_csv.exists():
        print("-- csv")
        ## ... la crea
        output_csv.mkdir(parents=True, exist_ok=True)
        ## Ciclo su tutti i file dbf degli shapefile disponibili
        for dbf_filename in output_zip.glob("**/*.dbf"):
            ## File di output (CSV)
            csv_filename = Path(output_csv, *dbf_filename.parts[2:]).with_suffix('.csv')
            ## Creo le eventuali sotto cartelle
            csv_filename.parent.mkdir(parents=True, exist_ok=True)
            ## Carico il file dbf
            dbf = Dbf5(dbf_filename)
            dbf.columns = [c.upper() for c in dbf.columns]
            ## Lo converto in CSV e lo salvo
            dbf.to_csv(csv_filename)
        ## Ciclo su tutti i file CSV
        for csv_filename in output_csv.glob("**/*.csv"):
            ## Carico il CSV come dataframe
            df = pd.read_csv(csv_filename, dtype = str)
            ## Per ogni divisione amministrativa superiore a quella corrente
            for parent in (source["divisions"][division_id] for division_id in source["divisions"][csv_filename.stem].get("parents",[])):
                ## Carico il CSV come dataframe
                jdf = pd.read_csv(Path(output_csv, parent["name"], parent["name"]+".csv"), dtype = str)
                ## Faccio il join selezionando le colonne che mi interessano
                df = pd.merge(df, jdf[[parent["key"]] + parent["fields"]], on=parent["key"], how="left")
            ## Sostituisco tutti i NaN con stringhe vuote
            df.fillna('', inplace=True)
            ## Aggiungo l'URI di OntoPiA
            if "key" in sources["ontopia"]["divisions"][csv_filename.stem]:
                df["ONTOPIA"] = df[sources["ontopia"]["divisions"][csv_filename.stem].get("key")].apply(
                    lambda x: "{host:s}/{path:s}/{code:0{digits:d}d}".format(
                        host = sources["ontopia"].get("url",""),
                        path = sources["ontopia"]["divisions"][csv_filename.stem].get("url",""),
                        code = int(x),
                        digits = sources["ontopia"]["divisions"][csv_filename.stem].get("digits",1)
                    )
                )
            ## Salvo il file arricchito
            df.to_csv(csv_filename, index = False, columns = [col for col in df.columns if "shape_" not in col.lower() and "pkuid" not in col.lower()])

        # JSON - Javascript Object Notation
        ## Cartella di output
        output_json = Path(source["name"], "json")
        ## Se non esiste...
        if not output_json.exists():
            print("-- json")
            ## ... la crea
            output_json.mkdir(parents=True, exist_ok=True)
            ## Ciclo su tutti i file csv
            for csv_filename in output_csv.glob("**/*.csv"):
                ## Carico il CSV come dataframe
                df = pd.read_csv(csv_filename, dtype = str)
                ## File di output (JSON)
                json_filename = Path(output_json, *csv_filename.parts[2:]).with_suffix('.json')
                ## Creo le eventuali sotto cartelle
                json_filename.parent.mkdir(parents=True, exist_ok=True)
                ## Salvo il file
                df.to_json(json_filename, orient="records")

    # Geojson + Topojson + Geobuf
    ## Cartelle di output
    output_geojson = Path(source["name"], "geojson")
    output_geopkg = Path(source["name"], "geopkg")
    output_topojson = Path(source["name"], "topojson")
    output_geobuf = Path(source["name"], "geobuf")

    ## Le creo se non esistono
    output_geojson.mkdir(parents=True, exist_ok=True)
    output_geopkg.mkdir(parents=True, exist_ok=True)
    output_topojson.mkdir(parents=True, exist_ok=True)
    output_geobuf.mkdir(parents=True, exist_ok=True)

    ## Ciclo su tutti gli shapefile
    for shp_filename in output_shp.glob("**/*.shp"):

        ## Carico gli shapefile come geodataframe
        gdf = gpd.read_file(shp_filename)

        # Geojson - https://geojson.org/
        ## File di output
        geojson_filename = Path(output_geojson, *shp_filename.parts[2:]).with_suffix('.json')
        ## Se non esiste...
        if not geojson_filename.exists():
            print("-- geojson")
            ## ... ne creo il percorso
            geojson_filename.parent.mkdir(parents=True, exist_ok=True)
            ## Converto in GEOJSON e salvo il file
            gdf.to_file(geojson_filename, driver="GeoJSON")

        # Geopackage - https://www.geopackage.org/
        ## File di output
        geopkg_filename = Path(output_geopkg, *shp_filename.parts[2:]).with_suffix('.gpkg')
        ## Se non esiste...
        if not geopkg_filename.exists():
            print("-- geopkg")
            ## ... ne creo il percorso
            geopkg_filename.parent.mkdir(parents=True, exist_ok=True)
            ## Converto in GEOJSON e salvo il file
            gdf.to_file(geopkg_filename, driver="GPKG")

        # Topojson - https://github.com/topojson/topojson
        ## File di output
        topojson_filename = Path(output_topojson, *shp_filename.parts[2:]).with_suffix('.json')
        ## Se non esiste...
        if not topojson_filename.exists():
            print("-- topojson")
            ## ... ne creo il percorso
            topojson_filename.parent.mkdir(parents=True, exist_ok=True)
            ## Carico e converto il GEOJSON in TOPOJSON
            tj = topojson.Topology(gdf, prequantize=False, topology=True)
            ## Salvo il file
            with open(topojson_filename, 'w') as f:
                f.write(tj.to_json())

        # Geobuf - https://github.com/pygeobuf/pygeobuf
        ## File di output
        #geobuf_filename = Path(output_geobuf, *shp_filename.parts[2:]).with_suffix('.pbf')
        ## Se non esiste...
        #if not geobuf_filename.exists() and geojson_filename.exists():
        #    print("-- geobuf")
            ## ... ne creo il percorso
        #    geobuf_filename.parent.mkdir(parents=True, exist_ok=True)
            ## Carico il GEOJSON e lo converto in GEOBUF
        #    with open(geojson_filename) as f:
        #        pbf = geobuf.encode(json.load(f))
            ## Salvo il file
        #    with open(geobuf_filename, 'wb') as f:
        #        f.write(pbf)

# ANPR - Archivio dei comuni
print("+++ ANPR +++")
## Scarico il file dal permalink di ANPR
with urlopen(sources["anpr"]["url"]) as res:

    ## Nome del file
    csv_filename = Path(sources["anpr"]["name"]).with_suffix(".csv")
    ## Carico come dataframe
    df = pd.read_csv(StringIO(res.read().decode('utf-8')), dtype = str)

    ## Ciclo su tutte le risorse istat
    for source in sources["istat"]:
        ## Divisione amministrativa utile per arricchire ANPR (quella comunale)
        division = source["divisions"].get(sources["anpr"]["division"]["name"])
        if division:

            print("Processing %s..." % source["name"])

            ## Carico i dati ISTAT come dataframe
            jdf = pd.read_csv(Path(source["name"], "csv", division["name"], division["name"]+".csv"), dtype = str)
            ## Aggiungo un suffisso a tutte le colonne uguale al nome della fonte ISTAT (_YYYYMMDD)
            jdf.rename(columns={col: "%s_%s" % (col,source["name"]) for col in jdf.columns}, inplace=True)
            ## Aggiungo una colonna GEO_YYYYMMDD con valore costante YYYYMMDD
            jdf["GEO_%s" % source["name"]] = source["name"]
            ## Faccio il join tra ANPR e fonte ISTAT selezionando solo le colonne che mi interessano
            df = pd.merge(
                df,
                jdf[
                    ["%s_%s" % (division["key"],source["name"])] + 
                    ["%s_%s" % (col,source["name"]) for col in division["fields"]] + 
                    ["GEO_%s" % source["name"]]
                ],
                left_on=sources["anpr"]["division"]["key"],
                right_on="%s_%s" % (division["key"],source["name"]),
                how="left"
            )
            ## Elimino tutte le colonne duplicate (identici valori su tutte le righe)
            df = df.loc[:,~df.T.duplicated(keep='first')]

    ## Sostituisco tutti i NaN con stringhe vuote
    df.fillna('', inplace=True)
    ## Concateno tutte le colonne GEO_YYYYMMDD in un'unica colonna GEO
    df["GEO"] = df[[col for col in df.columns if "GEO_" in col]].apply(lambda l: ','.join([str(x) for x in l if x]), axis=1)
    ## Elimino le colonne temporanee GEO_YYYYMMDD
    df.drop(columns=[col for col in df.columns if "GEO_" in col], inplace=True)
    ## Elimino i suffissi _YYYYMMDD da tutte le colonne
    df.rename(columns={col: re.sub(r"_\d+","",col) for col in df.columns}, inplace=True)
    ## Aggiungo la colonna di collegamento con OntoPiA
    df["ONTOPIA"] = df.apply(lambda row: "https://w3id.org/italia/controlled-vocabulary/territorial-classifications/cities/%s-(%s)" % (row["CODISTAT"], row["DATAISTITUZIONE"]), axis=1)
    ## Salvo il file arricchito
    df.to_csv(csv_filename, index=False)
