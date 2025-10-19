#!/bin/bash
docker compose exec server flask db init
docker compose exec server flask db migrate -m "Initial migration"
docker compose exec server flask db upgrade
docker compose exec server flask create-admin
