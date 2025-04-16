import json
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/indexing"]
GOOGLE_API_DISCOVERY_URL = "https://indexing.googleapis.com/$discovery/rest?version=v3"

def ping_search_engines(
    url: str,
    bing_api_key: str = None,
    google_service_account_path: str = None
):
    results = {}

    # 1. Google Indexing API
    if google_service_account_path:
        try:
            credentials = service_account.Credentials.from_service_account_file(
                google_service_account_path, scopes=GOOGLE_SCOPES)
            service = build("indexing", "v3", credentials=credentials)
            body = {"url": url, "type": "URL_UPDATED"}
            r = service.urlNotifications().publish(body=body).execute()
            results['google_indexing'] = r
        except Exception as e:
            results['google_indexing'] = str(e)
    else:
        results['google_indexing'] = "No credentials provided."

    # 2. Bing API
    if bing_api_key:
        bing_url = f"https://ssl.bing.com/webmaster/api.svc/json/SubmitUrl?apikey={bing_api_key}"
        payload = {
            "siteUrl": "https://jobfinders.site",
            "url": url
        }
        try:
            r = requests.post(bing_url, json=payload, timeout=10)
            results['bing'] = r.json()
        except Exception as e:
            results['bing'] = str(e)
    else:
        # Fallback generic ping
        try:
            ping_url = f"http://www.bing.com/ping?sitemap={url}"
            r = requests.get(ping_url, timeout=10)
            results['bing_fallback'] = r.status_code
        except Exception as e:
            results['bing_fallback'] = str(e)

    # 3. Ping-O-Matic
    try:
        r = requests.post("http://pingomatic.com/ping/", data={
            'title': 'JobFinders Site',
            'blogurl': url,
            'rssurl': url + "/rss"
        }, timeout=10)
        results['pingomatic'] = r.status_code
    except Exception as e:
        results['pingomatic'] = str(e)

    return results

def ping_indexnow(url: str, key: str, key_location: str):
    payload = {
        "host": "jobfinders.site",
        "urlList": [url],
        "key": key,
        "keyLocation": key_location
    }
    try:
        r = requests.post("https://api.indexnow.org/indexnow", json=payload, timeout=10)
        return {'indexnow': r.status_code}
    except Exception as e:
        return {'indexnow': str(e)}

