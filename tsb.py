import os
import psutil
import sqlite3
import sys
import traceback

import discord
from discord.ext import commands, tasks

import stats
from common import *
from secret import bot_key
import requests
import urllib

bot = commands.Bot(command_prefix=('!', '^'), case_insensitive=True)

# Fetch data loop
@tasks.loop(hours=2)
async def update_data():
    print('Loading data')
    for type in ['rt', 'ct']:
        for i in range(4):
            print("Loading data attempt ", i)
            try:
                await stats.fetch_events_data(type)
                stats.load_events_data(type)

                print("Data load successful")
                break
            except:
                traceback.print_exc()
            print("Data load failed")


# Checks that the DB is not corrupted
@tasks.loop(seconds=30)
async def check_db():
    try:
        stats.get_num_events("rt")
    except:
        tb = traceback.format_exc()
        print(tb)
        if "malformed" in tb.lower():
            print("DB corrupted!")
            reset_db()


# Deletes and recreates the database
def reset_db():
    try:
        stats.con.close()
    except:
        pass
    os.system("rm main.db")

    stats.con = sqlite3.connect("main.db")
    stats.con.row_factory = sqlite3.Row

    stats.load_events_data("rt")
    stats.load_events_data("ct")


# Checks that the memory is within limits
@tasks.loop(seconds=60 * 5)
async def print_memory():
    process = psutil.Process(os.getpid())
    mb = process.memory_info().rss / (1024 * 1024)
    print(f"{str(mb)}MB used")  # in bytes
    if mb > 100:
        print("Restarting!")
        os.execv(sys.executable, ['python'] + sys.argv)


@bot.event
async def on_ready():
    try:
        stats.load_events_data('rt')
        stats.load_events_data('ct')
    except:
        pass

    print(f'We have logged in as {bot.user}')
    print_memory.start()
    update_data.start()
    check_db.start()


async def send_messages(ctx, *args):
    await ctx.send('\n'.join(args), delete_after=30)


# !tierstats
@bot.command(aliases=['ts'])
async def tierstats(ctx, *args):
    usage = 'Usage: `!ts <RT/CT> <tier> (player name)` \nExample: `!ts rt 1`'
    if len(args) < 2:
        await send_messages(ctx, usage)
        return

    type = args[0].lower()
    tier = args[1].lower()

    if type == 'rt':
        if tier not in RT_TIER_MAP:
            await send_messages(ctx, 'Invalid RT tier: use <t1, t2, t3, t4, t5, t6, t7, top50>', usage)
            return
        tier = RT_TIER_MAP[tier]
    elif type == 'ct':
        if tier not in CT_TIER_MAP:
            await send_messages(ctx, 'Invalid CT tier: use <t1, t2, t3, t4, t5, t6, top50>', usage)
            return
        tier = CT_TIER_MAP[tier]
    else:
        await send_messages(ctx, 'Invalid type: use RT/CT', usage)
        return

    if len(args) >= 3:
        name = ' '.join(args[2:])
    else:
        name = ctx.author.display_name

    formatted_name = format_name(name)

    data = stats.calc_tier_stats(formatted_name, tier, type)
    if data is None:
        await send_messages(ctx, "The selected player couldn't be found")
    else:
        author = f'Lounge {type.upper()} {tier} Stats'
        await ctx.send(embed=create_embed(data, stats.player_name_map[formatted_name], author), delete_after=30)


