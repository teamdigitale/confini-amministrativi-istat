#!/bin/bash

set -x

DIV=$1

folder="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cartellaDati="$folder"/../20190101

# crea cartella con l'ouput della pulizia delle geometrie
mkdir -p "$cartellaDati"/shp_clean

# crea db sqlite e poi inizializzalo come db spaziale; cancellalo se preesiste
rm -f "$cartellaDati"/analisi.sqlite
sqlite3 "$cartellaDati"/analisi.sqlite "SELECT load_extension('mod_spatialite');
SELECT InitSpatialMetadata(1);"

cartella="$cartellaDati"/shp/$DIV
mkdir -p "$cartellaDati"/shp_clean/$DIV

# analizza lo shp originale
sqlite3 "$cartellaDati"/analisi.sqlite "SELECT load_extension('mod_spatialite');
-- importa shp $DIV come tabella virtuale
CREATE VIRTUAL TABLE \"$DIV\" USING VirtualShape("$cartella/$DIV", UTF-8, 32632);
-- crea tabella con output check geometrico
create table \""$DIV"_check\" as select PKUID,GEOS_GetLastWarningMsg() msg,ST_AsText(GEOS_GetCriticalPointFromMsg()) punto from \"$DIV\" WHERE ST_IsValid(geometry) <> 1;"

# conteggia errori rilevati
errori=$(sqlite3 "$cartellaDati"/analisi.sqlite "SELECT count(*) FROM \""$DIV"_check\"")

# se ci sono errori crea nuova tabella con geometrie corrette
if [ "$errori" -gt 0 ]; then
  sqlite3 "$cartellaDati"/analisi.sqlite "SELECT load_extension('mod_spatialite');
  CREATE table \""$DIV"_clean\" AS SELECT * FROM \"$DIV\";
  SELECT RecoverGeometryColumn('"$DIV"_clean','geometry',32632,'MULTIPOLYGON','XY');
  UPDATE \""$DIV"_clean\" SET geometry = MakeValid(geometry) WHERE ST_IsValid(geometry) <> 1;"
fi

# svuota tabella output
rm -fr "$cartellaDati"/shp_clean/$DIV/*

# esporta tabella con log errori file di input
#ogr2ogr -f CSV "$cartellaDati"/shp_clean/$DIV/$DIV"_check.csv" "$cartellaDati"/analisi.sqlite $DIV"_check"

# crea shapefile con geometrie corrette
ogr2ogr "$cartellaDati"/shp_clean/$DIV/$DIV.shp "$cartellaDati"/analisi.sqlite $DIV"_clean"

# elimina db sqlite
rm -f "$cartellaDati"/analisi.sqlite
