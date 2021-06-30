#!/bin/env python3
import json
import argparse
import random
import subprocess

from os import path

# Global var
try_bech32 = True


def parse_all_args():
    python_cmd = "python3 randomdelegatorpicker.py "
    ledger_eg = "--ledger ledger.json "
    poolid_eg = "--pool-id b40683f4baad755ff60f26dc73c3e371ac4c5e422feef2fc1f5f29bf "
    policyid_eg = "--policy-id 0e14267a8020229adc0184dd25fa3174c3f7d6caadcb4425c70e7c0 "
    exclude_eg = "--exclude 002545ccd16d81e202288049d22f0a50c3fbf520cf2a206ccd7765ff "
    winners_eg = "--winners 3 "
    min_tokens_eg = "--min-tokens 1 "
    unique_eg = "--unique "
    parser = argparse.ArgumentParser(
        description="Get random winner(s) for a raffle/giveaway.\nExample usage 1: "
                    + python_cmd + poolid_eg + exclude_eg + winners_eg + min_tokens_eg + unique_eg + "\n\n"
                    + "Example usage 2:\n" + python_cmd + ledger_eg + policyid_eg + winners_eg + min_tokens_eg + unique_eg
    )
    parser.add_argument('-i', "--pool-id", dest="id", help="the pool ID")
    parser.add_argument('-p', "--policy-id", dest="policyId", help="the token policy ID")
    parser.add_argument('-l', "--ledger",
                        dest="ledger",
                        default="ledger.json",
                        help="the path to a current ledger-state JSON file",
                        )
    parser.add_argument(
        '-e', "--exclude",
        dest="exclude_addresses",
        help="if specified will exclude provided address(es) from the raffle.\nE.g. --exclude "
             + "\"1b9bb7f381fd56c239903b380f44583ce5c43dd51a350497bc0824a4,"
               "002545ccd16d81e202288049d22f0a50c3fbf520cf2a206ccd7765ff\""
    )
    parser.add_argument(
        '-w', "--winners",
        dest="number_winners",
        help="if specified will generate specified number of winners"
    )
    parser.add_argument(
        '-m', "--min-tokens",
        dest="min_tokens",
        help="if specified will ignore addresses containing token balances below the provided threshold"
    )
    parser.add_argument(
        '-u', "--unique",
        action="store_true",
        help="if used, the winners will be unique (max 1 prize per address). "
             + "Only makes sense to use if --winners is specified."
    )
    return parser.parse_args()


def maybe_run_bech32(addr):
    global try_bech32
    if try_bech32:
        try:
            p1 = subprocess.p1 = subprocess.Popen(["./runbech32.sh", addr], stdout=subprocess.PIPE)
            decoded_address = p1.stdout.readline().decode("utf-8").rstrip()
            p1.stdout.close()
            return decoded_address
        except:
            try_bech32 = False
    return addr


def process_winner(winning_num, n, _total_tickets):
    accum = 0
    print("Prize #" + str(n) + " Winning number: " + str(winning_num))
    for p in eligible_participants:
        participant_tickets = eligible_participants[p]
        if participant_tickets == 0:
            continue
        accum += participant_tickets
        if accum > winning_num and participant_tickets > 0:
            if try_bech32:
                winner = maybe_run_bech32(p)
            print_result(winner, participant_tickets, _total_tickets)
            if unique:
                eligible_participants[p] = 0
                _total_tickets -= participant_tickets
            break
    if (accum < winning_num):
        print("!!! Something probably went wrong. accum < winning_num. " + ": accum =" + str(
            accum) + ", winning_num = " + str(winning_num))
    return _total_tickets


def calculate_chance(tickets, total_tickets):
    return str(round(tickets / total_tickets * 100, 2))


def print_result(winner, tickets, total_tickets):
    if giveaway_type == 1:
        congrats = "Congrats to " + winner + " (" + str(round(tickets / million)) + " out of " \
                   + str(round(total_tickets / million)) + " ADA, " \
                   + (calculate_chance(tickets, total_tickets)) + "% chance)!\n"
    else:
        congrats = "Congrats to " + winner + " (" + str(tickets) + " out of " + \
                   str(total_tickets) + " tokens, " + (calculate_chance(tickets, total_tickets)) + "% chance)!\n"
    print(congrats)


