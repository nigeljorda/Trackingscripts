import os
import json
import webbrowser
import requests
from urllib.parse import urlparse
import csv

# Trakt API URL for authorization and syncing
TRAKT_BASE_URL = 'https://api.trakt.tv'

# Function to load or request Trakt Client ID and Secret, storing them in a .json file
def get_client_credentials():
    credentials_file = 'trakt_credentials.json'
    
    if os.path.exists(credentials_file):
        with open(credentials_file, 'r') as f:
            credentials = json.load(f)
            client_id = credentials.get('client_id')
            client_secret = credentials.get('client_secret')
            if client_id and client_secret:
                return client_id, client_secret

    client_id = input("Enter your Trakt Client ID: ").strip()
    client_secret = input("Enter your Trakt Client Secret: ").strip()

    with open(credentials_file, 'w') as f:
        json.dump({'client_id': client_id, 'client_secret': client_secret}, f)

    return client_id, client_secret

# Function to authenticate Trakt using PIN-based flow and open the browser for the user
def authenticate_trakt():
    client_id, client_secret = get_client_credentials()

    # URL for OAuth2 PIN-based authorization
    auth_url = f"https://trakt.tv/oauth/authorize?response_type=code&client_id={client_id}&redirect_uri=urn:ietf:wg:oauth:2.0:oob"
    print(f"Opening browser to authorize Trakt. Please enter the PIN code provided.")
    
    # Open the browser automatically for the user
    webbrowser.open(auth_url)

    pin = input("Enter the PIN code you received from Trakt: ").strip()

    # Prepare the token request payload
    token_payload = {
        "code": pin,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        "grant_type": "authorization_code"
    }

    # Request the access token
    response = requests.post(f"{TRAKT_BASE_URL}/oauth/token", json=token_payload)
    
    if response.status_code == 200:
        token_data = response.json()
        with open('trakt_token.json', 'w') as f:
            json.dump(token_data, f)
        print("Successfully authenticated with Trakt.")
        return token_data['access_token'], client_id
    else:
        print(f"Error authenticating with Trakt: {response.status_code} - {response.text}")
        exit()

# Function to extract user from Trakt list URL
def parse_trakt_user_url(url):
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    if len(path_parts) >= 2 and path_parts[0] == 'users':
        return path_parts[1]
    raise ValueError("Invalid Trakt user URL format")

# Function to get watched items (movies and shows) from a Trakt user
def get_watched_items(access_token, client_id, username):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}',
        'trakt-api-version': '2',
        'trakt-api-key': client_id
    }
    
    # Fetch movies
    url_movies = f"{TRAKT_BASE_URL}/users/{username}/watched/movies"
    response_movies = requests.get(url_movies, headers=headers)
    
    if response_movies.status_code == 200:
        movies = response_movies.json()
    else:
        print(f"Error getting watched movies: {response_movies.status_code} - {response_movies.text}")
        exit()

    # Fetch shows
    url_shows = f"{TRAKT_BASE_URL}/users/{username}/watched/shows"
    response_shows = requests.get(url_shows, headers=headers)
    
    if response_shows.status_code == 200:
        shows = response_shows.json()
    else:
        print(f"Error getting watched shows: {response_shows.status_code} - {response_shows.text}")
        exit()

    # Combine both movie and show lists
    return movies + shows

# Main function to compare watched items between two users
def compare_users_watched():
    print("Enter the URLs of the two Trakt user profiles to compare. The second user's watched history will be compared to the first user's.")
    print("Movies and shows that are in the second user's history but not in the first user's history will be considered missing.")
    
    # Get URLs of the two Trakt users
    user1_url = input("Enter the URL of the first Trakt user: ").strip()
    user2_url = input("Enter the URL of the second Trakt user: ").strip()

    # Parse user URLs
    try:
        user1 = parse_trakt_user_url(user1_url)
        user2 = parse_trakt_user_url(user2_url)
    except ValueError as e:
        print(f"Error: {e}")
        exit()

    # Authenticate and get access token
    access_token, client_id = authenticate_trakt()

    # Get watched items for both users
    user1_items = get_watched_items(access_token, client_id, user1)
    user2_items = get_watched_items(access_token, client_id, user2)

    # Create sets of Trakt IDs for comparison
    user1_ids = {item['movie']['ids']['trakt'] if 'movie' in item else item['show']['ids']['trakt'] 
                 for item in user1_items}
    user2_ids = {item['movie']['ids']['trakt'] if 'movie' in item else item['show']['ids']['trakt'] 
                 for item in user2_items}

    # Find missing items
    missing_ids = user2_ids - user1_ids
    missing_items = []

    for item in user2_items:
        item_id = item['movie']['ids']['trakt'] if 'movie' in item else item['show']['ids']['trakt']
        if item_id in missing_ids:
            item_type = 'movie' if 'movie' in item else 'show'
            item_data = item[item_type]
            missing_items.append({
                'trakt_id': item_data['ids']['trakt'],
                'title': item_data['title'],
                'type': item_type,
                'url': f"https://trakt.tv/{item_type}s/{item_data['ids']['slug']}"
            })

    # Write missing items to CSV
    output_file = 'missing_items.csv'
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['trakt_id', 'title', 'type', 'url'])
        writer.writeheader()
        writer.writerows(missing_items)
    
    print(f"\nFound {len(missing_items)} items in the second user's history that are missing from the first user's history.")
    print(f"Results have been saved to {output_file}")

if __name__ == '__main__':
    compare_users_watched()
