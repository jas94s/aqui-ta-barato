import streamlit as st
import pandas as pd
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Aqui tá barato - Jijoca", page_icon="🛒")
st.title("🛒 Aqui tá barato")

# --- CONEXÃO COM GOOGLE SHEETS ---
# Você vai precisar criar as credenciais depois, por enquanto deixa assim pra testar local

@st.cache_resource
def conectar_planilha():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credenciais.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("aqui-ta-barato").sheet1
    return sheet

def carregar_dados():
    try:
        sheet = conectar_planilha()
        dados = sheet.get_all_records()
        return pd.DataFrame(dados)
    except:
        return pd.DataFrame(columns=["Produto", "Preço", "Mercado", "Data"])

def salvar_dado(produto, preco, mercado, data):
    sheet = conectar_planilha()
    sheet.append_row([produto, float(preco), mercado, data])

# Carrega
df = carregar_dados()
hoje = date.today().strftime("%d/%m/%Y")

tab1, tab2 = st.tabs(["🔍 Buscar Preços", "➕ Adicionar"])

with tab1:
    busca = st.text_input("O que você quer procurar?")
    if not df.empty:
        if busca:
            filtrados = df[df["Produto"].str.contains(busca, case=False, na=False)]
            st.dataframe(filtrados.sort_values("Preço"))
        else:
            st.dataframe(df.sort_values("Preço"))
    else:
        st.info("Nenhum produto ainda!")

with tab2:
    with st.form("form_produto", clear_on_submit=True):
        nome = st.text_input("Nome do produto")
        preco = st.number_input("Preço (R$)", min_value=0.0, format="%.2f")
        mercado = st.text_input("Nome do mercado")
        salvar = st.form_submit_button("Salvar Preço")
        if salvar:
            if nome and mercado and preco > 0:
                salvar_dado(nome, preco, mercado, hoje)
                st.success(f"{nome} salvo na base!")
                st.cache_data.clear()
            else:
                st.error("Preencha tudo!")