import discord
from discord.ext import commands
from discord.ext import tasks

from common import *
from secret import key
import stats

bot = commands.Bot(command_prefix=('!', '^'), case_insensitive=True)

@tasks.loop(hours=4)
async def update_data():
    try:
        print('Loading data')
        await stats.fetch_events_data(type='rt')
        stats.load_events_data(type='rt')
        await stats.fetch_events_data(type='ct')
        stats.load_events_data(type='ct')
        print('Finished loading data')
    except:
        print("Something unexpected went wrong while updating data")

@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))
    update_data.start()

async def sendMessages(ctx, *args):
    await ctx.send('\n'.join(args), delete_after=30)

# !tierstats
@bot.command(aliases=['ts'])
async def tierstats(ctx, *args):
    usage = 'Usage: !tierstats <RT/CT> <tier> (player name)'
    if (len(args) < 2):
        await sendMessages(ctx, usage)
        return

    type = args[0].lower()
    tier = args[1].lower()

    if (type == 'rt'):
        if tier not in rt_tier_map:
            await sendMessages(ctx, 'Invalid RT tier: use <t1, t2, t3, t4, t5, t6, t7, top50>', usage)
            return
        else:
            tier = rt_tier_map[tier]
    elif type == 'ct':
        if tier not in ct_tier_map:
            await sendMessages(ctx, 'Invalid CT tier: use <t1, t2, t3, t4, t5, t6, top50>', usage)
            return
        else:
            tier = ct_tier_map[tier]
    else:
        await sendMessages(ctx, 'Invalid type: use RT/CT', usage)
        return

    name = ''
    if (len(args) >= 3):
        name = ' '.join(args[2:])
    else:
        name = ctx.author.display_name

    formatted_name = format_name(name)

    data = stats.calc_tier_stats(formatted_name, tier, type)
    if (data == None):
        await sendMessages(ctx, "The selected player couldn't be found", usage)
    else:
        author = 'Lounge {} {} Stats'.format(type.upper(), tier)
        await ctx.send(embed=create_embed(data, stats.player_name_map[formatted_name], author), delete_after=30)

# !formatstats
@bot.command(aliases=['fs'])
async def formatstats(ctx, *args):
    usage = 'Usage: !formatstats <RT/CT> <event format> (player name)'
    if (len(args) < 2):
        await sendMessages(ctx, usage)
        return

    type = args[0].lower()
    format = args[1].lower()

    if (type not in ['rt', 'ct']):
        await sendMessages(ctx, 'Invalid type: use RT/CT', usage)
        return

    if (format == 'ffa'):
        format = 'FFA'

    if (format not in ['FFA','2v2','3v3','4v4','6v6']):
        await sendMessages(ctx, 'Invalid format: use <ffa, 2v2, 3v3, 4v4, 6v6>', usage)
        return

    name = ''
    if (len(args) >= 3):
        name = ' '.join(args[2:])
    else:
        name = ctx.author.display_name

    formatted_name = format_name(name)

    data = stats.calc_format_stats(formatted_name, format, type)
    if (data == None):
        await sendMessages(ctx, "The selected player couldn't be found", usage)
    else:
        author = 'Lounge {} {} Stats'.format(type.upper(), format)
        await ctx.send(embed=create_embed(data, stats.player_name_map[formatted_name], author), delete_after=30)

# !partneravg
@bot.command(aliases=['pavg', 'paverage', 'partneraverage'])
async def partneravg(ctx, *args):
    usage = 'Usage: !partneravg <RT/CT> (player name)'
    if (len(args) < 1):
        await sendMessages(ctx, usage)
        return

    type = args[0].lower()
    if (type not in ['rt', 'ct']):
        await sendMessages(ctx, 'Invalid type: use RT/CT', usage)
        return

    name = ''
    if (len(args) >= 2):
        name = ' '.join(args[1:])
    else:
        name = ctx.author.display_name

    formatted_name = format_name(name)
    data = stats.calc_partner_avg(formatted_name, type)
    if (data == None):
        await sendMessages(ctx, "The selected player couldn't be found", usage)
    else:
        author = 'Lounge {} Partner Average'.format(type.upper())
        await ctx.send(embed=create_embed(data, stats.player_name_map[formatted_name], author), delete_after=30)

# !partneravg10
@bot.command(aliases=['pavg10', 'paverage10', 'partneraverage10'])
async def partneravg10(ctx, *args):
    usage = 'Usage: !partneravg10 <RT/CT> (player name)'
    if (len(args) < 1):
        await sendMessages(ctx, usage)
        return

    type = args[0].lower()
    if (type not in ['rt', 'ct']):
        await sendMessages(ctx, 'Invalid type: use RT/CT', usage)
        return

    name = ''
    if (len(args) >= 2):
        name = ' '.join(args[1:])
    else:
        name = ctx.author.display_name

    formatted_name = format_name(name)
    data = stats.calc_partner_avg_ten(formatted_name, type)
    if (data == None):
        await sendMessages(ctx, "The selected player couldn't be found", usage)
    else:
        author = 'Lounge {} Partner Average (Last 10)'.format(type.upper())
        await ctx.send(embed=create_embed(data, stats.player_name_map[formatted_name], author), delete_after=30)

def create_embed(data, name, author):
    embed = discord.Embed(
                title = name,
                colour = discord.Colour.dark_blue()
            )
    embed.set_author(name=author,
        icon_url='https://www.mariokartboards.com/lounge/images/logo.png')

    if (len(data) == 0):
        embed.description = "No data found"
        return embed

    for key in data:
        val = data[key]
        if (isinstance(val, float)):
            val = "%.1f"%val
        embed.add_field(name=key, value=val, inline=True)

    return embed

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    raise error


# Define variable key in secret.py
bot.run(key)
