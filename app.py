import feedparser
from flask import Flask, render_template_string
from bs4 import BeautifulSoup
import requests
from deep_translator import GoogleTranslator
import time
import xml.etree.ElementTree as ET

app = Flask(__name__)

# キャッシュ用の部屋
CACHED_DATA = None
LAST_FETCH_TIME = 0
CACHE_DURATION = 3600  # 1時間

def get_bbc_news():
    RSS_URL = "https://feeds.bbci.co.uk/news/rss.xml"
    feed = feedparser.parse(RSS_URL)
    articles = []
    
    for entry in feed.entries[:2]:
        try:
            resp = requests.get(entry.link, timeout=5)
            soup = BeautifulSoup(resp.text, 'html.parser')
            p_tags = soup.find_all('p')
            paragraphs = [p.get_text() for p in p_tags if len(p.get_text().split()) > 10]
            text = " ".join(paragraphs[:5])
            if text:
                articles.append({
                    "title": f"📰 {entry.title}",
                    "url": entry.link,
                    "text": text
                })
        except Exception as e:
            print(f"Error fetching BBC: {e}")
            continue
    return articles

def get_latest_medical_abstract():
    try:
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=neuroscience&retmode=json&retmax=1&sort=pub_date"
        search_resp = requests.get(search_url, timeout=5).json()
        
        id_list = search_resp.get("esearchresult", {}).get("idlist", [])
        if id_list:
            pubmed_id = id_list[0]
            fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pubmed_id}&retmode=xml"
            fetch_resp = requests.get(fetch_url, timeout=5)
            
            root = ET.fromstring(fetch_resp.content)
            title_element = root.find(".//ArticleTitle")
            title = title_element.text if title_element is not None else "Latest Medical Research"
            
            abstract_texts = [elem.text for elem in root.findall(".//AbstractText") if elem.text]
            abstract = " ".join(abstract_texts)
            
            if abstract:
                return {
                    "title": f"🔬 [PubMed最新論文] {title}",
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/",
                    "text": abstract
                }
    except Exception as e:
        print(f"Error fetching PubMed: {e}")
    
    # 🌟【ここを修正】APIエラーやタイムアウトの時は、あの鬼むず長文を必ず出す！
    return {
        "title": "🔬 [PubMed/Challenge] Pathological manifestations of neurodegenerative conditions",
        "url": "https://pubmed.ncbi.nlm.nih.gov/",
        "text": (
            "Pathological manifestations of neurodegenerative conditions, particularly those "
            "characterized by the aberrant aggregation of misfolded tau proteins within the cortical "
            "interneurons, have long confounded clinicians seeking to elucidate the precise molecular "
            "cascades that precipitate synaptic dysfunction. While contemporary neuroimaging modalities, "
            "such as high-resolution positron emission tomography, have facilitated the in vivo visualization "
            "of amyloid-beta deposition, the degree to which these proteopathic aggregates directly correlate "
            "with cognitive decline remains a subject of intense academic disputation."
        )
    }

