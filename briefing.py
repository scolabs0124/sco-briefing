"""SCO 입시 일일 브리핑 자동 생성 스크립트"""
import os, json, datetime, urllib.parse, feedparser, anthropic, re

# === 한국 시간 ===
KST = datetime.timezone(datetime.timedelta(hours=9))
TODAY = datetime.datetime.now(KST).strftime("%Y-%m-%d")
DAY_NAME = ['월','화','수','목','금','토','일'][datetime.datetime.now(KST).weekday()]

# === 구글 뉴스 RSS로 한국어 입시 뉴스 수집 ===
KEYWORDS = ['2028 대입', '수능 개편', '고교학점제', '의대 정원', '학생부종합전형', '교육부 입시']

def fetch_news():
    items = []
    for kw in KEYWORDS:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(kw)}&hl=ko&gl=KR&ceid=KR:ko"
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:
            items.append({
                'title': entry.title,
                'link': entry.link,
                'published': getattr(entry, 'published', ''),
                'summary': re.sub(r'<[^>]+>', '', getattr(entry, 'summary', ''))[:300],
                'source': getattr(entry, 'source', {}).get('title', '') if hasattr(entry, 'source') else ''
            })
    # 중복 제거 (제목 기반)
    seen, unique = set(), []
    for it in items:
        key = it['title'][:30]
        if key not in seen:
            seen.add(key)
            unique.append(it)
    return unique[:25]

# === Claude API로 분석 + HTML 생성 ===
def analyze(news_items):
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
    news_text = '\n\n'.join([f"[{i+1}] {it['title']}\n출처: {it['source']}\n발행: {it['published']}\n요약: {it['summary']}\n링크: {it['link']}" for i, it in enumerate(news_items)])

    prompt = f"""당신은 스코랩스(SCO Labs)의 입시 정보 분석 AI입니다. 스코랩스 철학: "학이 아닌 습, 성적이 아닌 완성도".

오늘 날짜: {TODAY} ({DAY_NAME})

【수집된 입시 뉴스 {len(news_items)}건】
{news_text}

위 뉴스 중 상위 5건을 선정해 다음 JSON 형식으로만 응답하세요. 다른 텍스트 금지.

{{
  "key_summary": "오늘의 핵심 1줄 (60자 이내)",
  "best_pick": "학부모 즉시 발송 추천 1건의 제목",
  "stats": {{"urgent": 숫자, "important": 숫자, "info": 숫자}},
  "articles": [
    {{
      "id": 1,
      "priority": "긴급/중요/참고",
      "title": "기사 제목",
      "source": "출처",
      "date": "{TODAY}",
      "year": "적용 학년도 (예: 2028학년도)",
      "target": "대상 (예: 중3/고1/학부모)",
      "areas": ["영역 배열"],
      "url": "원문 URL",
      "summary1": "한 줄 요약 (사실 기반)",
      "changes": ["바뀐 점 1", "점 2", "점 3"],
      "mythQ": "학부모가 자주 하는 오해 질문",
      "mythA": "팩트 답변 (강한 톤)",
      "katok": "학부모 카톡 안내문 (200~300자, 스코 상담 CTA 포함, \\n으로 줄바꿈)",
      "card_titles": ["카드뉴스 제목 1", "제목 2", "제목 3"],
      "sco_view": "스코 학습관리 관점 해석"
    }}
  ]
}}

원칙: 사실 왜곡 금지, 마케팅 톤 강하게, 스코 철학 자연스럽게 반영."""

    msg = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )
    text = msg.content[0].text.strip()
    text = re.sub(r'^```json\s*', '', text).rstrip('` \n')
    return json.loads(text)

