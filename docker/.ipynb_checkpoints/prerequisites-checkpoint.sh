#!/bin/bash
set -a            
source .env
set +a

DATA_DIR=${STORAGE_DIR}/data

mkdir -p ${DATA_DIR}/certs
mkdir -p ${DATA_DIR}/esdata01
mkdir -p ${DATA_DIR}/kibanadata

chmod 777 ${DATA_DIR}/certs
chmod 777 ${DATA_DIR}/esdata01
chmod 777 ${DATA_DIR}/kibanadata