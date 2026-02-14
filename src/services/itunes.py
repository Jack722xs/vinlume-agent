import requests

def buscar_portada_album(busqueda):
    try:
        url = "https://itunes.apple.com/search"
        params = {"term": busqueda, "media": "music", "entity": "album", "limit": 1}
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        if data["resultCount"] > 0:
            return data["results"][0]["artworkUrl100"].replace("100x100bb", "600x600bb")
    except:
        pass
    return None