from flask import Flask, render_template_string
import feedparser
from deep_translator import GoogleTranslator
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
BBC_RSS_URL = "http://feeds.bbci.co.uk/news/world/rss.xml"

def get_article_body(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        paragraphs = soup.find_all('p')
        text_chunks = []
        for p in paragraphs:
            txt = p.get_text().strip()
            if len(txt) > 40 and "Cookie" not in txt and "BBC" not in txt[:10]:
                text_chunks.append(txt)
                # 500単語前後にするため、取得する段落を「5段落分」に増やしました
                if len(text_chunks) >= 5:
                    break
        return "\n\n".join(text_chunks) if text_chunks else "本文の取得に失敗しました。"
    except:
        return "本文を読み込めませんでした。"

def translate_text(text):
    if not text or "失敗" in text or "読み込めません" in text:
        return "（翻訳データを取得できませんでした）"
    try:
        # 長文を一気に翻訳するとエラーになりやすいため、段落ごとに分けて安全に翻訳します
        paragraphs = text.split("\n\n")
        translated_paragraphs = []
        translator = GoogleTranslator(source='en', target='ja')
        for p in paragraphs:
            if p.strip():
                translated_paragraphs.append(translator.translate(p))
        return "\n\n".join(translated_paragraphs)
    except:
        return "（翻訳エラー）"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>My Mega Deep English News</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background-color: #f5f5f5; }
        h1 { color: #cc0000; text-align: center; border-bottom: 3px solid #cc0000; padding-bottom: 10px; }
        .instruction { text-align: center; color: #666; font-size: 0.9rem; margin-bottom: 20px; }
        .article { background: white; padding: 30px; margin-bottom: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .news-container { display: flex; gap: 40px; }
        .english-side { flex: 1; border-right: 1px solid #eee; padding-right: 30px; }
        .japanese-side { flex: 1; color: #444; background-color: #fafafa; padding: 20px; border-radius: 5px; }
        .article h2 { margin-top: 0; font-size: 1.5rem; line-height: 1.3; }
        .article a { color: #1a0dab; text-decoration: none; }
        .article a:hover { text-decoration: underline; }
        .date { color: #888; font-size: 0.8rem; margin-bottom: 15px; }
        .summary { color: #333; line-height: 1.8; font-size: 1.05rem; white-space: pre-wrap; }
        
        #dict-popup {
            position: absolute;
            display: none;
            background: #333;
            color: #fff;
            padding: 8px 12px;
            border-radius: 5px;
            font-size: 13px;
            z-index: 1000;
            max-width: 250px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }
    </style>
</head>
<body>
    <h1>📰 My Mega Deep English & Japanese News (500 words)</h1>
    <div class="instruction">💡 500単語レベルのガッツリ長文です！わからない単語はドラッグして調べてみましょう。</div>
    <div>
        {% for item in articles %}
        <div class="article">
            <div class="date">{{ item.published }}</div>
            <div class="news-container">
                <div class="english-side">
                    <h2><a href="{{ item.link }}" target="_blank">{{ item.title }}</a></h2>
                    <p class="summary">{{ item.body_en }}</p>
                </div>
                <div class="japanese-side">
                    <h2 style="color: #555;">{{ item.title_ja }}</h2>
                    <p class="summary" style="color: #666;">{{ item.body_ja }}</p>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    
    <div id="dict-popup"></div>

    <script>
        document.addEventListener('mouseup', function(e) {
            var selectedText = window.getSelection().toString().trim();
            var popup = document.getElementById('dict-popup');
            
            if (selectedText.length > 0 && selectedText.length < 30) {
                fetch('https://api.dictionaryapi.dev/api/v2/entries/en/' + selectedText)
                    .then(function(res) { return res.json(); })
                    .then(function(data) {
                        if (data && data[0]) {
                            var definition = data[0].meanings[0].definitions[0].definition;
                            var partOfSpeech = data[0].meanings[0].partOfSpeech;
                            popup.innerHTML = '<b>' + selectedText + '</b> (' + partOfSpeech + '):<br>' + definition;
                        } else {
                            popup.innerHTML = '<b>' + selectedText + '</b><br><a href="https://ejje.weblio.jp/content/' + selectedText + '" target="_blank" style="color:#ffeb3b; text-decoration:underline;">Weblioで検索</a>';
                        }
                        popup.style.top = (e.pageY + 10) + 'px';
                        popup.style.left = (e.pageX + 10) + 'px';
                        popup.style.display = 'block';
                    })
                    .catch(function() {
                        popup.innerHTML = '<b>' + selectedText + '</b><br><a href="https://ejje.weblio.jp/content/' + selectedText + '" target="_blank" style="color:#ffeb3b; text-decoration:underline;">Weblioで検索</a>';
                        popup.style.top = (e.pageY + 10) + 'px';
                        popup.style.left = (e.pageX + 10) + 'px';
                        popup.style.display = 'block';
                    });
            } else {
                popup.style.display = 'none';
            }
        });

        document.addEventListener('mousedown', function(e) {
            var popup = document.getElementById('dict-popup');
            if (e.target !== popup) {
                popup.style.display = 'none';
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    feed = feedparser.parse(BBC_RSS_URL)
    articles = []
    # 500単語×3記事だと翻訳の待ち時間が長くなりすぎるため、最新の「2記事」を厳選して表示します
    for entry in feed.entries[:2]:
        url = entry.get('link', '#')
        en_title = entry.get('title', 'No Title')
        en_body = get_article_body(url)
        articles.append({
            'title': en_title,
            'link': url,
            'published': entry.get('published', ''),
            'body_en': en_body,
            'title_ja': translate_text(en_title),
            'body_ja': translate_text(en_body)
        })
    return render_template_string(HTML_TEMPLATE, articles=articles)

if __name__ == '__main__':
    app.run(debug=True, port=5002)