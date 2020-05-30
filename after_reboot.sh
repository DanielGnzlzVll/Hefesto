#!/bin/bash

cd /home/pi/Hefesto
git pull | grep "Already up to date."
up_to_date_or_error=$?

if [ $up_to_date_or_error -ne 0 ];
then
    echo "Reconstruyendo el container"
    sudo docker-compose build
    echo "Reiniciando el equipo"
    sudo reboot
else
    echo "Sin actualizaciones"
fi;
