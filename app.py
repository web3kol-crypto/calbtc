import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(page_title="calbtc.com | 智能共振雷达", layout="wide")

# --- 数据引擎 (使用 CryptoCompare 确保全球稳定性) ---
class CalBTCEngine:
    def __init__(self, interval='1d'):
        self.interval = interval

    def fetch_data(self):
        try:
            limit = 300 # 增加数据深度以保证 MA99 准确性
            
            # 建立多周期 API 映射逻辑
            if self.interval == '1h':
                url = f"https://min-api.cryptocompare.com/data/v2/histohour?fsym=BTC&tsym=USD&limit={limit}"
            elif self.interval == '4h':
                # API 限制，4h 通过小时级别聚合 4 倍点数实现
                url = f"https://min-api.cryptocompare.com/data/v2/histohour?fsym=BTC&tsym=USD&aggregate=4&limit={limit}"
            elif self.interval == '1d':
                url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym=BTC&tsym=USD&limit={limit}"
            elif self.interval == '1w':
                # 周线级别通过日线聚合 7 天实现
                url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym=BTC&tsym=USD&aggregate=7&limit={limit}"
            else:
                url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym=BTC&tsym=USD&limit={limit}"
                
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data['Response'] == 'Success':
                df = pd.DataFrame(data['Data']['Data'])
                df['time'] = pd.to_datetime(df['time'], unit='s')
                # 统一列名以适配计算逻辑
                df = df.rename(columns={'volumefrom': 'vol'})
                return df
            else:
                st.error(f"📡 API 响应错误: {data.get('Message')}")
                return None
        except Exception as e:
            st.error(f"📡 数据引擎连接失败: {e}")
            return None

    def get_analysis(self, df):
        if df is None or df.empty: return None
        cur_p = df['close'].iloc[-1]
        
        # 1. 枢轴点 (Pivot Points - 基于昨日波动)
        last = df.iloc[-2]
        p = (last['high'] + last['low'] + last['close']) / 3
        r1, s1 = 2*p - last['low'], 2*p - last['high']
        
        # 2. 斐波那契 (Fibonacci - 200周期波段)
        swing_h, swing_l = df['high'].max(), df['low'].min()
        fib_618 = swing_l + (swing_h - swing_l) * 0.618
        
        # 3. 移动平均线 (MA99 - 趋势分水岭)
        ma99 = df['close'].rolling(99).mean().iloc[-1]
        
        # 4. 心理整位数 (Psychological - 每 5000 关口)
        psych_level = round(cur_p / 5000) * 5000
        
        # 5. 筹码密集区 (POC - 最近 200 周期价值中枢)
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

# --- 侧边栏交互 ---
st.sidebar.header("calbtc 控制面板")
# 丰富周期选择
period = st.sidebar.selectbox("选择分析周期", ['1h', '4h', '1d', '1w'], index=2)
st.sidebar.info("💡 calbtc 集成 5 大量化维度，全自动检测价格共振区间。")

# --- 主界面 ---
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
        fig = go.Figure(data=[go.Candlestick(
            x=df['time'], 
            open=df['open'], 
            high=df['high'], 
            low=df['low'], 
            close=df['close'], 
            name="BTC-USD"
        )])
        # 绘制 5 维度参考线
        colors = ['#FF4B4B', '#FFAA00', '#7D3CFF', '#0068C9', '#83C9FF', '#29B09D']
        for (name, val), color in zip(analysis.items(), colors):
            fig.add_hline(y=val, line_dash="dot", line_color=color, annotation_text=name, annotation_position="top left")
        
        fig.update_layout(height=600, template="plotly_white", margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with right:
        # 修改标题为 AI 智能诊断
        st.write("### 🔍 AI 智能诊断")
        
        # 诊断逻辑：1.5% 范围内的指标视为共振
        hits = [name for name, val in analysis.items() if abs(val - cur_p) / cur_p < 0.015]
        
        if len(hits) >= 2:
            st.error(f"⚠️ **强共振区确认**：价格正处于 **{' & '.join(hits)}** 的影响区。此处阻力/支撑密集，建议谨慎操作。")
        else:
            st.success("✨ 市场目前处于主流技术指标空档期，主要由情绪驱动。")
            
        st.divider()
        st.markdown("**量化引擎驱动：** Pivot, Fibonacci, MA99, Psych, POC")

st.caption(f"© 2026 calbtc.com | 数据源：CryptoCompare | 更新：{datetime.now().strftime('%H:%M:%S')}")
