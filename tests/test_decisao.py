import pytest
from decisao import Amigo, Lugar, distancia_km, ponto_central, restricoes_do_grupo, verificar_restricoes
from decisao import distancia_km, ponto_central


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