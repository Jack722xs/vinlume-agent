import httpx
import logging

logger = logging.getLogger(__name__)

async def buscar_portada_album(busqueda):
    try:
        url = "https://itunes.apple.com/search"
        params = {"term": busqueda, "media": "music", "entity": "album", "limit": 1}
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params=params)
            data = response.json()
            
            if data["resultCount"] > 0:
                return data["results"][0]["artworkUrl100"].replace("100x100bb", "600x600bb")
    except Exception as e:
        logger.error(f"Error en búsqueda iTunes: {e}")
        pass
    return None