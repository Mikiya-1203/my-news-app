import feedparser
from flask import Flask, render_template_string
from bs4 import BeautifulSoup
import requests
from deep_translator import GoogleTranslator
import xml.etree.ElementTree as ET
import random  # 🌟 ランダム機能を追加

app = Flask(__name__)

def get_bbc_news():
    RSS_URL = "https://feeds.bbci.co.uk/news/rss.xml"
    feed = feedparser.parse(RSS_URL)
    articles = []
    
    # ニュースは厳選した1本にして、その代わり段落を多く（長く）する
    for entry in feed.entries[:1]:
        try:
            resp = requests.get(entry.link, timeout=5)
            soup = BeautifulSoup(resp.text, 'html.parser')
            p_tags = soup.find_all('p')
            paragraphs = [p.get_text() for p in p_tags if len(p.get_text().split()) > 10]
            
            # 🌟 段落数を8個に増やして、しっかりとした長文にする
            text = " ".join(paragraphs[:8])
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

def get_random_medical_long_text():
    # 🌟 毎回変わるように、ランダムな検索キーワードを用意
    keywords = ['neuroscience', 'cancer', 'immunology', 'genetics', 'cardiology', 'psychiatry', 'diabetes', 'virology']
    kw = random.choice(keywords)
    
    try:
        # キーワードで最新20件を検索
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={kw}&retmode=json&retmax=20"
        search_resp = requests.get(search_url, timeout=5).json()
        id_list = search_resp.get("esearchresult", {}).get("idlist", [])
        
        if len(id_list) < 2:
            return get_backup_text()
            
        # 🌟 2つの異なる論文をランダムに選んで合体させ、超長文を作る！
        chosen_ids = random.sample(id_list, 2)
        combined_text = ""
        
        for i, pid in enumerate(chosen_ids, 1):
            fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pid}&retmode=xml"
            fetch_resp = requests.get(fetch_url, timeout=5)
            root = ET.fromstring(fetch_resp.content)
            
            title_elem = root.find(".//ArticleTitle")
            p_title = title_elem.text if title_elem is not None else "Medical Research Part"
            
            abstract_texts = [elem.text for elem in root.findall(".//AbstractText") if elem.text]
            p_abstract = " ".join(abstract_texts)
            
            if p_abstract:
                combined_text += f"【Part {i}: {p_title}】\n{p_abstract}\n\n"
        
        if combined_text:
            return {
                "title": f"🔬 [PubMed医学長文] テーマ: {kw.upper()}",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{chosen_ids[0]}/",
                "text": combined_text.strip()
            }
    except Exception as e:
        print(f"Error fetching PubMed: {e}")
        
    return get_backup_text()

def get_backup_text():
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
            "with cognitive decline remains a subject of intense academic disputation. Furthermore, recent "
            "investigations into neuroinflammatory pathways suggest that microglial activation may inadvertently "
            "exacerbate synaptic pruning, thereby accelerating the symptomatic progression of cognitive impairments."
        )
    }

@app.route('/')
def index():
    # 🌟 毎回リアルタイムで新しく取得（キャッシュは廃止！）
    articles = get_bbc_news()
    med_article = get_random_medical_long_text()
    if med_article:
        articles.append(med_article)
        
    translated_articles = []
    
    for art in articles:
        try:
            # ⚡️ 細かく刻まず一発で丸ごと翻訳することで、キャッシュなしでも数秒の爆速処理を実現！
            full_translation = GoogleTranslator(source='en', target='ja').translate(art["text"])
        except Exception as e:
            full_translation = "[翻訳エラー。リロードしてみてください]"
        
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
        <title>爆速辞書＆音声付き 究極の英語長文アプリ</title>
        <style>
            body { font-family: sans-serif; margin: 20px; background: #f5f5f5; }
            .article { background: white; padding: 20px; margin-bottom: 30px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            h2 { color: #333; font-size: 20px; margin-bottom: 10px; }
            h2 a { color: #0066cc; text-decoration: none; }
            h2 a:hover { text-decoration: underline; }
            
            .speak-btn {
                background: #0088cc; color: white; border: none; padding: 10px 20px;
                border-radius: 20px; cursor: pointer; font-size: 14px; font-weight: bold;
                margin-bottom: 15px; display: inline-flex; align-items: center; gap: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: background 0.2s;
            }
            .speak-btn:hover { background: #0066aa; }
            .speak-btn.playing { background: #e03131; }

            .container { display: flex; gap: 20px; }
            .box { width: 50%; padding: 15px; border: 1px solid #ddd; border-radius: 5px; background: #fff; line-height: 1.7; white-space: pre-wrap; }
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
        <h1>📚 本日の特大長文（ニュース長文 ＋ 医学論文2本合体オムニバス）</h1>
        
        {% for art in articles %}
        <div class="article">
            <h2><a href="{{ art.url }}" target="_blank">{{ art.title }}</a></h2>
            
            <button class="speak-btn">🔊 英文を読み上げる</button>
            
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
            // 🌟 読み上げ機能のバグを完全に修正（コメント記号を // に修正）
            document.querySelectorAll('.speak-btn').forEach(button => {
                button.addEventListener('click', function() {
                    const articleDiv = this.closest('.article');
                    const englishText = articleDiv.querySelector('.english').innerText;
                    
                    if (window.speechSynthesis.speaking) {
                        window.speechSynthesis.cancel();
                        if (this.classList.contains('playing')) {
                            this.classList.remove('playing');
                            this.innerText = "🔊 英文を読み上げる";
                            return;
                        }
                    }
                    
                    document.querySelectorAll('.speak-btn').forEach(b => {
                        b.classList.remove('playing');
                        b.innerText = "🔊 英文を読み上げる";
                    });

                    const utterance = new SpeechSynthesisUtterance(englishText);
                    utterance.lang = 'en-US'; // アメリカ英語
                    utterance.rate = 0.9;    // スピード調整

                    utterance.onend = () => {
                        this.classList.remove('playing');
                        this.innerText = "🔊 英文を読み上げる";
                    };

                    this.classList.add('playing');
                    this.innerText = "🛑 止める";
                    window.speechSynthesis.speak(utterance);
                });
            });

            // ポップアップ辞書
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
    return render_template_string(html_template, articles=translated_articles)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)