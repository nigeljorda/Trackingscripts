import requests
import os
import json
import webbrowser
import csv
from urllib.parse import urlparse

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

# Function to extract user and list ID from Trakt list URL
def parse_trakt_list_url(url):
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    if len(path_parts) >= 4 and path_parts[0] == 'users' and path_parts[2] == 'lists':
        return path_parts[1], path_parts[3]
    raise ValueError("Invalid Trakt list URL format")

# Function to get items from a Trakt list
def get_list_items(access_token, client_id, username, list_id):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}',
        'trakt-api-version': '2',
        'trakt-api-key': client_id
    }
    
    url = f"{TRAKT_BASE_URL}/users/{username}/lists/{list_id}/items"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting list items: {response.status_code} - {response.text}")
        exit()

# Main comparison logic
def compare_trakt_lists():
    # Get the authentication token
    token_data = authenticate_trakt()
    access_token = token_data[0]
    client_id = token_data[1]
    
    # Explanation of the list URLs
    print("\nEnter the URLs of the Trakt lists to compare. The first list will be compared against the second list.")
    print("Items in the second list but not in the first will be shown as missing from the first list.")
    
    # Get list URLs from user
    list1_url = input("Enter the URL of the first Trakt list: ").strip()
    list2_url = input("Enter the URL of the second Trakt list: ").strip()
    
    # Parse list URLs
    try:
        username1, list_id1 = parse_trakt_list_url(list1_url)
        username2, list_id2 = parse_trakt_list_url(list2_url)
    except ValueError as e:
        print(f"Error: {e}")
        exit()
    
    # Get items from both lists
    list1_items = get_list_items(access_token, client_id, username1, list_id1)
    list2_items = get_list_items(access_token, client_id, username2, list_id2)
    
    # Create sets of Trakt IDs for comparison (handle both movies and shows)
    list1_ids = {item['movie']['ids']['trakt'] if 'movie' in item else item['show']['ids']['trakt'] 
                 for item in list1_items}
    list2_ids = {item['movie']['ids']['trakt'] if 'movie' in item else item['show']['ids']['trakt'] 
                 for item in list2_items}
    
    # Find missing items (items that are in list 2 but not in list 1)
    missing_ids = list2_ids - list1_ids
    missing_items = []
    
    for item in list2_items:
        item_id = item['movie']['ids']['trakt'] if 'movie' in item else item['show']['ids']['trakt']
        if item_id in missing_ids:
            item_type = 'movie' if 'movie' in item else 'show'
            item_data = item[item_type]
            
            # Handle seasons and episodes for shows
            if item_type == 'show' and 'seasons' in item_data:
                for season in item_data['seasons']:
                    for episode in season['episodes']:
                        missing_items.append({
                            'trakt_id': episode['ids']['trakt'],
                            'title': episode['title'],
                            'type': 'episode',
                            'url': f"https://trakt.tv/episodes/{episode['ids']['slug']}"
                        })
            
            # Add movies or shows
            elif item_type == 'movie':
                missing_items.append({
                    'trakt_id': item_data['ids']['trakt'],
                    'title': item_data['title'],
                    'type': item_type,
                    'url': f"https://trakt.tv/{item_type}s/{item_data['ids']['slug']}"
                })
            else:  # Handle shows without episodes
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
    
    print(f"\nFound {len(missing_items)} items in list 2 that are missing from list 1")
    print(f"Results have been saved to {output_file}")

if __name__ == "__main__":
    compare_trakt_lists()
