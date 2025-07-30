import urllib
import json
import requests
url = "https://openlibrary.org/search.json?q={}&fields=author_name,title,ratings_average,first_publish_year,number_of_pages_median,availability&limit=1"

headers = {
    "User-Agent": "BokCirkel/1.0"
}

class Book():
    """Class representing a book."""
    def __init__(self, title, author, year, pages, rating):
        self.title = title
        self.author = author
        self.year = year
        self.pages = pages
        self.rating = rating

    def __str__(self):
        return f"{self.title} by {self.author} ({self.year}) - {self.pages} pages, Rating: {self.rating}"

def fetch_book(query: str):
    """Fetch book information from Open Library."""
    response = requests.get(url.format(urllib.parse.quote(query)), headers=headers)
    docs = json.loads(response.text)["docs"]
    if not docs or len(docs) == 0:
        return None
    book = docs[0]
    return Book(book["title"], 
                book["author_name"][0] if "author_name" in book else "Unknown",
                book["first_publish_year"] if "first_publish_year" in book else "Unknown",
                book["number_of_pages_median"] if "number_of_pages_median" in book else "Unknown",
                book["ratings_average"] if "ratings_average" in book else "No rating"       )