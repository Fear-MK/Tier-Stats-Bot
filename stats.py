from collections import defaultdict
import csv
import aiohttp
import asyncio
import sys

from common import *

rt_data_url = 'https://www.mariokartboards.com/lounge/csv/events_rt.csv'
ct_data_url = 'https://www.mariokartboards.com/lounge/csv/events_ct.csv'

# player name -> list of events
rt_events_by_name = defaultdict(list)

# war id -> list of events
rt_events_by_war_id = defaultdict(list)

ct_events_by_name = defaultdict(list)
ct_events_by_war_id = defaultdict(list)

# badwolf -> Bad Wolf
player_name_map = {}

# Fetch csv and save to file
async def fetch_events_data(type = 'rt'):
    data_url = rt_data_url if type == 'rt' else ct_data_url
    out_file = 'events_{}.csv'.format(type)

    for i in range(5):
        try:
            events = await fetch(data_url)
            with open(out_file, "wb") as f:
                f.write(events)
            return
        except:
            print("Failed to fetch data: " + str(sys.exc_info()[0]))
        if i < 4:
            await asyncio.sleep(5)

# Load data from csv
def load_events_data(type = 'rt'):
    with open('events_{}.csv'.format(type)) as csvfile:
        events_by_name = defaultdict(list)
        events_by_war_id = defaultdict(list)

        reader = csv.reader(csvfile, delimiter=',')
        header = next(reader)

        for r in reader:
            event = dict(zip(header, r))

            if (event['type'] == 'Penalty' or event['type'] == 'Reward'):
                continue

            formatted_name = format_name(event['name'])
            player_name_map[formatted_name] = event['name']

            event['score'] = int(event['score'])
            event['races'] = int(event['races'])

            if (event['races'] <= 0):
                continue

            event['change_mmr'] = int(event['change_mmr'])
            event['scaled_score'] = (event['score']/event['races'])*12
            event['warid'] = int(event['warid'])

            events_by_name[formatted_name].append(event)
            events_by_war_id[event['warid']].append(event)


        global rt_events_by_name, rt_events_by_war_id, ct_events_by_name, ct_events_by_war_id
        if (type == 'rt'):
            rt_events_by_name = events_by_name
            rt_events_by_war_id = events_by_war_id
        else:
            ct_events_by_name = events_by_name
            ct_events_by_war_id = events_by_war_id

# Get partner score for one event
def get_partner_score(event, type):
    scores = []
    if (type == 'rt'):
        events = rt_events_by_war_id[event['warid']]
    else:
        events = ct_events_by_war_id[event['warid']]

    races = 0
    for partner in events:
        if partner['team'] == event['team'] and partner['player'] != event['player']:
            scores.append(partner['score'])
            races += partner['races']

    if len(scores) == 0:
        return None

    return sum(scores)/(races/12.0)

# Get avg partner score over multiple events
def get_avg_partner_score(player_events, type):
    partner_scores = []
    for event in player_events:
        score = get_partner_score(event, type);
        if score != None:
            partner_scores.append(score)

    avg_partner_score = None

    if(len(partner_scores) != 0):
        avg_partner_score = sum(partner_scores)/len(partner_scores)

    return avg_partner_score

def calc_stats(name, filter_func, type):
    if (name not in rt_events_by_name and name not in ct_events_by_name):
        return None

    if (type == 'rt'):
        player_events = rt_events_by_name[name]
    else:
        player_events = ct_events_by_name[name]

    total_events_played = len(player_events)
    player_events = list(filter(filter_func, player_events))

    if (len(player_events) == 0):
        return {}

    sorted_player_events = sorted(player_events, key=lambda e: e['warid'], reverse=True)
    player_events_ten = sorted_player_events[0:min(len(sorted_player_events),10)]

    events_played = len(player_events)
    events_percentage = len(player_events)/total_events_played

    wins = len([e for e in player_events if e['change_mmr'] > 0])
    losses = len([e for e in player_events if e['change_mmr'] < 0])

    wins_ten = len([e for e in player_events_ten if e['change_mmr'] > 0])
    losses_ten = len([e for e in player_events_ten if e['change_mmr'] < 0])

    win_percentage = wins/len(player_events)
    win_percentage_ten = wins_ten/len(player_events_ten)

    scaled_scores = list(map(lambda e: e['scaled_score'], player_events))
    avg_score = sum(scaled_scores)/len(scaled_scores)

    scaled_scores_ten = list(map(lambda e: e['scaled_score'], player_events_ten))
    avg_score_ten = sum(scaled_scores_ten)/len(scaled_scores_ten)

    scores = list(map(lambda e: e['score'], player_events))
    max_score = max(scores)

    mmr_diffs = list(map(lambda e: e['change_mmr'], player_events))
    mmr_diffs_ten = list(map(lambda e: e['change_mmr'], player_events_ten))

    max_gain = max(mmr_diffs)
    max_loss = min(mmr_diffs)
    mmr_change = sum(mmr_diffs)
    mmr_change_ten = sum(mmr_diffs_ten)

    if (max_gain <= 0):
        max_gain = None
    if (max_loss >= 0):
        max_loss = None

    avg_partner_score = get_avg_partner_score(player_events, type)
    avg_partner_score_ten = get_avg_partner_score(player_events_ten, type)

    return {
        "Events Played": events_played,
        "Event \%": events_percentage*100,
        "Average": avg_score,
        "Partner Average": avg_partner_score,
        "W-L": str(wins)+"-"+str(losses),
        "Win \%": win_percentage*100,
        "Gain/Loss": mmr_change,
        "Max Gain": max_gain,
        "Max Loss": max_loss,
        "Top Score": max_score,
        "Average (Last 10)": avg_score_ten,
        "Partner Average (Last 10)": avg_partner_score_ten,
        "W-L (Last 10)": str(wins_ten)+"-"+str(losses_ten),
        "Win \% (Last 10)": win_percentage_ten*100,
        "Gain/Loss (Last 10)": mmr_change_ten
    }


# Data for !tierstats
def calc_tier_stats(name, tier, type):
    return calc_stats(name, lambda e: e['tier'] == tier, type)

# Data for !formatstats
def calc_format_stats(name, format, type):
    data =  calc_stats(name, lambda e: e['type'] == format, type)

    if (format == 'FFA'):
        del data["Partner Average"]
        del data["Partner Average (Last 10)"]

    return data

# Data for !partneravg
def calc_partner_avg(name, type):
    data = calc_stats(name, lambda e: True, type)

    return {
        "Events Played": data["Events Played"],
        "Partner Average": data["Partner Average"],
    } if data else None

# Data for !partneravg10
def calc_partner_avg_ten(name, type):
    data = calc_stats(name, lambda e: True, type)

    return {
        "Partner Average": data["Partner Average (Last 10)"],
    } if data else None
