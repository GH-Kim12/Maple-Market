import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone

# -------------------- [설정] --------------------
st.set_page_config(page_title="메이플랜드 시세", page_icon="🍁")
st.title("🍁 메이플랜드 시세 검색기")
st.caption("실시간 '삽니다' 매물을 찾아드립니다.")

# -------------------- [함수] --------------------
@st.cache_data
def initialize_item_db():
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
            return item_map
    except:
        return {}
    return {}

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
        if item.get('tradeType') == 'buy': # 삽니다만 필터링
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

# -------------------- [화면] --------------------
with st.spinner('아이템 목록 로딩 중...'):
    item_map = initialize_item_db()

selected_item = st.selectbox(
    "검색할 아이템 선택", 
    options=list(item_map.keys()) if item_map else [], 
    index=None, 
    placeholder="여기에 입력하세요 (예: 장공)"
)

if selected_item:
    code = item_map[selected_item]
    st.divider()
    st.subheader(f"📢 {selected_item} 구매 희망 목록")
    
    with st.spinner('매물 조회 중...'):
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
                st.info("현재 등록된 '삽니다' 매물이 없습니다.")
        else:
            st.warning("데이터 조회 실패 (잠시 후 다시 시도하세요)")
