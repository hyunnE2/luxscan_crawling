import requests
from bs4 import BeautifulSoup

# Send a request to the website
url = 'https://www.koibito.co.kr/product_list.html?brand=GOYARD'  # Replace with the actual URL
response = requests.get(url)
print(response.status_code)
# Parse the HTML content
