FROM python:3.7-slim AS environment

RUN apt-get update
RUN apt-get install -y \
    gdal-bin \
    sqlite3 \
    #libsqlite3-mod-spatialite \
    libsqlite3-dev \
    #liblwgeom-2.5-0 \
    python3-dev \
    build-essential \
    libxml2-dev \
    libproj-dev \
    libgeos-dev \
    zlib1g-dev \
    pkg-config \
    automake \
    autoconf \
    autotools-dev \
    #m4 \
    libtool

ADD https://git.osgeo.org/gitea/rttopo/librttopo/archive/master.tar.gz /tmp
RUN tar zxf /tmp/master.tar.gz -C /tmp && rm /tmp/master.tar.gz
RUN cd /tmp/librttopo && \
    ./autogen.sh && \
    ./configure && \
    make && \
    make check && \
    make install

ADD https://www.gaia-gis.it/gaia-sins/freexl-1.0.5.tar.gz /tmp
RUN tar zxf /tmp/freexl-1.0.5.tar.gz -C /tmp && rm /tmp/freexl-1.0.5.tar.gz
RUN cd /tmp/freexl-1.0.5 && \
    ./configure && \
    make && \
    make install

ADD http://www.gaia-gis.it/gaia-sins/libspatialite-sources/libspatialite-5.0.0-beta0.tar.gz /tmp
RUN tar zxf /tmp/libspatialite-5.0.0-beta0.tar.gz -C /tmp && rm /tmp/libspatialite-5.0.0-beta0.tar.gz
RUN cd /tmp/libspatialite-5.0.0-beta0 && \
    ./configure --enable-rttopo=yes --enable-gcp=yes && \
    make -j8 && \
    make install-strip

RUN /sbin/ldconfig -v

RUN ln -s /usr/local/lib/mod_spatialite.so.7.1.0 /usr/lib/mod_spatialite.so

FROM environment AS application

RUN mkdir -p /app
WORKDIR /app
ADD requirements.txt /app
RUN pip install -r requirements.txt
ADD main.py /app

VOLUME ["/app"]

CMD ["python", "main.py"]

