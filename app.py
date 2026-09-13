import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Aqui tá barato - Jijoca", page_icon="🛒")

st.title("🛒 Aqui tá barato")
st.write("Cadastre e descubra onde tá mais barato em Jijoca e Jericoacoara")

if "produtos" not in st.session_state:
    st.session_state.produtos = pd.DataFrame(columns=["Produto", "Preço", "Mercado", "Data"])

hoje = date.today().strftime("%d/%m/%Y")

tab1, tab2 = st.tabs(["🔍 Buscar Preços", "➕ Adicionar"])

with tab1:
    st.subheader("Onde tá mais barato?")
    busca = st.text_input("Digite o produto que você quer procurar")
    if not st.session_state.produtos.empty:
        if busca:
            filtrados = st.session_state.produtos[st.session_state.produtos["Produto"].str.contains(busca, case=False)]
            st.dataframe(filtrados.sort_values("Preço"))
        else:
            st.dataframe(st.session_state.produtos.sort_values("Preço"))
    else:
        st.info("Nenhum produto cadastrado ainda. Vá em Adicionar!")

with tab2:
    st.subheader("Cadastrar novo preço")
    with st.form("form_produto", clear_on_submit=True):
        nome = st.text_input("Nome do produto (ex: Arroz 5kg)")
        preco = st.number_input("Preço (R$)", min_value=0.0, format="%.2f")
        mercado = st.text_input("Nome do mercado")
        salvar = st.form_submit_button("Salvar Preço")
        if salvar:
            if nome and mercado and preco > 0:
                novo = pd.DataFrame([[nome, preco, mercado, hoje]], columns=["Produto", "Preço", "Mercado", "Data"])
                st.session_state.produtos = pd.concat([st.session_state.produtos, novo], ignore_index=True)
                st.success(f"{nome} salvo com sucesso!")
            else:
                st.error("Preencha tudo certinho!")