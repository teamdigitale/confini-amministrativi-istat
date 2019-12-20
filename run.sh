#!/bin/bash
for DIV in ripartizioni-geografiche regioni unita-territoriali-sovracomunali comuni; do
    docker run --env DIV=$DIV --volume=$PWD:/app italia-conf-amm-istat:latest
done