def get_min_tokens():
    if min_tokens_arg is None:
        _min_tokens = 0
    else:
        _min_tokens = abs(int(min_tokens_arg))

    if giveaway_type == 1:
        _min_tokens *= million
    return _min_tokens


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
    print("--pool-id and --policy-id arguments are not supported, please use only one of them.")
    exit()
elif poolId is not None:
    giveaway_type = 1
elif policyId is not None:
    giveaway_type = 2

# TODO:implement --exclude for token giveaways
if giveaway_type == 2 and exclude_addresses is not None:
    print("--exclude ADDRESSES param is not yet supported for token giveaways and will be ignored.")

min_tokens = get_min_tokens()

ledger = args.ledger

if not path.exists(ledger):
    print("We tried but could not locate your ledger-state JSON file!")
    print("Use: \033[1;34mcardano-cli query ledger-state --mainnet --out-file ledger.json\033[0m to export one!")
    exit()

with open(ledger) as f:
    ledger = json.load(f)

eligible_participants_total = 0
tickets_total = 0
eligible_participants = {}

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
    print("Excluding the following addresses: " + str(exclude_addresses))

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
                eligible_participants_total += 1
                eligible_participants[d] = activestake
            else:
                excluded_stake += activestake
    print("Total pool stake on record: " + str(totalRecordedActiveStake))
    print("Total calculated pool stake: " + str((tickets_total + excluded_stake) / million) + "\n")
    print("Total eligible stake: " + str(tickets_total / million))
    print("Number of eligible addresses: " + str(eligible_participants_total))

elif giveaway_type == 2:
    utxos = ledger["stateBefore"]['esLState']['utxoState']['utxo']
    policy_holders = {}
    total_tokens = 0
    total_token_holders = 0
    total_eligible_tokens = 0
    for utxo in utxos:
        numberOfTokens = 0
        for policy in utxos[utxo]['amount']['policies']:
            if policy == policyId:
                address = utxos[utxo]['address']
                ph_tokens = 0
                total_token_holders += 1
                for x in utxos[utxo]['amount']['policies'][policyId]:
                    ph_tokens += (utxos[utxo]['amount']['policies'][policyId][x])
                if ph_tokens > min_tokens:
                    policy_holder_address = policy_holders.get(address)
                    if policy_holder_address is not None and policy_holder_address > 0:
                        policy_holders[address] += ph_tokens
                        total_token_holders -= 1
                    else:
                        policy_holders[address] = ph_tokens
                    total_eligible_tokens += ph_tokens
                total_tokens += ph_tokens
    tickets_total = total_eligible_tokens
    eligible_participants = policy_holders
    eligible_participants_total = len(policy_holders)

    print("Total # token holders: " + str(total_token_holders))
    print("Total # tokens minted: " + str(total_tokens))
    print("Total # eligible token holders: " + str(eligible_participants_total))
    print("Total # eligible tokens: " + str(total_eligible_tokens))

f.close()

# print("Full list of eligible participants:\n" + str(participants))
print()

if number_winners_arg is not None:
    number_winners = abs(int(number_winners_arg))
    try_bech32 = True if giveaway_type == 2 else False
    problems = 0
    if unique and eligible_participants_total < number_winners:
        exit("Too few delegators to pick from. Try a lower number of winners or omit --unique flag")
    for i in range(number_winners):
        try:
            winning_num = random.randint(1, tickets_total)
            tickets_total = process_winner(winning_num, i + 1, tickets_total)
        except:
            problems += 1
    if problems > 0:
        print("A number of problems occurred:" + str(problems))
else:
    winning_num = random.randint(1, tickets_total)
    tickets_total = process_winner(winning_num, 1, tickets_total)
if not try_bech32:
    print("You may need to use bech32 to convert winning addresses to 'addr...' format.\n")
print("Done! Well done to the winners, best of luck next time to everyone else!")
