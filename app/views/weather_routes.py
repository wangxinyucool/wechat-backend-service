# --- 关键修改：补全所有必需的 import ---
from flask import Blueprint, jsonify, request, Response, current_app
from flask_cors import CORS
import requests
from app.config import settings
# ------------------------------------

from app.services import weather_service

# 1. 创建一个蓝图对象
weather_bp = Blueprint('weather_bp', __name__, url_prefix='/api/weather')
# 对整个蓝图启用CORS，这是一个很好的实践
CORS(weather_bp) 

# 2. 在蓝图上定义路由
@weather_bp.route("/realtime/<string:city_name>", methods=['GET'])
def get_realtime_weather(city_name):
    """
    获取指定城市的实时天气、5天预报和空气质量的聚合数据。
    """
    if not city_name:
        return jsonify({"error": "未提供城市名称"}), 400

    data_bundle = weather_service.get_realtime_weather_bundle(city_name)

    if not data_bundle:
        return jsonify({"error": f"找不到城市 '{city_name}' 的天气数据"}), 404

    return jsonify(data_bundle)


@weather_bp.route("/history/<string:city_name>", methods=['GET'])
def get_history_weather(city_name):
    """
    获取指定城市的历史天气。
    """
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({"error": "缺少'date'参数, 请使用 ?date=YYYY-MM-DD 格式提供"}), 400

    data = weather_service.get_historical_weather(city_name, date_str)
    if data is None:
        return jsonify({"error": f"找不到城市 '{city_name}' 或日期 '{date_str}' 的历史数据"}), 404

    return jsonify(data)


@weather_bp.route("/trends/<string:city_name>", methods=['GET'])
def get_trends_weather(city_name):
    """
    获取指定城市的30天趋势预测数据。
    """
    data = weather_service.get_30_day_forecast(city_name)
    if data is None:
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
        return jsonify({"error": "Invalid layer code"}), 400

    tile_url = f"https://maps.openweathermap.org/maps/2.0/weather/{op}/{z}/{x}/{y}"
    params = {'appid': settings.API_KEY}

    try:
        # 使用 timeout，并恢复为更可靠的非流式请求
        res = requests.get(tile_url, params=params, timeout=(3, 10))
        res.raise_for_status()
        
        # *** 关键修改：修正了 Response 的创建方式 ***
        # 直接使用 res.content 返回完整的图片数据
        response = Response(res.content, content_type=res.headers['Content-Type'])
        
        # 透传缓存头
        if 'Cache-Control' in res.headers:
            response.headers['Cache-Control'] = res.headers['Cache-Control']
        
        return response

    except requests.exceptions.Timeout:
        current_app.logger.error(f"Timeout fetching tile: {tile_url}")
        return jsonify({"error": "Upstream service timeout"}), 504
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Tile proxy failed: {str(e)}")
        return jsonify({"error": "Failed to fetch tile"}), 502
