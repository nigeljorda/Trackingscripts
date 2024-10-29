import requests
from bs4 import BeautifulSoup
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# Function to fetch movies from a page and extract movie URL and rating if available
def fetch_movies_from_page(url, user="user1"):
    response = requests.get(url)
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    movie_tags = soup.select('.poster-container')

    movies = []
    for tag in movie_tags:
        # Extract the URL for each movie
        movie_url = 'https://letterboxd.com' + tag.find('div')['data-target-link']
        # Extract rating if it exists (for User 1 only)
        rating_tag = tag.select_one('.rating')
        rating = rating_tag.text.strip() if rating_tag else None
        if user == "user1":
            movies.append((movie_url, rating))
        else:
            movies.append(movie_url)
    return movies

# Function to handle pagination and scrape the entire list for a user
def scrape_user_movies(base_url, user="user1"):
    movies = []
    page = 1
    while True:
        url = f"{base_url}page/{page}/" if page > 1 else base_url
        page_movies = fetch_movies_from_page(url, user)

        # Stop if no more movies are found
        if not page_movies:
            break
        
        movies.extend(page_movies)
        page += 1
    
    return movies

# Main function to compare movies and save missing movies for User 2
def find_missing_movies(user1_name, user2_name, genre=None, output_csv='user2_missing_movies.csv'):
    # Construct the URL based on username and genre
    base_url = "https://letterboxd.com/{}/films/".format
    user1_url = base_url(user1_name) + (f"genre/{genre}/" if genre else "")
    user2_url = base_url(user2_name) + (f"genre/{genre}/" if genre else "")
    
    # Scrape movies from User 1 and User 2
    user1_movies = scrape_user_movies(user1_url, user="user1")
    user2_movies = set(scrape_user_movies(user2_url, user="user2"))  # use set for faster lookup
    
    # Find movies User 1 has seen but User 2 hasn't
    missing_movies = [(movie[0], movie[1]) for movie in user1_movies if movie[0] not in user2_movies]
    
    # Filter and sort by rating
    missing_movies = sorted(missing_movies, key=lambda x: x[1] or "", reverse=True)
    
    # Save to CSV
    df = pd.DataFrame(missing_movies, columns=['Letterboxd URL', 'Rating'])
    df.to_csv(output_csv, index=False)
    print(f"Missing movies for {user2_name} saved to {output_csv}")

# Get user input for usernames and optional genre
user1_name = input("Enter the username for User 1 (the primary list): ").strip()
user2_name = input("Enter the username for User 2 (the list to compare): ").strip()
genre_choice = input("Would you like to specify a genre? (e.g., horror, comedy) Leave blank for all movies: ").strip().lower()

# Run the comparison and save results
find_missing_movies(user1_name, user2_name, genre=genre_choice if genre_choice else None)
