"""Interface do Vamo? (Streamlit)."""

import requests
import streamlit as st

from decisao import RESTRICOES, Amigo, distancia_km, ponto_central, ranquear
from locais import ErroDeLocalizacao, buscar_lugares, geocodificar, link_google_maps

VIBES = {"tranquilo": "😌 Tranquilo", "agitado": "🎉 Agitado"}
TIPOS = {"restaurante": "🍽️ Restaurante", "bar": "🍻 Bar"}
ALERTA_DISTANCIA_KM = 30


# --- Funções ---

@st.cache_data(show_spinner=False)
def localizar(endereco: str, perto_de=None):
    """Geocodifica com cache: o mesmo endereço não gasta requisição de novo."""
    return geocodificar(endereco, perto_de)


def formulario_amigo(i: int) -> dict:
    """Campos de um amigo dentro do formulário."""
    st.markdown(f"**Amigo {i + 1}**")
    nome = st.text_input("Nome", key=f"nome_{i}", placeholder="Ex.: Ana")
    endereco = st.text_input("De onde sai (bairro ou endereço)", key=f"end_{i}", placeholder="Ex.: Batel")
    restricoes = st.multiselect(
        "Restrições", list(RESTRICOES), format_func=RESTRICOES.get, key=f"rest_{i}", placeholder="Nenhuma"
    )
    vibe = st.radio("Vibe", list(VIBES), format_func=VIBES.get, key=f"vibe_{i}", horizontal=True)
    return {"nome": nome.strip(), "endereco": endereco.strip(), "restricoes": set(restricoes), "vibe": vibe}


def mostrar_resultado(posicao: int, r) -> None:
    """Card de um lugar do ranking."""
    with st.container(border=True):
        st.markdown(f"### {posicao}. {r.lugar.nome}")
        st.caption(r.lugar.endereco)
        distancias = " · ".join(f"{nome}: {km:.1f} km" for nome, km in r.distancias_km.items())
        st.write(f"📍 {distancias}")
        if r.confirmadas:
            st.write("✅ Confirmado no mapa: " + ", ".join(RESTRICOES[x] for x in sorted(r.confirmadas)))
        if r.sem_informacao:
            st.write("⚠️ Sem informação, confirme com o lugar: " + ", ".join(RESTRICOES[x] for x in sorted(r.sem_informacao)))
        st.link_button("Ver no Google Maps (preço, fotos, cardápio)", link_google_maps(r.lugar))


# --- Página ---

st.set_page_config(page_title="Vamo?", page_icon="📍")
st.title("📍 Vamo?")
st.caption("Onde o grupo vai hoje, de um jeito justo para todo mundo.")

quantidade = st.number_input("Quantas pessoas vão?", min_value=2, max_value=8, value=3)

with st.form("grupo"):
    cidade = st.text_input("Cidade do rolê", value="Curitiba, PR")
    tipo = st.radio("Tipo de rolê", list(TIPOS), format_func=TIPOS.get, horizontal=True)
    respostas = []
    for i in range(int(quantidade)):
        st.divider()
        respostas.append(formulario_amigo(i))
    enviado = st.form_submit_button("Vamo? 🚀", type="primary")

if enviado:
    incompletos = [i + 1 for i, r in enumerate(respostas) if not r["nome"] or not r["endereco"]]
    if incompletos:
        st.error(f"Preencha nome e local de saída de: amigo(s) {incompletos}.")
        st.stop()

    try:
        with st.spinner("Localizando o grupo..."):
            local_cidade = localizar(cidade.strip())
            if local_cidade is None:
                st.error(f"Não encontrei a cidade '{cidade}'.")
                st.stop()

            amigos, encontrados, nao_achados = [], {}, []
            for r in respostas:
                local = localizar(r["endereco"], local_cidade.coordenada)
                if local is None:
                    nao_achados.append(f"{r['nome']} ({r['endereco']})")
                else:
                    amigos.append(Amigo(r["nome"], local.coordenada, r["restricoes"], r["vibe"]))
                    encontrados[r["nome"]] = local.endereco

        if nao_achados:
            st.error(
                f"Não encontrei perto de {cidade}: {', '.join(nao_achados)}. "
                "Tente o nome oficial do bairro ou um endereço com rua."
            )
            st.stop()

        centro = ponto_central([a.origem for a in amigos])

        with st.expander("📍 Onde encontrei cada um"):
            for nome, endereco in encontrados.items():
                st.write(f"**{nome}:** {endereco}")

        longe = [a.nome for a in amigos if distancia_km(a.origem, centro) > ALERTA_DISTANCIA_KM]
        if longe:
            st.warning(f"Confira o local de {', '.join(longe)}: parece muito longe do resto do grupo.")

        with st.spinner("Procurando lugares..."):
            lugares = buscar_lugares(centro, tipo)
    except ErroDeLocalizacao as erro:
        st.error(str(erro))
        st.stop()
    except requests.RequestException:
        st.error("O serviço de mapas não respondeu. Tente novamente em instantes.")
        st.stop()

    if not lugares:
        st.warning("Nenhum lugar encontrado perto do ponto central do grupo. Confira os endereços acima.")
        st.stop()

    st.subheader("Os 5 lugares mais justos para o grupo")
    for posicao, resultado in enumerate(ranquear(lugares, amigos, top=5), start=1):
        mostrar_resultado(posicao, resultado)

st.caption("Dados de lugares: © OpenStreetMap · Powered by [Geoapify](https://www.geoapify.com/)")