#!/bin/sh
# script to be run as root on the deployment frontend

USER=pierre
WWW=/var/www/html/spinorama-eqconverter
BACK=/home/$USER/run/eqconverter

cd /home/$USER/deploy

# frontend code
mkdir -p "$WWW"
chown -r $USER:$USER "$WWW"
cd "$WWW" && unzip /home/$USER/deploy/frontend.zip

# nginx conf
cp nginx.conf /etc/nginx/sites-available/spinorama-eqconverter
status=$(nginx -t)
if [ $status -ne 0 ]; then
    echo "KO after checking nginx config!"
    exit 1;
fi

# backend code

cd "$BACK" && unzip /home/$USER/deploy/backend.zip
if [ ! test -d "$BACK/venv"]; then
    apt install python3-pip
    cd "$BACK"
    python3 -m venv venv
    source venv/bin/activate
    pip3 install -r requirements.txt
else
    source venv/bin/activate
    pip3 install -U -r requirements.txt
fi

# systemd
mkdir -p /home/$USER/.config/systemd/user
cp etc/eqconverter.service /home/$USER/.config/systemd/user

systemctl --user daemon-reload
systemctl --user restart eqconverter.service

systemctl restart nginx
