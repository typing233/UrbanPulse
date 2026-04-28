import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


class CityDataGenerator:
    """城市数据生成器 - 模拟交通拥堵指数和AQI数据"""
    
    # 城市基础配置
    CITY_CONFIG = {
        "北京": {
            "lat": 39.9042,
            "lon": 116.4074,
            "base_traffic": 65,  # 基础拥堵指数
            "base_aqi": 85,      # 基础AQI
            "traffic_volatility": 15,
            "aqi_volatility": 20,
        },
        "上海": {
            "lat": 31.2304,
            "lon": 121.4737,
            "base_traffic": 55,
            "base_aqi": 65,
            "traffic_volatility": 12,
            "aqi_volatility": 15,
        }
    }
    
    # 区域配置（用于地图显示）
    DISTRICT_CONFIG = {
        "北京": [
            {"name": "朝阳区", "lat": 39.9222, "lon": 116.4860, "weight": 1.3},
            {"name": "海淀区", "lat": 39.9590, "lon": 116.2982, "weight": 1.2},
            {"name": "东城区", "lat": 39.9160, "lon": 116.4100, "weight": 1.0},
            {"name": "西城区", "lat": 39.9130, "lon": 116.3660, "weight": 1.0},
            {"name": "丰台区", "lat": 39.8620, "lon": 116.2860, "weight": 0.9},
        ],
        "上海": [
            {"name": "浦东新区", "lat": 31.2304, "lon": 121.5050, "weight": 1.3},
            {"name": "黄浦区", "lat": 31.2304, "lon": 121.4737, "weight": 1.2},
            {"name": "徐汇区", "lat": 31.1910, "lon": 121.4360, "weight": 1.1},
            {"name": "静安区", "lat": 31.2270, "lon": 121.4480, "weight": 1.0},
            {"name": "长宁区", "lat": 31.2190, "lon": 121.4250, "weight": 0.9},
        ]
    }
    
    def __init__(self, seed: int = 42):
        np.random.seed(seed)
        self._generate_baseline_patterns()
    
    def _generate_baseline_patterns(self):
        """生成基础的时间模式（日/周/季节）"""
        # 日模式：早高峰(7-9)和晚高峰(17-19)
        self.hourly_traffic_pattern = np.array([
            0.3, 0.2, 0.15, 0.15, 0.2, 0.3, 0.5, 0.8, 0.9, 0.7, 0.6, 0.5,
            0.5, 0.5, 0.6, 0.7, 0.85, 0.95, 0.9, 0.7, 0.5, 0.4, 0.35, 0.3
        ])
        
        # 周模式：工作日比周末拥堵
        self.weekly_traffic_pattern = np.array([1.0, 1.02, 0.98, 1.05, 1.1, 0.7, 0.65])
        
        # 季节模式：冬季AQI较高
        self.seasonal_aqi_pattern = np.array([
            1.3, 1.2, 1.1, 1.0, 0.9, 0.8, 0.75, 0.8, 0.9, 1.0, 1.15, 1.25
        ])
    
    def generate_historical_data(
        self,
        city: str,
        start_date: datetime = None,
        end_date: datetime = None,
        days: int = 30
    ) -> pd.DataFrame:
        """
        生成历史数据
        
        Args:
            city: 城市名称
            start_date: 开始日期
            end_date: 结束日期
            days: 数据天数（如果未指定开始/结束日期）
            
        Returns:
            包含时间序列数据的DataFrame
        """
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=days)
        
        config = self.CITY_CONFIG[city]
        
        # 生成每小时的时间戳
        date_range = pd.date_range(
            start=start_date,
            end=end_date,
            freq='h'
        )
        
        data = []
        for timestamp in date_range:
            hour = timestamp.hour
            day_of_week = timestamp.weekday()
            month = timestamp.month
            
            # 计算交通拥堵指数
            traffic = self._calculate_traffic(
                config, hour, day_of_week, timestamp
            )
            
            # 计算AQI
            aqi = self._calculate_aqi(
                config, month, day_of_week, timestamp
            )
            
            data.append({
                'timestamp': timestamp,
                'date': timestamp.date(),
                'hour': hour,
                'traffic_index': round(traffic, 1),
                'aqi': round(aqi, 0),
                'city': city
            })
        
        return pd.DataFrame(data)
    
    def _calculate_traffic(
        self,
        config: Dict,
        hour: int,
        day_of_week: int,
        timestamp: datetime
    ) -> float:
        """计算交通拥堵指数"""
        base = config['base_traffic']
        volatility = config['traffic_volatility']
        
        # 应用时间模式
        pattern_factor = self.hourly_traffic_pattern[hour]
        weekly_factor = self.weekly_traffic_pattern[day_of_week]
        
        # 随机波动
        random_noise = np.random.normal(0, volatility * 0.15)
        
        # 趋势项：假设随时间有轻微变化
        days_since_start = (timestamp - datetime(2024, 1, 1)).days
        trend = days_since_start * 0.005
        
        traffic = base * pattern_factor * weekly_factor + random_noise + trend
        
        # 限制在合理范围内
        return max(0, min(100, traffic))
    
    def _calculate_aqi(
        self,
        config: Dict,
        month: int,
        day_of_week: int,
        timestamp: datetime
    ) -> float:
        """计算AQI"""
        base = config['base_aqi']
        volatility = config['aqi_volatility']
        
        # 应用季节模式
        seasonal_factor = self.seasonal_aqi_pattern[month - 1]
        
        # 周末AQI稍低（交通减少）
        weekend_factor = 0.9 if day_of_week >= 5 else 1.0
        
        # 随机波动
        random_noise = np.random.normal(0, volatility * 0.2)
        
        # 连续几天的趋势（模拟污染累积/消散）
        auto_correlation = np.random.normal(0, volatility * 0.1)
        
        aqi = base * seasonal_factor * weekend_factor + random_noise + auto_correlation
        
        # 限制在合理范围内
        return max(0, min(500, aqi))
    
    def get_current_data(self, city: str) -> Dict:
        """获取当前实时数据"""
        now = datetime.now()
        config = self.CITY_CONFIG[city]
        
        hour = now.hour
        day_of_week = now.weekday()
        month = now.month
        
        traffic = self._calculate_traffic(config, hour, day_of_week, now)
        aqi = self._calculate_aqi(config, month, day_of_week, now)
        
        return {
            'city': city,
            'timestamp': now,
            'traffic_index': round(traffic, 1),
            'aqi': round(aqi, 0),
            'lat': config['lat'],
            'lon': config['lon'],
            'traffic_level': self._get_traffic_level(traffic),
            'aqi_level': self._get_aqi_level(aqi)
        }
    
    def get_district_data(self, city: str, date: datetime = None) -> pd.DataFrame:
        """获取各区域数据（用于地图展示）"""
        if date is None:
            date = datetime.now()
        
        districts = self.DISTRICT_CONFIG[city]
        city_config = self.CITY_CONFIG[city]
        
        # 使用日期和城市名生成确定性随机种子，确保同一日期结果一致
        if hasattr(date, 'toordinal'):
            date_seed = date.toordinal()
        else:
            date_seed = date.date().toordinal()
        rng = np.random.default_rng(hash(f'{city}_{date_seed}') % (2**32))
        
        data = []
        for district in districts:
            # 基于区域权重和城市基础数据计算
            traffic_base = city_config['base_traffic'] * district['weight']
            aqi_base = city_config['base_aqi'] * district['weight']
            
            # 添加一些随机性
            traffic = traffic_base + rng.normal(0, 10)
            aqi = aqi_base + rng.normal(0, 15)
            
            data.append({
                'district': district['name'],
                'lat': district['lat'],
                'lon': district['lon'],
                'traffic_index': round(max(0, min(100, traffic)), 1),
                'aqi': round(max(0, min(500, aqi)), 0),
                'traffic_level': self._get_traffic_level(traffic),
                'aqi_level': self._get_aqi_level(aqi)[0]
            })
        
        return pd.DataFrame(data)
    
    def _get_traffic_level(self, traffic: float) -> str:
        """根据拥堵指数获取拥堵等级"""
        if traffic < 30:
            return "畅通"
        elif traffic < 50:
            return "基本畅通"
        elif traffic < 70:
            return "轻度拥堵"
        elif traffic < 90:
            return "中度拥堵"
        else:
            return "严重拥堵"
    
    def _get_aqi_level(self, aqi: float) -> Tuple[str, str]:
        """根据AQI获取空气质量等级和颜色"""
        if aqi <= 50:
            return ("优", "#00e400")
        elif aqi <= 100:
            return ("良", "#ffff00")
        elif aqi <= 150:
            return ("轻度污染", "#ff7e00")
        elif aqi <= 200:
            return ("中度污染", "#ff0000")
        elif aqi <= 300:
            return ("重度污染", "#99004c")
        else:
            return ("严重污染", "#7e0023")
    
    def get_cities(self) -> List[str]:
        """获取支持的城市列表"""
        return list(self.CITY_CONFIG.keys())


# 便捷函数
def generate_data_for_cities(cities: List[str] = None, days: int = 30) -> Dict[str, pd.DataFrame]:
    """
    为多个城市生成数据
    
    Args:
        cities: 城市列表，默认使用所有配置城市
        days: 数据天数
        
    Returns:
        城市名到数据DataFrame的映射
    """
    generator = CityDataGenerator()
    
    if cities is None:
        cities = generator.get_cities()
    
    result = {}
    for city in cities:
        result[city] = generator.generate_historical_data(city, days=days)
    
    return result


def get_current_status() -> Dict[str, Dict]:
    """获取所有城市的当前状态"""
    generator = CityDataGenerator()
    result = {}
    for city in generator.get_cities():
        result[city] = generator.get_current_data(city)
    return result
