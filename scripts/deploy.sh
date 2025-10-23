#!/bin/bash
# script to run the deployment frontend
# note the various sudo commands

USER=spin
WWW=/var/www/html/spinorama-eqconverter
BACK=/home/$USER/run/eqconverter
DEPLOY=/home/$USER/deploy

cd /home/$USER/deploy

# frontend code
sudo mkdir -p "$WWW"
sudo tar zxvf /home/$USER/deploy/frontend.tgz -C "$WWW"
sudo chown -R $USER:$USER "$WWW"

# backend code
mkdir -p "$BACK"
tar zxvf /home/$USER/deploy/backend.tgz -C "$BACK"

if test -d "$BACK/venv"; then
    . "$BACK/venv/bin/activate"
    pip3 install -U -r "$BACK/requirements.txt"
else
    sudo apt install python3-full python3-pip
    cd "$BACK"
    python3 -m venv venv
    . venv/bin/activate
    pip3 install -r "$BACK/requirements.txt"
fi
chown -R $USER:$USER "$BACK"

# ----------------------------------------------------------------------
# 2 options for running
# ----------------------------------------------------------------------
# 1. with supervisor
sudo cp "${DEPLOY}/etc/eqconverter.conf" "/etc/supervisord/conf.d"
# prevent issue if own by root
sudo rm -f /home/spin/run/gunicorn.sock
# reload / update / restart
sudo supervisorctl reload
sudo supervisorctl update
sudo supervisorctl restart eqconverter

# 2. systemd
# mkdir -p /home/$USER/.config/systemd/user
# cp "${DEPLOY}/etc/eqconverter.service" "/home/${USER}/.config/systemd/user"

# systemctl --user daemon-reload
# systemctl --user restart eqconverter.service

# ----------------------------------------------------------------------
# Reverse proxy: nginx conf
# ----------------------------------------------------------------------
sudo cp etc/nginx-prod.conf /etc/nginx/sites-available/spinorama-eqconverter
status=$(sudo nginx -t)
if test -z "$status"; then
    echo "OK after checking nginx config!"
else
    echo "KO after checking nginx config!"
    exit 1;
fi

# sudo systemctl restart nginx
# or
# sudo nginx -s reload
