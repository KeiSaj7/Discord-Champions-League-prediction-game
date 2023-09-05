import asyncio
import discord
import gspread
import gspread.utils
import requests
import datetime
import pytz
from discord.ext import commands, tasks 
from prediction_game import *

TOKEN = open('token.txt','r') #
FOOTBALL_API_TOKEN = 'YOUR_API_TOKEN'
user_choices = {} # user.name : {match : choice}
match_messages = {} # message_id : match name
DISCORD_CHANNEL_ID = 'YOUR_DISCORD_CHANNEL_ID'
MIN_DELAY_BETWEEN_REQUESTS = 30  # (in seconds) I have introduced a delay to avoid google sheet API quota limit exception, to avoid hitting the limit I know I should use batching maybe will update it later

gc = gspread.service_account('<your_json_file>')
ws = gc.open('<your_google_sheet_name>').sheet1

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='<your_bot_prefix>',intents=intents)

@tasks.loop(hours= 168)
async def prediction_game():
    print('[PREDICTION GAME] Sending new matches.')
    match_messages.clear()
    user_choices.clear()
    europe_timezone = pytz.timezone('Europe/Warsaw') # You can change the timezone to whatever you want by just changing the city 
    today = datetime.datetime.now(europe_timezone)
    next_week = today + datetime.timedelta(days=7)
    if today.weekday() == 0: # the day in which matches will be send on discord server, 0 stands for Monday, 1 stand for Tuesday and etc.
        await send_scoreboard()
        channel = bot.get_channel(DISCORD_CHANNEL_ID) # the id of the discord channel where matches will be send
        api_url = 'https://api.football-data.org/v2/competitions/PL/matches' #PL stand for premier league
        headers = {'X-Auth-Token':FOOTBALL_API_TOKEN}
        params = {
            'dateFrom': today.date().isoformat(),
            'dateTo': next_week.date().isoformat()
        }
        response = requests.get(api_url, headers=headers, params=params)
        match_data = response.json().get('matches',[])
        additional_time = 0 # I've added additional_time to recognize the matches that start at the same hour
        for match in match_data:
            additional_time +=1
            match_time = datetime.datetime.fromisoformat(match["utcDate"][:-1])
            match_info = f"{match['homeTeam']['name']} 🆚 {match['awayTeam']['name']}"
            await update_google_sheet_matches(match_info)
            await asyncio.sleep(MIN_DELAY_BETWEEN_REQUESTS)
            embed = discord.Embed(description=match_info,color = discord.Color.magenta())
            embed.set_thumbnail(url='https://www.fifplay.com/img/public/premier-league-logo.png')
            embed.remove_author()
            message = await channel.send(embed=embed)
            match_messages[message.id] = f"{match['homeTeam']['name']} 🆚 {match['awayTeam']['name']}"
            await message.add_reaction('1️⃣')
            await message.add_reaction('❌')
            await message.add_reaction('2️⃣')
            # Schedule the match start time to remove reactions
            start_time = match_time + datetime.timedelta(minutes=1)
            end_time = match_time + datetime.timedelta(minutes=(130+additional_time))
            asyncio.create_task(remove_reactions_at_start(message, start_time))
            asyncio.create_task(get_match_results(match, end_time))  

async def remove_reactions_at_start(message, start_time):
    await asyncio.sleep((start_time - datetime.datetime.utcnow()).total_seconds())
    await message.delete()
    del match_messages[message.id]

async def get_match_results(match,end_time):
    await asyncio.sleep((end_time - datetime.datetime.utcnow()).total_seconds())
    print('[PREDICTION GAME] GETTING MATCH RESULTS')
    match_info = f"{match['homeTeam']['name']} 🆚 {match['awayTeam']['name']}"
    match_result = match.get('score', {}).get('winner')
    if match_result:
        match_results = {}
        match_results[match_info] = match_result.lower()  # Store match result (e.g., 'home_team', 'away_team', 'draw')
        await calculate_points(match_results)
        match_results.clear() 

async def delete_scoreboard_and_infoembed(scoreboard_embed, info_embed):
    await asyncio.sleep(168*60*60) #delete the scoreboard after the week
    await scoreboard_embed.delete()
    await info_embed.delete()

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user:
        return 
    if reaction.message.channel.id == DISCORD_CHANNEL_ID: # the id of the discord channel where matches will be send
        selected_choice = None
        if reaction.emoji == '1️⃣':
            selected_choice = 'home_team'
        elif reaction.emoji == '2️⃣':
            selected_choice = 'away_team'
        elif reaction.emoji == '❌':
            selected_choice = 'draw'
        if selected_choice:           
            match_id = reaction.message.id
            match_info = match_messages.get(match_id)
            await check_if_user_exists(user.name)     
            if match_info:
                if user.name in user_choices:
                    user_choices[user.name][match_info] = selected_choice
                else:
                    user_choices[user.name] = {match_info: selected_choice}
                await reaction.message.remove_reaction(reaction.emoji, user)
                await update_google_sheets_choice(user.name, match_info, selected_choice)

async def send_scoreboard():
    scoreboard = {}
    row = 7
    cell = f'D{row}'
    value = ws.acell(cell).value
    while value is not None:
        if ws.acell(f'E{row}').value is None:
            scoreboard[value] = 0
        else: 
            scoreboard[value] = int(ws.acell(f'E{row}').value)
        row += 1
        cell = f'D{row}'
        value = ws.acell(cell).value
    await asyncio.sleep(MIN_DELAY_BETWEEN_REQUESTS)
    sorted_scoreboard = dict(sorted(scoreboard.items(), key=lambda item: item[1], reverse=True))
    embed = discord.Embed(title="🏆 Scoreboard 🏆", color=discord.Color.gold())
    for user, points in sorted_scoreboard.items():
        embed.add_field(name=f'🏅{user}', value=f"Points: {points}", inline=False)
    channel = bot.get_channel(DISCORD_CHANNEL_ID) # the id of the discord channel where matches will be send
    scoreboard_embed = await channel.send(embed=embed)
    information_embed = discord.Embed(title=f"🏆 Matches for the current weekend ⚽", color=discord.Color.blue())
    info_embed = await channel.send(embed=information_embed)
    asyncio.create_task(delete_scoreboard_and_infoembed(scoreboard_embed, info_embed)) 

@bot.event  
async def on_ready():
    print(f'We have logged in as {bot.user}')
    prediction_game.start()

bot.run(TOKEN.read())