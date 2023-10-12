import asyncio
import requests
import pytz
import datetime
import gspread
import gspread.utils
import discord
from discord.ext import commands, tasks 

TOKEN = open('token.txt','r')
FOOTBALL_API_TOKEN = '' # Your football-data.org API token here
CHANNEL_ID =  # Your channel id(int) here
user_choices = {} # user.name : {match : choice}
match_messages = {} # message_id : match name
users_to_add = []


gc = gspread.service_account('') # Your google json file here
ws = gc.open('').sheet1 # Your google sheet name here


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='',intents=intents) # Your bot prefix here

@tasks.loop(hours= 168)
async def prediction_game():
    await weekly_clear()    
    print('[PREDICTION GAME] Sending new matches.') 
    europe_timezone = pytz.timezone('Europe/Warsaw') # Your timezone here
    today = datetime.datetime.now(europe_timezone)
    next_week = today + datetime.timedelta(days=7)
    await send_scoreboard()
    channel = bot.get_channel(CHANNEL_ID)
    api_url = 'https://api.football-data.org/v2/competitions/CL/matches' #CL stands for Champions League, PL stands for Premier League and etc.
    headers = {'X-Auth-Token':FOOTBALL_API_TOKEN}
    params = {
        'dateFrom': today.date().isoformat(),
        'dateTo': next_week.date().isoformat()
    }
    response = requests.get(api_url, headers=headers, params=params)
    match_data = response.json().get('matches',[])
    additional_time = 0
    this_week_matches = []
    for match in match_data:
        additional_time +=1
        match_time = datetime.datetime.fromisoformat(match["utcDate"][:-1])
        match_info = f"{match['homeTeam']['name']} 🆚 {match['awayTeam']['name']}"
        match_id = match['id']
        this_week_matches.append(match_info)
        embed = discord.Embed(description=match_info,color = discord.Color.magenta())
        embed.set_thumbnail(url='https://upload.wikimedia.org/wikipedia/en/thumb/f/f5/UEFA_Champions_League.svg/1200px-UEFA_Champions_League.svg.png') #UCL
        embed.remove_author()
        message = await channel.send(embed=embed)
        match_messages[message.id] = f"{match['homeTeam']['name']} 🆚 {match['awayTeam']['name']}"
        await message.add_reaction('1️⃣')
        await message.add_reaction('❌')
        await message.add_reaction('2️⃣')
        start_time = match_time + datetime.timedelta(minutes=1)
        end_time = match_time + datetime.timedelta(minutes=(160+additional_time))
        asyncio.create_task(remove_reactions_at_start(message, start_time))
        asyncio.create_task(get_match_results(match_id,match_info,end_time))
    await update_google_sheet_matches(this_week_matches)
    file = open("members.txt",'r',encoding='utf-8')
    members = file.read().splitlines()
    file.close()
    col = 8+len(members)
    row = len(match_messages)+19
    cell = gspread.utils.rowcol_to_a1(row,col)
    ws.batch_format([{
        'range' : f'I20:{cell}',
        'format' : {
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE",
            "wrapStrategy":"WRAP",
            "textFormat":{
                "bold":True 
            },
            "backgroundColor": {    
                "red": 1.0, 
                "green": 1.0, 
                "blue": 0.0,
            }
        }
    }])
    info_message = await channel.send('⚽ Predictions for the current weekend ⚽')
    await info_message_delete(info_message)


async def fetch_match_data(match_id):
    api_url = f'https://api.football-data.org/v2/matches/{match_id}'
    headers = {'X-Auth-Token': FOOTBALL_API_TOKEN}
    response = requests.get(api_url, headers=headers)
    return response.json()

async def remove_reactions_at_start(message, start_time):
    await asyncio.sleep((start_time - datetime.datetime.utcnow()).total_seconds())
    await message.delete()
    await update_google_sheet_members()
    await update_google_sheets_choice()

async def get_match_results(match_id,match_info,end_time):
    await asyncio.sleep((end_time - datetime.datetime.utcnow()).total_seconds())
    print('[PREDICTION GAME] GETTING MATCH RESULTS')
    match = await fetch_match_data(match_id)
    match_result = match['match']['score']['winner']
    print(f'[PREDICTION GAME] {match_info} : {match_result}')
    match_results = {}
    match_results[match_info] = match_result.lower()  # Store match result (e.g., 'home_team', 'away_team', 'draw')
    await calculate_points(match_results)