# === HTML 생성 (단순 버전) ===
def generate_html(data):
    articles_html = ''
    for a in data['articles']:
        badge_cls = {'긴급':'b-urgent','중요':'b-important','참고':'b-note'}.get(a['priority'], 'b-note')
        areas = ' '.join([f'<span class="badge b-cat">{x}</span>' for x in a.get('areas', [])])
        changes = ''.join([f'<li>{c}</li>' for c in a.get('changes', [])])
        titles = ''.join([f'<li>{t}</li>' for t in a.get('card_titles', [])])
        articles_html += f"""
<div class="card">
  <div class="badges">
    <span class="badge {badge_cls}">{a['priority']}</span>
    <span class="badge b-year">{a['year']}</span>
    <span class="badge b-tgt">{a['target']}</span>
    {areas}
  </div>
  <h2>{a['id']}. {a['title']}</h2>
  <div class="source">{a['source']} · {a['date']} · <a href="{a['url']}" target="_blank">원문</a></div>
  <p class="sum1">{a['summary1']}</p>
  <div class="block"><b>📌 무엇이 바뀌었나</b><ul>{changes}</ul></div>
  <div class="myth"><div class="q">❓ {a['mythQ']}</div><div class="a">→ {a['mythA']}</div></div>
  <div class="katok"><div class="l">📱 학부모 카톡문</div><p>{a['katok']}</p></div>
  <div class="titles"><div class="l">📰 카드뉴스 제목</div><ul>{titles}</ul></div>
  <div class="sco"><div class="l">💡 SCO 관점</div><p>{a['sco_view']}</p></div>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>SCO 입시 브리핑 — {TODAY}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,'Pretendard','Apple SD Gothic Neo',sans-serif;background:#f4f6fa;color:#1a1a1a;line-height:1.6;padding:20px}}
.wrap{{max-width:980px;margin:0 auto}}
.header{{background:linear-gradient(135deg,#1e3a8a 0%,#3b82f6 100%);color:#fff;padding:36px 28px;border-radius:14px}}
.header h1{{font-size:28px;font-weight:800}}
.header .sub{{margin-top:6px;font-size:14px;opacity:.92}}
.hero{{background:#fff7ed;border-left:6px solid #f97316;padding:20px 22px;border-radius:10px;margin-top:18px}}
.hero h2{{font-size:18px;color:#9a3412}}
.pick{{background:#ecfdf5;border:1px solid #6ee7b7;border-radius:12px;padding:18px 22px;margin-top:18px}}
.pick h3{{color:#065f46;font-size:15px}}
.card{{background:#fff;border-radius:14px;box-shadow:0 4px 14px rgba(0,0,0,.06);padding:26px;margin-top:22px;border-top:5px solid #3b82f6}}
.badges{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}}
.badge{{font-size:11px;padding:4px 10px;border-radius:999px;font-weight:700}}
.b-urgent{{background:#fef2f2;color:#b91c1c}}
.b-important{{background:#fffbeb;color:#b45309}}
.b-note{{background:#f3f4f6;color:#374151}}
.b-cat{{background:#eff6ff;color:#1d4ed8}}
.b-year{{background:#f0fdf4;color:#15803d}}
.b-tgt{{background:#fdf4ff;color:#a21caf}}
.card h2{{font-size:20px;font-weight:800;color:#111827}}
.source{{font-size:12px;color:#6b7280;margin-top:4px}}
.source a{{color:#3b82f6;text-decoration:none}}
.sum1{{margin-top:14px;font-size:15px;color:#1f2937}}
.block{{margin-top:14px;font-size:14px}}
.block ul{{margin-top:6px;padding-left:22px}}
.block li{{margin:3px 0}}
.myth{{margin-top:14px;background:#fff7ed;border-left:4px solid #f59e0b;padding:14px 16px;border-radius:8px}}
.myth .q{{font-weight:700;color:#9a3412}}
.myth .a{{margin-top:6px;color:#7c2d12}}
.katok{{margin-top:14px;background:#fef9c3;border-left:4px solid #eab308;padding:16px;border-radius:8px}}
.katok .l{{font-size:11px;color:#854d0e;font-weight:700;letter-spacing:1px}}
.katok p{{margin-top:6px;font-size:14px;color:#3f3f00;white-space:pre-wrap}}
.titles{{margin-top:14px;background:#eff6ff;border-left:4px solid #3b82f6;padding:14px 16px;border-radius:8px}}
.titles .l{{font-size:11px;color:#1d4ed8;font-weight:700;letter-spacing:1px}}
.titles ul{{margin-top:6px;padding-left:18px}}
.titles li{{color:#1e3a8a;margin:2px 0}}
.sco{{margin-top:14px;background:#111827;color:#f9fafb;padding:14px 16px;border-radius:8px}}
.sco .l{{font-size:11px;color:#9ca3af;font-weight:700;letter-spacing:1px}}
.sco p{{margin-top:6px;color:#e5e7eb}}
.ft{{text-align:center;color:#9ca3af;font-size:12px;margin-top:30px;padding:20px}}
</style></head><body>
<div class="wrap">
<div class="header"><h1>📅 SCO 입시 브리핑</h1><div class="sub">{TODAY} ({DAY_NAME}) · 스코랩스(SCO Labs) 입시정보팀</div></div>
<div class="hero"><h2>🔥 {data['key_summary']}</h2></div>
<div class="pick"><h3>💡 학부모 즉시 발송 추천</h3><p>"{data['best_pick']}"</p></div>
{articles_html}
<div class="ft">SCO LABS · 학이 아닌 습 · 매일 오전 11시 자동 생성</div>
</div></body></html>"""

# === 메인 ===
def main():
    print(f"[{TODAY}] 뉴스 수집 시작...")
    news = fetch_news()
    print(f"  → {len(news)}건 수집")

    print(f"[{TODAY}] AI 분석 시작...")
    data = analyze(news)
    print(f"  → 상위 {len(data['articles'])}건 분석 완료")

    print(f"[{TODAY}] HTML 생성...")
    html = generate_html(data)

    os.makedirs('site', exist_ok=True)
    filepath = f'site/briefing-{TODAY}.html'
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  → {filepath} 저장 완료")

    # JSON 데이터도 저장 (디버깅용)
    with open(f'site/briefing-{TODAY}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main()
