#!/bin/env python3
import json
import argparse
import random
import common
import subprocess

from os import path


def parse_all_args():
    parser = argparse.ArgumentParser(
        description="Get random winner(s) for a raffle/giveaway.\nExample usage 1: python3 random.py --ledger ledger.json"
                    + "--pool-id b40683f4baad755ff60f26dc73c3e371ac4c5e422feef2fc1f5f29bf "
                    + "--exclude 002545ccd16d81e202288049d22f0a50c3fbf520cf2a206ccd7765ff "
                    + "--winners 3 --min-tokens 1 --unique" + "\n\n"
                    + "Example usage 2: python3 random.py --ledger ledger.json "
                    + "--policy-id 0e14267a8020229adc0184dd25fa3174c3f7d6caadcb4425c70e7c04 "
                      "--winners 3 --min-tokens 3 --unique"
    )
    parser.add_argument("--pool-id", '-i', dest="id", help="the pool ID")
    parser.add_argument("--policy-id", '-p', dest="policyId", help="the token policy ID")
    parser.add_argument("--ledger", '-l',
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
        "--min-tokens", '-m',
        dest="min_tokens",
        help="if specified will ignore addresses containing token balances below the provided threshold"
    )
    parser.add_argument(
        "--unique", '-u',
        action="store_true",
        help="if used, the winners will be unique (max 1 prize per address). "
             + "Only makes sense to use if --winners is specified."
    )
    return parser.parse_args()


def maybe_run_bech32(addr, try_bech32):
    if common.bech32 == "":
        print("Empty path for bech32. You'll need to use bech32 to convert winning addresses to 'addr...' format.\n")
        try_bech32 = False
    elif try_bech32:
        try:
            return subprocess.run([common.bech32, "addr <<< " + addr])
        except:
            print("invalid path for bech32:" + common.bech32
                  + "\nYou'll need to use bech32 to convert winning addresses to 'addr...' format.\n")
            try_bech32 = False
    return addr, try_bech32


def get_winner(unique, winner, n, participants, total_tickets):
    accum = 0
    print("Prize #" + str(n) + " Winning number: " + str(winner))

    for participant in participants:
        participant_tickets = participants[participant]
        accum += participant_tickets
        try_bech32 = True if giveaway_type == 2 else False
        if accum > winner:
            participant, try_bech32 = maybe_run_bech32(participant, try_bech32)
            print_result(giveaway_type, participant, participant_tickets, total_tickets)
            if unique:
                participants[participant] = 0
                total_tickets -= participant_tickets
            return total_tickets


def calculate_chance(tickets, total_tickets):
    return str(round(tickets / total_tickets * 100, 2))


def print_result(giveaway_type, winner, tickets, total_tickets):
    switcher = {
        1: "Congrats to " + winner + " (" + str(round(tickets / million)) + " out of " +
           str(round(total_tickets / million)) + " ADA, " + (calculate_chance(tickets, total_tickets)) + "% chance)!\n",
        2: "Congrats to " + winner + " (" + str(tickets) + " out of " +
           str(total_tickets) + " tokens, " + (calculate_chance(tickets, total_tickets)) + "% chance)!\n"
    }
    print(switcher.get(giveaway_type))


def get_min_tokens(min_tokens_arg, giveaway_type):
    if min_tokens_arg is None:
        min_tokens = 0
    else:
        min_tokens = abs(int(min_tokens_arg))

    if giveaway_type == 1:
        min_tokens *= million
    return min_tokens


# Parsing Args
args = parse_all_args()

poolId = args.id
policyId = args.policyId

exclude_addresses = args.exclude_addresses
number_winners_arg = args.number_winners
min_tokens_arg = args.min_tokens
unique = args.unique

million = 1000000

giveaway_type = 0
if poolId is None and policyId is None:
    print("Neither --pool-id nor --policy-id was specified!")
    exit()
elif poolId is not None and policyId is not None:
    print("--pool-id and --policy-id arguments are not supported.")
    exit()
