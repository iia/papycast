#!/bin/sh

SCRIPTPATH="$(cd "$(dirname "$0")" > /dev/null 2>&1; pwd -P)"

. $SCRIPTPATH/papycast.conf

./stop.sh

/usr/bin/docker \
run \
--rm \
-p 5000:5000 \
--name papycast \
--device /dev/gpiomem \
--device /dev/spidev0.0 \
--env PAPYCAST_ENV_QR_WIFI_SSID=$PAPYCAST_ENV_QR_WIFI_SSID \
--env PAPYCAST_ENV_QR_WIFI_SSID_PSK=$PAPYCAST_ENV_QR_WIFI_SSID_PSK \
-i iia86/papycast:arm32v7-latest
