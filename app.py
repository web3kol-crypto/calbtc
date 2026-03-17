import streamlit as st
import pandas as pd
import numpy as np
from binance.client import Client

# --- 核心计算引擎 ---
class CalBTCEngine:
    def __init__(self, symbol='BTCUSDT', interval='1d'):
        self.client = Client()
        self.symbol = symbol
        self.interval = interval

    def fetch_data(self):
        # 获取 K 线，多拿一点数据用于计算筹码分布
        klines = self.client.get_klines(symbol=self.symbol, interval=self.interval, limit=200)
        df = pd.DataFrame(klines, columns=['time','open','high','low','close','vol','c_time','qav','trades','tb','tq','i'])
        df[['high', 'low', 'close', 'vol']] = df[['high', 'low', 'close', 'vol']].astype(float)
        return df

    def get_levels(self, df):
        # 1. 枢轴点 (Pivot)
        last = df.iloc[-2]
        p = (last['high'] + last['low'] + last['close']) / 3
        r1, s1 = 2*p - last['low'], 2*p - last['high']

        # 2. 斐波那契 (Fibonacci)
        swing_h, swing_l = df['high'].max(), df['low'].min()
        fib_618 = swing_l + (swing_h - swing_l) * 0.618

        # 3. 均线 (MA)
        ma99 = df['close'].rolling(99).mean().iloc[-1]

        # 4. 心理整位数 (Psychological)
        cur_p = df['close'].iloc[-1]
        # 寻找最近的 5000 整数位
        psych_level = round(cur_p / 5000) * 5000

        # 5. 筹码密集区 (Simple Volume Profile)
        # 将价格切成 20 个区间，看哪个区间的成交量总和最大
        bins = 20
        hist, bin_edges = np.histogram(df['close'], bins=bins, weights=df['vol'])
        poc_index = np.argmax(hist)
        poc_price = (bin_edges[poc_index] + bin_edges[poc_index+1]) / 2

        return {
            "Pivot R1": r1,
            "Fib 0.618": fib_618,
            "MA99": ma99,
            "心理关口": psych_level,
            "筹码峰 (POC)": poc_price
        }

# --- Streamlit 界面 ---
st.set_page_config(page_title="calbtc.com | 智能共振计算器")
st.title("🛡️ calbtc 智能监控引擎")

# 侧边栏：周期选择
interval = st.sidebar.selectbox("选择分析周期", ['1h', '4h', '1d', '1w'], index=2)

engine = CalBTCEngine(interval=interval)
df = engine.fetch_data()
levels = engine.get_levels(df)
cur_p = df['close'].iloc[-1]

# 显示五个维度
st.subheader(f"BTC 当前周期: {interval.upper()}")
cols = st.columns(5)
for i, (name, val) in enumerate(levels.items()):
    cols[i].metric(name, f"{val:,.0f}")

# --- 共振预警逻辑 ---
st.divider()
st.write("### 🔍 kudle 智能共振分析")

# 检查是否有多个指标落在当前价格 1% 的范围内
hits = []
for name, val in levels.items():
    if abs(val - cur_p) / cur_p < 0.015: # 1.5% 阈值
        hits.append(name)

if len(hits) >= 2:
    st.error(f"🚨 **强共振预警**：价格正处于 {' + '.join(hits)} 的重合区间！建议严格执行止盈/调仓策略。")
else:
    st.info("💡 目前指标分布较散，建议关注最上方的 R1 或 MA99 压制位。")

st.caption("calbtc.com - 为专业 Web3 交易者打造")