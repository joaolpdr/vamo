from dataclasses import dataclass

"""Integração com o Geoapify: endereços, busca de lugares e link para o Google Maps."""

import os
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv

from decisao import Coordenada, Lugar

load_dotenv()

URL_GEOCODE = "https://api.geoapify.com/v1/geocode/search"
URL_LUGARES = "https://api.geoapify.com/v2/places"
TIMEOUT = 10

CATEGORIAS = {
    "restaurante": "catering.restaurant,catering.cafe",
    "bar": "catering.bar,catering.pub,catering.biergarten,catering.taproom",
}

CATEGORIAS_AGITADAS = {"catering.bar", "catering.pub", "catering.biergarten", "catering.taproom"}

# Etiqueta do OpenStreetMap → restrição do app
ETIQUETAS_DIETA = {
    "diet:vegetarian": "vegetariano",
    "diet:vegan": "vegano",
    "diet:gluten_free": "sem_gluten",
}
VALORES_CONFIRMADOS = {"yes", "only"}


class ErroDeLocalizacao(Exception):
    """Falha ao consultar o serviço de mapas."""


def _chave() -> str:
    chave = os.getenv("GEOAPIFY_API_KEY")
    if not chave:
        raise ErroDeLocalizacao("Chave do Geoapify não encontrada. Confira o arquivo .env.")
    return chave


RAIO_BUSCA_ENDERECO_KM = 60


@dataclass
class Local:
    coordenada: Coordenada
    endereco: str   # endereço como o serviço entendeu, para mostrar ao usuário


def geocodificar(endereco: str, perto_de: Coordenada | None = None) -> Local | None:
    """Converte um endereço em coordenadas. Com `perto_de`, só aceita resultados próximos desse ponto."""
    params = {"text": endereco, "lang": "pt", "limit": 1, "format": "json", "apiKey": _chave()}
    if perto_de:
        lat, lon = perto_de
        params["filter"] = f"circle:{lon},{lat},{RAIO_BUSCA_ENDERECO_KM * 1000}"
        params["bias"] = f"proximity:{lon},{lat}"

    resposta = requests.get(URL_GEOCODE, params=params, timeout=TIMEOUT)
    resposta.raise_for_status()
    resultados = resposta.json().get("results", [])
    if not resultados:
        return None
    r = resultados[0]
    return Local(coordenada=(r["lat"], r["lon"]), endereco=r.get("formatted", endereco))

def converter_lugar(feature: dict) -> Lugar | None:
    """Transforma um item da resposta do Geoapify em Lugar. Ignora lugares sem nome."""
    props = feature["properties"]
    if not props.get("name"):
        return None

    categorias = set(props.get("categories", []))
    raw = props.get("datasource", {}).get("raw", {})
    dietas = {
        restricao
        for etiqueta, restricao in ETIQUETAS_DIETA.items()
        if raw.get(etiqueta) in VALORES_CONFIRMADOS
    }

    return Lugar(
        nome=props["name"],
        coordenada=(props["lat"], props["lon"]),
        categoria="bar" if categorias & CATEGORIAS_AGITADAS else "restaurante",
        dietas=dietas,
        endereco=props.get("formatted", ""),
        vibe="agitado" if categorias & CATEGORIAS_AGITADAS else "tranquilo",
    )


def buscar_lugares(centro: Coordenada, tipo: str, raio_m: int = 3000, limite: int = 40) -> list[Lugar]:
    """Busca lugares do tipo escolhido num raio em volta do centro."""
    lat, lon = centro
    resposta = requests.get(
        URL_LUGARES,
        params={
            "categories": CATEGORIAS[tipo],
            "filter": f"circle:{lon},{lat},{raio_m}",   # Geoapify usa longitude primeiro
            "bias": f"proximity:{lon},{lat}",
            "limit": limite,
            "apiKey": _chave(),
        },
        timeout=TIMEOUT,
    )
    resposta.raise_for_status()
    lugares = (converter_lugar(f) for f in resposta.json().get("features", []))
    return [lugar for lugar in lugares if lugar]


def link_google_maps(lugar: Lugar) -> str:
    """Link oficial do Google Maps (não precisa de chave) para ver preço, fotos e avaliações."""
    busca = f"{lugar.nome}, {lugar.endereco}" if lugar.endereco else lugar.nome
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(busca)}"