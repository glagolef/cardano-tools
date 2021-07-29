#!/bin/env python3
import json
import argparse
import math
import random
import subprocess

from os import path


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
    parser.add_argument(
        '-s', "--sqrt",
        action="store_true",
        help="if used, the participants' number of tickets will be square rooted, "
             + "giving smaller guys a greater chance of winning."
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


def process_winner(winning_num, prize_num, _total_tickets):
    accum = 0
    eligible_participants_length = len(eligible_participants)
    print("Prize #" + str(prize_num) + " Winning number: " + str(winning_num))
    for participant in eligible_participants:
        participant_tickets = eligible_participants[participant]
        if participant_tickets == 0:
            continue
        accum += participant_tickets
        if round(accum) >= winning_num and participant_tickets > 0:
            winner = maybe_run_bech32(participant)
            print_result(winner, participant_tickets, _total_tickets)
            if unique:
                eligible_participants[participant] = 0
                _total_tickets -= participant_tickets
            break
    if round(accum) < winning_num:
        print("!!! Something probably went wrong. accum < winning_num. " + ": accum =" + str(accum)
              + ", winning_num = " + str(winning_num))
    return round(_total_tickets)


def calculate_chance(tickets, total_tickets):
    return str(round(tickets / total_tickets * 100, 2))


def print_result(winner, tickets, total_tickets):
    tickets = round(tickets)
    if giveaway_type == delegator_str and not use_sqrt:
        divisor = million
    else:
        divisor = 1
    congrats = get_congrats_message(winner, tickets, total_tickets, divisor)
    print(congrats)


def get_congrats_message(winner, tickets, total_tickets, divisor):
    return "Congrats to " + winner + " (" + str(round(tickets / divisor)) + " out of " \
           + str(round(total_tickets / divisor)) + " tickets, " \
           + (calculate_chance(tickets, total_tickets)) + "% chance)!\n"


def get_min_tokens():
    if min_tokens_arg is None:
        _min_tokens = 0
    else:
        _min_tokens = abs(int(min_tokens_arg))

    if giveaway_type == delegator_str:
        _min_tokens *= million
    return _min_tokens


def maybe_apply_sqrt(num):
    if use_sqrt:
        return math.sqrt(num)
        # if more than 1 winners, do sqrt operation when collecting eligible participants
    else:
        return num


# Parsing Args
args = parse_all_args()

poolId = args.id
policyId = args.policyId

exclude_addresses = args.exclude_addresses
number_winners_arg = args.number_winners
min_tokens_arg = args.min_tokens
unique = args.unique
use_sqrt = args.sqrt

million = 1000000
delegator_str = "delegator"
token_hodler_str = "token_hodler"

giveaway_type = ""
try_bech32 = False

if poolId is None and policyId is None:
    print("Neither --pool-id nor --policy-id was specified!")
    exit()
elif poolId is not None and policyId is not None:
    print("--pool-id and --policy-id arguments are not supported, please use only one of them.")
    exit()
elif poolId is not None:
    giveaway_type = delegator_str
elif policyId is not None:
    giveaway_type = token_hodler_str
    try_bech32 = True

# TODO:implement --exclude for token giveaways
if giveaway_type == token_hodler_str and exclude_addresses is not None:
    print("--exclude ADDRESSES param is not yet supported for token giveaways and will be ignored.")

min_tokens = get_min_tokens()

ledger = args.ledger

if number_winners_arg is not None:
    number_winners = abs(int(number_winners_arg))
else:
    number_winners = 1

problems = 0

if not path.exists(ledger):
    print("We tried but could not locate your ledger-state JSON file!")
    print("Use: \033[1;34mcardano-cli query ledger-state --mainnet --out-file ledger.json\033[0m to export one!")
    exit()

with open(ledger) as ledger_stream:
    ledger = json.load(ledger_stream)

eligible_participants_total = 0
eligible_participants = {}

ineligible_participants_total = 0
eligible_tokens_total = 0
ineligible_tokens_total = 0

sqrt_eligible_tokens_total = 0

if giveaway_type == delegator_str:
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
    for delegator in blockstakedelegators[poolId]:
        if delegator in blockstake:
            activestake = blockstake[delegator]
            if exclude_addresses.__contains__(delegator) or min_tokens > activestake:
                ineligible_tokens_total += activestake
                ineligible_participants_total += 1
            else:
                eligible_tokens_total += activestake
                activestake = maybe_apply_sqrt(activestake)
                sqrt_eligible_tokens_total += activestake
                eligible_participants[delegator] = activestake
    eligible_participants_total = len(eligible_participants)
    print("Total pool stake on record: " + str(totalRecordedActiveStake))
    print("Total calculated pool stake (ADA): " + str((eligible_tokens_total + ineligible_tokens_total) / million) + "\n")
    print("Total # of eligible addresses: " + str(eligible_participants_total))
    print("Total eligible stake (ADA): " + str(eligible_tokens_total / million))

elif giveaway_type == token_hodler_str:
    utxos = ledger["stateBefore"]['esLState']['utxoState']['utxo']
    for utxo in utxos:
        numberOfTokens = 0
        for policy in utxos[utxo]['amount']['policies']:
            if policy == policyId:
                address = utxos[utxo]['address']
                ph_tokens = 0
                for x in utxos[utxo]['amount']['policies'][policyId]:
                    ph_tokens += (utxos[utxo]['amount']['policies'][policyId][x])
                if ph_tokens > min_tokens:
                    policy_holder_address = eligible_participants.get(address)
                    eligible_tokens_total += ph_tokens
                    ph_tokens = maybe_apply_sqrt(ph_tokens)
                    sqrt_eligible_tokens_total += ph_tokens
                    if policy_holder_address is not None and policy_holder_address > 0:
                        eligible_participants[address] += ph_tokens
                        # discount multiple entries by same address
                        eligible_participants_total -= 1
                    else:
                        eligible_participants[address] = ph_tokens
                else:
                    ph_tokens = maybe_apply_sqrt(ph_tokens)
                    ineligible_tokens_total += ph_tokens
                    ineligible_participants_total += 1

    eligible_participants_total = len(eligible_participants)

    print("Total # token holders: " + str(ineligible_participants_total + eligible_participants_total))
    print("Total # tokens minted: " + str(eligible_tokens_total + ineligible_tokens_total))
    print("Total # eligible token holders: " + str(eligible_participants_total))
    print("Total # eligible tokens: " + str(eligible_tokens_total))

if use_sqrt:
    print("Total eligible tickets: " + str(sqrt_eligible_tokens_total))
    eligible_tokens_total = sqrt_eligible_tokens_total

ledger_stream.close()

# print("Full list of eligible participants:\n" + str(participants))
print()

# if number_winners > 1:
if unique and eligible_participants_total < number_winners:
    exit("Too few delegators to pick from. Try a lower number of winners or omit --unique flag")
tickets_total = round(eligible_tokens_total)
for prize_num in range(number_winners):
    try:
        winning_num = random.randint(1, tickets_total)
        tickets_total = process_winner(winning_num, prize_num + 1, tickets_total)
    except:
        problems += 1
if problems > 0:
    print("A number of problems occurred:" + str(problems))

if not try_bech32 and giveaway_type == token_hodler_str:
    print("You may need to use bech32 to convert winning addresses to 'addr...' format.\n")
print("Done! Well done to the winners, best of luck next time to everyone else!")
