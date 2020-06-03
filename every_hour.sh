#!/bin/bash

cd /home/pi/Hefesto
git pull | grep "Already up to date."
up_to_date_or_error=$?

if [ $up_to_date_or_error -ne 0 ];
then
    echo "Reiniciando los contenedores"
    docker-compose restart
else
    echo "Sin actualizaciones"
fi;

echo "Reiniciando el equipo"
sudo reboot