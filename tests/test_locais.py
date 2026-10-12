from locais import converter_lugar, link_google_maps


def feature_falsa(categorias, raw=None, nome="Lugar Teste"):
    """Imita um item da resposta do Geoapify."""
    return {
        "properties": {
            "name": nome,
            "lat": -25.44,
            "lon": -49.29,
            "formatted": "Rua Teste, 123 - Curitiba",
            "categories": categorias,
            "datasource": {"raw": raw or {}},
        }
    }


def test_converte_restaurante_com_dietas_confirmadas():
    lugar = converter_lugar(feature_falsa(
        ["catering", "catering.restaurant"],
        raw={"diet:vegan": "yes", "diet:gluten_free": "only", "diet:vegetarian": "no"},
    ))
    assert lugar.coordenada == (-25.44, -49.29)
    assert lugar.vibe == "tranquilo"
    assert lugar.dietas == {"vegano", "sem_gluten"}   # "no" não conta


def test_bar_tem_vibe_agitada():
    lugar = converter_lugar(feature_falsa(["catering", "catering.pub"]))
    assert lugar.vibe == "agitado"


def test_lugar_sem_nome_e_ignorado():
    assert converter_lugar(feature_falsa(["catering.restaurant"], nome=None)) is None


def test_link_do_google_maps_usa_nome_e_endereco():
    lugar = converter_lugar(feature_falsa(["catering.restaurant"], nome="Cantina do Délio"))
    link = link_google_maps(lugar)
    assert link.startswith("https://www.google.com/maps/search/?api=1&query=")
    assert "Cantina" in link