# !formatstats
@bot.command(aliases=['fs'])
async def formatstats(ctx, *args):
    usage = 'Usage: `!fs <RT/CT> <event format> (player name)` \nExample: `!fs rt 2v2`'
    if len(args) < 2:
        await send_messages(ctx, usage)
        return

    type = args[0].lower()
    format = args[1].lower()

    if type not in ['rt', 'ct']:
        await send_messages(ctx, 'Invalid type: use RT/CT', usage)
        return

    if format not in EVENT_FORMAT_MAP:
        await send_messages(ctx, 'Invalid format: use <ffa, 2v2, 3v3, 4v4, 6v6>', usage)
        return
    format = EVENT_FORMAT_MAP[format]

    if len(args) >= 3:
        name = ' '.join(args[2:])
    else:
        name = ctx.author.display_name

    formatted_name = format_name(name)

    data = stats.calc_format_stats(formatted_name, format, type)
    if data is None:
        await send_messages(ctx, "The selected player couldn't be found")
    else:
        author = f'Lounge {type.upper()} {format} Stats'
        await ctx.send(embed=create_embed(data, stats.player_name_map[formatted_name], author), delete_after=30)


# !partneravg
@bot.command(aliases=['pavg', 'paverage', 'partneraverage'])
async def partneravg(ctx, *args):
    usage = 'Usage: `!pavg <RT/CT> (player name)`. \nExample: `^pavg rt`'
    if len(args) < 1:
        await send_messages(ctx, usage)
        return

    type = args[0].lower()
    if type not in ['rt', 'ct']:
        await send_messages(ctx, 'Invalid type: use RT/CT', usage)
        return

    if len(args) >= 2:
        name = ' '.join(args[1:])
    else:
        name = ctx.author.display_name

    formatted_name = format_name(name)
    data = stats.calc_partner_avg(formatted_name, type)
    if data is None:
        await send_messages(ctx, "The selected player couldn't be found")
    else:
        author = f'Lounge {type.upper()} Partner Average'
        await ctx.send(embed=create_embed(data, stats.player_name_map[formatted_name], author), delete_after=30)


# !partneravg10
@bot.command(aliases=['pavg10', 'paverage10', 'partneraverage10'])
async def partneravg10(ctx, *args):
    usage = 'Usage: `!pavg10 <RT/CT> (player name)`\n Example:`^pavg10 rt`'
    if len(args) < 1:
        await send_messages(ctx, usage)
        return

    type = args[0].lower()
    if type not in ['rt', 'ct']:
        await send_messages(ctx, 'Invalid type: use RT/CT', usage)
        return

    if len(args) >= 2:
        name = ' '.join(args[1:])
    else:
        name = ctx.author.display_name

    formatted_name = format_name(name)
    data = stats.calc_partner_avg_ten(formatted_name, type)
    if data is None:
        await send_messages(ctx, "The selected player couldn't be found")
    else:
        author = f'Lounge {type.upper()} Partner Average (Last 10)'
        await ctx.send(embed=create_embed(data, stats.player_name_map[formatted_name], author), delete_after=30)

