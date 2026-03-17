import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(page_title="calbtc.com | 智能共振雷达", layout="wide")

# --- 数据引擎 (使用 CryptoCompare 绕过区域限制) ---
class CalBTCEngine:
    def __init__(self, interval='1d'):
        self.interval = interval

    def fetch_data(self):
        try:
            # 映射周期
            limit = 200
            if self.interval == '1h':
                url = f"https://min-api.cryptocompare.com/data/v2/histohour?fsym=BTC&tsym=USD&limit={limit}"
            elif self.interval == '1d':
                url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym=BTC&tsym=USD&limit={limit}"
            else: # 1w
                url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym=BTC&tsym=USD&limit={limit}"
                
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data['Response'] == 'Success':
                df = pd.DataFrame(data['Data']['Data'])
                df['time'] = pd.to_datetime(df['time'], unit='s')
                # 统一列名以适配逻辑
                df = df.rename(columns={'volumefrom': 'vol'})
                return df
            else:
                st.error(f"📡 API 报错: {data.get('Message')}")
                return None
        except Exception as e:
            st.error(f"📡 数据抓取失败。原因: {e}")
            return None

    def get_analysis(self, df):
        if df is None or df.empty: return None
        cur_p = df['close'].iloc[-1]
        
        # 1. Pivot Points
        last = df.iloc[-2]
        p = (last['high'] + last['low'] + last['close']) / 3
        r1, s1 = 2*p - last['low'], 2*p - last['high']
        
        # 2. Fibonacci (200周期)
        swing_h, swing_l = df['high'].max(), df['low'].min()
        fib_618 = swing_l + (swing_h - swing_l) * 0.618
        
        # 3. Moving Average (MA99)
        ma99 = df['close'].rolling(99).mean().iloc[-1]
        
        # 4. 心理整位数
        psych_level = round(cur_p / 5000) * 5000
        
        # 5. 筹码密集区 (POC)
        price_bins = pd.cut(df['close'], bins=20)
        poc_zone = df.groupby(price_bins, observed=True)['vol'].sum().idxmax()
        poc_price = (poc_zone.left + poc_zone.right) / 2
        
        return {
            "当前价格": cur_p,
            "枢轴压力 R1": r1,
            "斐波那契 0.618": fib_618,
            "MA99 趋势线": ma99,
            "心理整位关口": psych_level,
            "筹码密集 POC": poc_price,
            "支撑位 S1": s1
        }

# --- 界面交互 ---
st.sidebar.header("calbtc 控制面板")
period = st.sidebar.selectbox("选择分析周期", ['1h', '1d'], index=1)
st.sidebar.info("提示：calbtc 已切换至加密原生聚合数据源，确保全地域稳定访问。")

st.title("🛡️ calbtc 智能监控引擎")

engine = CalBTCEngine(interval=period)
df = engine.fetch_data()

if df is not None:
    analysis = engine.get_analysis(df)
    cur_p = analysis.pop("当前价格")
    
    st.write(f"### 📊 {period.upper()} 周期实时维度")
    cols = st.columns(len(analysis))
    for i, (name, val) in enumerate(analysis.items()):
        delta = ((val - cur_p) / cur_p) * 100
        cols[i].metric(name, f"${val:,.0f}", f"{delta:+.1f}%")

    st.divider()
    left, right = st.columns([2, 1])
    
    with left:
        fig = go.Figure(data=[go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="BTC-USD")])
        colors = ['#FF4B4B', '#FFAA00', '#7D3CFF', '#0068C9', '#83C9FF', '#29B09D']
        for (name, val), color in zip(analysis.items(), colors):
            fig.add_hline(y=val, line_dash="dot", line_color=color, annotation_text=name, annotation_position="top left")
        fig.update_layout(height=600, template="plotly_white", margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.write("### 🔍 kudle 智能诊断")
        hits = [name for name, val in analysis.items() if abs(val - cur_p) / cur_p < 0.015]
        if len(hits) >= 2:
            st.error(f"⚠️ **强共振区确认**：价格正处于 {' & '.join(hits)} 的影响区。")
        else:
            st.success("✨ 市场目前指标分布平稳。")
        
        st.divider()
        st.markdown("**5 维度量化模型：** Pivot, Fibonacci, MA99, Psych, POC")

st.caption(f"© 2026 calbtc.com | 数据源：CryptoCompare | 更新：{datetime.now().strftime('%H:%M:%S')}")
