import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Aqui tá barato - Jijoca", page_icon="🛒", layout="centered")
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
        valores = sheet.get_all_values()
        if len(valores) <= 1:
            return pd.DataFrame(columns=["Produto", "Preço", "Mercado", "Data"])

        # Pega cabeçalho e limpa espaços e maiúsculas
        cabecalho = [h.strip().capitalize() for h in valores[0]]
        dados = valores[1:]
        df = pd.DataFrame(dados, columns=cabecalho)

        # Renomeia qualquer variação para o padrão
        mapa = {}
        for col in df.columns:
            col_lower = col.lower().strip()
            if "produt" in col_lower:
                mapa[col] = "Produto"
            elif "pre" in col_lower:
                mapa[col] = "Preço"
            elif "mercad" in col_lower:
                mapa[col] = "Mercado"
            elif "data" in col_lower:
                mapa[col] = "Data"
        df = df.rename(columns=mapa)

        # Garante as 4 colunas
        for c in ["Produto", "Preço", "Mercado", "Data"]:
            if c not in df.columns:
                df[c] = ""

        return df[["Produto", "Preço", "Mercado", "Data"]]
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return pd.DataFrame(columns=["Produto", "Preço", "Mercado", "Data"])

def salvar_dado(produto, preco, mercado, data):
    sheet = conectar_planilha()
    sheet.append_row([produto, float(preco), mercado, str(data)])

df = carregar_dados()
hoje = date.today().strftime("%d/%m/%Y")
tab1, tab2 = st.tabs(["🔍 Buscar Preços", "➕ Adicionar Preço"])

with tab1:
    busca = st.text_input("O que você quer procurar?")
    if not df.empty:
        if busca:
            # busca à prova de erro
            mask = df["Produto"].astype(str).str.contains(busca, case=False, na=False)
            df_filtrado = df[mask]
        else:
            df_filtrado = df

        if not df_filtrado.empty:
            # tenta converter preço pra ordenar
            try:
                df_filtrado["Preço"] = pd.to_numeric(df_filtrado["Preço"].astype(str).str.replace(",", ".").str.replace("R$", ""), errors='coerce')
                df_filtrado = df_filtrado.sort_values("Preço")
            except:
                pass
            st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum produto com esse nome.")
    else:
        st.info("Nenhum produto cadastrado ainda.")

with tab2:
    with st.form("form_produto", clear_on_submit=True):
        nome = st.text_input("Nome do produto *")
        preco = st.number_input("Preço (R$) *", min_value=0.0, format="%.2f")
        mercado = st.text_input("Nome do mercado *")
        salvar = st.form_submit_button("💾 Salvar", use_container_width=True)
        if salvar:
            if nome and mercado and preco > 0:
                salvar_dado(nome, preco, mercado, hoje)
                st.success(f"✅ {nome} salvo!")
                st.balloons()
                st.cache_resource.clear()
                st.cache_data.clear()
            else:
                st.error("Preencha todos os campos!")
