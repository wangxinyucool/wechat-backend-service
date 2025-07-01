# app/views/calculator_routes.py

from flask import Blueprint, request, jsonify
# 从我们创建的services模块中导入核心逻辑类
from app.services.carbon_estimator import CarbonEstimator

# 创建一个名为 'calculator_bp' 的蓝图
# url_prefix='/api' 表示这个蓝图下所有路由的URL都会以 /api 开头
calculator_bp = Blueprint('calculator_bp', __name__, url_prefix='/api')

# 在蓝图级别实例化计算器
estimator = CarbonEstimator()

@calculator_bp.route('/estimate', methods=['POST'])
def handle_estimation():
    """
    处理来自小程序端的碳排放估算请求。
    这是一个POST接口，接收JSON格式的数据。
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "请求体不能为空"}), 400

        fuel_data = data.get("fuel_data", {})
        electricity_data = data.get("electricity_data", {})

        results = estimator.estimate_total_emissions(fuel_data, electricity_data)
        return jsonify({"success": True, "data": results})

    except Exception as e:
        return jsonify({"success": False, "error": f"服务器内部错误: {str(e)}"}), 500