@bot.command() #Currently keeps typing after an error for around 3 seconds, don't know how to fix.
async def predict(ctx, *, args=None):
    usage = "Usage: `!predict <RT/CT> <event format> <players>`"
    example = "Example: `!predict ct 2 Marron, Thunda, Teovoni, brody, Luis, Sawyer, psycho, RoshiLBN, fruitz, jogn, James, Fear`"
    if args==None:
        await send_messages(ctx, usage)
    try:
        args = args.split(", ")
        player_ids = ["","","","","","","","","","","",""]
        if len(args) == 1:
            await send_messages(ctx, "Invalid input - make sure the player names are separated by commas. ", usage, example)
            return
        first_args = args[0].split(" ",maxsplit=2)  # Splitting player names and other arguments
        args.remove(args[0])
        args.insert(0,first_args[2])
        first_args.remove(first_args[2])  # there is definetly a more effecient way to do this
        if len(args) != 12:
            await send_messages(ctx,"Invalid player amount - must have 12 players.",usage,example)
            return
        if first_args[0].lower() == "rt":
            ladder_id="1"
        elif first_args[0].lower() == "ct":
            ladder_id="2"
        else:
            await send_messages(ctx,'Invalid type: use RT/CT',usage,
                                example)  # some form of error message subject to change
            return
        if first_args[1].lower() not in EVENT_FORMAT_MAP:
            await send_messages(ctx, 'Invalid format: use <ffa, 2v2, 3v3, 4v4, 6v6>', usage, example)
            return
        team_format=EVENT_FORMAT_MAP[first_args[1].lower()]

        r=requests.get(f'https://mkwlounge.gg/api/ladderplayer.php?ladder_id={ladder_id}&player_names={", ".join(args)}') #Requests all the player IDs
        #print(r.json())
        for player in r.json()["results"]: #sorts the player ids into order
            player_id = player["player_id"]
            for x in range(1, len(args)+1):
                if args[x-1].lower()==player["player_name"].lower():
                    player_ids[x-1:x]=[player_id]

        if "" in player_ids:
            await send_messages(ctx,
                                "I could not find one of those players in the database make sure the name is correctly capitalized (cannot predict placements). ",
                                usage)
            return

        s_quote = "'"
        d_quote = '"'  # I didnt know how to replace single quotations with double quotations and this is the solution I came up with

        event_data = stats.event_data_generation(player_ids,team_format)

        link = "https://www.mkwlounge.gg/ladder/tabler.php?ladder_id=" + ladder_id + "&event_data=" + str(
            event_data).replace(s_quote,d_quote)
        URL = "http://tinyurl.com/api-create.php"
        try:
            url = URL + "?" + urllib.parse.urlencode({"url": link})
            res = requests.get(url)
        except Exception:
            raise
        embedVar = discord.Embed(title="Prediction Link",url=res.text,colour=discord.Color.blue())
        embedVar.set_author(
            name='MMR/LR Prediction',
            icon_url='https://www.mkwlounge.gg/images/logo.png'
        )
        await ctx.send(embed=embedVar)
    except:
        await send_messages(ctx,"Invalid input. ",usage,example)
        return

@bot.command()
async def playerpage(ctx, ladder, *player):
    player=list(player)
    usage = "Usage: `!playerpage <RT/CT> <PLAYER>`"
    example = "Example: `!playerpage ct Fear`"

    if ladder.lower() == "rt":
        ladder_id="1"
    elif ladder.lower() == "ct":
        ladder_id="2"
    else:
        await send_messages(ctx,'Invalid type: use RT/CT',usage,example)  # some form of error message subject to change
        return
    
    player = " ".join(player).title()
    r=requests.get(f'https://mkwlounge.gg/api/ladderplayer.php?ladder_id={ladder_id}&player_name={player}')
    if r.json()["status"]=="failed":
        if r.json()["reason"] == "invalid player name":
            await send_messages(ctx,f"`{player}` is an invalid player name.",usage,example)
        else:
            await ctx.send("An unknown error invloving the Lounge API occurred. If the problem persists, contact Fear#1616.")
        return
    embedVar = discord.Embed(title=f"{player}'s Player Page",url=f'https://www.mkwlounge.gg/ladder/player.php?player_id={r.json()["results"][0]["player_id"]}&ladder_id={ladder_id}',colour=discord.Color.blue())
    embedVar.set_author(
        name='Lounge',
        icon_url='https://www.mkwlounge.gg/images/logo.png'
    )
    await ctx.send(embed=embedVar)
    
def create_embed(data, name, author):
    embed = discord.Embed(
        title=name,
        colour=discord.Colour.dark_blue()
    )
    embed.set_author(
        name=author,
        icon_url='https://www.mkwlounge.gg/images/logo.png'
    )

    if len(data) == 0:
        embed.description = "No data found"
        return embed

    for key, val in data.items():
        if isinstance(val, float):
            val = f"{val:.1f}"
        embed.add_field(name=key, value=val, inline=True)

    return embed

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send("Internal bot error. Please ping Forest (andrew#9232) if this persists.")
    raise error

# Define variable key in secret.py
bot.run(bot_key)
