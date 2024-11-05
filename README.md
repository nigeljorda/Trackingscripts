
# Tracking Scripts for Letterboxd, Trakt and Simkl

## Overview

This repository provides various Python scripts to manage your watch history and lists across **Letterboxd**, **Trakt** and **Simkl** platforms. The tools support exporting and importing lists, tracking histories, and comparing movie collections across users or lists.

## Requirements

- **Python 3.x**
- **Pandas**: For data handling and exporting in CSV format.
- **Requests**: For handling HTTP requests.
- **BeautifulSoup4**: Required by some Letterboxd scripts for HTML parsing.
- **Selenium** (for certain Letterboxd scripts): Required for web scraping tasks.
- **API Keys**: Simkl requires an API key, which is configured in `conf.ini`. Also in `importLetterboxdintoSimkl.py` fill in a TMDB API key. Trakt will also ask in the script itself to fill in your client_id and client_secret


## Scripts

### Letterboxd Scripts

#### 1. exportLetterboxdPopular.py
- **Description**: Exports a list of popular movies from Letterboxd into a CSV file.
- **Usage**: `python exportLetterboxdPopular.py`
- **Dependencies**: Requires Selenium.
- **Output**: A CSV file containing all items from a popular Letterboxd film page including TMDB ID.

#### 2. exportLetterboxdList.py
- **Description**: Exports user-defined lists from Letterboxd to CSV format.
- **Usage**: `python exportLetterboxdList.py`
- **Output**: A CSV file containing all items from a list including TMDB ID.

#### 3. exportLetterboxdHistory.py
- **Description**: Exports the user's viewing history from Letterboxd into a CSV file. Use this script first to generate the required CSV for Simkl and Trakt import scripts.
- **Usage**: `python exportLetterboxdHistory.py`
- **Output**: A CSV file containing watched movies with details like date and rating.

### Trakt Scripts

#### 4. importLetterboxdHistoryTrakt.py
- **Description**: Imports a viewing history CSV from Letterboxd into Trakt. **Run `exportLetterboxdHistory.py` first** to generate the required CSV file.
- **Usage**: `python importLetterboxdHistoryTrakt.py`
- **Note**: The script prompts for a Trakt Client_ID and Client_secret during execution.

#### 5. traktExport.py
- **Description**: Backups Trakt users watched history, ratings, watchlist and custom lists.
- **Usage**: `python traktexport.py`
- **Note**: The script prompts for a Trakt Client_ID and Client_secret during execution.

#### 6. traktImport.py
- **Description**: Imports Trakt users watched history, ratings, watchlist and custom lists. **Run `traktExport.py` first** since it only works with backups created with this script
- **Usage**: `python traktimport.py`
- **Note**: The script prompts for a Trakt Client_ID and Client_secret during execution.

#### 7. traktMarker.py
- **Description**: Marks episodes as watched until a specific episode.
- **Usage**: `python traktmarker.py`
- **Note**: The script prompts for a Trakt Client_ID and Client_secret during execution.

#### 8. traktDeleter.py
- **Description**: Deletes items from Trakt including history, ratings, watchlist and lists
- **Usage**: `python traktdeleter.py`
- **Note**: The script prompts for a Trakt Client_ID and Client_secret during execution.

### Simkl Scripts

#### 1. importLetterboxdintoSimkl.py
- **Description**: Imports Letterboxd data into Simkl, including Viewing history. **Run `exportLetterboxdHistory.py` first** to generate the required CSV file.
- **Usage**: `python importLetterboxdintoSimkl.py`
- **Dependencies**: Requires a Simkl Client ID, configured in `conf.ini`.
- **Note**: Change  `TMDB_API_KEY = 'YOURAPIKEY'` to your own in the python file

### Tools and Userscripts

#### Userscripts Directory (Simkl)
The `Userscripts` folder in Simkl includes scripts designed for **Tampermonkey**. For instance:
- **LetterboxdReviews**: Fetches the 20 most popular Letterboxd reviews for each movie and displays them on Simkl pages. Reload the page to load reviews.

## Configuration

###Simkl
For Simkl-specific scripts, change the `conf.ini` file in the root directory with your Simkl Client ID:

```ini
[SIMKL]
API_KEY = your_simkl_client_id
```

## User Profiles

- **Simkl Profile**: [Nigel's Trakt Dashboard](https://trakt.tv/users/nigelwestland)