@app.route('/')
def index():
    global CACHED_DATA, LAST_FETCH_TIME
    current_time = time.time()
    
    if CACHED_DATA and (current_time - LAST_FETCH_TIME < CACHE_DURATION):
        return CACHED_DATA

    articles = get_bbc_news()
    
    # 常に何かしらの医学論文データが返ってくるので確実に合流します
    med_article = get_latest_medical_abstract()
    articles.append(med_article)
        
    translated_articles = []
    
    for art in articles:
        words = art["text"].split()
        chunks = [" ".join(words[i:i+150]) for i in range(0, len(words), 150)]
        
        translated_chunks = []
        for chunk in chunks:
            try:
                translated_text = GoogleTranslator(source='en', target='ja').translate(chunk)
                translated_chunks.append(translated_text)
            except Exception as e:
                translated_chunks.append("[翻訳エラー]")
        
        full_translation = " ".join(translated_chunks)
        
        translated_articles.append({
            "title": art["title"],
            "url": art["url"],
            "english": art["text"],
            "japanese": full_translation
        })
        
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>爆速辞書付きニュース＆毎日最新医学論文</title>
        <style>
            body { font-family: sans-serif; margin: 20px; background: #f5f5f5; }
            .article { background: white; padding: 20px; margin-bottom: 30px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            h2 { color: #333; font-size: 20px; }
            h2 a { color: #0066cc; text-decoration: none; }
            h2 a:hover { text-decoration: underline; }
            .container { display: flex; gap: 20px; }
            .box { width: 50%; padding: 15px; border: 1px solid #ddd; border-radius: 5px; background: #fff; line-height: 1.6; }
            .english { font-size: 18px; font-family: 'Georgia', serif; }
            .japanese { font-size: 16px; color: #444; background: #fdfdfd; }
            #dict-popup {
                position: absolute; display: none; background: rgba(0, 0, 0, 0.9);
                color: white; padding: 12px; border-radius: 8px; max-width: 300px;
                font-size: 14px; z-index: 1000; box-shadow: 0 4px 10px rgba(0,0,0,0.3);
                line-height: 1.4;
            }
            #dict-popup a { color: #ffeb3b; text-decoration: underline; display: block; margin-top: 8px; }
            @media (max-width: 768px) {
                .container { flex-direction: column; }
                .box { width: 100%; }
            }
        </style>
    </head>
    <body>
        <h1>📚 本日の英文（最新ニュース2本 ＋ 本物の最新医学論文）</h1>
        
        {% for art in articles %}
        <div class="article">
            <h2><a href="{{ art.url }}" target="_blank">{{ art.title }}</a></h2>
            <div class="container">
                <div class="box english">{{ art.english }}</div>
                <div class="box japanese">{{ art.japanese }}</div>
            </div>
        </div>
        {% endfor %}

        <div id="dict-popup">
            <div id="popup-text">Loading...</div>
            <a id="weblio-link" href="#" target="_blank">Weblioで詳しく見る</a>
        </div>

        <script>
            document.addEventListener('mouseup', function(e) {
                var selectedText = window.getSelection().toString().trim();
                var popup = document.getElementById('dict-popup');
                if (selectedText.length > 0 && !selectedText.includes(' ') && selectedText.length < 30) {
                    popup.style.left = e.pageX + 'px';
                    popup.style.top = (e.pageY + 15) + 'px';
                    popup.style.display = 'block';
                    document.getElementById('popup-text').innerText = "🔍 '" + selectedText + "' を検索中...";
                    document.getElementById('weblio-link').href = "https://ejje.weblio.jp/content/" + encodeURIComponent(selectedText);
                    
                    fetch('https://api.dictionaryapi.dev/api/v2/entries/en/' + selectedText)
                        .then(response => response.json())
                        .then(data => {
                            if (data && data[0] && data[0].meanings && data[0].meanings[0]) {
                                var definition = data[0].meanings[0].definitions[0].definition;
                                var partOfSpeech = data[0].meanings[0].partOfSpeech;
                                document.getElementById('popup-text').innerHTML = "<strong>[" + partOfSpeech + "]</strong> " + definition;
                            } else {
                                document.getElementById('popup-text').innerText = "辞書にデータがありません。下のリンクを使ってね。";
                            }
                        })
                        .catch(err => {
                            document.getElementById('popup-text').innerText = "エラーが発生しました。";
                        });
                } else {
                    if (e.target.id !== 'dict-popup' && e.target.id !== 'popup-text' && e.target.id !== 'weblio-link') {
                        popup.style.display = 'none';
                    }
                }
            });
        </script>
    </body>
    </html>
    """
    
    CACHED_DATA = render_template_string(html_template, articles=translated_articles)
    LAST_FETCH_TIME = current_time
    
    return CACHED_DATA

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)