import os, json, requests
from datetime import datetime
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google import genai
from google.genai import types
from difflib import get_close_matches

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json = os.environ.get("GOOGLE_CREDS_JSON")
creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gc = gspread.authorize(creds)
SHEET_ID = os.environ.get("SHEET_ID") # Coloca o ID da sua planilha no Render > Environment
sheet = gc.open_by_key(SHEET_ID).sheet1

client_ai = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def baixar_imagem_twilio(media_url):
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    resp = requests.get(media_url, auth=(account_sid, auth_token))
    return resp.content

@app.route("/whatsapp", methods=['POST'])
def whatsapp():
    body = request.values.get("Body", "").strip()
    media_urls = [request.values.get(f"MediaUrl{i}") for i in range(10) if request.values.get(f"MediaUrl{i}")]
    resp = MessagingResponse()

    try:
        # CASO 1: LISTA DE COMPRAS (texto)
        if not media_urls and body and len(body) > 2:
            registros = sheet.get_all_records()
            itens_busca = [x.strip().lower() for x in body.replace("\n", ",").split(",") if x.strip()]

            if not registros:
                resp.message("Sua planilha ainda está vazia. Mande fotos de cupons primeiro!")
            else:
                resposta = "🛒 *Onde comprar mais barato:*\n\n"
                for item_busca in itens_busca:
                    produtos_planilha = [str(r.get('PRODUTO','')).lower() for r in registros]
                    match = get_close_matches(item_busca, produtos_planilha, n=1, cutoff=0.6)

                    if match:
                        nome_match = match[0]
                        ocorrencias = [r for r in registros if str(r.get('PRODUTO','')).lower() == nome_match]
                        try:
                            mais_barato = min(ocorrencias, key=lambda x: float(str(x.get('PREÇO', 999)).replace('R$','').replace(',','.').strip()))
                            resposta += f"*{item_busca.upper()}* -> R$ {mais_barato.get('PREÇO')} no {mais_barato.get('MERCADO')} ({mais_barato.get('PRODUTO')})\n"
                        except:
                            resposta += f"*{item_busca.upper()}* -> achei mas preço com erro\n"
                    else:
                        resposta += f"*{item_busca.upper()}* -> ainda não tenho preço\n"
                resp.message(resposta)

        # CASO 2: CUPOM (foto)
        elif media_urls:
            total_itens = 0
            mercados = []
            for media_url in media_urls:
                img_data = baixar_imagem_twilio(media_url)
                response = client_ai.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[
                        types.Part.from_bytes(data=img_data, mime_type="image/jpeg"),
                        'Extraia o mercado e os itens em JSON puro, sem markdown: {"mercado": "NOME DO MERCADO", "itens": [{"produto": "NOME PRODUTO", "preco": 12.50}]} Use ponto no preço.'
                    ]
                )
                texto = response.text.replace("```json","").replace("```","").strip()
                dados = json.loads(texto)
                for item in dados.get("itens", []):
                    sheet.append_row([item['produto'], item['preco'], dados.get("mercado",""), datetime.now().strftime("%d/%m/%Y")])
                    total_itens += 1
                mercados.append(dados.get("mercado",""))

            resp.message(f"✅ Sucesso! Salvei {total_itens} produtos de {len(media_urls)} foto(s) - {', '.join(set(mercados))}")

        else:
            resp.message("Olá! 👋\n\n1️⃣ Mande FOTO do cupom pra salvar\n2️⃣ Mande LISTA tipo: arroz, feijão, leite pra saber onde é mais barato")

    except Exception as e:
        print(f"ERRO: {e}")
        import traceback; traceback.print_exc()
        resp.message(f"❌ Erro: {str(e)[:300]}")

    return str(resp), 200, {'Content-Type': 'text/xml'}

if __name__ == "__main__":
    app.run()
