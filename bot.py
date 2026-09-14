import os, json, requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURAÇÕES (vem do Render) ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDS_JSON") # Conteúdo inteiro do .json
SHEET_ID = os.environ.get("SHEET_ID") # ID da sua planilha

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Conecta na planilha
creds_dict = json.loads(GOOGLE_CREDS_JSON)
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).sheet1

def analisar_cupom_com_gemini(image_url):
    # Baixa a imagem do Twilio
    img_data = requests.get(image_url).content
    
    prompt = """
    Você é um extrator de cupom fiscal brasileiro.
    Analise a imagem. Extraia: nome do mercado no topo, e para CADA produto: nome completo, preço unitário.
    Retorne APENAS um JSON válido no formato:
    {"mercado": "NOME DO MERCADO", "itens": [{"produto": "NOME", "preco": 12.50}]}
    Se não conseguir ler o preço, pule o item. Converta vírgula para ponto.
    """
    
    response = model.generate_content([
        prompt,
        {"mime_type": "image/jpeg", "data": img_data}
    ])
    # Limpa a resposta pra virar JSON
    texto = response.text.replace("```json","").replace("```","").strip()
    return json.loads(texto)

@app.route("/whatsapp", methods=['POST'])
def whatsapp():
    msg = request.values.get("Body", "").lower()
    media_url = request.values.get("MediaUrl0")
    resp = MessagingResponse()
    
    # --- CASO 1: USUÁRIO MANDOU FOTO ---
    if media_url:
        try:
            dados = analisar_cupom_com_gemini(media_url)
            mercado = dados.get("mercado", "Desconhecido")
            count = 0
            for item in dados.get("itens", []):
                sheet.append_row([
                    item['produto'],
                    item['preco'],
                    mercado,
                    datetime.now().strftime("%d/%m/%Y")
                ])
                count += 1
            resp.message(f"✅ Sucesso! Li {count} produtos do {mercado} e salvei na planilha!")
        except Exception as e:
            print(e)
            resp.message(f"❌ Errei ao ler o cupom. Tenta mandar uma foto mais nítida? Erro: {str(e)[:100]}")
        return str(resp)

    # --- CASO 2: USUÁRIO MANDOU TEXTO ---
    if "preço" in msg or "preco" in msg or "quanto" in msg:
        # Lógica simples de busca na planilha
        produto_busca = msg.replace("preço","").replace("quanto custa","").strip()
        try:
            registros = sheet.get_all_records()
            encontrados = [r for r in registros if produto_busca in str(r['produto']).lower()]
            if encontrados:
                # Pega o mais barato
                melhor = min(encontrados, key=lambda x: float(x['preco']))
                resp.message(f"💰 Achei! {melhor['produto']} por R${melhor['preco']} no {melhor['mercado']}")
            else:
                resp.message(f"Não achei {produto_busca} na planilha ainda. Manda um cupom?")
        except:
            resp.message("Ainda estou aprendendo a buscar. Manda um cupom primeiro!")
    else:
        resp.message("Olá! 👋 Mande a FOTO do seu cupom fiscal que eu salvo tudo automático, ou pergunte ex: 'preço do arroz'")

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))