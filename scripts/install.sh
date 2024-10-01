#!/bin/sh

BACKEND_PORT=9999 API_URL=https://eqconverter.spinorama.org reflex export
rsync -arv frontend.zip backend.zip deploy.sh etc pierre@es.spinorama.org:/home/pierre/deploy
