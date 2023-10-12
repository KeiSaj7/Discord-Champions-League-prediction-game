# Discord-Champions-League-prediction-game
## How it works
Every week bot sends all matches from Champions League for the whole week. Users can vote by discord emoji's. Choices are being updated in google sheet once the match starts. 160 minutes after the match starts the results are being fetched and marked in google sheet.

## Libraries
- discord.py
- gspread
- asyncio
- requests
- pytz
- datetime
## What you will need
- football-data.org API token
- google json file here to access google sheet
- discord bot token
