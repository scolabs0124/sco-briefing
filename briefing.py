"""SCO 입시 일일 브리핑 v3 - v9 수준 5개 버튼 + Canvas PNG 통합"""
import os, json, datetime, urllib.parse, feedparser, anthropic, re, sys

KST = datetime.timezone(datetime.timedelta(hours=9))
TODAY = datetime.datetime.now(KST).strftime("%Y-%m-%d")
DAY_NAME = ['월','화','수','목','금','토','일'][datetime.datetime.now(KST).weekday()]

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
    seen, unique = set(), []
    for it in items:
        key = it['title'][:30]
        if key not in seen:
            seen.add(key); unique.append(it)
    return unique[:25]

def extract_json(text):
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text)
    start = text.find('{'); end = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end+1]
    return text

def call_claude(client, prompt, max_tok=24000):
    msg = client.messages.create(model="claude-sonnet-4-5-20250929", max_tokens=max_tok,
        messages=[{"role": "user", "content": prompt}])
    return msg.content[0].text

def analyze(news_items):
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
    news_text = '\n\n'.join([f"[{i+1}] {it['title']}\n출처: {it['source']}\n발행: {it['published']}\n요약: {it['summary']}\n링크: {it['link']}" for i, it in enumerate(news_items)])

    prompt = f"""당신은 스코랩스(SCO Labs) 입시 분석 AI입니다. 철학: "학이 아닌 습, 성적이 아닌 완성도".

오늘: {TODAY} ({DAY_NAME})

【수집된 뉴스 {len(news_items)}건】
{news_text}

상위 5건을 다음 JSON으로만 응답. 마크다운 코드블록 사용 금지. 큰따옴표 escape는 \\".

{{
  "key_summary": "오늘 핵심 1줄",
  "best_pick": "학부모 즉시 발송 추천 1건 제목",
  "stats": {{"urgent": 1, "important": 2, "info": 2}},
  "articles": [
    {{
      "id": 1,
      "priority": "긴급",
      "title": "기사 제목",
      "shortTitle": "파일명용 짧은제목공백없이",
      "source": "출처",
      "date": "{TODAY}",
      "year": "2028학년도",
      "target": "중3/고1/학부모",
      "areas": ["수능", "내신"],
      "url": "원문 URL",
      "hookBig": "큰 후킹 카피 (3-4줄, <br>로 줄바꿈)",
      "hookLabel": "📢 학부모 주목",
      "summary1": "한 줄 요약",
      "changeA": {{"label": "CHANGE 1", "title": "변화1 제목 (<br>)", "desc": "설명"}},
      "changeB": {{"label": "CHANGE 2", "title": "변화2 제목", "desc": "설명"}},
      "mythQ": "학부모 오해 질문",
      "mythA": "팩트 답변",
      "impacts": ["영향1", "영향2", "영향3", "영향4"],
      "actions": ["액션1", "액션2", "액션3", "액션4"],
      "ctaHook": "8번 카드 후킹",
      "katok": "학부모 카톡 안내문 200-300자, \\n으로 줄바꿈",
      "sms": "[SCO] 80자 단문",
      "hashtags": ["해시태그20개샵없이"],
      "counseling": ["멘트1", "멘트2", "멘트3", "멘트4", "멘트5"],
      "card_titles": ["카드뉴스 제목1", "제목2", "제목3"],
      "sco_view": "스코 학습관리 관점",
      "blogTitle": "블로그 SEO 제목",
      "blogSummary": "블로그 요약 1-2문장",
      "grades": {{
        "중3": {{"katok": "중3 학부모 카톡 200자", "actions": ["액션1", "액션2", "액션3"]}},
        "고1": {{"katok": "고1 학부모 카톡", "actions": ["액션1", "액션2", "액션3"]}},
        "고2": {{"katok": "고2 학부모 카톡", "actions": ["액션1", "액션2", "액션3"]}},
        "고3": {{"katok": "고3 학부모 카톡", "actions": ["액션1", "액션2", "액션3"]}}
      }}
    }}
  ]
}}

원칙: 사실 왜곡 X, 마케팅 톤 강하게, 스코 철학 반영. 모든 필드 빠짐없이."""

    text = call_claude(client, prompt)
    json_text = extract_json(text)
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        print(f"\n=== JSON 파싱 1차 실패 ===\n{e}")
        print(f"응답 끝 300자: {json_text[-300:]}")
        # 재시도 - 더 단순한 형식 요청
        retry_prompt = prompt + "\n\n⚠️ 이전 응답이 JSON 파싱 실패. 모든 큰따옴표를 정확히 escape하고, 응답이 잘리지 않게 articles는 상위 3건만 응답하세요. 순수 JSON만."
        text2 = call_claude(client, retry_prompt)
        return json.loads(extract_json(text2))

