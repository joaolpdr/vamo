from datetime import datetime

import pytest

from decisao import (
    Amigo, Lugar, distancia_km, nota_do_grupo, ponto_central, pontuar,
    ranquear, restricoes_do_grupo, situacao_horario, verificar_restricoes,
)


def test_distancia_de_um_ponto_para_ele_mesmo_e_zero():
    assert distancia_km((-25.4387, -49.2871), (-25.4387, -49.2871)) == 0


def test_um_grau_de_latitude_tem_cerca_de_111_km():
    assert distancia_km((0, 0), (1, 0)) == pytest.approx(111.19, abs=0.1)


def test_ponto_central_e_a_media_das_coordenadas():
    assert ponto_central([(0, 0), (0, 2)]) == (0, 1)


def test_ponto_central_sem_pontos_gera_erro():
    with pytest.raises(ValueError):
        ponto_central([])


# --- Restrições ---

def amigo(nome, restricoes=()):
    return Amigo(nome=nome, origem=(0, 0), restricoes=set(restricoes), vibe="tranquilo")


def lugar(nome, dietas=()):
    return Lugar(nome=nome, coordenada=(0, 0), categoria="restaurante", dietas=set(dietas))


def test_restricoes_do_grupo_junta_as_de_todos():
    grupo = [amigo("Ana", ["vegano"]), amigo("Bruno"), amigo("Carla", ["sem_gluten"])]
    assert restricoes_do_grupo(grupo) == {"vegano", "sem_gluten"}


def test_lugar_vegano_atende_vegetariano():
    confirmadas, sem_info = verificar_restricoes(lugar("Verde", ["vegano"]), {"vegetariano"})
    assert confirmadas == {"vegetariano"}
    assert sem_info == set()


def test_restricao_sem_dado_no_mapa_fica_como_sem_informacao():
    confirmadas, sem_info = verificar_restricoes(lugar("Bistrô", ["vegetariano"]), {"vegetariano", "sem_gluten"})
    assert confirmadas == {"vegetariano"}
    assert sem_info == {"sem_gluten"}


# --- Pontuação justa ---

def test_grupo_prefere_lugar_equilibrado_a_lugar_que_deixa_alguem_de_fora():
    bar_a = nota_do_grupo([1.0, 1.0, 0.2])   # dois amam, um odeia
    bar_b = nota_do_grupo([0.7, 0.7, 0.7])   # todos gostam
    assert bar_b > bar_a


def test_lugar_mais_perto_ganha_quando_o_resto_e_igual():
    grupo = [Amigo("Ana", origem=(0, 0))]
    perto = Lugar("Perto", coordenada=(0, 0.01), categoria="restaurante")
    longe = Lugar("Longe", coordenada=(0, 0.05), categoria="restaurante")
    ranking = ranquear([longe, perto], grupo)
    assert ranking[0].lugar.nome == "Perto"


def test_restricao_sem_informacao_reduz_a_nota():
    grupo = [Amigo("Ana", origem=(0, 0), restricoes={"vegano"})]
    confirmado = Lugar("Verde", coordenada=(0, 0.01), categoria="restaurante", dietas={"vegano"})
    sem_dado = Lugar("Bistrô", coordenada=(0, 0.01), categoria="restaurante")
    assert pontuar(confirmado, grupo).nota > pontuar(sem_dado, grupo).nota


def test_resultado_aponta_quem_ficou_menos_satisfeito():
    grupo = [Amigo("Ana", origem=(0, 0)), Amigo("Bruno", origem=(0, 0.08))]
    resultado = pontuar(Lugar("Perto da Ana", coordenada=(0, 0), categoria="restaurante"), grupo)
    assert resultado.menos_satisfeito == "Bruno"

# --- Horário ---

SABADO_20H = datetime(2026, 10, 17, 20, 0)
DOMINGO_1H = datetime(2026, 10, 18, 1, 0)
SEGUNDA_15H = datetime(2026, 10, 19, 15, 0)


def lugar_com_horario(horario):
    return Lugar("Bar", coordenada=(0, 0), categoria="bar", horario=horario)


def test_lugar_aberto_no_horario_escolhido():
    assert situacao_horario(lugar_com_horario("Mo-Sa 18:00-23:00"), SABADO_20H) == "aberto"


def test_lugar_fechado_no_horario_escolhido():
    assert situacao_horario(lugar_com_horario("Mo-Sa 18:00-23:00"), SEGUNDA_15H) == "fechado"


def test_horario_que_passa_da_meia_noite():
    assert situacao_horario(lugar_com_horario("Sa 18:00-02:00"), DOMINGO_1H) == "aberto"


def test_sem_horario_no_mapa_fica_sem_informacao():
    assert situacao_horario(lugar_com_horario(""), SABADO_20H) == "sem_informacao"


def test_horario_em_formato_invalido_fica_sem_informacao():
    assert situacao_horario(lugar_com_horario("abre quando o dono quiser"), SABADO_20H) == "sem_informacao"


def test_ranking_remove_lugares_fechados():
    grupo = [Amigo("Ana", origem=(0, 0))]
    aberto = Lugar("Aberto", coordenada=(0, 0.01), categoria="bar", horario="Mo-Su 18:00-23:00")
    fechado = Lugar("Fechado", coordenada=(0, 0.01), categoria="bar", horario="Mo-Su 08:00-12:00")
    nomes = [r.lugar.nome for r in ranquear([aberto, fechado], grupo, quando=SABADO_20H)]
    assert nomes == ["Aberto"]