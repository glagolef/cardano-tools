# cardano-tools

## random-delegator-picker

This python program draws a weighted random active delegator or delegators of a particular pool for a giveaway. 

The more ada a delegator has, the more chance it has of getting drawn.

The pool's owner and reward accounts are automatically removed from the draw as including them would likely be illegal.

The tool is based off [pooltool.io getSigma.py script](https://github.com/papacarp/pooltool.io/tree/master/leaderLogs)

## Dependencies

Requires ```python3```, ledger.json (generated by ```cardano-cli```)

## Usage & Examples
This pulls down the latest ledger state and may take a few minutes. No need to run more than once per epoch as _active_ delegators are used.
```bash
cardano-cli query ledger-state --mainnet > ledger.json
```
This will generate 3 unique winners, excluding 1b9bb7f381fd56c239903b380f44583ce5c43dd51a350497bc0824a4 staking key as well as delegators that have less than 1 ada.
```bash
python3 randomdelegatorpicker.py --ledger ledger.json --pool-id b40683f4baad755ff60f26dc73c3e371ac4c5e422feef2fc1f5f29bf --exclude 1b9bb7f381fd56c239903b380f44583ce5c43dd51a350497bc0824a4 --winners 3 --min-ada 1 --unique
```
If working directory has a ledger.json file already, only --pool-id argument is required. All others are optional but may be useful to specify.
```bash
python3 randomdelegatorpicker.py -h
usage: randomdelegatorpicker.py [-h] -p ID [-l LEDGER] [-e EXCLUDE_ADDRESSES] [-w NUMBER_WINNERS] [-m MIN_ADA] [-u]

Get random winner(s) for a raffle/giveaway. Example usage: python3 random.py -l ledger.json -p b40683f4baad755ff60f26dc73c3e371ac4c5e422feef2fc1f5f29bf -e
1b9bb7f381fd56c239903b380f44583ce5c43dd51a350497bc0824a4 -w 3 -m 1 -u

optional arguments:
  -h, --help            show this help message and exit
  -p ID, --pool-id ID   the pool ID
  -l LEDGER, --ledger LEDGER
                        the path to a current ledger-state JSON file
  -e EXCLUDE_ADDRESSES, --exclude EXCLUDE_ADDRESSES
                        if specified will exclude provided address(es) from the raffle. E.g. --exclude
                        "002545ccd16d81e202288049d22f0a50c3fbf520cf2a206ccd7765ff"
  -w NUMBER_WINNERS, --winners NUMBER_WINNERS
                        if specified will generate specified number of winners
  -m MIN_ADA, --min-ada MIN_ADA
                        if specified will ignore addresses containing balances below the provided threshold
  -u, --unique          if specified, the winners will be unique (max 1 prize per address)

```
