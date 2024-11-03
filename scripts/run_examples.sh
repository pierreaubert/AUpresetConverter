#!/bin/sh

cd examples_rews && for i in *.txt; do
  ../eq2eq.py -input "$i" -format aupreset -output ../examples_aupreset/"${i%.txt}.aupreset";
done
mv *.aupreset ../examples_aupreset
cd ..

cd examples_rews && for i in *.txt; do
  ../eq2eq.py -input "$i" -format rmetmeq -output ../examples_tmeq/"${i%.txt}.tmeq";
done
mv *.tmeq ../examples_tmeq

cd ..
