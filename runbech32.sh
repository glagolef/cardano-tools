#!/bin/sh
#specify bech32 path below if it's not in $PATH
#bech32=""
if command -v bech32 addr $1 > /dev/null 2>&1
then
  echo $1 | bech32 addr
else
  echo $1
fi