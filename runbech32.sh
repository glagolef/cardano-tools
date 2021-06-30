#!/bin/sh
#specify bech32 path below if it's not in $PATH
#bech32=""
if bech32 -v COMMAND &> /dev/null
then
  echo $1 | bech32 addr
else
  echo $1
fi