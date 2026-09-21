import os, json, requests
from datetime import datetime
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google import genai
from google.genai import types

app = Flask(__name__)

# --- CONFIG ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json = os.environ.get("GOOGLE_CREDS_JSON")
creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)
SHEET_ID = os.environ.get("SHEET_ID")
sheet = gc.open_by_key(SHEET_ID).sheet1
client_ai = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def baixar_imagem_twilio(media_url):
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    resp = requests.get(media_url, auth=(account_sid, auth_token))
    return resp.content

def pega_valor_real(valor_str):
    try:
        v = str(valor_str).replace('R$','').replace(' ','').replace(',','.').strip()
        return float(v)
    except:
        return 9999.0

@app.route("/whatsapp", methods=['POST'])
def whatsapp():
    body = request.values.get("Body", "").strip()
    media_urls = [request.values.get(f"MediaUrl{i}") for i in range(10) if request.values.get(f"MediaUrl{i}")]
    resp = MessagingResponse()

    try:
        # CASO 1: LISTA DE COMPRAS
        if not media_urls and body:
            registros = sheet.get_all_records()
            print(f"Total registros: {len(registros)}")
            
            itens_busca = [x.strip().lower() for x in body.replace("\n", ",").split(",") if x.strip()]

            if not registros:
                resp.message("Planilha vazia. Mande fotos primeiro!")
            else:
                resposta = "🛒 *Onde comprar mais barato:*\n\n"
                for item_busca in itens_busca:
                    # BUSCA INTELIGENTE: verifica se o que buscou ESTÁ CONTIDO no produto
                    ocorrencias = []
                    for r in registros:
                        nome_prod = str(r.get('produto','') or r.get('PRODUTO','') or '').lower()
                        if item_busca in nome_prod:
                            ocorrencias.append(r)

                    if ocorrencias:
                        mais_barato = min(ocorrencias, key=lambda x: pega_valor_real(x.get('preço') or x.get('PREÇO') or x.get('preco') or 0))
                        preco = mais_barato.get('preço') or mais_barato.get('PREÇO') or mais_barato.get('preco')
                        mercado = mais_barato.get('mercado') or mais_barato.get('MERCADO')
                        prod = mais_barato.get('produto') or mais_barato.get('PRODUTO')
                        resposta += f"*{item_busca.upper()}* -> {preco} no {mercado} ({prod})\n"
                    else:
                        resposta += f"*{item_busca.upper()}* -> ainda não tenho preço\n"
                
                resp.message(resposta)

        # CASO 2: FOTO DE CUPOM
        elif media_urls:
            total_itens = 0
            mercados = []
            for media_url in media_urls:
                img_data = baixar_imagem_twilio(media_url)
                response = client_ai.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[
                        types.Part.from_bytes(data=img_data, mime_type="image/jpeg"),
                        'Extraia o mercado e os itens em JSON puro, sem markdown: {"mercado": "NOME", "itens": [{"produto": "NOME PRODUTO", "preco": 12.50}]} Use ponto no preço.'
                    ]
                )
                texto = response.text.replace("```json","").replace("```","").strip()
                dados = json.loads(texto)
                for item in dados.get("itens", []):
                    sheet.append_row([item['produto'], f"R$ {item['preco']}".replace('.',','), dados.get("mercado",""), datetime.now().strftime("%d/%m/%Y")])
                    total_itens += 1
                mercados.append(dados.get("mercado",""))
            resp.message(f"✅ Sucesso! Salvei {total_itens} produtos - {', '.join(set(mercados))}")
        else:
            resp.message("Olá! 👋\n1️⃣ Mande FOTO do cupom\n2️⃣ Mande LISTA: sal, banana, ovo")

    except Exception as e:
        print(f"ERRO: {e}")
        import traceback; traceback.print_exc()
        resp.message(f"❌ Erro: {str(e)[:300]}")

    return str(resp), 200, {'Content-Type': 'text/xml'}

if __name__ == "__main__":
    app.run()
