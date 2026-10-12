"""Regras de decisão do Vamo?: distância, ponto central e pontuação justa."""

from math import asin, cos, radians, sin, sqrt

RAIO_TERRA_KM = 6371

Coordenada = tuple[float, float]  # (latitude, longitude)


def distancia_km(origem: Coordenada, destino: Coordenada) -> float:
    """Distância em linha reta entre dois pontos na superfície da Terra (fórmula de Haversine)."""
    lat1, lon1 = map(radians, origem)
    lat2, lon2 = map(radians, destino)
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * RAIO_TERRA_KM * asin(sqrt(a))


def ponto_central(pontos: list[Coordenada]) -> Coordenada:
    """Média das coordenadas do grupo. Boa aproximação dentro de uma mesma cidade."""
    if not pontos:
        raise ValueError("É preciso informar pelo menos um ponto de partida.")
    latitudes = [lat for lat, _ in pontos]
    longitudes = [lon for _, lon in pontos]
    return sum(latitudes) / len(pontos), sum(longitudes) / len(pontos)