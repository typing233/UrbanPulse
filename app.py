import streamlit as st
import pandas as pd
import numpy as np
from datetime import date as date_type, datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict

from data_generator import CityDataGenerator, generate_data_for_cities, get_current_status


# 页面配置
st.set_page_config(
    page_title="城市健康状况可视化",
    page_icon="🌆",
    layout="wide",
    initial_sidebar_state="expanded"
)


# 全局样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #1e88e5, #e53935);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .city-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1e88e5;
    }
    .traffic-good { color: #00c853; }
    .traffic-moderate { color: #ffab00; }
    .traffic-bad { color: #ff3d00; }
    .aqi-good { color: #00e400; }
    .aqi-moderate { color: #ffff00; }
    .aqi-bad { color: #ff7e00; }
    .aqi-severe { color: #ff0000; }
</style>
""", unsafe_allow_html=True)


# 会话状态管理
def init_session_state():
    if 'data_generator' not in st.session_state:
        st.session_state.data_generator = CityDataGenerator()
    
    if 'historical_data' not in st.session_state:
        st.session_state.historical_data = generate_data_for_cities(days=30)
    
    if 'llm_config' not in st.session_state:
        st.session_state.llm_config = {
            'base_url': '',
            'api_key': '',
            'model_name': 'gpt-3.5-turbo',
            'enabled': False
        }


def get_traffic_color(value: float) -> str:
    """根据拥堵指数获取颜色类"""
    if value < 50:
        return 'traffic-good'
    elif value < 70:
        return 'traffic-moderate'
    else:
        return 'traffic-bad'


def get_aqi_color(aqi: float) -> str:
    """根据AQI获取颜色类"""
    if aqi <= 50:
        return 'aqi-good'
    elif aqi <= 100:
        return 'aqi-moderate'
    elif aqi <= 150:
        return 'aqi-bad'
    else:
        return 'aqi-severe'


def get_aqi_hex_color(aqi: float) -> str:
    """根据AQI获取十六进制颜色"""
    if aqi <= 50:
        return '#00e400'
    elif aqi <= 100:
        return '#ffff00'
    elif aqi <= 150:
        return '#ff7e00'
    elif aqi <= 200:
        return '#ff0000'
    elif aqi <= 300:
        return '#99004c'
    else:
        return '#7e0023'


def create_traffic_map(city: str, district_data: pd.DataFrame) -> go.Figure:
    """创建交通拥堵地图"""
    city_config = CityDataGenerator.CITY_CONFIG[city]
    
    fig = px.scatter_mapbox(
        district_data,
        lat='lat',
        lon='lon',
        size='traffic_index',
        color='traffic_index',
        color_continuous_scale=[
            (0.0, '#00c853'),   # 畅通 - 绿色
            (0.5, '#ffab00'),   # 中度 - 黄色
            (1.0, '#ff3d00')    # 拥堵 - 红色
        ],
        range_color=[0, 100],
        hover_name='district',
        hover_data={
            'traffic_index': True,
            'traffic_level': True,
            'lat': False,
            'lon': False
        },
        size_max=25,
        zoom=10,
        center={'lat': city_config['lat'], 'lon': city_config['lon']}
    )
    
    fig.update_layout(
        mapbox_style='carto-positron',
        height=250,
        margin={'r': 0, 't': 0, 'l': 0, 'b': 0},
        coloraxis_colorbar={
            'title': '拥堵指数',
            'tickvals': [0, 25, 50, 75, 100],
            'ticktext': ['畅通', '基本畅通', '轻度拥堵', '中度拥堵', '严重拥堵']
        }
    )
    
    return fig


def create_aqi_map(city: str, district_data: pd.DataFrame) -> go.Figure:
    """创建AQI地图"""
    city_config = CityDataGenerator.CITY_CONFIG[city]
    
    fig = px.scatter_mapbox(
        district_data,
        lat='lat',
        lon='lon',
        size='aqi',
        color='aqi',
        color_continuous_scale=[
            (0.0, '#00e400'),     # 优
            (0.1, '#ffff00'),     # 良
            (0.3, '#ff7e00'),     # 轻度污染
            (0.5, '#ff0000'),     # 中度污染
            (0.75, '#99004c'),    # 重度污染
            (1.0, '#7e0023')      # 严重污染
        ],
        range_color=[0, 500],
        hover_name='district',
        hover_data={
            'aqi': True,
            'aqi_level': True,
            'lat': False,
            'lon': False
        },
        size_max=25,
        zoom=10,
        center={'lat': city_config['lat'], 'lon': city_config['lon']}
    )
    
    fig.update_layout(
        mapbox_style='carto-positron',
        height=250,
        margin={'r': 0, 't': 0, 'l': 0, 'b': 0},
        coloraxis_colorbar={
            'title': 'AQI',
            'tickvals': [0, 50, 100, 150, 200, 300, 500],
            'ticktext': ['优', '良', '轻度', '中度', '重度', '严重', '']
        }
    )
    
    return fig


def create_time_series_chart(
    city_data: pd.DataFrame,
    city_name: str,
    start_date,
    end_date
) -> go.Figure:
    """创建时序折线图"""
    # 统一日期类型处理（支持 datetime.date 和 datetime.datetime）
    def to_date(d):
        if hasattr(d, 'date'):
            return d.date()
        return d
    
    start_date_ = to_date(start_date)
    end_date_ = to_date(end_date)
    
    # 筛选日期范围
    mask = (city_data['timestamp'].dt.date >= start_date_) & \
           (city_data['timestamp'].dt.date <= end_date_)
    filtered_data = city_data.loc[mask]
    
    # 创建子图
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=('交通拥堵指数趋势', '空气质量AQI趋势')
    )
    
    # 交通拥堵指数
    fig.add_trace(
        go.Scatter(
            x=filtered_data['timestamp'],
            y=filtered_data['traffic_index'],
            name='拥堵指数',
            line=dict(color='#1e88e5', width=2),
            fill='tozeroy',
            fillcolor='rgba(30, 136, 229, 0.1)'
        ),
        row=1, col=1
    )
    
    # 添加拥堵等级参考线
    fig.add_hline(y=50, line_dash='dash', line_color='#ffab00', 
                  annotation_text='拥堵阈值', row=1, col=1)
    fig.add_hline(y=70, line_dash='dash', line_color='#ff3d00', 
                  annotation_text='严重拥堵', row=1, col=1)
    
    # AQI
    fig.add_trace(
        go.Scatter(
            x=filtered_data['timestamp'],
            y=filtered_data['aqi'],
            name='AQI',
            line=dict(color='#e53935', width=2),
            fill='tozeroy',
            fillcolor='rgba(229, 57, 53, 0.1)'
        ),
        row=2, col=1
    )
    
    # 添加AQI等级参考线
    fig.add_hline(y=50, line_dash='dash', line_color='#00e400', 
                  annotation_text='优', row=2, col=1)
    fig.add_hline(y=100, line_dash='dash', line_color='#ffff00', 
                  annotation_text='良', row=2, col=1)
    fig.add_hline(y=150, line_dash='dash', line_color='#ff7e00', 
                  annotation_text='轻度污染', row=2, col=1)
    
    # 更新布局
    fig.update_layout(
        height=280,
        showlegend=False,
        title_text=f'{city_name} - 历史数据趋势',
        title_x=0.5,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    
    fig.update_xaxes(title_text='', row=2, col=1)
    fig.update_yaxes(title_text='拥堵指数', row=1, col=1, range=[0, 100])
    fig.update_yaxes(title_text='AQI', row=2, col=1, range=[0, 250])
    
    return fig


def create_comparison_chart(
    beijing_data: pd.DataFrame,
    shanghai_data: pd.DataFrame,
    start_date,
    end_date
) -> go.Figure:
    """创建两城市对比图"""
    # 统一日期类型处理
    def to_date(d):
        if hasattr(d, 'date'):
            return d.date()
        return d
    
    start_date_ = to_date(start_date)
    end_date_ = to_date(end_date)
    
    # 筛选日期
    mask_bj = (beijing_data['timestamp'].dt.date >= start_date_) & \
              (beijing_data['timestamp'].dt.date <= end_date_)
    mask_sh = (shanghai_data['timestamp'].dt.date >= start_date_) & \
              (shanghai_data['timestamp'].dt.date <= end_date_)
    
    bj_filtered = beijing_data.loc[mask_bj]
    sh_filtered = shanghai_data.loc[mask_sh]
    
    # 按日期聚合
    bj_daily = bj_filtered.groupby('date').agg({
        'traffic_index': 'mean',
        'aqi': 'mean'
    }).reset_index()
    
    sh_daily = sh_filtered.groupby('date').agg({
        'traffic_index': 'mean',
        'aqi': 'mean'
    }).reset_index()
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('交通拥堵指数对比', '空气质量AQI对比'),
        horizontal_spacing=0.15
    )
    
    # 交通对比
    fig.add_trace(
        go.Scatter(
            x=bj_daily['date'],
            y=bj_daily['traffic_index'],
            name='北京',
            line=dict(color='#e53935', width=2)
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=sh_daily['date'],
            y=sh_daily['traffic_index'],
            name='上海',
            line=dict(color='#1e88e5', width=2)
        ),
        row=1, col=1
    )
    
    # AQI对比
    fig.add_trace(
        go.Scatter(
            x=bj_daily['date'],
            y=bj_daily['aqi'],
            name='北京',
            line=dict(color='#e53935', width=2),
            showlegend=False
        ),
        row=1, col=2
    )
    
    fig.add_trace(
        go.Scatter(
            x=sh_daily['date'],
            y=sh_daily['aqi'],
            name='上海',
            line=dict(color='#1e88e5', width=2),
            showlegend=False
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        height=250,
        title_text='北京 vs 上海 对比分析',
        title_x=0.5,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        )
    )
    
    fig.update_yaxes(title_text='平均拥堵指数', row=1, col=1)
    fig.update_yaxes(title_text='平均AQI', row=1, col=2)
    
    return fig


def render_city_column(city: str, col, selected_date: date_type, data_type: str):
    """渲染单个城市的列"""
    generator = st.session_state.data_generator
    
    # 获取当前数据
    current_data = generator.get_current_data(city)
    
    # 获取区域数据（用于地图）
    district_data = generator.get_district_data(city, selected_date)
    
    # 城市标题
    col.markdown(f"""
    <div class="city-card">
        <h2 style="margin: 0; text-align: center;">🏙️ {city}</h2>
        <p style="margin: 0.5rem 0 0 0; text-align: center; font-size: 0.9rem; opacity: 0.9;">
            当前时间: {current_data['timestamp'].strftime('%Y-%m-%d %H:%M')}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 指标卡片
    metric_col1, metric_col2 = col.columns(2)
    
    # 交通拥堵指数
    traffic_value = current_data['traffic_index']
    traffic_color = get_traffic_color(traffic_value)
    traffic_level = current_data['traffic_level']
    
    metric_col1.markdown(f"""
    <div class="metric-card">
        <div style="font-size: 0.8rem; color: #666;">🚗 交通拥堵指数</div>
        <div style="font-size: 2rem; font-weight: bold;" class="{traffic_color}">{traffic_value}</div>
        <div style="font-size: 0.85rem; margin-top: 0.25rem;">{traffic_level}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # AQI
    aqi_value = current_data['aqi']
    aqi_color = get_aqi_color(aqi_value)
    aqi_level = current_data['aqi_level'][0]
    
    metric_col2.markdown(f"""
    <div class="metric-card">
        <div style="font-size: 0.8rem; color: #666;">🌬️ 空气质量 AQI</div>
        <div style="font-size: 2rem; font-weight: bold;" class="{aqi_color}">{int(aqi_value)}</div>
        <div style="font-size: 0.85rem; margin-top: 0.25rem;">{aqi_level}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # 地图标签页
    if data_type == "交通拥堵指数":
        col.markdown("#### 📍 交通拥堵地图")
        traffic_map = create_traffic_map(city, district_data)
        col.plotly_chart(traffic_map, use_container_width=True, key=f"traffic_{city}")
    elif data_type == "空气质量AQI":
        col.markdown("#### 🌬️ 空气质量地图")
        aqi_map = create_aqi_map(city, district_data)
        col.plotly_chart(aqi_map, use_container_width=True, key=f"aqi_{city}")
    else:
        tab1, tab2 = col.tabs(["📍 交通拥堵地图", "🌬️ 空气质量地图"])
        with tab1:
            traffic_map = create_traffic_map(city, district_data)
            st.plotly_chart(traffic_map, use_container_width=True, key=f"traffic_{city}")
        with tab2:
            aqi_map = create_aqi_map(city, district_data)
            st.plotly_chart(aqi_map, use_container_width=True, key=f"aqi_{city}")
    
    # 历史趋势图
    col.markdown("### 📈 历史数据趋势")
    
    city_data = st.session_state.historical_data[city]
    
    # 计算日期范围（默认显示最近7天）
    end_date = selected_date
    start_date = end_date - timedelta(days=7)
    
    # 可选择的日期范围
    date_range = col.slider(
        "选择日期范围",
        min_value=end_date - timedelta(days=29),
        max_value=end_date,
        value=(start_date, end_date),
        format="YYYY-MM-DD",
        key=f"slider_{city}"
    )
    
    # 绘制时序图
    time_fig = create_time_series_chart(
        city_data, city, date_range[0], date_range[1]
    )
    col.plotly_chart(time_fig, use_container_width=True, key=f"timeseries_{city}")


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.header("⚙️ 设置")
        
        st.markdown("---")
        st.subheader("📅 日期选择")
        
        # 日期选择
        today = datetime.now().date()
        min_date = today - timedelta(days=29)
        
        selected_date = st.date_input(
            "选择查看日期",
            value=today,
            min_value=min_date,
            max_value=today,
            key="main_date"
        )
        
        st.markdown("---")
        st.subheader("🎨 显示设置")
        
        data_type = st.radio(
            "主要数据类型",
            ["交通拥堵指数", "空气质量AQI", "两者都显示"],
            index=2
        )
        
        st.markdown("---")
        st.subheader("🤖 LLM 配置")
        st.caption("OpenAI 兼容 API 格式")
        
        # LLM 配置
        llm_enabled = st.checkbox(
            "启用 LLM 分析",
            value=st.session_state.llm_config['enabled'],
            key="llm_enabled"
        )
        
        if llm_enabled:
            base_url = st.text_input(
                "API Base URL",
                value=st.session_state.llm_config['base_url'],
                placeholder="https://api.openai.com/v1",
                key="llm_base_url"
            )
            
            api_key = st.text_input(
                "API Key",
                value=st.session_state.llm_config['api_key'],
                type="password",
                key="llm_api_key"
            )
            
            model_name = st.text_input(
                "Model Name",
                value=st.session_state.llm_config['model_name'],
                placeholder="gpt-3.5-turbo",
                key="llm_model_name"
            )
            
            # 测试连接按钮
            if st.button("测试连接", key="test_llm"):
                if test_llm_connection(base_url, api_key, model_name):
                    st.success("连接成功！")
                else:
                    st.error("连接失败，请检查配置")
            
            # 更新会话状态
            st.session_state.llm_config.update({
                'enabled': llm_enabled,
                'base_url': base_url,
                'api_key': api_key,
                'model_name': model_name
            })
        else:
            st.session_state.llm_config['enabled'] = False
        
        st.markdown("---")
        st.markdown("### ℹ️ 关于")
        st.info(
            "城市健康状况可视化应用\n\n"
            "数据来源：模拟数据（演示用途）\n"
            "支持城市：北京、上海"
        )
        
        # 刷新数据按钮
        if st.button("🔄 刷新数据", type="primary"):
            st.session_state.data_generator = CityDataGenerator(seed=int(datetime.now().timestamp()))
            st.session_state.historical_data = generate_data_for_cities(days=30)
            st.rerun()
    
    return selected_date, data_type


def test_llm_connection(base_url: str, api_key: str, model_name: str) -> bool:
    """测试LLM连接"""
    if not base_url or not api_key:
        return False
    
    try:
        from openai import OpenAI
        
        client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        
        return True
    except Exception:
        return False


def get_llm_analysis() -> str:
    """获取LLM数据分析"""
    if not st.session_state.llm_config['enabled']:
        return "LLM 分析功能未启用，请在侧边栏配置并启用。"
    
    config = st.session_state.llm_config
    
    if not config['base_url'] or not config['api_key']:
        return "请先配置完整的 LLM API 参数。"
    
    try:
        from openai import OpenAI
        
        client = OpenAI(
            base_url=config['base_url'],
            api_key=config['api_key']
        )
        
        # 准备数据摘要
        generator = st.session_state.data_generator
        cities = generator.get_cities()
        
        data_summary = []
        for city in cities:
            current = generator.get_current_data(city)
            data_summary.append(
                f"{city}: 拥堵指数 {current['traffic_index']} ({current['traffic_level']}), "
                f"AQI {int(current['aqi'])} ({current['aqi_level'][0]})"
            )
        
        prompt = f"""
        请分析以下两个城市的当前健康状况数据：
        
        {chr(10).join(data_summary)}
        
        请给出：
        1. 两个城市的健康状况对比分析
        2. 出行建议
        3. 健康提示（针对空气质量）
        
        请用简洁、友好的语言回答。
        """
        
        response = client.chat.completions.create(
            model=config['model_name'],
            messages=[
                {"role": "system", "content": "你是一个城市健康状况分析专家，擅长分析交通拥堵和空气质量数据。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"LLM 分析出错: {str(e)}"


def main():
    """主应用函数"""
    init_session_state()
    
    # 标题
    st.markdown('<h1 class="main-header">🌆 城市健康状况可视化</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p style="text-align: center; font-size: 1.1rem; color: #666; margin-bottom: 2rem;">'
        '实时监控北京和上海的交通拥堵指数与空气质量 AQI'
        '</p>',
        unsafe_allow_html=True
    )
    
    # 渲染侧边栏
    selected_date, data_type = render_sidebar()
    
    # LLM 分析区域
    if st.session_state.llm_config['enabled']:
        with st.expander("🤖 AI 智能分析", expanded=True):
            col1, col2 = st.columns([4, 1])
            with col2:
                if st.button("生成分析", type="primary", use_container_width=True):
                    with st.spinner("正在分析数据..."):
                        analysis = get_llm_analysis()
                        st.session_state.llm_analysis = analysis
            
            with col1:
                if 'llm_analysis' in st.session_state:
                    st.markdown(st.session_state.llm_analysis)
                else:
                    st.info("点击右侧按钮生成 AI 分析报告")
        
        st.markdown("---")
    
    # 左右分栏布局
    col1, col2 = st.columns(2)
    
    # 渲染北京列
    with col1:
        render_city_column("北京", col1, selected_date, data_type)
    
    # 渲染上海列
    with col2:
        render_city_column("上海", col2, selected_date, data_type)
    
    # 底部对比分析
    st.markdown("---")
    st.markdown("## 📊 跨城市对比分析")
    
    # 对比图表
    beijing_data = st.session_state.historical_data["北京"]
    shanghai_data = st.session_state.historical_data["上海"]
    
    # 日期范围选择
    col_compare1, col_compare2, col_compare3 = st.columns([1, 1, 2])
    
    with col_compare1:
        compare_start = st.date_input(
            "对比开始日期",
            value=datetime.now().date() - timedelta(days=7),
            min_value=datetime.now().date() - timedelta(days=29),
            max_value=datetime.now().date(),
            key="compare_start"
        )
    
    with col_compare2:
        compare_end = st.date_input(
            "对比结束日期",
            value=datetime.now().date(),
            min_value=datetime.now().date() - timedelta(days=29),
            max_value=datetime.now().date(),
            key="compare_end"
        )
    
    # 确保开始日期不晚于结束日期
    if compare_start > compare_end:
        st.warning("开始日期不能晚于结束日期，已自动调换")
        compare_start, compare_end = compare_end, compare_start
    
    # 创建并显示对比图
    compare_fig = create_comparison_chart(
        beijing_data,
        shanghai_data,
        datetime.combine(compare_start, datetime.min.time()),
        datetime.combine(compare_end, datetime.min.time())
    )
    
    st.plotly_chart(compare_fig, use_container_width=True)
    
    # 数据表格
    with st.expander("📋 详细数据表格"):
        # 聚合每日数据
        bj_daily = beijing_data.groupby('date').agg({
            'traffic_index': ['mean', 'min', 'max'],
            'aqi': ['mean', 'min', 'max']
        }).round(1)
        
        sh_daily = shanghai_data.groupby('date').agg({
            'traffic_index': ['mean', 'min', 'max'],
            'aqi': ['mean', 'min', 'max']
        }).round(1)
        
        # 合并数据
        combined = pd.concat(
            [bj_daily, sh_daily],
            keys=['北京', '上海'],
            axis=1
        )
        
        st.dataframe(
            combined,
            use_container_width=True
        )


if __name__ == "__main__":
    main()
