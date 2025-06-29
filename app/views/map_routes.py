# app/views/map_routes.py

from flask import Blueprint, request, jsonify
import pandas as pd

# 创建一个名为 'map_bp' 的蓝图
map_bp = Blueprint('map_bp', __name__, url_prefix='/map')

# 此变量用于临时存储处理后的数据
PROCESSED_DATA = None


@map_bp.route('/upload', methods=['POST'])
def upload_file():
    global PROCESSED_DATA

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '请求中未包含文件部分'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '未选择任何文件'}), 400

    if file:
        try:
            df = pd.read_excel(file)
            df_renamed = df.rename(columns={
                '经度': 'lng', '纬度': 'lat',
                '污染物浓度': 'concentration', '标记名称': 'name'
            })

            required_columns = ['lng', 'lat', 'concentration', 'name']
            if not all(col in df_renamed.columns for col in required_columns):
                missing = [col for col in required_columns if col not in df_renamed.columns]
                return jsonify({'success': False, 'message': f'Excel文件中缺少必要的列: {", ".join(missing)}'}), 400

            PROCESSED_DATA = df_renamed.to_dict('records')
            return jsonify({'success': True, 'message': f'文件 "{file.filename}" 上传并处理成功!'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'文件解析失败: {str(e)}'}), 500

    return jsonify({'success': False, 'message': '未知错误'}), 500


@map_bp.route('/get-data', methods=['GET'])
def get_data():
    if PROCESSED_DATA is not None:
        data_with_id = [dict(p, id=i) for i, p in enumerate(PROCESSED_DATA)]
        return jsonify({'success': True, 'points': data_with_id})
    else:
        return jsonify({'success': True, 'points': []})
