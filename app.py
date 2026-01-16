import streamlit as st
import requests
import pandas as pd
import json
import os
from datetime import datetime, timezone

# -------------------- [설정 및 디자인] --------------------
st.set_page_config(page_title="메이플랜드 시세", page_icon="🍁", layout="wide")
st.title("🍁 메이플랜드 시세 검색기")
st.caption("아이템을 검색하여 '팝니다'와 '삽니다' 시세를 한눈에 확인하세요.")

# -------------------- [데이터 로직] --------------------
@st.cache_data
def initialize_item_db():
    # GitHub에 함께 올린 items.json 파일을 읽습니다.
    file_path = "items.json"
    
    if not os.path.exists(file_path):
        return {}, "파일 없음 (items.json을 GitHub에 올려주세요)"
    
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
        return {}, f"파일 읽기 에러: {str(e)}"

def get_market_price(item_code):
    url = f"https://api.mapleland.gg/trade?itemCode={item_code}"
    # 헤더를 최대한 실제 브라우저처럼 위장합니다.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://mapleland.gg/",
        "Origin": "https://mapleland.gg",
        "Accept": "application/json, text/plain, */*"
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            return res.json()
        else:
            return None
    except:
        return None

def format_data(data_list):
    results = []
    for item in data_list:
        try:
            # 시간 계산
            updated = item.get('updated_at')
            dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            diff = int((datetime.now(timezone.utc) - dt).total_seconds() / 60)
            time_str = f"{diff}분 전" if diff < 60 else f"{diff//60}시간 전"
            
            # 거래 타입 확인 (buy/sell)
            trade_type = item.get('tradeType')
            
            results.append({
                '타입': trade_type, # 필터링을 위해 타입 저장
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

# 1. 데이터 로드
item_map, status = initialize_item_db()

if not item_map:
    st.error(f"⚠️ 아이템 목록 로드 실패: {status}")
    st.info("💡 PC에서 'items.json'을 생성하여 GitHub에 업로드했는지 확인해주세요.")
    st.stop()

# 2. 검색창 (자동완성)
selected_item = st.selectbox(
    "검색할 아이템 선택",
    options=list(item_map.keys()),
    index=None,
    placeholder="여기에 아이템 이름을 입력하거나 선택하세요 (예: 엘릭서, 장공)"
)

# 3. 결과 출력
if selected_item:
    code = item_map[selected_item]
    st.divider()
    st.header(f"📢 {selected_item} 시세 정보")
    
    with st.spinner('실시간 매물을 불러오는 중...'):
        raw_data = get_market_price(code)
        
        if raw_data is None:
            st.error(f"⛔ 거래 데이터 조회 실패 (서버 차단됨)")
            st.caption("해결책: 잠시 후 다시 시도하거나, 로컬(PC) 환경에서 실행해주세요.")
        elif not raw_data:
            st.info("데이터가 비어있습니다.")
        else:
            df = format_data(raw_data)
            
            if not df.empty:
                # 🔵 팝니다 (Sell) vs 🔴 삽니다 (Buy) 분리
                df_sell = df[df['타입'] == 'sell']
                df_buy = df[df['타입'] == 'buy']
                
                # 탭으로 화면 분리
                tab1, tab2 = st.tabs(["🔵 팝니다 (매물)", "🔴 삽니다 (구매희망)"])
                
                # --- [탭 1] 팝니다 (Sell) ---
                with tab1:
                    if not df_sell.empty:
                        # 정렬: 최신순
                        df_sell = df_sell.sort_values(by='raw_time', ascending=True)
                        
                        # 최저가 정보 (파는 거니까 싼 게 중요)
                        min_price = df_sell['가격'].min()
                        st.metric("현재 최저가", f"{min_price:,} 메소")
                        
                        st.dataframe(
                            df_sell[['닉네임', '가격', '수량', '메시지', '시간']], 
                            hide_index=True, 
                            use_container_width=True
                        )
                    else:
                        st.info("등록된 판매 매물이 없습니다.")
                
                # --- [탭 2] 삽니다 (Buy) ---
                with tab2:
                    if not df_buy.empty:
                        # 정렬: 최신순
                        df_buy = df_buy.sort_values(by='raw_time', ascending=True)
                        
                        # 최고가 정보 (사는 거니까 비싸게 사주는 게 중요)
                        max_price = df_buy['가격'].max()
                        st.metric("현재 최고 매입가", f"{max_price:,} 메소")
                        
                        st.dataframe(
                            df_buy[['닉네임', '가격', '수량', '메시지', '시간']], 
                            hide_index=True, 
                            use_container_width=True
                        )
                    else:
                        st.info("등록된 구매 희망글이 없습니다.")
            else:
                st.info("거래 내역이 없습니다.")