async def delete_scoreboard_and_infoembed(scoreboard_embed, info_embed):
    await asyncio.sleep(168*60*60)
    await scoreboard_embed.delete()
    await info_embed.delete()

async def info_message_delete(info_message):
    await asyncio.sleep(168*60*60)
    await info_message.delete()

async def send_scoreboard():
    file = open("members.txt",'r',encoding='utf-8')
    members = file.read().splitlines()
    file.close()
    points = ws.batch_get(
        ["E7:E30"],
    )[0]
    scoreboard = {}
    for i,member in enumerate(members):
        if i > len(points)-1:
            break
        scoreboard[member] = points[i][0]
    sorted_scoreboard = dict(sorted(scoreboard.items(), key=lambda item: int(item[1]), reverse=True))
    embed = discord.Embed(title="🏆 Scoreboard 🏆", color=discord.Color.gold())
    for user, points in sorted_scoreboard.items():
        embed.add_field(name=f'🏅{user}', value=f"Points: {points}", inline=False)
    channel = bot.get_channel(CHANNEL_ID)
    scoreboard_embed = await channel.send(embed=embed)
    information_embed = discord.Embed(title=f"🏆 Matches for the current weekend ⚽", color=discord.Color.blue())
    info_embed = await channel.send(embed=information_embed)
    asyncio.create_task(delete_scoreboard_and_infoembed(scoreboard_embed, info_embed)) 

async def weekly_clear():
    match_messages.clear()
    user_choices.clear()
    users_to_add.clear() 
    ws.batch_clear(['H20:Z50'])
    ws.batch_format([{
    "range" : "H20:Z50",
    'format' :{
        "backgroundColor": {
            "red": 1.0,
            "green": 1.0,
            "blue": 1.0
        }
    }}])

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user:
        return 
    if reaction.message.channel.id == CHANNEL_ID:
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

async def calculate_points(match_results):
    print('[PREDICTION GAME] CALCULATING POINTS')
    points = {}
    for user,choices in user_choices.items():
        points[user] = 0
        for match, choice in choices.items():
            if(match in match_results):
                if(choice == match_results[match]):
                    points[user] += 1
    await add_points_to_google_sheet(points,match_results)
 
async def add_points_to_google_sheet(points,match_results):
    print('[PREDICTION GAME] ADDING POINTS')
    file = open('members.txt','r',encoding='utf-8')
    members = file.read().splitlines()
    file.close()
    result_format = []
    letter = 'I'
    for match,result in match_results.items():
        match_row = 20 + list(match_messages.values()).index(match) 
        column = gspread.utils.rowcol_to_a1(match_row,8+len(members))
        for i,member in enumerate(members):
            if member in user_choices:
                if match in user_choices[member]:
                    if user_choices[member][match] == result:
                        result_format.append(f'{letter}{match_row}')
                    else:
                        result_format.append('')
            else:
                result_format.append('')
            letter = chr(ord(letter)+1)
    c = result_format.count('')
    for i in range(c):
        result_format.remove('')
    batch = [{
        'range' : f'I{match_row}:{column}',
        'format' : {
            "backgroundColor": {
                "red": 1.0,     
                "green": 0.0, 
                "blue": 0.0,
            }
        }
    }]
    for node in result_format:
        batch.append({
            'range' : f'{node}',
            'format' : {
                "backgroundColor": {
                    "red": 0.0,     
                    "green": 1.0, 
                    "blue": 0.0,
                }
            }
        })
    ws.batch_format(batch)
    if not points:
        return
    values = []
    all_values = ws.get_values('D7:E30')
    for value in all_values:
        if value[0] in points:
            values.append([int(value[1])+points[value[0]]])
        else:
             values.append([value[1]])
    ws.batch_update([{  
         'range' : 'E7:E30',
         'values' : values
    }])

            
async def check_if_user_exists(user_name):
    file = open('members.txt','r',encoding='utf-8')
    members = file.read().splitlines()
    for member in members:
        if member == user_name:
            return
    file.close()
    await update_members_file(user_name)


