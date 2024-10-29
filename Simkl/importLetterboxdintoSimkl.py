import requests
import pandas as pd
import json
from datetime import datetime
import os
import time
import configparser

# Simkl and TMDB API base URLs
SIMKL_BASE_URL = 'https://api.simkl.com'
TMDB_BASE_URL = 'https://api.themoviedb.org/3'

# TMDB API Key (replace with your TMDB API key)
TMDB_API_KEY = 'YOURAPIKEY'

# Function to load Simkl credentials from conf.ini
def get_client_credentials():
    config = configparser.ConfigParser()
    config.read('conf.ini')

    client_id = config["CONFIGS"]["client_id"]
    
    # Check if access_token exists in the config
    if "access_token" in config["CONFIGS"]:
        return client_id, config["CONFIGS"]["access_token"]
    
    return client_id, None

# Function to authenticate with Simkl using OAuth and PIN method
def authenticate_simkl_oauth():
    client_id, access_token = get_client_credentials()

    # If we already have an access token, return it
    if access_token:
        print("Access token found in conf.ini.")
        return client_id, access_token

    # If no access token, start the authorization flow
    get_pin_url = f"https://api.simkl.com/oauth/pin?client_id={client_id}"
    pin_request = requests.get(get_pin_url).json()

    if 'user_code' in pin_request:
        user_code = pin_request['user_code']
        verification_url = pin_request['verification_url']

        print(f"Please go to {verification_url} and enter the code: {user_code}")
        input("After entering the code and authorizing, press Enter to continue...")

        # Verify the code and get access token
        code_verification_url = f"https://api.simkl.com/oauth/pin/{user_code}?client_id={client_id}"
        code_verification_request = requests.get(code_verification_url).json()

        if 'access_token' in code_verification_request:
            access_token = code_verification_request['access_token']

            # Save the access token in conf.ini
            config = configparser.ConfigParser()
            config.read('conf.ini')
            config.set('CONFIGS', 'access_token', access_token)

            with open('conf.ini', 'w') as configfile:
                config.write(configfile)

            print("Successfully authenticated with Simkl.")
            return client_id, access_token
        else:
            print(f"Error retrieving access token: {code_verification_request}")
            return None, None
    else:
        print(f"Error retrieving PIN: {pin_request}")
        return None, None

# Function to retrieve total episodes of a show using TMDB API
def get_total_episodes_from_tmdb(tmdb_id):
    tmdb_url = f"{TMDB_BASE_URL}/tv/{tmdb_id}?api_key={TMDB_API_KEY}"
    response = requests.get(tmdb_url)

    if response.status_code == 200:
        show_data = response.json()
        total_episodes = 0

        for season in show_data['seasons']:
            if season['season_number'] > 0:  # Skip season 0 (specials)
                total_episodes += season['episode_count']

        return total_episodes, show_data['seasons']
    else:
        print(f"Failed to retrieve show data from TMDB. Response: {response.status_code} - {response.text}")
        return 0, []

# Function to mark movies and shows as watched on Simkl in a batch request, including ratings
def mark_watched_batch_simkl(movies, shows, movies_with_ratings, access_token, client_id):
    simkl_url = f"{SIMKL_BASE_URL}/sync/history"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'simkl-api-key': client_id
    }

    # For shows, fetch total episodes from TMDB if no specific seasons are provided
    for show in shows:
        tmdb_id = show.get("ids", {}).get("tmdb")
        total_episodes, seasons = get_total_episodes_from_tmdb(tmdb_id)

        if total_episodes > 0:
            show['seasons'] = [
                {
                    'number': season['season_number'],
                    'episodes': [{'number': ep} for ep in range(1, season['episode_count'] + 1)]
                }
                for season in seasons if season['season_number'] > 0  # Skip season 0
            ]

    # Add movies with ratings
    payload = {
        "movies": [{"ids": {"tmdb": movie_id}, "watched_at": str(datetime.now()), "rating": movies_with_ratings.get(movie_id)} for movie_id in movies],
        "shows": shows  # Updated to pass seasons and episodes when available
    }

    response = requests.post(simkl_url, headers=headers, json=payload)

    if response.status_code == 201:
        print("Successfully marked all movies and shows as watched on Simkl.")
        return True
    else:
        print(f"Failed to mark items as watched. Response: {response.status_code} - {response.text}")
        return False

