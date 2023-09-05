import asyncio
import gspread
import gspread.utils

MIN_DELAY_BETWEEN_REQUESTS = 30  # in seconds

gc = gspread.service_account('<your_json_file>')
ws = gc.open('<your_google_sheet_name>').sheet1

async def calculate_points(match_results):
    print('[PREDICTION GAME] CALCULATING POINTS')
    await asyncio.sleep(MIN_DELAY_BETWEEN_REQUESTS)
    users = []
    num = 7
    node = f'D{num}'
    cell = ws.acell(node).value
    while cell != None:
        users.append(cell)
        num += 1
        node = f'D{num}'
        cell = ws.acell(node).value
    for user in users:
        col = ws.find(user, in_row=19).col
        for match in match_results:
            await asyncio.sleep(MIN_DELAY_BETWEEN_REQUESTS)
            row = ws.find(match,in_column=8).row
            cell_address = gspread.utils.rowcol_to_a1(row,col)
            if match_results[match] ==  ws.cell(row,col).value:
                await add_points_to_google_sheet(user)
                ws.format(f'{cell_address}:{cell_address}', {
                    "backgroundColor": {
                        "red": 0.0, 
                        "green": 1.0,
                        "blue": 0.0
                }})
            else:
                ws.format(f'{cell_address}:{cell_address}', {
                    "backgroundColor": {
                        "red": 1.0, 
                        "green": 0.0,
                        "blue": 0.0
                }})  

async def add_points_to_google_sheet(user):
    print('[PREDICTION GAME] ADDING POINTS TO GOOGLE SHEET')
    row = ws.find(user,in_column=4)
    row = row.row
    cell_address = gspread.utils.rowcol_to_a1(row,5)
    if ws.cell(row,5).value == None:
        ws.update_cell(row,5,1)
        ws.format(f'{cell_address}:{cell_address}', {
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
            }})
    else:
        ws.update_cell(row,5,str(int(ws.cell(row,5).value)+1))
    await asyncio.sleep(MIN_DELAY_BETWEEN_REQUESTS)

async def check_if_user_exists(user_name):
    num = 7
    node = f'D{num}'
    cell = ws.acell(node).value
    while cell != None:
        await asyncio.sleep(4)
        if cell == user_name:
            return
        num += 1
        node = f'D{num}'
        cell = ws.acell(node).value
    await asyncio.sleep(MIN_DELAY_BETWEEN_REQUESTS)
    await update_google_sheet_members(user_name, node)

async def update_google_sheet_matches(match_info):
    num = 20
    node = f'H{num}'
    cell = ws.acell(node).value
    while cell != None:
        num += 1
        node = f'H{num}'
        cell = ws.acell(node).value 
    await asyncio.sleep(MIN_DELAY_BETWEEN_REQUESTS)
    ws.update_cell(row=num, col=8, value=match_info)
    cell_address = gspread.utils.rowcol_to_a1(num, 8)
    ws.format(f'{cell_address}:{cell_address}', {
        "backgroundColor": {
            "red": 0.0, 
            "green": 2.0,
            "blue": 1.0
        },
        "horizontalAlignment": "CENTER",
        "textFormat":{
            "bold":True 
        },
        "wrapStrategy":"WRAP"
    })
    
async def update_google_sheet_members(member_name,node):
    ws.update_acell(label=node, value=member_name)
    ws.format(f'{node}:{node}',{
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
    })
    col = 9
    while ws.cell(row=19, col=col).value is not None:
        col += 1    
    ws.update_cell(row=19, col=col, value=member_name)
    cell_address = gspread.utils.rowcol_to_a1(19, col)
    ws.format(f'{cell_address}:{cell_address}',{
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
    })
    await asyncio.sleep(MIN_DELAY_BETWEEN_REQUESTS)

async def update_google_sheets_choice(user_name, match_info, selected_choice):
    col = ws.find(user_name,in_row=19)
    col = col.col
    row = ws.find(match_info,in_column=8)
    row = row.row
    ws.update_cell(row=row,col=col,value=selected_choice)
    node = gspread.utils.rowcol_to_a1(row,col)
    ws.format(f'{node}:{node}',{
        "horizontalAlignment": "CENTER",
        "verticalAlignment": "MIDDLE",
        "wrapStrategy":"WRAP",
        "textFormat":{
            "bold":True 
        },
        "backgroundColor": {
            "red": 0.0, 
            "green": 100.0,
            "blue": 0.0
        }
    })
    await asyncio.sleep(MIN_DELAY_BETWEEN_REQUESTS)
