#!/bin/bash
# Detiene el proxy local y limpia el laboratorio temporal.
pkill -f "php -S 127.0.0.1:8898" 2>/dev/null
pkill -f "php -S 127.0.0.1:8899" 2>/dev/null
sleep 0.5
rm -rf /tmp/rnd-proxy-local
echo "Proxy local detenido."