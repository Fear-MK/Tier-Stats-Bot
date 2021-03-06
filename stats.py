import asyncio
import csv
import os
import sqlite3
import subprocess

from common import *

# badwolf -> Bad Wolf
player_name_map = {}

con = sqlite3.connect("main.db")
con.row_factory = sqlite3.Row

# Fetch csv and save to file
async def fetch_events_data(type = 'rt'):
    ladder_id = 1 if type == 'rt' else 2
    data_url = f'https://mkwlounge.gg/csv/events_ladder_id_{ladder_id}.csv'
    out_csv = f'events_{type}.csv'

    print("Calling wget")
    wget_string = f"timeout -s KILL 120 wget -nv -O {'temp.csv'} {data_url}"
    process = subprocess.Popen(wget_string, shell=True)

    for i in range(125):
        if process.poll() is not None:
            break
        await asyncio.sleep(2.5)

    rc = process.poll()
    print("Return code: ", rc)

    if not os.path.exists("temp.csv"):
        raise FileNotFoundError()

    if rc != 0:
        os.system("rm temp.csv")
        raise FileNotFoundError()

    os.system(f"mv temp.csv {out_csv}")
    os.system("rm wget-log.*")

# Load data from csv
def load_events_data(type = 'rt'):
    with open(f'events_{type}.csv') as csv_file:
        cur = con.cursor()

        reader = csv.reader(csv_file, delimiter=',')
        header = next(reader)

        cols = ['player_name', 'team', 'player_id', 'change_lr', 'multiplier', 'races', 'score',
                'event_id', 'event_type', 'tier', 'player_id',
                'scaled_score']

        cur.execute(f"DROP TABLE IF EXISTS {type};")

        create_sql = f"""
        CREATE TABLE {type} (
            name integer,
            team integer,
            player integer,
            change_lr integer,
            multiplier integer,
            races integer,
            score integer,
            event_id integer,
            event_type text,
            tier text,
            player_id integer,
            scaled_score double
        );
        """

        cur.execute(create_sql)
        cur.execute(f"CREATE INDEX event_id_{type} ON {type}(event_id)")
        cur.execute(f"CREATE INDEX name_{type} ON {type}(name)")

        for r in reader:
            event = dict(zip(header, r))

            if event['event_type'] == 'Penalty' or event['event_type'] == 'Reward':
                continue

            formatted_name = format_name(event['player_name'])
            player_name_map[formatted_name] = event['player_name']

            event['player_name']=formatted_name
            event['score'] = int(event['score'])
            event['races'] = int(event['races'])

            if event['races'] <= 0:
                continue

            event['change_lr'] = int(event['change_lr'])
            event['scaled_score'] = (event['score']/event['races'])*12
            event['event_id'] = int(event['event_id'])

            values = [event[i] for i in cols]

            cur.execute(f"INSERT INTO {type} VALUES ({', '.join(['?'] * len(values))});", values)

        con.commit()

def fetch_sql(query):
    cur = con.cursor()
    cur.execute(query)
    return cur.fetchall()

def get_num_events(type):
    try:
        return fetch_sql(f"SELECT count(*) as count from {type}")[0]['count']
    except:
        return 0

def get_events_by_war_id(event_id, type):
    return fetch_sql(f"SELECT * from {type} WHERE event_id={event_id};")

def get_events_by_name(name, type):
    return fetch_sql(f"SELECT * from {type} WHERE name=\"{name}\";")

# Get partner score for one event
def get_partner_score(event, type):
    scores = []
    events = get_events_by_war_id(event['event_id'], type)

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
        score = get_partner_score(event, type)
        if score is not None:
            partner_scores.append(score)

    avg_partner_score = None

    if len(partner_scores) != 0:
        avg_partner_score = sum(partner_scores)/len(partner_scores)

    return avg_partner_score

