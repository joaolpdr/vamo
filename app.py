"""Interface do Vamo? (Streamlit)."""

from datetime import date, datetime, time

import requests
import streamlit as st

from decisao import (
    RESTRICOES, Amigo, distancia_km, explicar, ponto_central, ranquear, situacao_horario,
)
from locais import ErroDeLocalizacao, buscar_lugares, geocodificar, link_google_maps

VIBES = {"tranquilo": "😌 Tranquilo", "agitado": "🎉 Agitado"}
TIPOS = {"restaurante": "🍽️ Restaurante", "bar": "🍻 Barzinho", "balada": "🪩 Balada"}
BOLSO = ["Não conferi", "Cabe", "Não cabe"]
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


def mostrar_resultado(posicao: int, r, quando: datetime) -> None:
    """Card de um lugar do ranking, com a marcação de preço."""
    with st.container(border=True):
        st.markdown(f"### {posicao}. {r.lugar.nome}")
        st.caption(r.lugar.endereco)
        distancias = " · ".join(f"{nome}: {km:.1f} km" for nome, km in r.distancias_km.items())
        st.write(f"📍 {distancias}")
        if situacao_horario(r.lugar, quando) == "aberto":
            st.write(f"🕒 Aberto às {quando:%H:%M}")
        else:
            st.write("🕒 Horário não informado no mapa, confira no Google Maps")
        if r.confirmadas:
            st.write("✅ Confirmado no mapa: " + ", ".join(RESTRICOES[x] for x in sorted(r.confirmadas)))
        if r.sem_informacao:
            st.write("⚠️ Sem informação, confirme com o lugar: " + ", ".join(RESTRICOES[x] for x in sorted(r.sem_informacao)))
        st.link_button("Ver no Google Maps (preço, fotos, cardápio)", link_google_maps(r.lugar))
        st.radio("Cabe no bolso do grupo?", BOLSO, key=f"bolso_{posicao}", horizontal=True)


def escolher(ranking: list) -> tuple:
    """Aplica a marcação de preço. Retorna (lugar escolhido, se o preço foi conferido)."""
    marcacoes = {r.lugar.nome: st.session_state.get(f"bolso_{i}", "Não conferi") for i, r in enumerate(ranking, 1)}
    cabem = [r for r in ranking if marcacoes[r.lugar.nome] == "Cabe"]
    nao_conferidos = [r for r in ranking if marcacoes[r.lugar.nome] == "Não conferi"]
    if cabem:
        return cabem[0], True
    if nao_conferidos:
        return nao_conferidos[0], False
    return None, False


def buscar(cidade: str, tipo: str, respostas: list[dict], quando: datetime) -> None:
    """Localiza o grupo, busca e ranqueia. Guarda tudo no session_state."""
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
        st.error(f"Não encontrei perto de {cidade}: {', '.join(nao_achados)}. Tente o nome oficial do bairro ou um endereço com rua.")
        st.stop()

    centro = ponto_central([a.origem for a in amigos])
    lugares = buscar_lugares(centro, tipo)
    if not lugares:
        st.warning("Nenhum lugar encontrado perto do ponto central do grupo. Confira os endereços.")
        st.stop()

    for chave in [k for k in st.session_state if str(k).startswith("bolso_")]:
        del st.session_state[chave]   # nova busca, marcações zeradas

    st.session_state.update(
        ranking=ranquear(lugares, amigos, top=5, quando=quando),
        amigos=amigos,
        encontrados=encontrados,
        quando=quando,
        fechados=sum(situacao_horario(l, quando) == "fechado" for l in lugares),
        longe=[a.nome for a in amigos if distancia_km(a.origem, centro) > ALERTA_DISTANCIA_KM],
        decidido=False,
    )


# --- Página ---

st.set_page_config(page_title="Vamo?", page_icon="📍")
st.title("📍 Vamo?")
st.caption("Onde o grupo vai hoje, de um jeito justo para todo mundo.")

quantidade = st.number_input("Quantas pessoas vão?", min_value=2, max_value=8, value=3)

with st.form("grupo"):
    cidade = st.text_input("Cidade do rolê", value="Curitiba, PR")
    tipo = st.radio("Tipo de rolê", list(TIPOS), format_func=TIPOS.get, horizontal=True)
    col_dia, col_hora = st.columns(2)
    dia = col_dia.date_input("Dia", value=date.today(), format="DD/MM/YYYY")
    hora = col_hora.time_input("Horário", value=time(20, 0), step=1800)
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
        with st.spinner("Procurando o lugar mais justo..."):
            buscar(cidade, tipo, respostas, datetime.combine(dia, hora))
    except ErroDeLocalizacao as erro:
        st.error(str(erro))
        st.stop()
    except requests.RequestException:
        st.error("O serviço de mapas não respondeu. Tente novamente em instantes.")
        st.stop()

if "ranking" in st.session_state:
    ranking, quando = st.session_state.ranking, st.session_state.quando

    with st.expander("📍 Onde encontrei cada um"):
        for nome, endereco in st.session_state.encontrados.items():
            st.write(f"**{nome}:** {endereco}")
    if st.session_state.longe:
        st.warning(f"Confira o local de {', '.join(st.session_state.longe)}: parece muito longe do resto do grupo.")

    if not ranking:
        st.warning("Todos os lugares encontrados estão fechados nesse horário. Tente outro horário.")
        st.stop()

    st.subheader(f"Os {len(ranking)} lugares mais justos para {quando:%d/%m} às {quando:%H:%M}")
    if st.session_state.fechados:
        st.caption(f"{st.session_state.fechados} lugar(es) fechado(s) nesse horário foram removidos.")
    st.caption("Confira o preço no Google Maps e marque se cabe no bolso do grupo.")

    for posicao, resultado in enumerate(ranking, start=1):
        mostrar_resultado(posicao, resultado, quando)

    if st.button("Decidir 🎯", type="primary"):
        st.session_state.decidido = True

    if st.session_state.decidido:
        escolhido, preco_conferido = escolher(ranking)
        if escolhido is None:
            st.warning("Nenhum dos 5 lugares cabe no bolso. Tente outro tipo de rolê ou outro horário.")
        else:
            st.success(f"## Vamo no {escolhido.lugar.nome}! 🎉")
            for frase in explicar(escolhido, st.session_state.amigos):
                st.write(f"- {frase}")
            if not preco_conferido:
                st.info("Ninguém conferiu o preço ainda. Vale dar uma olhada no Google Maps antes de ir.")
            st.link_button("Abrir no Google Maps", link_google_maps(escolhido.lugar))

st.caption("Dados de lugares: © OpenStreetMap · Powered by [Geoapify](https://www.geoapify.com/)")