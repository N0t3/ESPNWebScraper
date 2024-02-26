import requests
from bs4 import BeautifulSoup
import csv
import re

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Define your Google Sheets API scopes
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# The ID of your Google Sheets spreadsheet
SPREADSHEET_ID = ""

# Your credentials file
CREDENTIALS_FILE = "credentials.json"

def get_game_urls(league, week_number):
    # Dictionary mapping league names to their corresponding URLs
    league_urls = {
        'NBA': f"https://www.espn.com/nba/schedule/_/date/{week_number}",
        'NCAAM': f"https://www.espn.com/mens-college-basketball/schedule/_/date/{week_number}",
        'NCAAW': f"https://www.espn.com/womens-college-basketball/schedule/_/date/{week_number}"
    }
    
    # Check if the provided league is valid
    if league not in league_urls:
        print("Invalid league. Please choose from NBA, NCAAM, or NCAAW.")
        return []

    # Construct the URL based on the selected league and week number
    url = league_urls[league]
    
    try:
        # Send a GET request to the URL with headers and cookies
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        cookies = {
            # Add cookies if necessary to bypass security measures
        }
        response = requests.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()  # Raise an exception for bad status codes
    except requests.RequestException as e:
        print("Failed to fetch the webpage:", e)
        return []

    # Parse the HTML content of the page
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all <a> tags with class "AnchorLink"
    game_links = soup.find_all('a', class_='AnchorLink')

    # Extract game IDs from the href attributes of the <a> tags
    game_ids = []
    for link in game_links:
        href = link.get('href')
        # Check if the href attribute contains "gameId" to ensure it's a game URL
        if 'gameId' in href:
            # Use regular expression to extract the game ID from the URL
            game_id = re.search(r'gameId/(\d+)', href).group(1)
            game_ids.append(game_id)

    return game_ids

def check_league(url):
    if "nba" in url:
        return "NBA"
    elif "womens-college-basketball" in url:
        return "NCAAW"
    elif "mens-college-basketball" in url:
        return "NCAAM"
    else:
        return "Unknown"

def scrape_game_info(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
    except requests.RequestException as e:
        print("Failed to fetch data from the URL:", e)
        return None, None, None, None, None, None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Extracting team names
    team_names = soup.find_all('span', {'class': 'rteQ'})
    if len(team_names) != 2:
        print("Failed to find both team names.")
        return None, None, None, None, None, None
    TeamOne = team_names[0].text.strip()
    TeamTwo = team_names[1].text.strip()

    # Extracting team attributes
    team_att = soup.find_all('div', {'class': 'Touj AsfG ucZk  Umfe '})
    TeamOneAtt = team_att[0].text.strip() if team_att else None
    TeamTwoAtt = team_att[1].text.strip() if len(team_att) > 1 else None

    # Extracting money lines
    money_lines = soup.find_all('div', {'class': 'nfCS iygL FuEs'})
    if len(money_lines) < 6:
        print("Failed to find both money lines.")
        return None, None, None, None, None, None
    home_money_line_text = money_lines[2].text.strip()  # Extract 3rd element
    away_money_line_text = money_lines[5].text.strip()

    # Handle 'EVEN' or 'even' money lines
    if home_money_line_text.lower() == 'even':
        home_money_line = 100
    else:
        home_money_line = float(home_money_line_text)
    if away_money_line_text.lower() == 'even':
        away_money_line = 100
    else:
        away_money_line = float(away_money_line_text)

    # Extracting team predictions
    team1_prediction_text = soup.find('div', {
        'class': 'matchupPredictor__teamValue matchupPredictor__teamValue--b left-0 top-0 flex items-baseline absolute copy'}).text.strip()
    team2_prediction_text = soup.find('div', {
        'class': 'matchupPredictor__teamValue matchupPredictor__teamValue--a bottom-0 right-0 flex items-baseline absolute copy'}).text.strip()

    # Remove the percentage sign (%) from the prediction text
    team1_prediction_text = re.sub(r'%', '', team1_prediction_text)
    team2_prediction_text = re.sub(r'%', '', team2_prediction_text)

    # Convert the prediction text to float
    team1_prediction = float(team1_prediction_text)
    team2_prediction = float(team2_prediction_text)

    # Calculate the probability of winning per money line for each team
    pr_w_ml_team1 = ((team1_prediction * 100) / home_money_line)
    pr_w_ml_team2 = ((team2_prediction * 100) / away_money_line)

    return TeamOne, TeamTwo, TeamOneAtt, TeamTwoAtt, home_money_line, away_money_line, team1_prediction, team2_prediction, pr_w_ml_team1, pr_w_ml_team2

# Create a new Google Sheets service
def create_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("sheets", "v4", credentials=creds)

def write_to_sheets(service, data):
    # Get the current values in the spreadsheet
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range="A:E").execute()
    values = result.get('values', [])

    # Find the next available row
    next_row = len(values) + 1

    # Prepare the range for the new data
    range_name = f"A{next_row}:E{next_row}"

    # Append the new data to the spreadsheet
    body = {'values': data}
    service.spreadsheets().values().append(spreadsheetId=SPREADSHEET_ID, range=range_name, valueInputOption="USER_ENTERED", body=body).execute()
    print("New data appended to Google Sheets.")

# Initialize Google Sheets service
service = create_service()

# Prompt the user for league type and week number
print("Choose a league:")
print("1. NBA")
print("2. NCAAM")
print("3. NCAAW")
league_choice = input("Enter the number corresponding to your choice: ")

# Validate the user's input and set the league variable accordingly
if league_choice == '1':
    league = 'NBA'
elif league_choice == '2':
    league = 'NCAAM'
elif league_choice == '3':
    league = 'NCAAW'
else:
    print("Invalid choice. Please enter a number between 1 and 3.")
    exit()

# Prompt the user to enter the week number
week_number = input("Enter the week number: ")

# Get the game URLs for the specified league and week
game_ids = get_game_urls(league, week_number)

# Loop through game IDs and scrape data
for game_id in game_ids:
    if league == "NBA":
        url = f"https://www.espn.com/nba/game/_/gameId/{game_id}/"
    elif league == "NCAAM":
        url = f"https://www.espn.com/mens-college-basketball/game/_/gameId/{game_id}/"
    elif league == "NCAAW":
        url = f"https://www.espn.com/womens-college-basketball/game/_/gameId/{game_id}/"

    print(f"Scraping data for game ID: {game_id}")

    # Scrape game info
    TeamOne, TeamTwo, _, _, home_money_line, away_money_line, team1_prediction, team2_prediction, _, _ = scrape_game_info(url)

    if TeamOne and TeamTwo and home_money_line and away_money_line and team1_prediction and team2_prediction:
        # Prepare data to be written to Google Sheets
        data = [
            [TeamOne, team1_prediction, home_money_line, game_id, check_league(url)],
            [TeamTwo, team2_prediction, away_money_line, game_id, check_league(url)]
        ]
        # Write data to Google Sheets
        write_to_sheets(service, data)
        print("Data saved to Google Sheets for game ID:", game_id)
    else:
        print("Failed to scrape game info for game ID:", game_id)

print("Google Sheets updated successfully.")
