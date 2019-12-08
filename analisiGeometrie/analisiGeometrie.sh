#!/bin/bash

set -x

folder="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cartellaDati="$folder"/../20190101

# crea cartella con l'ouput della pulizia delle geometrie
mkdir -p "$folder"/../20190101/shp_clean

# crea db sqlite e poi inizializzalo come db spaziale; cancellalo se preesiste
rm "$folder"/analisi.sqlite
sqlite3 "$folder"/analisi.sqlite "SELECT load_extension('mod_spatialite');
SELECT InitSpatialMetadata(1);"

cartella="$cartellaDati"/shp/regioni
mkdir -p "$cartellaDati"/shp_clean/regioni

# analizza lo shp originale
sqlite3 "$folder"/analisi.sqlite "SELECT load_extension('mod_spatialite');
-- importa shp regioni come tabella virtuale
CREATE VIRTUAL TABLE regioni USING VirtualShape("$cartella/regioni", UTF-8, 32632);
-- crea tabella con output check geometrico
create table regioni_check as select PKUID,GEOS_GetLastWarningMsg() msg,ST_AsText(GEOS_GetCriticalPointFromMsg()) punto from regioni WHERE ST_IsValid(geometry) <> 1;"

# conteggia errori rilevati
errori=$(sqlite3 "$folder"/analisi.sqlite "SELECT count(*) FROM regioni_check")

# se ci sono errori crea nuova tabella con geometrie corrette
if [ "$errori" -gt 0 ]; then
  sqlite3 "$folder"/analisi.sqlite "SELECT load_extension('mod_spatialite');
  CREATE table regioni_clean AS SELECT * FROM regioni;
  SELECT RecoverGeometryColumn('regioni_clean','geometry',32632,'MULTIPOLYGON','XY');
  UPDATE regioni_clean SET geometry = MakeValid(geometry) WHERE ST_IsValid(geometry) <> 1;"
fi

# svuota tabella output
rm -r "$folder"/../20190101/shp_clean/regioni/*

# esporta tabella con log errori file di input
ogr2ogr -f CSV "$folder"/../20190101/shp_clean/regioni/regioni_check.csv "$folder"/analisi.sqlite regioni_check

# crea shapefile con geometrie corrette
ogr2ogr "$folder"/../20190101/shp_clean/regioni/regioni.shp "$folder"/analisi.sqlite regioni_clean