elif poolId is not None:
    giveaway_type = 1
elif policyId is not None:
    giveaway_type = 2

min_tokens = get_min_tokens(min_tokens_arg, giveaway_type)

ledger = args.ledger

if not path.exists(ledger):
    print("We tried but could not locate your ledger-state JSON file!")
    print("Use: \033[1;34mcardano-cli query ledger-state --mainnet --out-file ledger.json\033[0m to export one!")
    exit()

with open(ledger) as f:
    ledger = json.load(f)

participants_total = 0
tickets_total = 0
participants = {}

if giveaway_type == 1:
    stakequery = "pstakeSet"
    stakeinfo = "active"

    blockstakedelegators = {}
    blockstake = {}
    bs = {}

    epoch = ledger['lastEpoch']
    print("Current Epoch: " + str(epoch))
    totalRecordedActiveStake = int(ledger['stakeDistrib'][poolId]['individualPoolStake']['numerator']) / million
    stateBefore = ledger["stateBefore"]
    # Exclude pool owners and reward accounts
    poolData = stateBefore['esLState']['delegationState']['pstate']['pParams pState'][poolId]
    pool_owners = poolData['owners']
    pool_rewards = poolData['rewardAccount']['credential']['key hash']
    ledger_set = stateBefore["esSnapshots"][stakequery]

    if exclude_addresses is None:
        exclude_addresses = ""
    for po in pool_owners:
        exclude_addresses += "," + str(po)
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
        if delegatorid is not None:
            if delegatorid not in blockstake:
                blockstake[delegatorid] = snapstake
            else:
                blockstake[delegatorid] = blockstake[delegatorid] + snapstake
    total_bs = 0
    excluded_stake = 0
    for d in blockstakedelegators[poolId]:
        if d in blockstake:
            activestake = blockstake[d]
            if exclude_addresses is not None and exclude_addresses.__contains__(d):
                excluded_stake += activestake
            elif activestake > min_tokens:
                tickets_total += activestake
                participants_total += 1
                participants[d] = activestake
            else:
                excluded_stake += activestake
    print("Total pool stake on record: " + str(totalRecordedActiveStake))
    print("Total calculated pool stake: " + str((tickets_total + excluded_stake) / million) + "\n")
    print("Total eligible stake: " + str(tickets_total / million))
    print("Number of eligible addresses: " + str(participants_total))
    # print("Full list of eligible delegators:\n" + str(delegators))

elif giveaway_type == 2:
    utxos = ledger["stateBefore"]['esLState']['utxoState']['utxo']
    policyHolders = {}
    totalTokens = 0
    totalEligibleTokens = 0
    for utxo in utxos:
        numberOfTokens = 0
        for policy in utxos[utxo]['amount']['policies']:
            if policy == policyId:
                address = utxos[utxo]['address']
                tokens = 0
                for x in utxos[utxo]['amount']['policies'][policyId]:
                    tokens += (utxos[utxo]['amount']['policies'][policyId][x])
                if tokens > min_tokens:
                    policyHolders[address] = tokens
                    totalEligibleTokens += tokens
                totalTokens += tokens

    tickets_total = totalEligibleTokens
    participants = policyHolders
    participants_total = len(policyHolders)

    print(policyHolders)
    print("Total # policy holders: " + str(participants_total))
    print("Total # tokens minted: " + str(totalTokens))
    print("Total # tokens eligible: " + str(totalEligibleTokens))

print()
if number_winners_arg is not None:
    number_winners = abs(int(number_winners_arg))
    if unique and participants_total < number_winners:
        exit("Too few delegators to pick from. Try a lower number of winners or omit --unique flag")
    for i in range(number_winners):
        winning_num = random.randint(1, tickets_total)
        tickets_total = get_winner(unique, winning_num, i + 1, participants, tickets_total)
else:
    winning_num = random.randint(1, tickets_total)
    tickets_total = get_winner(unique, winning_num, 1, participants, tickets_total)
print("Done!")
