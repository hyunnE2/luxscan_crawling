import requests
from bs4 import BeautifulSoup
import js2py

# Send a request to the website
url = 'https://www.trenbe.com/product/++94799888?catalog=&options=owned&resale=true'  # Replace with the actual URL
response = requests.get(url)

# Parse the HTML content
soup = BeautifulSoup(response.content, 'html.parser')

# Find the script tag containing the dataLayer
# This is a simplified example. The actual implementation might need more specific searching
script_tag = soup.find('script', text=lambda text: text and 'dataLayer' in text)

if script_tag:
    # Extract the JavaScript code
    js_code = script_tag.string

    # Find the dataLayer definition
    start = js_code.find('dataLayer = ') + len('dataLayer = ')
    end = js_code.find(';', start)
    data_layer_js = js_code[start:end]

    # Evaluate the JavaScript code to get the dataLayer
    context = js2py.EvalJs()
    context.execute(f'dataLayer = {data_layer_js}')
    data_layer = context.dataLayer

    # Print the dataLayer
    print(data_layer)
else:
    print("No script tag with dataLayer found.")