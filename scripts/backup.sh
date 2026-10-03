#!/bin/sh
set -eu
mkdir -p backups
stamp=$(date +%Y%m%d-%H%M%S)
tar -czf "backups/hausmonitor-v53-$stamp.tar.gz" data .env
