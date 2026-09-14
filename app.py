import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Aqui tá barato - Jijoca", page_icon="🛒")
st.title("🛒 Aqui tá barato - Jijoca")

ID_PLANILHA = "1bY2JXhGjyr4-VV1jHVI77Fbc3OhtzwYc7CMe6TkkX1Q"
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def conectar_planilha():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPE)
    client = gspread.authorize(creds)
    return client.open_by_key(ID_PLANILHA).sheet1

def carregar_dados():
    try:
        sheet = conectar_planilha()
        return pd.DataFrame(sheet.get_all_records())
    except:
        return pd.DataFrame(columns=["Produto", "Preço", "Mercado", "Data"])

def salvar_dado(produto, preco, mercado, data):
    sheet = conectar_planilha()
    sheet.append_row([produto, float(preco), mercado, str(data)])

df = carregar_dados()
hoje = date.today().strftime("%d/%m/%Y")
tab1, tab2 = st.tabs(["🔍 Buscar", "➕ Adicionar"])
with tab1:
    busca = st.text_input("O que procurar?")
    if not df.empty:
        if busca:
            st.dataframe(df[df["Produto"].str.contains(busca, case=False, na=False)].sort_values("Preço"), use_container_width=True)
        else:
            st.dataframe(df.sort_values("Preço"), use_container_width=True)
    else:
        st.info("Nenhum produto ainda!")
with tab2:
    with st.form("form", clear_on_submit=True):
        nome = st.text_input("Produto")
        preco = st.number_input("Preço R$", min_value=0.0, format="%.2f")
        mercado = st.text_input("Mercado")
        ok = st.form_submit_button("Salvar")
        if ok and nome and mercado and preco>0:
            salvar_dado(nome, preco, mercado, hoje)
            st.success("Salvo!")
            st.cache_resource.clear()
            st.rerun()
