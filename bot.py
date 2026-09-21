import os, json, requests
from requests.auth import HTTPBasicAuth
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google import genai
from google.genai import types
from datetime import datetime

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDS_JSON")
SHEET_ID = os.environ.get("SHEET_ID")

# Cliente NOVO
client_ai = genai.Client(api_key=GEMINI_API_KEY)

creds_dict = json.loads(GOOGLE_CREDS_JSON)
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
g_client = gspread.authorize(creds)
sheet = g_client.open_by_key(SHEET_ID).sheet1

def baixar_imagem_twilio(url):
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    resp = requests.get(url, auth=HTTPBasicAuth(sid, token))
    return resp.content

def analisar_cupom_com_gemini(image_url):
    img_data = baixar_imagem_twilio(image_url)
    
    prompt = """Você é um extrator de cupom fiscal brasileiro.
    Extraia: nome do mercado no topo, e para CADA produto: nome completo, preço unitário.
    Retorne APENAS um JSON válido no formato:
    {"mercado": "NOME DO MERCADO", "itens": [{"produto": "NOME", "preco": 12.50}]}
    """

    response = client_ai.models.generate_content(
        model="gemini-3.6-flash",
        contents=[
            types.Part.from_bytes(data=img_data, mime_type="image/jpeg"),
            prompt
        ]
    )
    texto = response.text.replace("```json","").replace("```","").strip()
    return json.loads(texto)

@app.route("/whatsapp", methods=['POST'])
def whatsapp():
    media_url = request.values.get("MediaUrl0")
    resp = MessagingResponse()
    if media_url:
        try:
            dados = analisar_cupom_com_gemini(media_url)
            mercado = dados.get("mercado", "Desconhecido")
            count = 0
            for item in dados.get("itens", []):
                sheet.append_row([item['produto'], item['preco'], mercado, datetime.now().strftime("%d/%m/%Y")])
                count += 1
            resp.message(f"✅ Sucesso! Li {count} produtos do {mercado} e salvei!")
        except Exception as e:
            print(e)
            resp.message(f"❌ Erro ao ler: {str(e)[:200]}")
        return str(resp)
    resp.message("Olá! 👋 Mande a FOTO do seu cupom fiscal!")
    return str(resp)

@app.route("/", methods=['GET'])
def home():
    return "bot online"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
