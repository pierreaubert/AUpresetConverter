#!/bin/sh

touch env.log

## SSH AGENT
## ----------------------------------------------------------------------
ssh-agent -k >> env.log 2>&1
eval `ssh-agent`
echo $SSH_AGENT_SOCK
if ! test -f ~/.ssh/id_rsa_github; then
    echo "ERROR github key don\'t exists!"
fi

## Github keys
## ----------------------------------------------------------------------
github=$(ssh-add -l | grep github | cut -d ' ' -f 3)
if test -z $github; then
    ssh-add ~/.ssh/id_rsa_github >> env.log 2>&1
    github=$(ssh-add -l 2>&1 | grep github | cut -d ' ' -f 3)
fi

## python virtualenv
## ----------------------------------------------------------------------
CODE=$PWD
export PYTHONPATH=$CODE
if ! test -d $CODE/.venv; then
    python3 -m venv .venv
    source $CODE/.venv/bin/activate
    # rehash
    pip3 install -U pip
    pip3 install -r requirements.txt
fi
source $CODE/.venv/bin/activate

## summary
## ----------------------------------------------------------------------
echo 'CODE           ' "$CODE"
echo ' ' "$(python3 --version) $(which python3)"
echo ' ' "$(pip3 -V) "
echo '  PYTHONPATH   ' "$PYTHONPATH"
echo '  github key   ' "$github"
