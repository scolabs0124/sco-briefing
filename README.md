# SCO 입시 브리핑 — 자동화 시스템

매일 오전 11시(한국 시간) GitHub Actions가 자동으로:
1. 입시 뉴스 수집 (구글 뉴스 RSS)
2. Claude AI로 상위 5건 분석
3. HTML 브리핑 생성
4. `site/` 폴더에 저장 + GitHub에 자동 push
5. Netlify가 자동 감지해서 사이트 갱신

## 구조
- `.github/workflows/daily-briefing.yml` — 스케줄·실행
- `briefing.py` — 메인 분석 스크립트
- `site/` — 생성된 브리핑 HTML 저장소 (Netlify 배포 루트)

## 비밀 키 (Settings → Secrets)
- `ANTHROPIC_API_KEY` — Claude API 키

## 수동 실행
GitHub 저장소 → Actions → "SCO 입시 일일 브리핑 자동 생성" → Run workflow

## SCO LABS · 학이 아닌 습
