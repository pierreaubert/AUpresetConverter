#!/bin/sh

cd examples_rews && for i in *.txt; do
  ../rew2aupreset.py -i "$i" -o ../examples_aupreset/"${i%.txt}.aupreset";
done

cd ..

