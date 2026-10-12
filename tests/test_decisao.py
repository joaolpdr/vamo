import pytest

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
    