# Infrastructure Daily Digest Bot (Professional Edition, Optimized for Clarity & Telegram)

import subprocess
import sys
import os
from datetime import datetime, timedelta
import asyncio
import nest_asyncio
import re
import json
import pytz
from typing import List, Dict

# Enable nested asyncio for Google Colab
nest_asyncio.apply()

def install_packages():
    packages = [
        'requests',
        'beautifulsoup4',
        'python-telegram-bot',
        'google-generativeai',
        'lxml',
        'python-dateutil',
        'pytz'
    ]
    for package in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package, "-q"])
        except Exception as e:
            print(f"Error installing {package}: {e}")

install_packages()

import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from telegram import Bot
from telegram.constants import ParseMode
from dateutil import parser
import warnings
warnings.filterwarnings('ignore')

class InfrastructureDigestBot:
    def __init__(self, gemini_api_key: str, telegram_bot_token: str, telegram_chat_id: str):
        self.gemini_api_key = gemini_api_key
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id

        genai.configure(api_key=gemini_api_key)
        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest')
        self.telegram_bot = Bot(token=telegram_bot_token)

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0',
        })
        self.session.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text.strip())
        text = re.sub(r'[^\x00-\x7F]+', '', text)  # remove non-ascii
        return text[:200] + "..." if len(text) > 200 else text

    def scrape_example(self) -> List[Dict]:
        urls = {
            "ET Infra": "https://infra.economictimes.indiatimes.com/",
            "Infrastructure Today": "https://infrastructuretoday.co.in/",
            "L&T": "https://www.larsentoubro.com/corporate/media/press-releases/",
            "Construction World": "https://www.constructionworld.in/latest-news",
            "ONGC": "https://ongcindia.com/",
            "Projects Today": "https://www.projectstoday.com/News",
            "BEML": "https://www.bemlindia.in/press-release/"
        }

        headlines = []
        for source, url in urls.items():
            try:
                response = self.session.get(url, timeout=20)
                soup = BeautifulSoup(response.content, 'html.parser')

                if source == "ET Infra":
                    articles = soup.select('h3 a')
                elif source == "Infrastructure Today":
                    articles = soup.select('.jeg_post_title a')
                elif source == "L&T":
                    articles = soup.select('div.latest-news h3 a')
                elif source == "Construction World":
                    articles = soup.select('h3 a')
                elif source == "ONGC":
                    articles = soup.select('div.news a')
                elif source == "Projects Today":
                    articles = soup.select('div.card h4 a')
                elif source == "BEML":
                    articles = soup.select('div.page-title h1')
                else:
                    articles = []

                for article in articles[:10]:
                    title = self.clean_text(article.get_text(strip=True))
                    href = article.get("href")
                    link = href if href and href.startswith("http") else f"{url.rstrip('/')}/{href.lstrip('/')}" if href else url
                    if title:
                        headlines.append({"title": title, "source": source, "url": link})

            except Exception as e:
                print(f"Scraping error from {source}: {e}")

        return headlines

    def categorize_headlines(self, headlines: List[Dict]) -> Dict[str, List[Dict]]:
        categories = {
            'Energy & Oil': [],
            'Construction & Infrastructure': [],
            'Tenders & Contracts': [],
            'Technology & Innovation': [],
            'Heavy Equipment': [],
            'Other News': []
        }
        energy = ['oil', 'gas', 'energy', 'ongc']
        construction = ['construction', 'infrastructure', 'bridge', 'metro']
        tenders = ['tender', 'bid', 'contract']
        tech = ['technology', 'digital', 'ai']
        equipment = ['crane', 'loader', 'excavator', 'backhoe', 'bulldozer', 'heavy equipment', 'jcb', 'construction machine']

        for h in headlines:
            title = h['title'].lower()
            if any(k in title for k in energy):
                categories['Energy & Oil'].append(h)
            elif any(k in title for k in construction):
                categories['Construction & Infrastructure'].append(h)
            elif any(k in title for k in tenders):
                categories['Tenders & Contracts'].append(h)
            elif any(k in title for k in equipment):
                categories['Heavy Equipment'].append(h)
            elif any(k in title for k in tech):
                categories['Technology & Innovation'].append(h)
            else:
                categories['Other News'].append(h)

        return categories

    def generate_digest_with_gemini(self, categorized_headlines: Dict) -> str:
        try:
            ist = pytz.timezone("Asia/Kolkata")
            now_ist = datetime.now(ist)
            date_only = now_ist.strftime("%d %B %Y")
            greeting = "Good Morning Mr. Keshav Agarwal" if now_ist.hour < 12 else "Good Evening Mr. Keshav Agarwal"

            headlines_text = ""
            total_articles = 0
            for cat, items in categorized_headlines.items():
                if items:
                    headlines_text += f"\n{cat}:\n"
                    for h in items:
                        headlines_text += f"- {h['title']} ({h['source']})\n"
                        total_articles += 1

            if not headlines_text.strip():
                headlines_text = "No infrastructure news available."

            prompt = f"""{greeting}! \U0001F4C8\n{date_only}

Here are today's top Infrastructure Headlines ({total_articles} total):
{headlines_text}

Now write a Telegram-friendly summary using the following rules:
- Use only <b> and <i> HTML tags.
- For each category (like Energy & Oil, Heavy Equipment, etc.), summarize in 2–3 impactful sentences.
- Include specific company names, numbers, and regions.
- Mention the source name (e.g., ET Infra), but do not hyperlink it.
- Make a separate section for <b>Heavy Equipment</b> updates (like cranes, excavators, machinery).
- End with: \U0001F680 Stay ahead with CD Jindal AI Assistant"""

            response = self.gemini_model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini failed: {e}")
            return self.create_fallback_digest(categorized_headlines)

    def create_fallback_digest(self, categorized_headlines: Dict) -> str:
        ist = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(ist)
        date_only = now_ist.strftime("%d %B %Y")
        greeting = "Good Morning Mr. Keshav Agarwal" if now_ist.hour < 12 else "Good Evening Mr. Keshav Agarwal"

        digest = f"<b>{greeting}! \U0001F4C8</b>\n{date_only}\n\n<b>Daily Infrastructure Industry Digest</b>\n\n"

        for category, items in categorized_headlines.items():
            if items:
                sources = list(set(i['source'] for i in items))
                digest += f"<b>{category}:</b>\n{len(items)} key updates from {', '.join(sources[:2])}.\n\n"

        if not any(categorized_headlines.values()):
            digest += "No infrastructure news today.\n\n"

        digest += "\U0001F680 Stay ahead with CD Jindal AI Assistant"
        return digest

    async def send_to_telegram(self, message: str):
        try:
            clean_message = (
                message.replace("<ul>", "")
                       .replace("</ul>", "")
                       .replace("<li>", "• ")
                       .replace("</li>", "\n")
                       .replace("<br>", "\n")
                       .replace("<br/>", "\n")
                       .replace("<br />", "\n")
                       .replace("&nbsp;", " ")
            )
            await self.telegram_bot.send_message(
                chat_id=self.telegram_chat_id,
                text=clean_message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            print("Sent successfully")
        except Exception as e:
            print(f"Telegram error: {e}")

    async def run_digest(self):
        print("Running Digest...")
        headlines = self.scrape_example()
        categorized = self.categorize_headlines(headlines)
        digest = self.generate_digest_with_gemini(categorized)
        await self.send_to_telegram(digest)

# Replace with real keys
GEMINI_API_KEY = "AIzaSyA9fTCND8yn7wLG_-DdJBNQVCuJtTuW6TU"
TELEGRAM_BOT_TOKEN = "7890456652:AAGpWlvqHMUk8wF4tmuQsua3dSBxlwWSdlM"
TELEGRAM_CHAT_ID = "8091448586"

bot = InfrastructureDigestBot(GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
asyncio.run(bot.run_digest())