# Function to import movies and shows to the user's watchlist on Simkl
def import_watchlist_simkl(movies, shows, access_token, client_id):
    simkl_url = f"{SIMKL_BASE_URL}/sync/add-to-list"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'simkl-api-key': client_id
    }

    payload = {
        "movies": [{"ids": {"tmdb": movie_id}, "to": "plantowatch"} for movie_id in movies],
        "shows": [{"ids": {"tmdb": show_id}, "to": "plantowatch"} for show_id in shows]
    }

    response = requests.post(simkl_url, headers=headers, json=payload)

    if response.status_code == 201:
        print("Successfully imported watchlist to Simkl.")
        return True
    else:
        print(f"Failed to import watchlist. Response: {response.status_code} - {response.text}")
        return False


# Function to process the CSV file and collect items for the batch request
def process_csv(file_path):
    # Read the CSV file
    data = pd.read_csv(file_path)

    # Collect movies, shows, and ratings
    movies = []
    shows = []
    movies_with_ratings = {}
    letterboxd_urls = {}

    # Loop through each row
    for index, row in data.iterrows():
        tmdb_id = row['TMDB ID']
        media_type = row['Type']
        letterboxd_url = row.get('Letterboxd URL', '')
        letterboxd_urls[tmdb_id] = letterboxd_url

        if media_type == 'movie':
            movies.append(tmdb_id)
            if 'Rating' in row and not pd.isnull(row['Rating']):
                # Store rating if available
                movies_with_ratings[tmdb_id] = int(row['Rating'])
        elif media_type == 'show':
            shows.append({"ids": {"tmdb": tmdb_id}})
    
    return movies, shows, letterboxd_urls, movies_with_ratings

# Function to retrieve Simkl watched history (movies, shows, and anime)
def retrieve_simkl_history(access_token, client_id):
    simkl_url = f"{SIMKL_BASE_URL}/sync/all-items"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'simkl-api-key': client_id
    }

    response = requests.get(simkl_url, headers=headers)

    if response.status_code == 200:
        print("Successfully retrieved Simkl watched history.")
        return response.json()  # Return the JSON data of all items
    else:
        print(f"Failed to retrieve watched history from Simkl. Response: {response.status_code} - {response.text}")
        return None

# Function to extract TMDB IDs from Simkl history and differentiate by type (movie, show, anime)
def extract_tmdb_ids_from_simkl(simkl_history):
    simkl_movie_ids = []
    simkl_show_ids = []
    simkl_anime_ids = []

    # Process movies
    for movie_item in simkl_history.get('movies', []):
        try:
            movie_data = movie_item.get('movie', {})
            if 'ids' in movie_data and 'tmdb' in movie_data['ids']:
                tmdb_id = str(movie_data['ids']['tmdb'])
                simkl_movie_ids.append(tmdb_id)
                print(f"Extracted TMDB ID: {tmdb_id} for movie: {movie_data['title']}")
            else:
                print(f"Skipping movie item without valid TMDB ID: {movie_item}")
        except Exception as e:
            print(f"Error processing movie item: {movie_item}, error: {e}")

    # Process shows
    for show_item in simkl_history.get('shows', []):
        try:
            show_data = show_item.get('show', {})
            if 'ids' in show_data and 'tmdb' in show_data['ids']:
                tmdb_id = str(show_data['ids']['tmdb'])
                simkl_show_ids.append(tmdb_id)
                print(f"Extracted TMDB ID: {tmdb_id} for show: {show_data['title']}")
            else:
                print(f"Skipping show item without valid TMDB ID: {show_item}")
        except Exception as e:
            print(f"Error processing show item: {show_item}, error: {e}")

    # Process anime
    for anime_item in simkl_history.get('anime', []):
        try:
            anime_data = anime_item.get('show', {})  # Anime is also listed under 'show'
            if 'ids' in anime_data and 'tmdb' in anime_data['ids']:
                tmdb_id = str(anime_data['ids']['tmdb'])
                simkl_anime_ids.append(tmdb_id)
                print(f"Extracted TMDB ID: {tmdb_id} for anime: {anime_data['title']}")
            else:
                print(f"Skipping anime item without valid TMDB ID: {anime_item}")
        except Exception as e:
            print(f"Error processing anime item: {anime_item}, error: {e}")

    return simkl_movie_ids, simkl_show_ids, simkl_anime_ids

