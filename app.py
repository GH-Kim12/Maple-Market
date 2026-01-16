import streamlit as st
import requests
import pandas as pd
import json
import os
from datetime import datetime, timezone

# -------------------- [설정] --------------------
st.set_page_config(page_title="메이플랜드 시세", page_icon="🍁")
st.title("🍁 메이플랜드 시세 검색기")
st.caption("차단 우회 버전 (파일 로드 방식)")

# -------------------- [데이터 로직] --------------------
@st.cache_data
def initialize_item_db():
    # [변경점] URL 다운로드 대신, 같이 업로드한 items.json 파일을 읽습니다.
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
            return None # 에러 발생 시 None 반환
    except:
        return None

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

item_map, status = initialize_item_db()

if not item_map:
    st.error(f"⚠️ 아이템 목록 로드 실패: {status}")
    st.stop()

# 검색창
# -------------------- [화면 UI] --------------------

item_map, status = initialize_item_db()

if not item_map:
    st.error(f"⚠️ 아이템 목록 로드 실패: {status}")
    st.stop()

# ✅ 여기가 수정된 부분입니다 (자동완성 기능 부활)
# 텍스트 입력 대신 '선택 상자'를 사용하여 목록에서 고를 수 있게 합니다.
selected_item = st.selectbox(
    "검색할 아이템 선택",
    options=list(item_map.keys()), # 전체 아이템 목록을 넣습니다
    index=None,                    # 처음엔 아무것도 선택 안 된 상태
    placeholder="여기에 아이템 이름을 입력하거나 선택하세요 (예: 장공)"
)

if selected_item:
    code = item_map[selected_item]
    
    st.divider()
    st.subheader(f"📢 {selected_item} 구매 희망 목록")
    
    with st.spinner('매물 조회 중...'):
        raw_data = get_market_price(code)
        
        if raw_data is None:
            st.error(f"⛔ 거래 데이터 조회 실패 (서버 차단됨)")
            st.caption("해결책: PC에서 실행하거나, 잠시 후 다시 시도해보세요.")
        elif not raw_data:
            st.info("데이터가 비어있습니다.")
        else:
            df = format_data(raw_data)
            if not df.empty:
                # 최신순 정렬
                df = df.sort_values(by='raw_time', ascending=True)
                
                # 최고가 표시
                max_price = df.iloc[0]['가격']
                st.metric("최고 매입가", f"{max_price:,} 메소")
                
                # 표 출력
                st.dataframe(
                    df[['구매자', '가격', '수량', '메시지', '시간']], 
                    hide_index=True, 
                    use_container_width=True
                )
            else:
                st.info("현재 '삽니다' 매물이 없습니다.")

if keyword:
    candidates = {name: code for name, code in item_map.items() if keyword.replace(" ", "") in name.replace(" ", "")}
    
    if not candidates:
        st.warning("❌ 검색 결과가 없습니다.")
    elif len(candidates) > 10:
        st.warning(f"🔍 너무 많은 결과 ({len(candidates)}개). 더 구체적으로 입력하세요.")
    else:
        st.success(f"아이템 {len(candidates)}개 발견")
        
        for name, code in candidates.items():
            with st.expander(f"📌 {name} 시세 보기", expanded=True):
                raw_data = get_market_price(code)
                
                if raw_data is None:
                    st.error(f"⛔ 거래 데이터 조회 실패 (서버 차단됨)")
                    st.caption("해결책: 이 기능은 PC(로컬)에서만 작동할 수 있습니다.")
                elif not raw_data:
                    st.info("데이터가 비어있습니다.")
                else:
                    df = format_data(raw_data)
                    if not df.empty:
                        df = df.sort_values(by='raw_time', ascending=True)
                        st.metric("최고 매입가", f"{df.iloc[0]['가격']:,} 메소")
                        st.dataframe(df[['구매자', '가격', '수량', '메시지', '시간']], hide_index=True, use_container_width=True)
                    else:
                        st.info("매물이 없습니다.")
