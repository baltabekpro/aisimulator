#!/bin/sh
sleep 10
/usr/bin/mc alias set local http://minio:9000 minioadmin minioadmin23252325
if ! /usr/bin/mc ls local | grep -q "default"; then
    /usr/bin/mc mb local/default
fi
