#!/bin/env python3
import json
import argparse
import random
from os import path

parser = argparse.ArgumentParser(
    description="Get random winner(s) for a raffle/giveaway. Example usage: python3 random.py --ledger ledger.json"
                + "--pool-id b40683f4baad755ff60f26dc73c3e371ac4c5e422feef2fc1f5f29bf "
                + "--exclude 1b9bb7f381fd56c239903b380f44583ce5c43dd51a350497bc0824a4 --winners 3 --min-ada 1 --unique"
)
parser.add_argument("--pool-id", '-p', dest="id", help="the pool ID", required=True)
parser.add_argument(
    "--ledger", '-l',
    dest="ledger",
    default="ledger.json",
    help="the path to a current ledger-state JSON file",
)
parser.add_argument(
    "--exclude", '-e',
    dest="exclude_addresses",
    help="if specified will exclude provided address(es) from the raffle.\nE.g. --exclude "
        + "\"1b9bb7f381fd56c239903b380f44583ce5c43dd51a350497bc0824a4,"
          "002545ccd16d81e202288049d22f0a50c3fbf520cf2a206ccd7765ff\""
)
parser.add_argument(
    "--winners", '-w',
    dest="number_winners",
    help="if specified will generate specified number of winners"
)
parser.add_argument(
    "--min-ada", '-m',
    dest="min_ada",
    help="if specified will ignore addresses containing balances below the provided threshold"
)
parser.add_argument(
    "--unique", '-u',
    action="store_true",
    help="if used, the winners will be unique (max 1 prize per address). "
         + "Only makes sense to use if --winners is specified."
)
# Args
args = parser.parse_args()

poolId = args.id
ledger = args.ledger
exclude_addresses = args.exclude_addresses
number_winners = args.number_winners
min_ada = args.min_ada
unique = args.unique

million = 1000000


def get_winner(unique, winner, n, delegators, total_stake):
    accum = 0
    print("Prize #" + str(n) + " Winning number: " + str(winner))
    for delegator in delegators:
        del_stake = delegators[delegator]
        accum += del_stake
        if accum > winner:
            print( "Congrats to " + delegator + " (" + str(round(del_stake / million)) + "/" +
                  str(round(total_stake / million)) + " ada or " + (
                      str(round(del_stake / total_stake * 100, 2))) + "% chance)!\n")
            if unique:
                delegators[delegator] = 0
                total_stake -= del_stake
            return total_stake


if not path.exists(ledger):
    print("We tried but could not locate your ledger-state JSON file!")
    print("Use: \033[1;34mcardano-cli query ledger-state --mainnet --out-file ledger.json\033[0m to export one!")
    exit()

with open(ledger) as f:
    ledger = json.load(f)

stakequery = "pstakeSet"
stakeinfo = "active"

blockstakedelegators = {}
blockstake = {}
bs = {}

epoch=ledger['lastEpoch']
print("Current Epoch: " + str(epoch))
totalRecordedActiveStake=int(ledger['stakeDistrib'][poolId]['individualPoolStake']['numerator'])/million
stateBefore = ledger["stateBefore"]
# Exclude pool owners and reward accounts
poolData = stateBefore['esLState']['delegationState']['pstate']['pParams pState'][poolId]
pool_owners = poolData['owners']
pool_rewards = poolData['rewardAccount']['credential']['key hash']
ledger_set = stateBefore["esSnapshots"][stakequery]

if exclude_addresses is None:
    exclude_addresses = ""
for po in pool_owners:
    exclude_addresses += str(po) + ","
if not exclude_addresses.__contains__(pool_rewards):
    exclude_addresses += str(pool_rewards)
print("Excluding the following staking addresses: " + str(exclude_addresses))

# Retrieve list of delegators
for item2 in ledger_set["delegations"]:
    keyhashobj = []
    for itemsmall in item2:
        if "key hash" in itemsmall:
            keyhashobj.append(itemsmall["key hash"])
        else:
            poolid = itemsmall
    if poolid not in blockstakedelegators:
        blockstakedelegators[poolid] = keyhashobj
    else:
        blockstakedelegators[poolid] = (
                blockstakedelegators[poolid] + keyhashobj
        )

for item2 in ledger_set["stake"]:
    delegatorid = None
    for itemsmall in item2:
        if isinstance(itemsmall, int):
            snapstake = itemsmall
        else:
            delegatorid = itemsmall["key hash"]
    if delegatorid != None:
        if delegatorid not in blockstake:
            blockstake[delegatorid] = snapstake
        else:
            blockstake[delegatorid] = blockstake[delegatorid] + snapstake
total_bs = 0

active_addresses = 0
total_stake = 0
delegators = {}

if min_ada is None:
    min_ada = 0
else:
    min_ada = abs(int(min_ada) * million)

excluded_stake = 0
for d in blockstakedelegators[poolId]:
    if d in blockstake:
        activestake = blockstake[d]
        if exclude_addresses is not None and exclude_addresses.__contains__(d):
            excluded_stake += activestake
        elif activestake > min_ada:
            total_stake += activestake
            active_addresses += 1
            delegators[d] = activestake
print("Total pool stake on record: " + str(totalRecordedActiveStake))
print("Total calculated pool stake: " + str((total_stake + excluded_stake) / million) + "\n")
print("Total eligible stake: " + str(total_stake / million))
print("Number of eligible addresses: " + str(active_addresses))

if number_winners is not None:
    number_winners = abs(int(number_winners))
    if unique and active_addresses < number_winners:
        exit("Too few delegators to pick from. Try a lower number of winners or omit --unique flag")
    for i in range(number_winners):
        winning_num = random.randint(1, total_stake)
        total_stake = get_winner(unique, winning_num, i+1, delegators, total_stake)
else:
    winning_num = random.randint(1, total_stake)
    total_stake = get_winner(unique, winning_num, 1, delegators, total_stake)
# print("Full list of eligible delegators:\n" + str(delegators))
print("Done!")