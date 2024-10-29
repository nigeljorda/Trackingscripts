import requests
from bs4 import BeautifulSoup
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# Function to scrape movie URLs from a single page of a Letterboxd list
def fetch_movie_links_from_page(url):
    response = requests.get(url)
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    movie_tags = soup.select('.poster-container')

    # Extract the movie URLs
    movies = [
        'https://letterboxd.com' + tag.find('div')['data-target-link']
        for tag in movie_tags if tag.find('div') and 'data-target-link' in tag.find('div').attrs
    ]
    return movies

# Function to handle pagination dynamically and use concurrent fetching
def scrape_movies_from_list(base_url):
    movies = []
    page = 1
    while True:
        url = f"{base_url}page/{page}/" if page > 1 else base_url
        page_movies = fetch_movie_links_from_page(url)
        
        # Stop if there are no more movies on this page
        if not page_movies:
            break
        
        movies.extend(page_movies)
        page += 1
    
    return movies

# Compare two lists and find movies present in list1 but missing in list2
def find_missing_movies(list1_url, list2_url, output_csv='missing_movies.csv'):
    # Scrape movies from both lists
    list1_movies = scrape_movies_from_list(list1_url)
    list2_movies = scrape_movies_from_list(list2_url)
    
    # Ensure only unique movies are compared
    list1_movies = list(set(list1_movies))
    list2_movies = list(set(list2_movies))
    
    # Find movies in list1 but not in list2
    missing_movies = [movie for movie in list1_movies if movie not in list2_movies]
    
    # Output the count of missing movies
    print(f"Number of movies in List 1 but not in List 2: {len(missing_movies)}")
    
    # Create a DataFrame and save to CSV
    df = pd.DataFrame(missing_movies, columns=['Letterboxd URL'])
    df.to_csv(output_csv, index=False)
    print(f"Missing movies saved to {output_csv}")

# Prompt user input for list URLs
list1_url = input("Enter the URL of the main list (List 1): ").strip()
list2_url = input("Enter the URL of the list to find missing movies (List 2): ").strip()

# Run the comparison and export results
find_missing_movies(list1_url, list2_url)
