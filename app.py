import streamlit as st
import requests
import pandas as pd
import json
import os
from datetime import datetime, timezone

# -------------------- [설정] --------------------
st.set_page_config(page_title="메이플랜드 시세", page_icon="🍁", layout="wide")
st.title("🍁 메이플랜드 시세 검색기")

# -------------------- [데이터 로직] --------------------
@st.cache_data
def initialize_item_db():
    file_path = "items.json"
    if not os.path.exists(file_path):
        return {}, "파일 없음 (items.json 필요)"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            items = json.load(f)
        item_map = {}
        for item in items:
            name = item.get('name') or item.get('itemName')
            code = item.get('code') or item.get('itemCode') or item.get('id')
            if name and code:
                item_map[name] = code
        return item_map, "성공"
    except Exception as e:
        return {}, str(e)

def get_market_price(item_code):
    url = f"https://api.mapleland.gg/trade?itemCode={item_code}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://mapleland.gg/",
        "Origin": "https://mapleland.gg"
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        return res.json() if res.status_code == 200 else None
    except:
        return None

def format_data(data_list):
    results = []
    for item in data_list:
        try:
            updated = item.get('updated_at')
            dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            diff = int((datetime.now(timezone.utc) - dt).total_seconds() / 60)
            time_str = f"{diff}분 전" if diff < 60 else f"{diff//60}시간 전"
            
            results.append({
                '타입': item.get('tradeType'), 
                '닉네임': item.get('traderDiscordInfo', {}).get('global_name', '알수없음'),
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
item_map, status = initialize_item_db()
if not item_map:
    st.error(status)
    st.stop()

# 1. 검색창
selected_item = st.selectbox(
    "검색할 아이템 선택",
    options=list(item_map.keys()),
    index=None,
    placeholder="여기에 아이템 이름을 입력하거나 선택하세요"
)

# 2. 결과 출력 (안정적인 컨테이너 사용)
result_container = st.container()

if selected_item:
    with result_container:
        code = item_map[selected_item]
        st.divider()
        st.header(f"📢 {selected_item}")
        
        with st.spinner('조회 중...'):
            raw_data = get_market_price(code)
            
            if not raw_data:
                st.info("데이터가 없습니다.")
            else:
                df = format_data(raw_data)
                if not df.empty:
                    # ✅ [핵심 변경] Tabs 대신 '라디오 버튼' 사용 (에러 원천 차단)
                    # horizontal=True 옵션을 주면 탭처럼 가로로 배치됩니다.
                    view_option = st.radio(
                        "보고 싶은 시세를 선택하세요", 
                        ["🔵 팝니다 (매물)", "🔴 삽니다 (구매희망)"], 
                        horizontal=True
                    )
                    
                    st.divider() # 구분선
                    
                    if view_option == "🔵 팝니다 (매물)":
                        df_sell = df[df['타입'] == 'sell']
                        if not df_sell.empty:
                            df_sell = df_sell.sort_values(by='raw_time', ascending=True)
                            st.metric("🔥 최저가", f"{df_sell['가격'].min():,} 메소")
                            st.dataframe(df_sell[['닉네임', '가격', '수량', '메시지', '시간']], hide_index=True, use_container_width=True)
                        else:
                            st.info("판매 매물이 없습니다.")
                            
                    else: # 삽니다 선택 시
                        df_buy = df[df['타입'] == 'buy']
                        if not df_buy.empty:
                            df_buy = df_buy.sort_values(by='raw_time', ascending=True)
                            st.metric("💰 최고 매입가", f"{df_buy['가격'].max():,} 메소")
                            st.dataframe(df_buy[['닉네임', '가격', '수량', '메시지', '시간']], hide_index=True, use_container_width=True)
                        else:
                            st.info("구매 희망글이 없습니다.")
                else:
                    st.info("거래 내역이 없습니다.")
