# AUpresetConverter

Here are set of utility to manipulate an EQ generated by REW or in APO
format.

A common use case on MacOS is that when you have done a room calibration and
you are getting some EQs generated by REW, you may have to manually
copy the EQ into AUNBandEQ. It takes 5 minutes to copy the parameters
but it is very error prone and boring.

Another use case is to use an EQ generated by
[autoEQ](https://github.com/jaakkopasanen/AutoEq/tree/master/results)
for your headphone. You feed it to the tool and you get a preset.

# How it works?

The easiest way is to use <a href="https://eqconverter.spinorama.org/">eqconverter.spinorama.org/</a>

You can also run it locally:

## Installation

```
python3 -m venv venv
source ./venv/bin/activate
pip3 install -r requirements.txt
pip3 install -r requirements-dev.txt
npm i .
```

## Run it

```
./eq2eq.py
```
will display usage.

## AUNBandEQ
```
./eq2eq.py -input eq.txt -format aupreset
```
will copy the AUpreset to the standard output.

You may want to copy it where most DAW can find it:

```
./eq2eq.py -input eq.txt -format aupreset -install
```

you can redirect to a file with the -output flag.

```
./eq2eq.py -input eq.txt -output eq.aupreset
```

will copy the AUpreset where DAWs(1) expect to find them (2).

- (1) at least Reaper and Logic will
- (2) ~/Library/Audio/Presets/Apple/AUNBandEQ

## REW TotalMix EQ
```
./eq2eq.py -input eq.txt -format rmetmeq -output eq.tmeq
```
You can then import the eq in TotalMix.
![RME: how to import eq in a channel](/assets/totalmix-how-to-import-channel.png)

# Running the App

## In developement mode

Start the backend:
```
export EQCONVERTER_ENV="dev"
python3 ./backend.py &
```
and then a reverse proxy for the frontend, either
```
python3 ./scripts/debug_server.py &
```
or
```
mkdir -p logs
nginx -p `pwd` -c ./etc/nginx-dev.conf
```

Point your browser to `http://0.0.0.0:8000/docs` for the swagger documentation and to `http://127.0.01:7999/` for the main page.


## In production

If you want to expose it on the internet, you can use a reverse proxy, you will need a domain name and the associated certificate.
In the `etc` directory, you will find a config file for `nginx` (the reverse proxy) and a systemd service config file.

the systemd file should go to `~/.config/systemd/user`, edit the path and then you can run it via:

```
systemctl --user enable eqconverter.service
systemctl --user start eqconverter.service
systemctl --user status eqconverter.service
```

The nginx file should go to `/etc/nginx/site-available`. Look at the ngnix manual for more details.



