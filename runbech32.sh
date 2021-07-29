#!/bin/sh
#specify bech32 path below if it's not in $PATH
#bech32="/path/to/bech32"
if command -v bech32 addr $1 > /dev/null 2>&1
then
  if [[ $1 == addr* ]]
  then
    echo $1 | bech32
  else
    echo $1 | bech32 addr
  fi
else
  echo $1
fi