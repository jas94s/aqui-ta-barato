import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Aqui tá barato - Jijoca", page_icon="🛒", layout="centered")
st.title("🛒 Aqui tá barato - Jijoca")

# SEU ID DA PLANILHA
ID_PLANILHA = "1bY2JXhGjyr4-VV1jHVI77Fbc3OhtzwYc7CMe6TkkX1Q"
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def conectar_planilha():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], 
        scopes=SCOPE
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(ID_PLANILHA).sheet1
    
    # Cria cabeçalho se a planilha estiver vazia
    try:
        if not sheet.get_all_values():
            sheet.append_row(["Produto", "Preço", "Mercado", "Data"])
    except:
        pass
        
    return sheet

def carregar_dados():
    try:
        sheet = conectar_planilha()
        dados = sheet.get_all_records()
        if not dados:
            return pd.DataFrame(columns=["Produto", "Preço", "Mercado", "Data"])
        df = pd.DataFrame(dados)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return pd.DataFrame(columns=["Produto", "Preço", "Mercado", "Data"])

def salvar_dado(produto, preco, mercado, data):
    sheet = conectar_planilha()
    sheet.append_row([produto, float(preco), mercado, str(data)])

# Carrega
df = carregar_dados()
hoje = date.today().strftime("%d/%m/%Y")

# Abas
tab1, tab2 = st.tabs(["🔍 Buscar Preços", "➕ Adicionar Preço"])

with tab1:
    busca = st.text_input("O que você quer procurar? ex: arroz, feijão")
    if not df.empty:
        df_filtrado = df
        if busca:
            df_filtrado = df[df["Produto"].astype(str).str.contains(busca, case=False, na=False)]
        
        if not df_filtrado.empty and "Preço" in df_filtrado.columns:
            try:
                df_filtrado["Preço"] = pd.to_numeric(df_filtrado["Preço"], errors='coerce')
                st.dataframe(df_filtrado.sort_values("Preço"), use_container_width=True, hide_index=True)
            except:
                st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum produto encontrado com esse nome.")
    else:
        st.info("Nenhum produto cadastrado ainda. Seja o primeiro a adicionar!")

with tab2:
    st.subheader("Adicionar novo preço")
    with st.form("form_produto", clear_on_submit=True):
        nome = st.text_input("Nome do produto *")
        preco = st.number_input("Preço (R$) *", min_value=0.0, format="%.2f")
        mercado = st.text_input("Nome do mercado *")
        salvar = st.form_submit_button("💾 Salvar Preço", use_container_width=True)
        
        if salvar:
            if nome and mercado and preco > 0:
                try:
                    salvar_dado(nome, preco, mercado, hoje)
                    st.success(f"✅ {nome} salvo por R$ {preco:.2f} no {mercado}!")
                    st.balloons()
                    st.cache_resource.clear()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.error("Preencha todos os campos obrigatórios (*)")
