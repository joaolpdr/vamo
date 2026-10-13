from dataclasses import dataclass, field
from datetime import datetime

from opening_hours import OpeningHours

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
    vibe: str = "tranquilo"
    horario: str = ""   # horário no formato do OpenStreetMap

def restricoes_do_grupo(amigos: list[Amigo]) -> set[str]:
    """Todas as restrições do grupo juntas: se uma pessoa precisa, o grupo precisa."""
    return set().union(*(a.restricoes for a in amigos))


def verificar_restricoes(lugar: Lugar, restricoes: set[str]) -> tuple[set[str], set[str]]:
    """Separa as restrições em (confirmadas no mapa, sem informação)."""
    atendidas = set(lugar.dietas)
    for dieta in lugar.dietas:
        atendidas |= ATENDE_TAMBEM.get(dieta, set())
    return restricoes & atendidas, restricoes - atendidas

def situacao_horario(lugar: Lugar, quando: datetime) -> str:
    """'aberto', 'fechado' ou 'sem_informacao' no horário escolhido."""
    if not lugar.horario:
        return "sem_informacao"
    try:
        estado, _ = OpeningHours(lugar.horario).state(quando)
    except Exception:   # horário escrito num formato que a biblioteca não entende
        return "sem_informacao"
    nome = str(estado).split(".")[-1].lower()
    return {"open": "aberto", "closed": "fechado"}.get(nome, "sem_informacao")

# --- Pontuação ---

DISTANCIA_MAXIMA_KM = 10      # a partir daqui, a distância vale zero
PESO_DISTANCIA = 0.6
PESO_VIBE = 0.4
SATISFACAO_VIBE_DIFERENTE = 0.4
PESO_QUEM_FICA_PIOR = 0.5     # 0 = só média; 1 = só o menos satisfeito
PENALIDADE_SEM_INFORMACAO = 0.10


@dataclass
class Resultado:
    lugar: Lugar
    nota: float
    satisfacoes: dict[str, float]
    distancias_km: dict[str, float]
    menos_satisfeito: str
    confirmadas: set[str]
    sem_informacao: set[str]


def satisfacao(amigo: Amigo, lugar: Lugar) -> tuple[float, float]:
    """Retorna (satisfação de 0 a 1, distância em km) de um amigo com um lugar."""
    km = distancia_km(amigo.origem, lugar.coordenada)
    nota_distancia = max(0.0, 1 - km / DISTANCIA_MAXIMA_KM)
    nota_vibe = 1.0 if amigo.vibe == lugar.vibe else SATISFACAO_VIBE_DIFERENTE
    return PESO_DISTANCIA * nota_distancia + PESO_VIBE * nota_vibe, km


def nota_do_grupo(satisfacoes: list[float]) -> float:
    """Combina a média do grupo com a satisfação de quem fica pior."""
    media = sum(satisfacoes) / len(satisfacoes)
    return PESO_QUEM_FICA_PIOR * min(satisfacoes) + (1 - PESO_QUEM_FICA_PIOR) * media


def pontuar(lugar: Lugar, amigos: list[Amigo]) -> Resultado:
    """Calcula a nota justa de um lugar para o grupo, com os detalhes para explicar a escolha."""
    satisfacoes, distancias = {}, {}
    for amigo in amigos:
        satisfacoes[amigo.nome], distancias[amigo.nome] = satisfacao(amigo, lugar)

    confirmadas, sem_info = verificar_restricoes(lugar, restricoes_do_grupo(amigos))
    nota = nota_do_grupo(list(satisfacoes.values())) * (1 - PENALIDADE_SEM_INFORMACAO * len(sem_info))

    return Resultado(
        lugar=lugar,
        nota=nota,
        satisfacoes=satisfacoes,
        distancias_km=distancias,
        menos_satisfeito=min(satisfacoes, key=satisfacoes.get),
        confirmadas=confirmadas,
        sem_informacao=sem_info,
    )


def ranquear(
    lugares: list[Lugar], amigos: list[Amigo], top: int = 5, quando: datetime | None = None
) -> list[Resultado]:
    """Os melhores lugares para o grupo. Com `quando`, remove os que o mapa sabe que estão fechados."""
    if quando:
        lugares = [l for l in lugares if situacao_horario(l, quando) != "fechado"]
    resultados = [pontuar(lugar, amigos) for lugar in lugares]
    return sorted(resultados, key=lambda r: r.nota, reverse=True)[:top]

# --- Explicação ---

def _juntar(nomes: list[str]) -> str:
    """['Ana', 'Bruno', 'Carla'] → 'Ana, Bruno e Carla'."""
    return nomes[0] if len(nomes) == 1 else f"{', '.join(nomes[:-1])} e {nomes[-1]}"


def explicar(resultado: Resultado, amigos: list[Amigo]) -> list[str]:
    """Frases que explicam por que o lugar é justo para o grupo."""
    frases = []

    quem = max(resultado.distancias_km, key=resultado.distancias_km.get)
    frases.append(f"Quem vai mais longe é {quem}, com {resultado.distancias_km[quem]:.1f} km.")

    abriram_mao = [a.nome for a in amigos if a.vibe != resultado.lugar.vibe]
    if not abriram_mao:
        frases.append("A vibe agrada todo mundo.")
    else:
        verbo = "abriu mão" if len(abriram_mao) == 1 else "abriram mão"
        frases.append(f"{_juntar(abriram_mao)} preferia(m) outra vibe e {verbo} disso.")

    if resultado.confirmadas:
        frases.append("✅ Confirmado no mapa: " + ", ".join(RESTRICOES[x] for x in sorted(resultado.confirmadas)) + ".")
    if resultado.sem_informacao:
        frases.append("⚠️ Confirme com o lugar: " + ", ".join(RESTRICOES[x] for x in sorted(resultado.sem_informacao)) + ".")
    return frases