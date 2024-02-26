# Web Scraping and Google Sheets Integration

This Python script scrapes game information from ESPN for various basketball leagues (NBA, NCAAM, NCAAW) and writes the data to a Google Sheets spreadsheet.

## Installation

1. Clone this repository to your local machine.
2. Install the required dependencies using pip:

    pip install requests beautifulsoup4 google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client


## Usage

1. Obtain credentials for the Google Sheets API and save them to a file named `credentials.json`.
2. Update the `SPREADSHEET_ID` variable in the script with the ID of your Google Sheets spreadsheet.
3. Run the script and follow the prompts to choose the league and enter the week number for which you want to scrape game data.

## Example

    ```bash
    python main.py

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