def calc_stats(name, filter_func, type):
    player_events = get_events_by_name(name, type)

    if len(player_events) == 0:
        return None

    total_events_played = len(player_events)
    player_events = list(filter(filter_func, player_events))

    if len(player_events) == 0:
        return {}

    sorted_player_events = sorted(player_events, key=lambda e: e['event_id'], reverse=True)
    player_events_ten = sorted_player_events[0:min(len(sorted_player_events),10)]

    events_played = len(player_events)
    events_percentage = len(player_events)/total_events_played

    wins = len([e for e in player_events if e['change_lr'] > 0])
    losses = len([e for e in player_events if e['change_lr'] < 0])

    wins_ten = len([e for e in player_events_ten if e['change_lr'] > 0])
    losses_ten = len([e for e in player_events_ten if e['change_lr'] < 0])

    win_percentage = wins/len(player_events)
    win_percentage_ten = wins_ten/len(player_events_ten)

    scaled_scores = [e['scaled_score'] for e in player_events]
    avg_score = sum(scaled_scores)/len(scaled_scores)

    scaled_scores_ten = [e['scaled_score'] for e in player_events_ten]
    avg_score_ten = sum(scaled_scores_ten)/len(scaled_scores_ten)

    scores = [e['score'] for e in player_events if e['races'] <= 12]
    max_score = max(scores)

    lr_diffs = [e['change_lr'] for e in player_events]
    lr_diffs_ten = [e['change_lr'] for e in player_events_ten]

    max_gain = max(lr_diffs)
    max_loss = min(lr_diffs)
    lr_change = sum(lr_diffs)
    lr_change_ten = sum(lr_diffs_ten)

    if max_gain <= 0:
        max_gain = None
    if max_loss >= 0:
        max_loss = None

    avg_partner_score = get_avg_partner_score(player_events, type)
    avg_partner_score_ten = get_avg_partner_score(player_events_ten, type)

    return {
        "Events Played": events_played,
        "Event \%": events_percentage*100,
        "Average": avg_score,
        "Partner Average": avg_partner_score,
        "W-L": f"{wins}-{losses}",
        "Win \%": win_percentage*100,
        "Gain/Loss": lr_change,
        "Max Gain": max_gain,
        "Max Loss": max_loss,
        "Top Score": max_score,
        "Average (Last 10)": avg_score_ten,
        "Partner Average (Last 10)": avg_partner_score_ten,
        "W-L (Last 10)": f"{wins_ten}-{losses_ten}",
        "Win \% (Last 10)": win_percentage_ten*100,
        "Gain/Loss (Last 10)": lr_change_ten
    }


# Data for !tierstats
def calc_tier_stats(name, tier, type):
    return calc_stats(name, lambda e: e['tier'] == tier, type)

# Data for !formatstats
def calc_format_stats(name, format, type):
    data =  calc_stats(name, lambda e: e['event_type'] == format, type)

    if format == 'FFA' and data:
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

def event_data_generation(player_ids, format):
    p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11,p12=player_ids #p=player
    if format=="FFA":
        event_data={"races":12,"format":"1","tier":"Tier 1","teams":[{"players":[{"player_id":p1,"score":12}]},{"players":[{"player_id":p2,"score":11}]},{"players":[{"player_id":p3,"score":10}]},{"players":[{"player_id":p4,"score":9}]},{"players":[{"player_id":p5,"score":8}]},{"players":[{"player_id":p6,"score":7}]},{"players":[{"player_id":p7,"score":6}]},{"players":[{"player_id":p8,"score":5}]},{"players":[{"player_id":p9,"score":4}]},{"players":[{"player_id":p10,"score":3}]},{"players":[{"player_id":p11,"score":2}]},{"players":[{"player_id":p12,"score":1}]}]}
    elif format=="2v2":
        event_data={"races":12,"format":"2","tier":"Tier 1","teams":[{"players":[{"player_id":p1,"score":12},{"player_id":p2,"score":11}]},{"players":[{"player_id":p3,"score":10},{"player_id":p4,"score":9}]},{"players":[{"player_id":p5,"score":8},{"player_id":p6,"score":7}]},{"players":[{"player_id":p7,"score":6},{"player_id":p8,"score":5}]},{"players":[{"player_id":p9,"score":4},{"player_id":p10,"score":3}]},{"players":[{"player_id":p11,"score":2},{"player_id":p12,"score":1}]}]}
    elif format=="3v3":
        event_data={"races":12,"format":"3","tier":"Tier 1","teams":[{"players":[{"player_id":p1,"score":12},{"player_id":p2,"score":11},{"player_id":p3,"score":10}]},{"players":[{"player_id":p4,"score":9},{"player_id":p5,"score":8},{"player_id":p6,"score":7}]},{"players":[{"player_id":p7,"score":6},{"player_id":p8,"score":5},{"player_id":p9,"score":4}]},{"players":[{"player_id":p10,"score":3},{"player_id":p11,"score":2},{"player_id":p12,"score":1}]}]}
    elif format=="4v4":
        event_data={"races":12,"format":"4","tier":"Tier 1","teams":[{"players":[{"player_id":p1,"score":12},{"player_id":p2,"score":11},{"player_id":p3,"score":10},{"player_id":p4,"score":9}]},{"players":[{"player_id":p5,"score":8},{"player_id":p6,"score":7},{"player_id":p7,"score":6},{"player_id":p8,"score":5}]},{"players":[{"player_id":p9,"score":4},{"player_id":p10,"score":3},{"player_id":p11,"score":2},{"player_id":p12,"score":1}]}]}
    elif format=="6v6":
        event_data={"races":12,"format":"6","tier":"Tier 1","teams":[{"players":[{"player_id":p1,"score":12},{"player_id":p2,"score":11},{"player_id":p3,"score":10},{"player_id":p4,"score":9},{"player_id":p5,"score":8},{"player_id":p6,"score":7}]},{"players":[{"player_id":p7,"score":6},{"player_id":p8,"score":5},{"player_id":p9,"score":4},{"player_id":p10,"score":3},{"player_id":p11,"score":2},{"player_id":p12,"score":1}]}]}
    else:
        print("Invalid")
        event_data=""
    return event_data