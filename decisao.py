from dataclasses import dataclass, field

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

RESTRICOES = {
    "vegetariano": "Vegetariano",
    "vegano": "Vegano",
    "sem_gluten": "Sem glúten",
}

# Uma dieta confirmada no mapa também atende a estas outras
ATENDE_TAMBEM = {
    "vegano": {"vegetariano"},
}


@dataclass
class Amigo:
    nome: str
    origem: Coordenada
    restricoes: set[str] = field(default_factory=set)
    vibe: str = "tranquilo"


@dataclass
class Lugar:
    nome: str
    coordenada: Coordenada
    categoria: str
    dietas: set[str] = field(default_factory=set)  # dietas confirmadas no mapa
    endereco: str = ""


def restricoes_do_grupo(amigos: list[Amigo]) -> set[str]:
    """Todas as restrições do grupo juntas: se uma pessoa precisa, o grupo precisa."""
    return set().union(*(a.restricoes for a in amigos))


def verificar_restricoes(lugar: Lugar, restricoes: set[str]) -> tuple[set[str], set[str]]:
    """Separa as restrições em (confirmadas no mapa, sem informação)."""
    atendidas = set(lugar.dietas)
    for dieta in lugar.dietas:
        atendidas |= ATENDE_TAMBEM.get(dieta, set())
    return restricoes & atendidas, restricoes - atendidas