async def update_members_file(user_name):
    file = open('members.txt','a',encoding='utf-8')
    file.write(f'\n{user_name}')
    users_to_add.append(user_name)
    members = file.read().splitlines()
    file.close()
    col = 8+len(members)
    row = len(match_messages)+19
    cell = gspread.utils.rowcol_to_a1(row,col)
    ws.batch_format([{
            'range' : f'I20:{cell}',
            'format' : {
                "horizontalAlignment": "CENTER",
                "verticalAlignment": "MIDDLE",
                "wrapStrategy":"WRAP",
                "textFormat":{
                    "bold":True 
                },
                "backgroundColor": {    
                    "red": 1.0, 
                    "green": 1.0, 
                    "blue": 0.0,
                }
            }
    }])

async def update_google_sheet_members():
    if not users_to_add:
        print('EMPTY')
        return
    file = open('members.txt','r',encoding='utf-8')
    users = file.read().splitlines()
    column_values = ws.batch_get(["D7:D30"])[0]
    start_cell = gspread.utils.rowcol_to_a1(19,8+len(users))
    end_cell = gspread.utils.rowcol_to_a1(19,8+len(users)+len(users_to_add)-1)
    values = []
    members = [[]]
    for user in users_to_add:
        values.append([user,0])
        members[0].append(user)
    ws.batch_update([{
        'range' : f'D{7+len(column_values)}:E{6+len(column_values)+len(users_to_add)}',
        'values' : values
    },{
        'range' : f'{start_cell}:{end_cell}',
        'values' : members

    }])
    ws.batch_format([{
        'range' : f'D{7+len(column_values)}:D{6+len(column_values)+len(users_to_add)}',
        'format' : {
            "horizontalAlignment": "CENTER",
            "wrapStrategy":"WRAP",
            "textFormat":{
                "bold":True 
            },
            "backgroundColor": {
                "red": 180.0, 
                "green": 167.0,
                "blue": 114.0
            }
        }
    },
    {
        'range' : f'E{7+len(column_values)}:E{6+len(column_values)+len(users_to_add)}',
        'format' : {
            "horizontalAlignment": "CENTER",
            "wrapStrategy":"WRAP",
            "textFormat":{
                "bold":True 
            },
            "backgroundColor": {
                "red": 0.0, 
                "green": 0.6, 
                "blue": 0.15,
                "alpha":0.7
            }
        }
    },
    {   
        'range' : f'{start_cell}:{end_cell}',
        'format' : {
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE",
            "wrapStrategy":"WRAP",
            "textFormat":{
                "bold":True 
            },
            "backgroundColor": {
                "red": 180.0, 
                "green": 167.0,
                "blue": 114.0
            }
        }      

    }])
    users_to_add.clear()

async def update_google_sheet_matches(this_week_matches):
    if not this_week_matches:
        return
    column_values = ws.batch_get(["H20:H350"])[0]
    empty_cell = len(column_values)+20
    values = [[] for _ in range(len(this_week_matches))]
    for i,match in enumerate(this_week_matches):
        values[i].append(match)
    ws.batch_update([{
        'range' : f'H{empty_cell}:H{empty_cell+len(this_week_matches)-1}',
        'values' : values
        }])
    ws.batch_format([{
        'range' : f'H{empty_cell}:H{empty_cell+len(this_week_matches)-1}',
        'format' : {
            "backgroundColor": {
                "red": 0.0, 
                "green": 2.0,
                "blue": 1.0
            },
            "horizontalAlignment": "CENTER",
            "textFormat" : {
                "bold":True 
            },
            "wrapStrategy" : "WRAP"
        }
    }])
    
async def update_google_sheets_choice():
    file = open('members.txt','r',encoding='utf-8')
    member_list = file.read().splitlines()
    values = []
    for i,(id,match) in enumerate(match_messages.items()):
        values.append([])
        for member in member_list:
            if member in user_choices and match in user_choices[member]:
                values[i].append(user_choices[member][match])
            else:
                values[i].append('')  
    column_values = ws.batch_get(["H20:H50"])[0]
    col = 8+len(values[0])
    row = len(match_messages)+19
    cell = gspread.utils.rowcol_to_a1(row,col)
    ws.batch_update([{
        'range' : f'I20:{cell}', 
        'values' : values
    }])


bot.run(TOKEN.read())