# ===== HTML 템플릿 (v9 수준) =====
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>SCO 입시 브리핑 — __TODAY__</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,'Pretendard','Apple SD Gothic Neo',sans-serif;background:#f4f6fa;color:#1a1a1a;line-height:1.6;padding:20px}
.wrap{max-width:980px;margin:0 auto}
.header{background:linear-gradient(135deg,#0b1e3f 0%,#1a3a6b 100%);color:#fff;padding:36px 28px;border-radius:14px}
.header h1{font-size:28px;font-weight:800}
.header .sub{margin-top:6px;font-size:14px;opacity:.92}
.hero{background:#fff7ed;border-left:6px solid #f97316;padding:20px 22px;border-radius:10px;margin-top:18px}
.hero h2{font-size:18px;color:#9a3412}
.pick{background:#ecfdf5;border:1px solid #6ee7b7;border-radius:12px;padding:18px 22px;margin-top:18px}
.pick h3{color:#065f46;font-size:15px}
.card{background:#fff;border-radius:14px;box-shadow:0 4px 14px rgba(0,0,0,.06);padding:26px;margin-top:22px;border-top:5px solid #3b82f6}
.card.urgent{border-top-color:#dc2626}.card.important{border-top-color:#f59e0b}.card.note{border-top-color:#6b7280}
.badges{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
.badge{font-size:11px;padding:4px 10px;border-radius:999px;font-weight:700}
.b-urgent{background:#fef2f2;color:#b91c1c}.b-important{background:#fffbeb;color:#b45309}.b-note{background:#f3f4f6;color:#374151}
.b-cat{background:#eff6ff;color:#1d4ed8}.b-year{background:#f0fdf4;color:#15803d}.b-tgt{background:#fdf4ff;color:#a21caf}
.card h2{font-size:20px;font-weight:800;color:#111827}
.source{font-size:12px;color:#6b7280;margin-top:4px}.source a{color:#3b82f6;text-decoration:none}
.sum1{margin-top:14px;font-size:15px;color:#1f2937}
.block{margin-top:14px;font-size:14px}.block ul{margin-top:6px;padding-left:22px}.block li{margin:3px 0}
.myth{margin-top:14px;background:#fff7ed;border-left:4px solid #f59e0b;padding:14px 16px;border-radius:8px}
.myth .q{font-weight:700;color:#9a3412}.myth .a{margin-top:6px;color:#7c2d12}
.katok{margin-top:14px;background:#fef9c3;border-left:4px solid #eab308;padding:16px;border-radius:8px}
.katok .l{font-size:11px;color:#854d0e;font-weight:700;letter-spacing:1px}
.katok p{margin-top:6px;font-size:14px;color:#3f3f00;white-space:pre-wrap}
.titles{margin-top:14px;background:#eff6ff;border-left:4px solid #3b82f6;padding:14px 16px;border-radius:8px}
.titles .l{font-size:11px;color:#1d4ed8;font-weight:700;letter-spacing:1px}
.titles ul{margin-top:6px;padding-left:18px}.titles li{color:#1e3a8a;margin:2px 0}
.sco{margin-top:14px;background:#111827;color:#f9fafb;padding:14px 16px;border-radius:8px}
.sco .l{font-size:11px;color:#9ca3af;font-weight:700;letter-spacing:1px}.sco p{margin-top:6px;color:#e5e7eb}
.make-bar{background:linear-gradient(135deg,#7c2d12 0%,#b91c1c 100%);border-radius:10px;padding:14px 18px;margin-top:18px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.make-bar .lbl{color:white;font-size:12px;font-weight:800;letter-spacing:.5px;margin-right:6px}
.make-btn{background:white;color:#7c2d12;border:none;padding:9px 14px;border-radius:7px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit}
.make-btn:hover{background:#fef2f2}.make-btn.full{background:#fbbf24;color:#78350f}.make-btn.parent{background:#16a34a;color:white}
.ft{text-align:center;color:#9ca3af;font-size:12px;margin-top:30px;padding:20px}
</style></head><body>
<canvas id="sco-export-canvas" width="1080" height="1350" style="display:none"></canvas>
<div class="wrap">
<div class="header"><h1>📅 SCO 입시 브리핑</h1><div class="sub">__TODAY__ (__DAY__) · 스코랩스(SCO Labs) 입시정보팀</div></div>
<div class="hero"><h2>🔥 __KEY_SUMMARY__</h2></div>
<div class="pick"><h3>💡 학부모 즉시 발송 추천</h3><p>__BEST_PICK__</p></div>
__ARTICLES_HTML__
<div class="ft">SCO LABS · 학이 아닌 습 · 매일 오전 11시 자동 생성 (서버)</div>
</div>
<script>
const ARTICLES = __ARTICLES_JSON__;

function downloadFile(filename, content, mime){
  mime = mime || 'text/plain;charset=utf-8';
  const blob = new Blob([content],{type:mime});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = filename;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
}
function openInNewTab(html){
  const blob = new Blob([html],{type:'text/html;charset=utf-8'});
  window.open(URL.createObjectURL(blob),'_blank');
}

function genCardsHTML(id){
  const a = ARTICLES[id]; if(!a) return '<h1>데이터 없음</h1>';
  const titles = a.card_titles || [];
  const cards = [
    {cls:'c1', label:a.hookLabel||'📢', main:a.hookBig||a.title, isHook:true},
    {cls:'c2', label:'CHANGE 1', main:(a.changeA&&a.changeA.title)||'', sub:(a.changeA&&a.changeA.desc)||''},
    {cls:'c3', label:'CHANGE 2', main:(a.changeB&&a.changeB.title)||'', sub:(a.changeB&&a.changeB.desc)||''},
    {cls:'c4', label:'⚠️ 학부모 오해', main:a.mythQ||'', sub:a.mythA||''},
    {cls:'c5', label:'💔 영향', list:a.impacts||[]},
    {cls:'c6', label:'📋 할 일', list:a.actions||[]},
    {cls:'c7', label:'💡 SCO 관점', main:a.ctaHook||a.sco_view||'', sub:'학이 아닌 습'},
    {cls:'c8', label:'📩 무료 진단', main:'우리 아이 맞춤 진단', sub:'카카오톡 채널/DM/프로필 링크', isCta:true}
  ];
  return '<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><title>'+a.title+' 카드뉴스</title><style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:-apple-system,Pretendard,sans-serif;background:#e5e7eb;padding:20px}.cards{max-width:1100px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(500px,1fr));gap:24px}.card{width:100%;aspect-ratio:1/1;border-radius:18px;padding:54px 48px;display:flex;flex-direction:column;justify-content:space-between;color:white;font-weight:700;position:relative;line-height:1.4}.num{position:absolute;top:20px;right:24px;font-size:13px;opacity:.6}.brand{position:absolute;bottom:24px;left:48px;font-size:12px;opacity:.7}.label{font-size:16px;font-weight:700;opacity:.85;margin-bottom:14px;letter-spacing:1px}.main{font-size:36px;font-weight:900;line-height:1.25}.hook{font-size:46px;font-weight:900;line-height:1.2}.sub{font-size:18px;line-height:1.5;font-weight:500;opacity:.9;margin-top:14px}.cta{font-size:42px;font-weight:900;color:#fbbf24}ul{padding-left:24px;margin-top:8px}li{font-size:24px;margin-bottom:8px;font-weight:600}.c1{background:linear-gradient(135deg,#0b1e3f,#1a3a6b)}.c2{background:linear-gradient(135deg,#b91c1c,#ea580c)}.c3{background:linear-gradient(135deg,#1a3a6b,#3b82f6)}.c4{background:linear-gradient(135deg,#b45309,#d97706)}.c5{background:linear-gradient(135deg,#7f1d1d,#dc2626)}.c6{background:linear-gradient(135deg,#064e3b,#059669)}.c7{background:linear-gradient(135deg,#0b1e3f,#1e293b)}.c8{background:linear-gradient(135deg,#0b1e3f,#ea580c)}</style></head><body><div class="cards">'+cards.map((c,i)=>{
    let body='';
    if(c.isHook) body='<div><div class="label">'+c.label+'</div><div class="hook">'+c.main+'</div></div>';
    else if(c.isCta) body='<div><div class="label">'+c.label+'</div><div class="cta">'+c.main+'</div><div class="sub">'+c.sub+'</div></div>';
    else if(c.list) body='<div><div class="label">'+c.label+'</div><ul>'+c.list.map(x=>'<li>'+x+'</li>').join('')+'</ul></div>';
    else body='<div><div class="label">'+c.label+'</div><div class="main">'+c.main+'</div>'+(c.sub?'<div class="sub">'+c.sub+'</div>':'')+'</div>';
    return '<div class="card '+c.cls+'"><div class="num">'+(i+1)+'/8</div>'+body+'<div class="brand">SCO LABS</div></div>';
  }).join('')+'</div></body></html>';
}

function genBlogHTML(id){
  const a = ARTICLES[id]; if(!a) return '<h1>데이터 없음</h1>';
  return '<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><title>'+(a.blogTitle||a.title)+'</title><style>body{font-family:-apple-system,Pretendard,sans-serif;background:#f7f8fa;line-height:1.8;padding:20px}.wrap{max-width:780px;margin:0 auto;background:white;border-radius:14px;overflow:hidden}.hd{background:linear-gradient(135deg,#0b1e3f,#1a3a6b);color:white;padding:48px 44px}.hd h1{font-size:28px;font-weight:800}.summary{background:#fff7ed;border-left:6px solid #ea580c;padding:20px 28px;color:#9a3412;font-weight:600}.body{padding:24px 44px}.body h2{font-size:20px;font-weight:800;color:#0b1e3f;margin:30px 0 14px;padding-left:14px;border-left:5px solid #0b1e3f}.body p{font-size:15px;color:#374151;margin-bottom:12px}.body ul{padding-left:26px;margin:10px 0}.cta{background:linear-gradient(135deg,#0b1e3f,#ea580c);color:white;padding:24px;border-radius:12px;margin:24px 0}.tags{background:#f3f4f6;padding:18px;border-radius:10px;margin:20px 0;font-size:13px;color:#6b7280}</style></head><body><div class="wrap"><div class="hd"><div style="opacity:.7;font-size:12px">📅 '+a.date+' · SCO LABS</div><h1>'+(a.blogTitle||a.title)+'</h1></div><div class="summary">'+(a.blogSummary||a.summary1||'')+'</div><div class="body"><h2>1. 무엇이 바뀌었나</h2><p>'+(a.summary1||'')+'</p><h2>2. 학부모 오해</h2><p><b>Q.</b> '+(a.mythQ||'')+'<br><b>A.</b> '+(a.mythA||'')+'</p><h2>3. 우리 아이 영향</h2><ul>'+((a.impacts||[]).map(x=>'<li>'+x+'</li>').join(''))+'</ul><h2>4. 지금 할 일</h2><ul>'+((a.actions||[]).map(x=>'<li><b>'+x+'</b></li>').join(''))+'</ul><h2>5. SCO 관점</h2><p>'+(a.sco_view||'')+'</p><div class="cta"><h3>💡 무료 입시 진단</h3><p>카카오톡 채널/DM/프로필 링크</p></div><div class="tags">'+((a.hashtags||[]).map(h=>'#'+h).join(' '))+'</div></div></div></body></html>';
}

function genGradesHTML(id){
  const a = ARTICLES[id]; if(!a||!a.grades) return '<h1>학년별 데이터 없음</h1>';
  const colors = {'중3':'#b91c1c','고1':'#ea580c','고2':'#1a3a6b','고3':'#7c3aed'};
  return '<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><title>학년별 카톡</title><style>body{font-family:-apple-system,Pretendard,sans-serif;background:#f7f8fa;padding:20px;line-height:1.7}.wrap{max-width:1000px;margin:0 auto}.hd{background:linear-gradient(135deg,#0b1e3f,#1a3a6b);color:white;padding:32px;border-radius:14px;margin-bottom:24px}.cards{display:grid;grid-template-columns:repeat(2,1fr);gap:20px}.card{background:white;border-radius:12px;padding:24px}.card h2{font-size:18px;font-weight:800;color:white;padding:6px 14px;border-radius:6px;display:inline-block;margin-bottom:14px}.katok{background:#fef3c7;border:1.5px dashed #f59e0b;border-radius:8px;padding:16px;font-size:13px;color:#78350f;white-space:pre-line}.actions{margin-top:14px}.actions ul{padding-left:18px}.actions li{font-size:13px;color:#374151;margin-bottom:4px}@media(max-width:700px){.cards{grid-template-columns:1fr}}</style></head><body><div class="wrap"><div class="hd"><h1 style="font-size:22px">학년별 맞춤 카톡 안내문</h1><div style="font-size:14px;opacity:.85;margin-top:6px">'+a.title+' · '+a.date+'</div></div><div class="cards">'+Object.keys(a.grades).map(g=>{const d=a.grades[g];return '<div class="card"><h2 style="background:'+(colors[g]||'#0b1e3f')+'">'+g+' 학부모용</h2><div class="katok">'+d.katok+'</div><div class="actions"><b>이 학년이 할 일</b><ul>'+((d.actions||[]).map(x=>'<li>'+x+'</li>').join(''))+'</ul></div></div>';}).join('')+'</div></div></body></html>';
}

function genCaptions(id){
  const a = ARTICLES[id]; if(!a) return '';
  return '=== SCO 콘텐츠 패키지 · '+a.date+' ===\\n\\n[인스타 캡션]\\n'+(a.hookBig||'').replace(/<[^>]+>/g,' ')+'\\n\\n'+(a.summary1||'')+'\\n\\n📩 DM/프로필\\n\\n'+((a.hashtags||[]).map(h=>'#'+h).join(' '))+'\\n\\n[카톡 채널 발송]\\n'+(a.katok||'')+'\\n\\n[SMS]\\n'+(a.sms||'')+'\\n\\n[상담 멘트]\\n'+((a.counseling||[]).map((m,i)=>(i+1)+'. "'+m+'"').join('\\n\\n'));
}

function genParentMessage(id){
  const a = ARTICLES[id]; if(!a) return '';
  return '📢 SCO 입시 브리핑\\n━━━━━━━━━━━━━━━\\n'+a.date+'\\n\\n🎯 오늘의 핵심\\n《'+a.title+'》\\n\\n📌 NOW\\n  ✓ '+(a.summary1||'')+'\\n\\n❓ FAQ\\n  Q. '+(a.mythQ||'')+'\\n  A. '+(a.mythA||'')+'\\n\\n💡 SCO의 답\\n  '+(a.sco_view||'')+'\\n\\n━━━━━━━━━━━━━━━\\n📩 무료 입시 진단\\n   ▶ 카카오톡 채널 / DM\\n━━━━━━━━━━━━━━━\\n\\nSCO Labs · '+(a.source||'');
}

function _wrapText(ctx,text,x,y,maxW,lh){const chars=text.split('');let line='',cy=y;for(let i=0;i<chars.length;i++){const t=line+chars[i];if(ctx.measureText(t).width>maxW&&line!==''){ctx.fillText(line,x,cy);line=chars[i];cy+=lh}else line=t}ctx.fillText(line,x,cy);return cy+lh}
function _roundRect(ctx,x,y,w,h,r){ctx.beginPath();ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath()}

function drawParentCardCanvas(id){
  const a=ARTICLES[id]; if(!a){alert('데이터 없음');return}
  const canvas=document.getElementById('sco-export-canvas');
  const ctx=canvas.getContext('2d'); const W=1080,H=1350,PAD=80;
  const FONT='"Apple SD Gothic Neo","Pretendard",-apple-system,sans-serif';
  const bg=ctx.createLinearGradient(0,0,0,H);
  bg.addColorStop(0,'#0b1e3f');bg.addColorStop(.6,'#1e3a8a');bg.addColorStop(1,'#1a3a6b');
  ctx.fillStyle=bg;ctx.fillRect(0,0,W,H);
  ctx.fillStyle='rgba(255,255,255,.85)';ctx.font='800 22px '+FONT;ctx.fillText('SCO LABS',PAD,PAD+10);
  ctx.fillStyle='rgba(255,255,255,.7)';ctx.font='600 24px '+FONT;ctx.textAlign='right';ctx.fillText(a.date||'',W-PAD,PAD+10);ctx.textAlign='left';
  let y=160;
  ctx.fillStyle='rgba(251,191,36,.25)';_roundRect(ctx,PAD,y,260,50,25);ctx.fill();
  ctx.fillStyle='#fbbf24';ctx.font='800 22px '+FONT;ctx.fillText('📢 SCO 입시 브리핑',PAD+22,y+33);
  y=260;ctx.fillStyle='#fff';ctx.font='900 46px '+FONT;
  y=_wrapText(ctx,(a.title||'').slice(0,60),PAD,y+40,W-PAD*2,60);
  y+=30;ctx.fillStyle='rgba(255,255,255,.2)';ctx.fillRect(PAD,y,W-PAD*2,2);
  y+=40;ctx.fillStyle='#fbbf24';ctx.font='800 22px '+FONT;ctx.fillText('📌 NOW',PAD,y);
  y+=40;ctx.fillStyle='rgba(255,255,255,.95)';ctx.font='500 26px '+FONT;
  y=_wrapText(ctx,(a.summary1||'').slice(0,150),PAD,y,W-PAD*2,40);
  y+=20;ctx.fillStyle='rgba(255,255,255,.08)';_roundRect(ctx,PAD,y,W-PAD*2,200,20);ctx.fill();
  ctx.fillStyle='#fbbf24';ctx.font='700 22px '+FONT;ctx.fillText('❓ '+(a.mythQ||'').slice(0,35),PAD+30,y+45);
  ctx.fillStyle='rgba(255,255,255,.95)';ctx.font='500 22px '+FONT;
  _wrapText(ctx,'→ '+(a.mythA||'').slice(0,100),PAD+30,y+90,W-PAD*2-60,36);
  y+=230;ctx.fillStyle='rgba(255,255,255,.2)';ctx.fillRect(PAD,y,W-PAD*2,2);
  y+=40;ctx.fillStyle='#fbbf24';ctx.font='800 22px '+FONT;ctx.fillText('💡 SCO의 답',PAD,y);
  y+=40;ctx.fillStyle='rgba(255,255,255,.95)';ctx.font='700 28px '+FONT;
  _wrapText(ctx,'학(學)이 아닌 습(習). 매일 실행이 결국 이깁니다.',PAD,y,W-PAD*2,42);
  const cY=H-220;
  const cg=ctx.createLinearGradient(0,cY,W,cY+130);
  cg.addColorStop(0,'#ea580c');cg.addColorStop(1,'#fbbf24');
  ctx.fillStyle=cg;_roundRect(ctx,PAD,cY,W-PAD*2,130,20);ctx.fill();
  ctx.fillStyle='#0b1e3f';ctx.font='900 32px '+FONT;ctx.textAlign='center';
  ctx.fillText('📩 무료 입시 진단 신청',W/2,cY+50);
  ctx.font='600 20px '+FONT;ctx.fillText('카카오톡 채널 / DM / 프로필 링크',W/2,cY+90);
  ctx.fillStyle='rgba(255,255,255,.5)';ctx.font='700 16px '+FONT;ctx.fillText('S C O   L A B S',W/2,H-30);ctx.textAlign='left';
  const link=document.createElement('a');
  link.download='SCO_학부모카드_'+(a.date||'')+'_'+id+'.png';
  link.href=canvas.toDataURL('image/png');
  document.body.appendChild(link);link.click();document.body.removeChild(link);
}

function makeContent(id, type){
  const a = ARTICLES[id]; if(!a){alert('기사 데이터 없음');return}
  const safeTitle = (a.shortTitle||a.title||'').replace(/[\\/\\\\:*?"<>|]/g,'').slice(0,30);
  const base = 'SCO_'+a.date+'_'+id+'_'+safeTitle;
  if(type==='cards'){
    const h=genCardsHTML(id);downloadFile(base+'_카드뉴스.html',h,'text/html;charset=utf-8');openInNewTab(h);
  } else if(type==='blog'){
    const h=genBlogHTML(id);downloadFile(base+'_블로그.html',h,'text/html;charset=utf-8');openInNewTab(h);
  } else if(type==='captions'){
    downloadFile(base+'_캡션.txt',genCaptions(id),'text/plain;charset=utf-8');
  } else if(type==='grades'){
    const h=genGradesHTML(id);downloadFile(base+'_학년별카톡.html',h,'text/html;charset=utf-8');openInNewTab(h);
  } else if(type==='parent'){
    drawParentCardCanvas(id);
    const text=genParentMessage(id);
    navigator.clipboard.writeText(text).then(()=>alert('📲 학부모 발송 풀세트!\\n✅ PNG 카드 다운로드\\n✅ 텍스트 클립보드 복사\\n→ 카톡 채널에 첨부+붙여넣기')).catch(()=>{});
    downloadFile(base+'_학부모발송.txt',text,'text/plain;charset=utf-8');
  } else if(type==='full'){
    const c=genCardsHTML(id),b=genBlogHTML(id),g=genGradesHTML(id),t=genCaptions(id);
    downloadFile(base+'_카드뉴스.html',c,'text/html;charset=utf-8');
    setTimeout(()=>downloadFile(base+'_블로그.html',b,'text/html;charset=utf-8'),300);
    setTimeout(()=>downloadFile(base+'_캡션.txt',t,'text/plain;charset=utf-8'),600);
    setTimeout(()=>downloadFile(base+'_학년별카톡.html',g,'text/html;charset=utf-8'),900);
    setTimeout(()=>openInNewTab(c),1200);
    alert('🚀 풀패키지 4개 파일 다운로드 시작!');
  }
}
</script></body></html>'''

def generate_html(data):
    articles_html = ''
    for a in data['articles']:
        badge_cls = {'긴급':'b-urgent','중요':'b-important','참고':'b-note'}.get(a.get('priority',''), 'b-note')
        card_cls = {'긴급':'urgent','중요':'important','참고':'note'}.get(a.get('priority',''), '')
        areas = ' '.join([f'<span class="badge b-cat">{x}</span>' for x in a.get('areas', [])])
        changes_html = ''
        if a.get('changeA'): changes_html += f'<li>{a["changeA"].get("title","").replace("<br>"," ")}: {a["changeA"].get("desc","")}</li>'
        if a.get('changeB'): changes_html += f'<li>{a["changeB"].get("title","").replace("<br>"," ")}: {a["changeB"].get("desc","")}</li>'
        titles = ''.join([f'<li>{t}</li>' for t in a.get('card_titles', [])])
        articles_html += f'''
<div class="card {card_cls}" id="card-{a['id']}">
  <div class="badges">
    <span class="badge {badge_cls}">{a.get('priority','')}</span>
    <span class="badge b-year">{a.get('year','')}</span>
    <span class="badge b-tgt">{a.get('target','')}</span>
    {areas}
  </div>
  <h2>{a.get('id','')}. {a.get('title','')}</h2>
  <div class="source">{a.get('source','')} · {a.get('date','')} · <a href="{a.get('url','#')}" target="_blank">원문</a></div>
  <p class="sum1">{a.get('summary1','')}</p>
  <div class="block"><b>📌 무엇이 바뀌었나</b><ul>{changes_html}</ul></div>
  <div class="myth"><div class="q">❓ {a.get('mythQ','')}</div><div class="a">→ {a.get('mythA','')}</div></div>
  <div class="katok"><div class="l">📱 학부모 카톡문</div><p>{a.get('katok','')}</p></div>
  <div class="titles"><div class="l">📰 카드뉴스 제목</div><ul>{titles}</ul></div>
  <div class="sco"><div class="l">💡 SCO 관점</div><p>{a.get('sco_view','')}</p></div>
  <div class="make-bar">
    <span class="lbl">⚡ 자동 콘텐츠 제작</span>
    <button class="make-btn full" onclick="makeContent({a['id']},'full')">🚀 풀패키지</button>
    <button class="make-btn" onclick="makeContent({a['id']},'cards')">📸 카드뉴스</button>
    <button class="make-btn" onclick="makeContent({a['id']},'blog')">✍️ 블로그</button>
    <button class="make-btn" onclick="makeContent({a['id']},'captions')">💬 캡션</button>
    <button class="make-btn" onclick="makeContent({a['id']},'grades')">👨‍👩‍👧 학년별</button>
    <button class="make-btn parent" onclick="makeContent({a['id']},'parent')">📲 학부모 발송용</button>
  </div>
</div>'''

    # ARTICLES JS 객체로 변환 (id를 key로)
    articles_dict = {a['id']: a for a in data['articles']}
    articles_json = json.dumps(articles_dict, ensure_ascii=False)

    return HTML_TEMPLATE.replace('__TODAY__', TODAY).replace('__DAY__', DAY_NAME).replace('__KEY_SUMMARY__', data.get('key_summary','')).replace('__BEST_PICK__', data.get('best_pick','')).replace('__ARTICLES_HTML__', articles_html).replace('__ARTICLES_JSON__', articles_json)

def main():
    print(f"[{TODAY}] 뉴스 수집...")
    news = fetch_news()
    print(f"  → {len(news)}건")
    if len(news) == 0: sys.exit(1)
    print(f"[{TODAY}] AI 분석...")
    data = analyze(news)
    print(f"  → {len(data.get('articles',[]))}건")
    print(f"[{TODAY}] HTML 생성...")
    html = generate_html(data)
    os.makedirs('site', exist_ok=True)
    with open(f'site/briefing-{TODAY}.html', 'w', encoding='utf-8') as f:
        f.write(html)
    with open(f'site/briefing-{TODAY}.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  → 완료")

if __name__ == '__main__':
    main()
