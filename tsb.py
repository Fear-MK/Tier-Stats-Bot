import os
import psutil
import sqlite3
import sys
import traceback

import discord
from discord.ext import commands, tasks

import stats
from common import *
from secret import key

bot = commands.Bot(command_prefix=('!', '^'), case_insensitive=True)


# Fetch data loop
@tasks.loop(hours=2)
async def update_data():
    print('Loading data')
    for type in ['rt', 'ct']:
        for i in range(4):
            print("Loading data attempt ", i)
            try:
                await stats.fetch_events_data(type=type)
                stats.load_events_data(type=type)

                print("Data load successful")
                return
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
        if "malformed" in tb:
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

    stats.load_events_data(type="rt")
    stats.load_events_data(type="ct")


# Checks that the memory is within limits
@tasks.loop(seconds=60 * 5)
async def print_memory():
    process = psutil.Process(os.getpid())
    mb = process.memory_info().rss / (1024 * 1024)
    print(str(mb) + "MB used")  # in bytes
    if mb > 100:
        print("Restarting!")
        os.execv(sys.executable, ['python'] + sys.argv)


@bot.event
async def on_ready():
    try:
        stats.load_events_data(type='rt')
        stats.load_events_data(type='ct')
    except:
        pass
    print(f'We have logged in as {bot.user}')
    print_memory.start()
    # update_data.start()
    check_db.start()


async def send_messages(ctx, *args):
    await ctx.send('\n'.join(args), delete_after=30)


# !tierstats
@bot.command(aliases=['ts'])
async def tierstats(ctx, *args):
    usage = 'Usage: `!ts <RT/CT> <tier> (player name)` \nExample: `!ts rt 1`'
    if (len(args) < 2):
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
        await send_messages(ctx, "The selected player couldn't be found", usage)
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
        await send_messages(ctx, "The selected player couldn't be found", usage)
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
    if (data == None):
        await send_messages(ctx, "The selected player couldn't be found", usage)
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
        await send_messages(ctx, "The selected player couldn't be found", usage)
    else:
        author = f'Lounge {type.upper()} Partner Average (Last 10)'
        await ctx.send(embed=create_embed(data, stats.player_name_map[formatted_name], author), delete_after=30)


def create_embed(data, name, author):
    embed = discord.Embed(
        title=name,
        colour=discord.Colour.dark_blue()
    )
    embed.set_author(
        name=author,
        icon_url='https://www.mariokartboards.com/lounge/images/logo.png'
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
    ctx.send("Internal bot error. Please ping Forest (andrew#9232) if this persists.")
    raise error

# Define variable key in secret.py
bot.run(key)
