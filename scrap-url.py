import base64
import re
import sys
import json
import urllib.parse
from curl_cffi import requests
from bs4 import BeautifulSoup

def clean_extracted_url(raw_url):
    if not raw_url:
        return ""
    if "uddg=" in raw_url:
        try:
            match = re.search(r'[?&]uddg=([^&]+)', raw_url)
            if match:
                return urllib.parse.unquote(match.group(1))
        except Exception:
            pass
    if "/ck/a?!" in raw_url:
        try:
            match = re.search(r'[?&]u=([^&]+)', raw_url)
            if match:
                b64_str = match.group(1)
                if b64_str.startswith("a1"):
                    b64_str = b64_str[2:]
                missing_padding = len(b64_str) % 4
                if missing_padding:
                    b64_str += '=' * (4 - missing_padding)
                decoded_bytes = base64.b64decode(b64_str)
                return decoded_bytes.decode('utf-8')
        except Exception:
            pass
    if raw_url.startswith("//"):
        return f"https:{raw_url}"
    return raw_url

def generic_scrap(target_url, css_selector):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    try:
        response = requests.get(target_url, headers=headers, impersonate="chrome120")
        if response.status_code != 200:
            print(json.dumps({"error": f"Status code {response.status_code}"}, ensure_ascii=False))
            return
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    results = []
    
    for container in soup.select(css_selector):
        link_tag = container.select_one('a.result__url, h2 a, a')
        if link_tag and link_tag.get('href'):
            raw_url = link_tag.get('href')
            final_url = clean_extracted_url(raw_url)
            results.append({
                "title": link_tag.get_text().strip(),
                "url": final_url
            })
            
    print(json.dumps(results, ensure_ascii=False))

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: python scrap-url.py <URL> <CSS_SELECTOR>"}, ensure_ascii=False))
        sys.exit(1)
        
    generic_scrap(sys.argv[1], sys.argv[2])