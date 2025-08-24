import json
import requests
import logging
from pathlib import Path

# Load Hardcover API key from file
API_KEY_FILE = Path(".hardcover-api-key")
if not API_KEY_FILE.exists():
    raise FileNotFoundError("Missing .hardcover-api-key file with your Hardcover API token.")

with API_KEY_FILE.open("r", encoding="utf-8") as f:
    API_KEY = f.read().strip()

API_URL = "https://api.hardcover.app/v1/graphql"
HEADERS = {
    "authorization": API_KEY,
    "content-type": "application/json",
}


class Book:
    """Class representing a book."""
    def __init__(self, title, author, year, pages, rating):
        self.title: str = title
        self.author: str = author
        self.year: int = year
        self.pages: int = pages
        self.rating: float= rating

    def __str__(self):
        # Format numeric ratings to 3 decimal points, stripping unnecessary zeros
        if isinstance(self.rating, (int, float)):
            rating_str = f"{self.rating:.3f}".rstrip('0').rstrip('.')
        else:
            rating_str = str(self.rating)
        return f"{self.title} by {self.author} ({self.year}) - {self.pages} pages, Rating: {rating_str}"


def fetch_book(query: str):
    """Fetch book information from Hardcover API by title."""
    logging.info(f"Fetching book for query: {query}")

    gql_query = """
    query SearchBook($query: String!) {
      search(query: $query, query_type: "Book", per_page: 1, page: 1) {
        results
      }
    }
    """

    variables = {"query": query}
    logging.debug(f"Sending search query:\n{gql_query}\nWith variables: {variables}")

    response = requests.post(API_URL, headers=HEADERS, json={"query": gql_query, "variables": variables})
    logging.debug(f"Search HTTP status: {response.status_code}")
    response.raise_for_status()

    data = response.json()
    logging.debug(f"Search response data: {json.dumps(data, indent=2)}")

    if "errors" in data:
        logging.error(f"Hardcover API returned errors: {data['errors']}")
        return None

    results = data.get("data", {}).get("search", {}).get("results", {})
    hits = results.get("hits", [])

    if not hits:
        logging.info(f"No search hits found for query: {query}")
        return None

    book_doc = hits[0].get("document", {})
    if not book_doc:
        logging.error(f"No book document found in first hit for query: {query}")
        return None

    title = book_doc.get("title", "Unknown")
    author = "Unknown"
    contributions = book_doc.get("contributions", [])
    if contributions and contributions[0].get("author") and contributions[0]["author"].get("name"):
        author = contributions[0]["author"]["name"]

    year = str(book_doc.get("release_year", "Unknown"))
    pages = book_doc.get("pages", "Unknown")
    rating = book_doc.get("rating", "No rating")

    logging.info(f"Found book: {title} by {author} ({year})")
    return Book(title, author, year, pages, rating)
