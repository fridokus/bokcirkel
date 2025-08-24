import json
import requests
import logging
from dataclasses import dataclass
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


@dataclass
class Book:
    """Class representing a book."""
    title: str
    author: str
    year: int|None
    pages: int|None
    rating: float|None
    img_url: str|None

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

    year = book_doc.get("release_year")
    pages = book_doc.get("pages")
    rating = book_doc.get("rating")


    img_url = None
    if book_doc.get("image"):
        img_url = book_doc.get("image").get("url")

    logging.info(f"Found book: {title} by {author} ({year})")
    return Book(title=title, author=author, year=year, pages=pages, rating=rating, img_url=img_url)
