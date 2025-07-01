from flask import Blueprint, jsonify, request
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

# --- 新增：获取地图图层API路由 ---
@weather_bp.route("/map_layers", methods=['GET'])
def get_map_layers():
    """
    获取所有可用的天气地图图层的URL模板。
    前端将使用这些URL来在地图上渲染天气图层。
    """
    urls = weather_service.get_map_layer_urls()
    return jsonify(urls)