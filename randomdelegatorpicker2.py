#!/bin/env python3
import json
import argparse
import math
import random
import subprocess
from os import path
import requests
from requests.structures import CaseInsensitiveDict
import time
import functools
import datetime
# poolId = 'pool1ksrg8a964464las0ymw88slrwxkychjz9lh09lqltu5m7nw3pq0'
start_time = datetime.datetime.now()

headers = CaseInsensitiveDict()
headers["project_id"] = "3teoBXL8asW1eHbwNSwM8InJtJmNyFfJ"
million = 1000000
blockfrostURL = "https://cardano-mainnet.blockfrost.io"

fetchFailureError="Fetching pool delegations failed. Trying again"

def parse_all_args():
    python_cmd = "python3 randomdelegatorpicker.py "
    poolid_eg = "--pool-id b40683f4baad755ff60f26dc73c3e371ac4c5e422feef2fc1f5f29bf "
    exclude_eg = "--exclude 002545ccd16d81e202288049d22f0a50c3fbf520cf2a206ccd7765ff "
    winners_eg = "--winners 3 "
    min_tokens_eg = "--min-tokens 1 "
    unique_eg = "--unique "
    parser = argparse.ArgumentParser(
        description="Get random winner(s) for a raffle/giveaway.\nExample usage 1: "
                    + python_cmd + poolid_eg + exclude_eg + winners_eg + min_tokens_eg + unique_eg + "\n\n"
    )
    parser.add_argument('-i', "--pool-id", dest="id", help="the pool ID")
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

def calculate_amount(a):
    amount = extract_amount(a)
    return round(maybe_apply_sqrt(amount / million))

def extract_amount(a):
    return int(a['amount'])

def fetchBlockfrostList(str):
    pageNum = 1
    list = []
    while True:
        try:
            response = requests.get(
                f"{blockfrostURL}{str}?page={pageNum}",
                # blockfrostURL + str + f"?page=1",
                headers=headers)

            if response.status_code == 200:
                if response.content == b'[]':
                    break
                respList = response.json()
                list.extend(respList)
                pageNum += 1
            else:
                print("Retrying. Got response code " + str(response.status_code))
        except:
            print(fetchFailureError)
    return list

def process_winner(winning_num, prize_num, _total_tickets):
    accum = 0
    print("Prize #" + str(prize_num) + " Winning number: " + str(winning_num))
    for participant in eligible_participants:

        (participant_tickets, participant_stake) = eligible_participants[participant]
        if participant_tickets == 0:
            continue
        accum += participant_tickets
        if accum >= winning_num:
            print_result(participant, participant_stake, participant_tickets, _total_tickets)
            winners.append(participant)
            if unique:
                eligible_participants[participant] = (0, 0)
                _total_tickets -= participant_tickets
            break
    if round(accum) < winning_num:
        print("!!! Something went wrong. accum < winning_num. " + ": accum =" + str(accum)
              + ", winning_num = " + str(winning_num))
    return _total_tickets


def calculate_chance(tickets, total_tickets):
    return round(tickets / total_tickets * 100, 2)


def print_result(winner, tokens, tickets, total_tickets):
    congrats = get_congrats_message(winner, tokens, tickets, total_tickets)
    print(congrats)


def get_congrats_message(winner, tokens, tickets, total_tickets):
    return "Congrats to " + winner + " (~" + str(tokens) +" ADA) " \
           + " (" + str(tickets) + " out of " \
           + str(total_tickets) + " tickets, " \
           + str(calculate_chance(tickets, total_tickets)) + "% chance)!\n"


def get_min_tokens():
    if min_tokens_arg is None:
        _min_tokens = 0
    else:
        _min_tokens = abs(int(min_tokens_arg))
    return _min_tokens


def maybe_apply_sqrt(num):
    if use_sqrt:
        return math.sqrt(num)
    else:
        return num


# Parsing Args
args = parse_all_args()

poolId = args.id

exclude_addresses = args.exclude_addresses
number_winners_arg = args.number_winners
min_tokens_arg = args.min_tokens
unique = args.unique
use_sqrt = args.sqrt

delegator_str = "delegator"
token_hodler_str = "token_hodler"

giveaway_type = ""

if poolId is None:
    print("--pool-id was not specified!")
    exit()

min_tokens = get_min_tokens()
number_winners = abs(int(number_winners_arg)) if number_winners_arg is not None else 1

fetchSuccessful = False
delegsList = fetchBlockfrostList(f"/api/v0/pools/{poolId}/delegators")
totalStakedAmount = 0
eligible_participants = {}
eligible_tickets_total = 0

for deleg in delegsList:
    stake_address = deleg['address']
    fetchSuccessful = False
    pageNum = 1

    rewardsList = fetchBlockfrostList(f"/api/v0/accounts/{stake_address}/history")
    # for rewards in rewardsList:
    rewardsWithMyPool = list(filter(lambda a: a['pool_id'] == poolId, rewardsList))
    rewardsLength = len(rewardsWithMyPool)
    if rewardsLength > 1:
        totalStakeWithMyPool = functools.reduce(lambda a, b :
                                                calculate_amount(a) if isinstance(a, dict) else a + calculate_amount(b),
                                                rewardsWithMyPool)
        last_staked_amount = round(int(rewardsWithMyPool[len(rewardsWithMyPool) - 1]['amount']) / million)
    elif rewardsLength == 1:
        totalStakeWithMyPool = calculate_amount(rewardsList[0])
        last_staked_amount = round(int(rewardsWithMyPool[len(rewardsWithMyPool) - 1]['amount']) / million)
    else:
        totalStakeWithMyPool = 0
        last_staked_amount = 0
    totalStakedAmount += last_staked_amount
    print(stake_address + " : " + str(last_staked_amount) + " : " + str(totalStakeWithMyPool))
    if last_staked_amount > min_tokens:
        eligible_tickets_total += totalStakeWithMyPool
        eligible_participants[stake_address] = (totalStakeWithMyPool,last_staked_amount)
eligible_participants_total = len(eligible_participants)
print("total staked amount: " + str(totalStakedAmount))
print("Total # of eligible addresses: " + str(eligible_participants_total))

if unique and eligible_participants_total < number_winners:
    exit("Too few delegators to pick from. Try a lower number of winners or omit --unique flag")
tickets_total = eligible_tickets_total
errors = 0
winners = []
for prize_num in range(number_winners):
    try:
        winning_num = random.randint(1, tickets_total)
        tickets_total = process_winner(winning_num, prize_num, tickets_total)
    except:
        errors += 1
if errors > 0:
    print("A number of errors occurred:" + str(errors))

print(str(winners))
print("Done! Well done to the winners, best of luck next time to everyone else!")
end_time = datetime.datetime.now()
print("Start time: " + str(start_time))
print("End time: " + str(end_time))
print("Total execution time: " + str(end_time - start_time))
