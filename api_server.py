from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, date
from data_generator import CityDataGenerator, generate_data_for_cities, get_current_status
import pandas as pd
import numpy as np

app = Flask(__name__)
CORS(app)

generator = CityDataGenerator()

def convert_np_types(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_np_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_np_types(v) for v in obj]
    return obj

@app.route('/api/cities', methods=['GET'])
def get_cities():
    cities = generator.get_cities()
    return jsonify(cities)

@app.route('/api/current/<city>', methods=['GET'])
def get_current_city_data(city):
    try:
        data = generator.get_current_data(city)
        return jsonify(convert_np_types(data))
    except KeyError:
        return jsonify({'error': f'City {city} not found'}), 404

@app.route('/api/district/<city>', methods=['GET'])
def get_district_data(city):
    try:
        date_str = request.args.get('date')
        if date_str:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            selected_date = datetime.now()
        
        data = generator.get_district_data(city, selected_date)
        return jsonify(data.to_dict(orient='records'))
    except KeyError:
        return jsonify({'error': f'City {city} not found'}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/historical/<city>', methods=['GET'])
def get_historical_data(city):
    try:
        days = int(request.args.get('days', 30))
        data = generator.generate_historical_data(city, days=days)
        
        result = []
        for _, row in data.iterrows():
            result.append({
                'timestamp': row['timestamp'].isoformat(),
                'date': str(row['date']),
                'hour': int(row['hour']),
                'traffic_index': float(row['traffic_index']),
                'aqi': float(row['aqi']),
                'city': row['city']
            })
        
        return jsonify(result)
    except KeyError:
        return jsonify({'error': f'City {city} not found'}), 404

@app.route('/api/hourly/<city>', methods=['GET'])
def get_hourly_data(city):
    try:
        date_str = request.args.get('date')
        if date_str:
            start_date = datetime.strptime(date_str, '%Y-%m-%d')
            end_date = start_date
        else:
            end_date = datetime.now()
            start_date = end_date
        
        data = generator.generate_historical_data(
            city, 
            start_date=start_date.replace(hour=0, minute=0, second=0),
            end_date=end_date.replace(hour=23, minute=59, second=59)
        )
        
        hourly_data = []
        for _, row in data.iterrows():
            hourly_data.append({
                'hour': int(row['hour']),
                'traffic_index': float(row['traffic_index']),
                'aqi': float(row['aqi']),
                'timestamp': row['timestamp'].isoformat()
            })
        
        return jsonify(hourly_data)
    except KeyError:
        return jsonify({'error': f'City {city} not found'}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/status', methods=['GET'])
def get_all_status():
    status = get_current_status()
    return jsonify(convert_np_types(status))

@app.route('/api/llm/test', methods=['POST'])
def test_llm_connection():
    try:
        data = request.json
        base_url = data.get('base_url', '')
        api_key = data.get('api_key', '')
        model_name = data.get('model_name', 'gpt-3.5-turbo')
        
        if not base_url or not api_key:
            return jsonify({'success': False, 'error': 'Missing base_url or api_key'})
        
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
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/llm/analyze', methods=['POST'])
def get_llm_analysis():
    try:
        data = request.json
        config = data.get('config', {})
        city_data = data.get('data', {})
        
        if not config.get('enabled'):
            return jsonify({'analysis': 'LLM 分析功能未启用'})
        
        base_url = config.get('base_url', '')
        api_key = config.get('api_key', '')
        model_name = config.get('model_name', 'gpt-3.5-turbo')
        
        if not base_url or not api_key:
            return jsonify({'analysis': '请先配置完整的 LLM API 参数'})
        
        from openai import OpenAI
        
        client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
        
        data_summary = []
        for city, info in city_data.items():
            data_summary.append(
                f"{city}: 拥堵指数 {info.get('traffic_index', 'N/A')} "
                f"({info.get('traffic_level', 'N/A')}), "
                f"AQI {info.get('aqi', 'N/A')} ({info.get('aqi_level', ['N/A'])[0]})"
            )
        
        prompt = f"""
        请分析以下城市的当前健康状况数据：
        
        {chr(10).join(data_summary)}
        
        请给出：
        1. 城市健康状况分析
        2. 出行建议
        3. 健康提示（针对空气质量）
        
        请用简洁、友好的语言回答。
        """
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个城市健康状况分析专家，擅长分析交通拥堵和空气质量数据。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        return jsonify({'analysis': response.choices[0].message.content})
    except Exception as e:
        return jsonify({'analysis': f'LLM 分析出错: {str(e)}'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
