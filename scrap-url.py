import base64
import re
import sys
import urllib.parse
from curl_cffi import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, Query, HTTPException

# Initialisation de l'application FastAPI
app = FastAPI(title="Movie Keeper Scraper API")

def clean_extracted_url(raw_url):
    if not raw_url:
        return ""
    
    if "r.search.yahoo.com" in raw_url:
        try:
            # Cherche après /RU= ou ?RU= jusqu'au prochain / ou & ou fin de chaîne
            match = re.search(r'(?:[/?&])RU=([^/&]+)', raw_url)
            if match:
                return urllib.parse.unquote(match.group(1))
        except Exception:
            pass

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

def generic_scrap(target_url: str, css_selector: str):
    # Fix : Décodage multiple des paramètres URL pour corriger le double URL-encode (%2520 -> %20 -> ' ')
    decoded_url = target_url
    while "%" in decoded_url:
        previous_url = decoded_url
        decoded_url = urllib.parse.unquote(decoded_url)
        if decoded_url == previous_url:
            break

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        # Contourne la redirection automatique vers la page de consentement RGPD (GUCE) de Yahoo
        "Cookie": "A1=d=AQABBGM...; A3=d=AQABBGM...; YES=1"
    }

    try:
        response = requests.get(
            decoded_url, 
            headers=headers, 
            impersonate="chrome120", 
            allow_redirects=True
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Le site cible a répondu avec un code {response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de connexion lors du scraping : {str(e)}")

    soup = BeautifulSoup(response.text, 'html.parser')
    results = []
    
    for container in soup.select(css_selector):
        link_tag = container.select_one('a.result__url, h2 a, a')
        if link_tag and link_tag.get('href'):
            raw_url = link_tag.get('href')
            final_url = clean_extracted_url(raw_url)
            
            # Nettoyage du texte du titre (gestion des retours à la ligne et espaces superflus)
            title = " ".join(link_tag.get_text().split())
            
            results.append({
                "title": title,
                "url": final_url
            })
            
    return results

# --- POINT D'ENTRÉE HTTP (Pour le conteneur Java) ---
@app.get("/scrap")
def api_scrap(url: str = Query(..., description="L'URL de recherche à scraper"), 
              selector: str = Query(..., description="Le sélecteur CSS à cibler")):
    return generic_scrap(url, selector)

# --- BLOC DE COMPATIBILITÉ CLI ---
if __name__ == "__main__":
    if len(sys.argv) >= 3:
        import json
        try:
            print(json.dumps(generic_scrap(sys.argv[1], sys.argv[2]), ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
            sys.exit(1)
    else:
        print("Pour lancer le serveur HTTP, utilise : uvicorn main:app --reload")