# Function to compare CSV TMDB IDs with Simkl API TMDB IDs and report missing items by type
def compare_csv_and_simkl_history(csv_data, simkl_history):
    # Extract TMDB IDs from the Simkl history
    simkl_movie_ids, simkl_show_ids, simkl_anime_ids = extract_tmdb_ids_from_simkl(simkl_history)

    # Separate CSV TMDB IDs by type
    csv_movie_ids = csv_data[csv_data['Type'] == 'movie']['TMDB ID'].astype(str).tolist()
    csv_show_ids = csv_data[csv_data['Type'] == 'show']['TMDB ID'].astype(str).tolist()

    # Compare CSV TMDB IDs with Simkl movie, show, and anime history
    missing_movies = [tmdb_id for tmdb_id in csv_movie_ids if tmdb_id not in simkl_movie_ids and tmdb_id not in simkl_anime_ids]
    missing_shows = [tmdb_id for tmdb_id in csv_show_ids if tmdb_id not in simkl_show_ids]

    # Report missing movies (cross-check with anime)
    if missing_movies:
        print("\nThe following movies were not marked as watched on Simkl (or found as anime):")
        for tmdb_id in missing_movies:
            letterboxd_url = csv_data[csv_data['TMDB ID'] == int(tmdb_id)]['Letterboxd URL'].values[0]
            print(f"Missing Movie - TMDb ID: {tmdb_id}, Letterboxd URL: {letterboxd_url}")

    # Report missing shows
    if missing_shows:
        print("\nThe following shows were not marked as watched on Simkl:")
        for tmdb_id in missing_shows:
            letterboxd_url = csv_data[csv_data['TMDB ID'] == int(tmdb_id)]['Letterboxd URL'].values[0]
            print(f"Missing Show - TMDb ID: {tmdb_id}, Letterboxd URL: {letterboxd_url}")

if __name__ == "__main__":
    # Authenticate and retrieve access token
    client_id, access_token = authenticate_simkl_oauth()
    if not access_token:
        print("Authentication failed. Exiting...")
        exit()

    print(f"Access token: {access_token}")

    # Load the CSV data once to avoid reloading multiple times
    csv_file_path = 'watched_movies_tmdb.csv'  # Ensure this path is correct and the file is in the same folder
    csv_data = pd.read_csv(csv_file_path)

    # Extract data from the CSV for movies and shows
    movies, shows, letterboxd_urls, movies_with_ratings = process_csv(csv_file_path)

    # Mark movies/shows as watched on Simkl, automatically importing ratings
    if mark_watched_batch_simkl(movies, shows, movies_with_ratings, access_token, client_id):
        print("Waiting 5 seconds for Simkl to update the history...")
        time.sleep(5)  # Wait for a few seconds to allow Simkl to update the history

    # Retrieve watched history from Simkl
    simkl_history = retrieve_simkl_history(access_token, client_id)

    if simkl_history:
        # Compare CSV items with Simkl history and debug mismatches
        compare_csv_and_simkl_history(csv_data, simkl_history)

    # Ask if the user wants to import their watchlist
    print("Do you want to import your watchlist as well?")
    import_watchlist_choice = input("Type 'yes' or 'no': ").strip().lower()

    # If the user chose to import their watchlist
    if import_watchlist_choice == 'yes':
        watchlist_csv_path = 'watchlist_tmdb.csv'  # Path to the watchlist CSV file
        watchlist_movies, watchlist_shows, _, _ = process_csv(watchlist_csv_path)
        if import_watchlist_simkl(watchlist_movies, watchlist_shows, access_token, client_id):
            print("Watchlist has been successfully imported to Simkl.")
        else:
            print("There was an issue importing the watchlist.")
    else:
        print("Skipping watchlist import.")

    print("All items have been processed.")
