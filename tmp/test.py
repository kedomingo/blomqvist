import base64
import json
import random
import re
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


def resolve_dood_stream(url):
  # Step 1: Fetch the HTML content of the page
  headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Referer': url
  }
  response = requests.get(url, headers=headers)
  soup = BeautifulSoup(response.text, 'html.parser')

  # Step 2: Find the <a> tag with class "wp-btn-iframe__shortcode" and text "STREAM DD"
  stream_a_tag = soup.find('a', class_="wp-btn-iframe__shortcode",
                           text="STREAM DD")
  if not stream_a_tag:
    print("STREAM DD button not found.")
    return None

  # Step 3: Get the value of the "data-localize" attribute
  data_localize = stream_a_tag.get("data-localize")
  if not data_localize:
    print("data-localize attribute not found.")
    return None

  # Step 4: Find the <script> tag and extract the JSON object based on the variable name in data-localize
  script_tags = soup.find_all('script', text=True)
  json_data = None
  for script in script_tags:
    if data_localize in script.text:
      # Extract the variable content (assuming it's assigned directly in the JS)
      json_text = re.search(
          rf'var {re.escape(data_localize)}\s*=\s*(\{{.*?\}});', script.text)
      if json_text:
        json_data = json.loads(json_text.group(1))
        break
  if not json_data:
    print(f"JSON data for {data_localize} not found.")
    return None

  # Step 5: Get the iframe_url from the JSON object and decode the base64 url
  iframe_url_encoded = json_data.get("iframe_url")
  if not iframe_url_encoded:
    print("iframe_url not found in JSON.")
    return None

  iframe_url = base64.b64decode(iframe_url_encoded).decode('utf-8')

  # Step 6: Follow the iframe URL to get the new HTML
  iframe_response = requests.get(iframe_url, headers=headers)
  iframe_soup = BeautifulSoup(iframe_response.text, 'html.parser')

  # Step 7: Extract and reverse the OLID
  olid_match = re.search(r"var OLID\s*=\s*'([^']+)'", iframe_response.text)
  if not olid_match:
    print("OLID variable not found.")
    return None
  olid = olid_match.group(1)
  reversed_olid = olid[::-1]

  # Step 8: Find the JS code that sets the iframe src and evaluate the JS string
  js_match = re.search(
      r"document\.body\.innerHTML\s*=\s*'<iframe[^>]*src=\"([^\"]+)\"",
      iframe_response.text)
  if not js_match:
    print("iframe src pattern not found.")
    return None

  # Evaluate the JS string (mimicking JavaScript variable replacement)
  iframe_src_template = js_match.group(1)

  # Replace '+OLID+' with reversed_olid using Python's string evaluation
  # This is essentially evaluating the JS logic to replace OLID
  iframe_src = iframe_src_template.replace("'+OLID+'", reversed_olid)

  #### FROM HERE, we deal with Doodstream
  headers['Referer'] = iframe_src
  session = requests.Session()
  response = session.get(iframe_src, allow_redirects=True, headers=headers)
  # might be redirected
  domain = extract_domain(response.url)

  if response.status_code != 200:
    print(
        f"Failed to retrieve content from {url}, status code: {response.status_code}")
    return None

  # Step 2: Parse the HTML and find the jQuery $.get() call
  soup = BeautifulSoup(response.text, 'html.parser')

  # Search for the $.get() call in the JavaScript code
  script_tags = soup.find_all('script', text=True)
  get_url = None
  token = None

  for script in script_tags:
    match = re.search(r"\$\.get\('(/pass_md5/[^']+)'", script.text)
    if match:
      get_url = match.group(1)  # Extract the URL inside $.get()

      # Extract the last segment (token) from the URL
      token_match = re.search(r"/([^/]+)$", get_url)
      if token_match:
        token = token_match.group(1)
      break

  if not get_url or not token:
    print("Could not find the $.get() URL or token.")
    return None

  # Step 3: Follow the extracted URL using the same domain and get the HTML text
  final_url = f"https://{domain}{get_url}"

  headers['Referer'] = final_url
  final_response = session.get(final_url, headers=headers)
  if final_response.status_code != 200:
    print(
      f"Failed to retrieve content from {final_url}, status code: {final_response.status_code}")
    return None

  # Step 4: Append the last segment (token) to the HTML content
  final_html_content = final_response.text + f"{make_play(token)}"

  # Return the final HTML content with the appended token
  return final_html_content


def make_play(token):
  a = ''
  chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  n = len(chars)

  # Generate a random 10-character string
  for o in range(10):
    a += random.choice(chars)

  # Add the token and expiry time (in milliseconds)
  return a + '?token='+token+'&expiry=' + str(
    int(time.time() * 1000))


def extract_domain(url):
  try:
    # Parse the URL
    parsed_url = urlparse(url)
    # Get the domain name (netloc)
    domain = parsed_url.netloc

    # Handle cases where 'www.' is present or absent
    if domain.startswith('www.'):
      domain = domain[4:]  # Remove 'www.' if present

    return domain
  except Exception as e:
    print(f"Error extracting domain: {e}")
    return None