from flask import Flask
import threading
import os
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import re
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Flask(__name__)

print("Bot iniciado...")


async def getProductDataShopee(link):
    try:
        print("Procurando produto na Shopee...")
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(link,
                         headers=headers,
                         timeout=100,
                         allow_redirects=True)
        final_url = r.url
        r = requests.get(final_url, headers=headers, timeout=100)
        soup = BeautifulSoup(r.text, 'html.parser')

        title_tag = soup.find("meta", property="og:title")
        title = title_tag["content"] if title_tag else "Produto sem nome"

        img_tag = soup.find("meta", property="og:image")
        img_url = img_tag["content"] if img_tag else None

        price_regex = re.findall(r"R\$[\s]?\d+[.,]?\d*", r.text)
        price_text = price_regex[0] if price_regex else "Preço não encontrado"

        mensagem = f"🔥 {title}\n💬 Oferta especial pra você!\n💰 {price_text}\n🔗 {link}"

        # with open("shopee_page.html", "w", encoding="utf-8") as file:
        #     file.write(r.text)

        return mensagem, img_url

    except Exception as e:
        return f"Erro ao processar link da Shopee: {e}", None


async def getProductDataAmzn(link):
    try:
        print("Procurando produto na Amazon...")
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(link,
                         headers=headers,
                         timeout=100,
                         allow_redirects=True)
        final_url = r.url
        r = requests.get(final_url, headers=headers, timeout=100)

        # Salvar o HTML para debug com timestamp
        filename = f"amz_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(filename, "w", encoding="utf-8") as file:
            file.write(r.text)

        soup = BeautifulSoup(r.text, 'html.parser')

        # Título
        title_tag = soup.find("span", id="productTitle")
        title = title_tag.get_text(
            strip=True) if title_tag else "Produto sem nome"

        # Imagem principal
        img_tag = soup.find("img", id="landingImage")
        img_url = img_tag["data-old-hires"] if img_tag and img_tag.has_attr(
            "data-old-hires") else None

        # Preço – buscar todos os <span class="a-offscreen"> com R$
        price_spans = soup.find_all("span", class_="a-offscreen")
        prices = []

        for span in price_spans:
            text = span.get_text(strip=True)
            match = re.search(r"R\$[\s]?\d+[.,]?\d*", text)
            if match:
                value = float(
                    match.group(0).replace("R$",
                                           "").replace(".",
                                                       "").replace(",", "."))
                prices.append(value)

        if prices:
            max_price = max(prices)
            price_text = f"R$ {max_price:,.2f}".replace(".", "v").replace(
                ",", ".").replace("v", ",")
        else:
            price_text = "Preço não encontrado"

        # Mensagem final
        mensagem = f"🔥 {title}\n💬 Oferta especial pra você!\n💰 {price_text}\n🔗 {link}"
        return mensagem, img_url

    except Exception as e:
        return f"Erro ao processar link da Amazon: {e}", None


async def getProductDataMercadoLivre(link):
    try:
        print("Procurando produto no Mercado Livre...")
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(link,
                         headers=headers,
                         timeout=100,
                         allow_redirects=True)
        final_url = r.url
        r = requests.get(final_url, headers=headers, timeout=100)

        # Salva o HTML para debug
        # filename = f"merc_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        # with open(filename, "w", encoding="utf-8") as file:
        #     file.write(r.text)

        soup = BeautifulSoup(r.text, 'html.parser')

        # Título
        title_tag = soup.find("meta", property="og:title")
        title = title_tag["content"] if title_tag else "Produto sem nome"

        # Imagem
        img_tag = soup.find("meta", property="og:image")
        img_url = img_tag["content"] if img_tag else None

        # Seleciona o container do preço atual
        current_price_container = soup.find("div",
                                            class_="poly-price__current")

        if current_price_container:
            fraction_tag = current_price_container.find(
                "span", class_="andes-money-amount__fraction")
            cents_tag = current_price_container.find(
                "span", class_="andes-money-amount__cents")

            if fraction_tag:
                fraction = fraction_tag.get_text(strip=True)
                cents = cents_tag.get_text(strip=True) if cents_tag else "00"
                price_text = f"R$ {fraction},{cents}"
            else:
                price_text = "Preço não encontrado"
        else:
            price_text = "Preço não encontrado"

        mensagem = f"🔥 {title}\n💬 Oferta especial pra você!\n💰 {price_text}\n🔗 {link}"
        return mensagem, img_url

    except Exception as e:
        return f"Erro ao processar link do Mercado Livre: {e}", None


# === Handler ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "shopee" in text:
        match = re.search(r'https:\/\/[^\s]+', text)
        if match:
            msg, image_url = await getProductDataShopee(match.group(0))
        else:
            msg, image_url = "Link da Shopee não encontrado.", None

    elif "mercadolivre.com" in text:
        match = re.search(r'https:\/\/[^\s]+', text)
        if match:
            msg, image_url = await getProductDataMercadoLivre(match.group(0))
        else:
            msg, image_url = "Link da Shopee não encontrado.", None

    elif "amzn" in text:
        match = re.search(r'https:\/\/[^\s]+', text)
        if match:
            msg, image_url = await getProductDataAmzn(match.group(0))
        else:
            msg, image_url = "Link da Shopee não encontrado.", None
    else:
        msg, image_url = "Link da Shopee não encontrado.", None

    if image_url:
        await context.bot.send_photo(chat_id=update.effective_chat.id,
                                     photo=image_url,
                                     caption=msg,
                                     parse_mode='Markdown')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=msg,
                                       parse_mode='Markdown')


# === Bot Runner ===
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,
                               handle_message))
app.run_polling()


def run_telegram_bot():
    import asyncio

    async def main():
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        await app.run_polling()

    asyncio.run(main())


@app.route("/")
def home():
    return "Bot está rodando!", 200


if __name__ == "__main__":
    # Rodar Flask e Telegram bot em threads diferentes
    threading.Thread(target=run_telegram_bot).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
