#!/bin/sh

THUMBNAILS_DIR=${THUMBNAILS_DIR:-"/data/thumbnails"}
PHOTOS_DIR=${PHOTOS_DIR:-"/data/photos"}
LISTEN_PORT=${LISTEN_PORT:-"5000"}
LISTEN_HOST=${LISTEN_HOST:-"127.0.0.1"}

cd /app
python app.py -l ${LISTEN_HOST} -p ${LISTEN_PORT} -t ${THUMBNAILS_DIR} ${PHOTOS_DIR} 