from flask import Blueprint, jsonify, request, Response
import requests
from app.config import settings
# ------------------------------------

from app.services import weather_service

# 1. 创建一个蓝图对象
# 'weather_bp' 是蓝图的名称
# __name__ 是必需的参数
# url_prefix 会给这个蓝图下的所有路由加上统一的前缀
weather_bp = Blueprint('weather_bp', __name__, url_prefix='/api/weather')


# 2. 在蓝图上定义路由
@weather_bp.route("/realtime/<string:city_name>", methods=['GET'])
def get_realtime_weather(city_name):
    """
    获取指定城市的实时天气、5天预报和空气质量的聚合数据。
    这是小程序“实时天气”标签页的核心接口。
    """
    if not city_name:
        return jsonify({"error": "未提供城市名称"}), 400

    data_bundle = weather_service.get_realtime_weather_bundle(city_name)

    if not data_bundle:
        return jsonify({"error": f"找不到城市 '{city_name}' 的天气数据"}), 404

    return jsonify(data_bundle)

# 后续的天气地图、历史数据等其他接口，我们都将在这里添加
# --- 新增：历史天气API路由 ---
@weather_bp.route("/history/<string:city_name>", methods=['GET'])
def get_history_weather(city_name):
    """
    获取指定城市的历史天气。
    日期通过查询参数 'date' 传入, 格式为 YYYY-MM-DD
    示例: /api/weather/history/Shanghai?date=2024-07-01
    """
    # 从URL查询参数中获取 'date'
    date_str = request.args.get('date')

    # 验证参数是否存在
    if not date_str:
        return jsonify({"error": "缺少'date'参数, 请使用 ?date=YYYY-MM-DD 格式提供"}), 400

    # 调用服务函数获取数据
    data = weather_service.get_historical_weather(city_name, date_str)

    if data is None:
        return jsonify({"error": f"找不到城市 '{city_name}' 或日期 '{date_str}' 的历史数据"}), 404

    return jsonify(data)

# --- 新增：30天趋势预测API路由 ---
@weather_bp.route("/trends/<string:city_name>", methods=['GET'])
def get_trends_weather(city_name):
    """
    获取指定城市的30天趋势预测数据。
    示例: /api/weather/trends/Shanghai
    """
    data = weather_service.get_30_day_forecast(city_name)

    if data is None:
        # 复用历史数据的错误信息，或创建一个更通用的
        return jsonify({"error": f"找不到城市 '{city_name}' 的30天趋势数据"}), 404

    return jsonify(data)

@weather_bp.route("/map_layers", methods=['GET'])
def get_map_layers():
    """
    获取所有可用的天气地图图层的URL模板。
    """
    urls = weather_service.get_map_layer_urls()
    return jsonify(urls)


@weather_bp.route("/map_tile/<string:op>/<int:z>/<int:x>/<int:y>", methods=['GET'])
def get_map_tile_proxy(op, z, x, y):
    """
    作为OpenWeatherMap地图瓦片的安全代理。
    """
    valid_ops = ["PR0", "TA2", "CL", "WS10", "APM"]
    if op not in valid_ops:
        return "Invalid layer code", 400

    tile_url = f"https://maps.openweathermap.org/maps/2.0/weather/{op}/{z}/{x}/{y}"
    params = {'appid': settings.API_KEY}

    try:
        res = requests.get(tile_url, params=params)
        res.raise_for_status()
        
        # 创建一个响应对象
        response = Response(res.content, content_type=res.headers['Content-Type'])
        
        # *** 关键修改：手动添加CORS头，允许任何来源读取此响应 ***
        response.headers['Access-Control-Allow-Origin'] = '*'
        
        return response

    except requests.exceptions.RequestException as e:
        print(f"代理请求失败: {e}")
        return "Failed to fetch tile", 502
