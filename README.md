# Confini Amministrativi ISTAT

[![Data and open data on forum.italia.it](https://img.shields.io/badge/Forum-Dati%20e%20open%20data-blue.svg)](https://forum.italia.it/c/dati)
[![Confini Amministrativi ISTAT on forum.italia.it](https://img.shields.io/badge/Thread-%5BCall%20for%20ideas%5D%20Confini%20amministrativi%20ISTAT-blue.svg)](https://forum.italia.it/t/call-for-ideas-confini-amministrativi-istat/12224)

[![Join the #datascience channel](https://img.shields.io/badge/Slack%20channel-%23datascience-blue.svg?logo=slack)](https://developersitalia.slack.com/archives/C9B2NV3R6)
[![Get invited](https://slack.developers.italia.it/badge.svg)](https://slack.developers.italia.it/)

Collezione di utilities per facilitare il riuso dei dati ISTAT e ANPR sui confini amministrativi italiani. Per approfondimenti e discussione è aperto un [thread dedicato su Forum Italia](https://forum.italia.it/t/call-for-ideas-confini-amministrativi-istat/12224).

> Work in progress

## Contenuto del repository

Nel file `sources.json` ci sono i link a tutti gli shapefile rilasciati da ISTAT dal 2001 elencati in [questa tabella](https://www.istat.it/it/archivio/222527).

Lo script `main.py` scarica gli archivi zip dal sito ISTAT, li decomprime e li elabora in cartelle nominate con la data di rilascio: `YYYYMMDD/`.

Al momento sono supportati i seguenti formati di output:

* [ESRI shapefile](https://it.wikipedia.org/wiki/Shapefile) nella cartella `shp/` (formato originale)
* [Comma-separated values](https://it.wikipedia.org/wiki/Comma-separated_values) nella cartella `csv/`
* [Geojson](https://it.wikipedia.org/wiki/GeoJSON) nella cartella `geojson/`
* [Topojson](https://it.wikipedia.org/wiki/GeoJSON#TopoJSON) nella cartella `topojson/`
* [Geobuf](https://github.com/pygeobuf/pygeobuf) nella cartella `geobuf/`

> Avvertenza: al momento le cartelle e i file di output risultanti dall'esecuzione dell'applicazione **non** sono inseriti nel repository.

## Come eseguire l'applicazione

Clona questo repository con [Git](https://git-scm.com/): `git clone https://github.com/teamdigitale/confini-amministrativi-istat.git`.
Entra nella cartella appena creata: `cd confini-amministrativi-istat/`.

Il file `requirements.txt` elenca tutte le dipendenze necessarie a eseguire l'applicazione.
Si consiglia di operare sempre in un ambiente isolato creando un apposito *virtual environment*.
Con [pipenv](https://pipenv.kennethreitz.org/en/latest/) è sufficiente entrare nel virtualenv con `pipenv shell` e la prima volta installare le dipendenze con `pipenv install`.

Infine, per eseguire l'applicazione: `python main.py`.

> Avvertenza: al momento viene processato solo il primo elemento di `sources.json` (lo shapefile più recente disponibile).

> Avvertenza: al momento la conversione in geobuf è commentata perché va in errore

## Come contribuire

Ogni contributo è benvenuto, puoi aprire una issue oppure proporre una pull request, così come partecipare alla [discussione su Forum Italia](https://forum.italia.it/t/call-for-ideas-confini-amministrativi-istat/12224).
