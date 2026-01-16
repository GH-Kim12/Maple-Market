import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone

# -------------------- [설정] --------------------
st.set_page_config(page_title="메이플랜드 시세", page_icon="🍁")
st.title("🍁 메이플랜드 시세 검색기")
st.caption("모바일 최적화 버전 (삽니다 매물 검색)")

# -------------------- [데이터 로직] --------------------
@st.cache_data
def initialize_item_db():
    # Streamlit Cloud 서버가 차단당했을 경우를 대비해 예외 처리를 강화합니다.
    url = "https://mapleland.gg/api/items?v=260112"
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 200:
            items = response.json()
            item_map = {}
            for item in items:
                name = item.get('name') or item.get('itemName')
                code = item.get('code') or item.get('itemCode') or item.get('id')
                if name and code:
                    item_map[name] = code
            return item_map, "성공"
        else:
            return {}, f"서버 차단됨 (상태코드: {response.status_code})"
    except Exception as e:
        return {}, f"에러 발생: {str(e)}"

def get_market_price(item_code):
    url = f"https://api.mapleland.gg/trade?itemCode={item_code}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://mapleland.gg/",
        "Origin": "https://mapleland.gg"
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        return res.json() if res.status_code == 200 else []
    except:
        return []

def format_data(data_list):
    results = []
    for item in data_list:
        if item.get('tradeType') == 'buy': 
            try:
                updated = item.get('updated_at')
                dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                diff = int((datetime.now(timezone.utc) - dt).total_seconds() / 60)
                time_str = f"{diff}분 전" if diff < 60 else f"{diff//60}시간 전"
                
                results.append({
                    '구매자': item.get('traderDiscordInfo', {}).get('global_name', '알수없음'),
                    '가격': item.get('itemPrice'), 
                    '수량': item.get('tradeOption', {}).get('each', 1),
                    '메시지': item.get('comment', ''), 
                    '시간': time_str,
                    'raw_time': diff 
                })
            except:
                continue
    return pd.DataFrame(results)

# -------------------- [화면 UI] --------------------

# 1. 데이터 로드 상태 확인
with st.spinner('서버 연결 중...'):
    item_map, status = initialize_item_db()

# 디버깅 정보 (문제가 생기면 화면에 이유가 뜹니다)
if not item_map:
    st.error(f"⚠️ 아이템 목록을 불러오지 못했습니다.\n원인: {status}")
    st.info("해결책: PC에서 'items.json' 파일을 만들어 GitHub에 함께 올려야 합니다.")
    st.stop()
else:
    # 정상적으로 로드되면 몇 개인지 작게 표시
    st.toast(f"✅ {len(item_map)}개 아이템 로드 완료!")

# 2. 검색창 (Selectbox 대신 Text Input 사용 -> 모바일 렉 해결)
keyword = st.text_input("검색할 아이템 이름 (예: 장공, 일비)", placeholder="입력 후 Enter를 누르세요")

if keyword:
    # 입력한 단어가 포함된 아이템 찾기
    candidates = {name: code for name, code in item_map.items() if keyword.replace(" ", "") in name.replace(" ", "")}
    
    if not candidates:
        st.warning("❌ 검색 결과가 없습니다. 이름을 다시 확인해주세요.")
    
    elif len(candidates) > 10:
        st.warning(f"🔍 '{keyword}' 관련 아이템이 너무 많습니다 ({len(candidates)}개). 더 정확하게 입력해주세요.")
    
    else:
        # 검색 결과가 1개 이상이면 버튼으로 선택하게 함
        st.success(f"총 {len(candidates)}개의 아이템을 찾았습니다.")
        
        # 탭으로 결과를 나눠서 보여줌
        tabs = st.tabs(list(candidates.keys()))
        
        for i, (name, code) in enumerate(candidates.items()):
            with tabs[i]:
                st.write(f"**[{name}]** 매물을 조회합니다...")
                raw_data = get_market_price(code)
                
                if raw_data:
                    df = format_data(raw_data)
                    if not df.empty:
                        df = df.sort_values(by='raw_time', ascending=True)
                        max_price = df.iloc[0]['가격']
                        st.metric(label="최고 매입가", value=f"{max_price:,} 메소")
                        st.dataframe(
                            df[['구매자', '가격', '수량', '메시지', '시간']], 
                            hide_index=True, 
                            use_container_width=True
                        )
                    else:
                        st.info("현재 '삽니다' 매물이 없습니다.")
                else:
                    st.warning("데이터 조회 실패")
