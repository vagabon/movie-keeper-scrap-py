import base64
import re
import sys
import urllib.parse
from typing import List, Dict
from curl_cffi import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, Query, HTTPException

app = FastAPI(title="Movie Keeper Scraper API")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
}

def clean_extracted_url(raw_url: str) -> str:
    if not raw_url:
        return ""
    
    # Nettoyage DuckDuckGo uddg=
    if "uddg=" in raw_url:
        try:
            match = re.search(r'[?&]uddg=([^&]+)', raw_url)
            if match:
                return urllib.parse.unquote(match.group(1))
        except Exception:
            pass

    # Nettoyage Bing / MSN
    if "/ck/a?!" in raw_url:
        try:
            match = re.search(r'[?&]u=([^&]+)', raw_url)
            if match:
                b64_str = match.group(1)
                if b64_str.startswith("a1"):
                    b64_str = b64_str[2:]
                b64_str += '=' * (-len(b64_str) % 4)
                return base64.b64decode(b64_str).decode('utf-8')
        except Exception:
            pass

    if raw_url.startswith("//"):
        return f"https:{raw_url}"
        
    return raw_url

def generic_scrap(target_url: str, css_selector: str) -> List[Dict[str, str]]:
    try:
        if "duckduckgo.com" in target_url:
            parsed = urllib.parse.urlparse(target_url)
            query_params = urllib.parse.parse_qs(parsed.query)
            q = query_params.get('q', [''])[0]

            with requests.Session(impersonate="chrome120") as session:
                # 1. On récupère d'abord le jeton VQD obligatoire pour DuckDuckGo
                init_res = session.get(f"https://duckduckgo.com/?q={urllib.parse.quote(q)}", headers=HEADERS)
                vqd_match = re.search(r'vqd=([\d-]+)', init_res.text)
                vqd = vqd_match.group(1) if vqd_match else ""

                # 2. Soumission de la recherche sur html.duckduckgo.com
                post_headers = HEADERS.copy()
                post_headers.update({
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "https://html.duckduckgo.com",
                    "Referer": "https://html.duckduckgo.com/"
                })
                
                payload = {"q": q, "b": "", "kl": "fr-fr"}
                if vqd:
                    payload["vqd"] = vqd

                response = session.post(
                    "https://html.duckduckgo.com/html/",
                    data=payload,
                    headers=post_headers,
                    timeout=10
                )
        else:
            response = requests.get(target_url, headers=HEADERS, impersonate="chrome120", timeout=10)

        if response.status_code not in (200, 202, 301, 302):
            raise HTTPException(
                status_code=500, 
                detail=f"Le site cible a répondu avec un code {response.status_code}"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de connexion lors du scraping : {str(e)}")

    soup = BeautifulSoup(response.text, 'html.parser')
    results = []

    # Mapping automatique des sélecteurs obsolètes vers les vrais sélecteurs HTML de DDG
    actual_selector = css_selector
    if "duckduckgo.com" in target_url and css_selector in [".web-result", "a.result-link"]:
        actual_selector = ".result__a"

    for container in soup.select(actual_selector):
        link_tag = container if container.name == 'a' else container.select_one('a.result__a, a')
        if link_tag and link_tag.get('href'):
            raw_url = link_tag.get('href')
            final_url = clean_extracted_url(raw_url)
            results.append({
                "title": link_tag.get_text().strip(),
                "url": final_url
            })

    return results

@app.get("/scrap")
def api_scrap(url: str = Query(...), selector: str = Query(...)):
    return generic_scrap(url, selector)
