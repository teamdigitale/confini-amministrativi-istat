FROM python:3.7-slim

RUN apt-get update && apt-get install -y \
    gdal-bin \
    sqlite3 \
    libsqlite3-mod-spatialite \
    liblwgeom-2.5-0

RUN mkdir -p /app
WORKDIR /app
ADD requirements.txt /app
ADD main.py /app
RUN pip install -r requirements.txt

VOLUME ["/app"]

#CMD ["python", "main.py"]
CMD ["bash", "_utils/analisiGeometrie.sh"]
#CMD ["ls", "/app"]
