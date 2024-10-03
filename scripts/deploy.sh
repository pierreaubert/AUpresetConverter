#!/bin/bash
# script to be run as root on the deployment frontend

USER=pierre
WWW=/var/www/html/spinorama-eqconverter
BACK=/home/$USER/run/eqconverter

cd /home/$USER/deploy

# frontend code
mkdir -p "$WWW"
chown -r $USER:$USER "$WWW"
cd "$WWW" && unzip -o -q /home/$USER/deploy/frontend.zip

# nginx conf
cp etc/nginx.conf /etc/nginx/sites-available/spinorama-eqconverter
status=$(nginx -t)
if test -z "$status"; then
    echo "OK after checking nginx config!"
else
    echo "KO after checking nginx config!"
    exit 1;
fi

# backend code

cd "$BACK" && unzip -o -q /home/$USER/deploy/backend.zip

if [ -d "$BACK/venv" ]; then
    . "$BACK/venv/bin/activate"
    pip3 install -U -r requirements.txt
else
    apt install python3-pip
    cd "$BACK"
    python3 -m venv venv
    source venv/bin/activate
    pip3 install -r requirements.txt
fi

# systemd
mkdir -p /home/$USER/.config/systemd/user
cp etc/eqconverter.service /home/$USER/.config/systemd/user

systemctl --user daemon-reload
systemctl --user restart eqconverter.service

systemctl restart nginx
