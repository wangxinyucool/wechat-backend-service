# app/__init__.py

from flask import Flask
from flask_cors import CORS


def create_app():
    """
    应用工厂函数
    """
    app = Flask(__name__)

    # 允许所有来源的跨域请求
    CORS(app)

    # 在函数内部导入并注册蓝图
    from .views.calculator_routes import calculator_bp
    from .views.map_routes import map_bp

    app.register_blueprint(calculator_bp)
    app.register_blueprint(map_bp)

    # 提供一个根路由用于健康检查
    @app.route("/")
    def index():
        return "后端服务健康运行中！"

    return app
