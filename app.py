import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from binance.client import Client
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(page_title="calbtc.com | 智能共振雷达", layout="wide")

# --- 数据引擎 ---
class CalBTCEngine:
    def __init__(self, symbol='BTCUSDT', interval='1d'):
        # 使用 tld='me' 或备用 base_url 绕过部分云服务器对 binance.com 的访问限制
        self.client = Client(tld='me') 
        self.symbol = symbol
        self.interval = interval

    def fetch_data(self):
        try:
            # 获取 200 根 K 线以确保筹码密集区（POC）计算精准
            klines = self.client.get_klines(symbol=self.symbol, interval=self.interval, limit=200)
            df = pd.DataFrame(klines, columns=['time','open','high','low','close','vol','c_time','qav','trades','tb','tq','i'])
            df['time'] = pd.to_datetime(df['time'], unit='ms')
            df[['high', 'low', 'close', 'vol']] = df[['high', 'low', 'close', 'vol']].astype(float)
            return df
        except Exception as e:
            st.error(f"📡 币安 API 连接失败。原因: {e}")
            return None

    def get_analysis(self, df):
        if df is None: return None
        cur_p = df['close'].iloc[-1]
        
        # 1. Pivot Points (基于昨日/上个周期波动)
        last = df.iloc[-2]
        p = (last['high'] + last['low'] + last['close']) / 3
        r1 = 2*p - last['low']
        s1 = 2*p - last['high']
        
        # 2. Fibonacci (取近200周期波段 0.618 位)
        swing_h, swing_l = df['high'].max(), df['low'].min()
        fib_618 = swing_l + (swing_h - swing_l) * 0.618
        
        # 3. Moving Average (MA99 机构趋势线)
        ma99 = df['close'].rolling(99).mean().iloc[-1]
        
        # 4. 心理整位数 (Psychological - 每 5000 刀一个关口)
        psych_level = round(cur_p / 5000) * 5000
        
        # 5. 筹码密集区 (Volume Profile POC)
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
period = st.sidebar.selectbox("选择分析周期", ['1h', '4h', '1d', '1w'], index=2)
st.sidebar.info("提示： calbtc 集成 5 大量化维度，寻找价格共振区间。")

# --- 主界面 ---
st.title("🛡️ calbtc 智能监控引擎")

try:
    engine = CalBTCEngine(interval=period)
    df = engine.fetch_data()
    
    if df is not None:
        analysis = engine.get_analysis(df)
        cur_p = analysis.pop("当前价格")
        
        # 顶部指标卡片
        st.write(f"### 📊 {period.upper()} 周期实时维度")
        cols = st.columns(len(analysis))
        for i, (name, val) in enumerate(analysis.items()):
            delta = ((val - cur_p) / cur_p) * 100
            cols[i].metric(name, f"${val:,.0f}", f"{delta:+.1f}%")

        # K 线可视化
        st.divider()
        left, right = st.columns([2, 1])
        
        with left:
            fig = go.Figure(data=[go.Candlestick(
                x=df['time'], 
                open=df['open'], 
                high=df['high'], 
                low=df['low'], 
                close=df['close'], 
                name="BTCUSDT"
            )])
            
            # 绘制压力支撑热力线
            colors = ['#FF4B4B', '#FFAA00', '#7D3CFF', '#0068C9', '#83C9FF', '#29B09D']
            for (name, val), color in zip(analysis.items(), colors):
                fig.add_hline(y=val, line_dash="dot", line_color=color, annotation_text=name, annotation_position="top left")
            
            fig.update_layout(height=600, template="plotly_white", margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

        with right:
            st.write("### 🔍 kudle 智能诊断")
            # 诊断逻辑：1.5% 范围内的指标视为共振
            hits = [name for name, val in analysis.items() if abs(val - cur_p) / cur_p < 0.015]
            
            if len(hits) >= 2:
                st.error(f"⚠️ **检测到强共振区域**\n\n当前价格正处于 **{' & '.join(hits)}** 的重叠影响区。")
                st.write("建议：此处阻力/支撑密集，属于高胜率博弈点，请结合 1H 周期寻找反转信号。")
            else:
                st.success("✨ 市场目前处于主流指标空档期，波动主要受短期情绪驱动。")
                st.write(f"建议关注上方最接近的压力位：**${min([v for v in analysis.values() if v > cur_p]):,.0f}**")

            st.divider()
            st.markdown(f"""
            **5 维度模型说明：**
            1. **Pivot**: 基于波动率的日内生命线
            2. **Fibonacci**: 全球交易者公认的波段回撤位
            3. **MA99**: 机构级趋势压制/支撑参考
            4. **Psych**: 散户心理挂单密集的整数关口
            5. **POC**: 筹码分布最集中的“价值中枢”
            """)

except Exception as e:
    st.error(f"程序运行遇到未知错误: {e}")

st.caption(f"© 2026 calbtc.com | Kudle Lab 量化引擎 | 最后更新：{datetime.now().strftime('%H:%M:%S')}")
