# 文件路径: app/services/heatmap_service.py

# ... (请确保所有需要的import语句都在文件顶部) ...
import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.interpolate import Rbf
from pykrige.ok import OrdinaryKriging
from shapely.geometry import Polygon, MultiPolygon
import io
import base64
import os

# --- 全局路径设置 (不变) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROVINCE_DATA_PATH = os.path.join(os.path.dirname(BASE_DIR), 'shanxigeo')


def create_heatmap_image(excel_file, options):
    """
    【最终集大成版】
    - 支持 克里金(kriging) 和 径向基函数(rbf) 插值。
    - 热图被精确地裁剪到不规则边界内。
    - 支持自定义显示范围，并提供一个优秀的默认视野。
    - 支持多种色标选择，默认使用'jet'。
    - 支持自定义数据点标记。
    """
    try:
        # --- 1. 数据读取与准备 ---
        df = pd.read_excel(excel_file)
        points = df[['经度', '纬度']].values
        values = df['污染物浓度'].values

        # --- 2. 动态路径和底图加载 ---
        city_folder = options.get('city', 'taiyuangeo')
        CITY_DATA_PATH = os.path.join(PROVINCE_DATA_PATH, city_folder)
        boundary_gdf = gpd.read_file(os.path.join(CITY_DATA_PATH, 'boundary.geojson'))

        # --- 3. 空间插值计算 ---
        xmin, ymin, xmax, ymax = boundary_gdf.total_bounds
        resolution = options.get('grid_resolution', 200)
        grid_x, grid_y = np.mgrid[xmin:xmax:complex(0, resolution), ymin:ymax:complex(0, resolution)]

        interp_method = options.get('interpolation_method', 'kriging')

        if interp_method == 'kriging':
            OK = OrdinaryKriging(points[:, 0], points[:, 1], values, variogram_model='linear', verbose=False,
                                 enable_plotting=False)
            gridx_1d = np.linspace(xmin, xmax, resolution)
            gridy_1d = np.linspace(ymin, ymax, resolution)
            grid_z, ss = OK.execute('grid', gridx_1d, gridy_1d)
            grid_z = grid_z.T
        elif interp_method == 'rbf':
            rbfi = Rbf(points[:, 0], points[:, 1], values, function='multiquadric', smooth=0)
            grid_z = rbfi(grid_x, grid_y)
        else:
            OK = OrdinaryKriging(points[:, 0], points[:, 1], values, variogram_model='linear', verbose=False,
                                 enable_plotting=False)
            gridx_1d = np.linspace(xmin, xmax, resolution)
            gridy_1d = np.linspace(ymin, ymax, resolution)
            grid_z, ss = OK.execute('grid', gridx_1d, gridy_1d)
            grid_z = grid_z.T

        # --- 4. 开始绘图 ---
        fig, ax = plt.subplots(figsize=(12, 12), dpi=150)
        ax.set_aspect('equal')
        # 【修改点1】色标选择，默认'jet'
        colormap = options.get('colormap', 'jet')
        heatmap = ax.imshow(
            grid_z.T, extent=(xmin, xmax, ymin, ymax), origin='lower',
            cmap=colormap, interpolation='bilinear'
        )

        # --- 5. 裁剪与图层绘制 ---
        clip_geom = boundary_gdf.geometry.iloc[0]
        clipping_path_polygon = None
        if isinstance(clip_geom, Polygon):
            clipping_path_polygon = plt.Polygon(clip_geom.exterior.coords, transform=ax.transData)
        elif isinstance(clip_geom, MultiPolygon):
            largest_polygon = max(clip_geom.geoms, key=lambda p: p.area)
            clipping_path_polygon = plt.Polygon(largest_polygon.exterior.coords, transform=ax.transData)

        if clipping_path_polygon:
            heatmap.set_clip_path(clipping_path_polygon)

        for layer_name in options.get('map_layers', []):
            layer_path = os.path.join(CITY_DATA_PATH, f"{layer_name}.geojson")
            if os.path.exists(layer_path):
                layer_gdf = gpd.read_file(layer_path)
                if 'road' in layer_name or 'highway' in layer_name:
                    layer_gdf.plot(ax=ax, edgecolor='#4a4a4a', linewidth=0.4, alpha=0.7, zorder=3)
                elif 'water' in layer_name or 'river' in layer_name:
                    layer_gdf.plot(ax=ax, edgecolor='#3498db', facecolor='#3498db', linewidth=0.8, alpha=0.6, zorder=2)
                elif 'rail' in layer_name:
                    layer_gdf.plot(ax=ax, edgecolor='#5e5e5e', linewidth=0.4, linestyle='--', zorder=3)
                else:
                    layer_gdf.plot(ax=ax, edgecolor='white', facecolor='none', linewidth=0.6, linestyle=':', zorder=2)

        boundary_gdf.plot(ax=ax, edgecolor='black', facecolor='none', linewidth=1.5, zorder=5)

        if options.get('show_points', False):
            point_size = options.get('point_size', 20)
            ax.scatter(points[:, 0], points[:, 1], s=point_size, c='black', edgecolors='white', linewidths=0.5,
                       zorder=10)

        # --- 6. 设置图表样式和范围 ---
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        ax.set_title("污染物浓度空间插值热力图", fontsize=18)
        fig.colorbar(heatmap, ax=ax, label='污染物浓度', shrink=0.75)

        # 【修改点2】灵活的显示范围设置
        # 检查前端是否传递了自定义范围
        if 'extent' in options and options.get('extent'):
            extent = options['extent']
            # 确保所有坐标都存在
            if all(k in extent for k in ['xmin', 'xmax', 'ymin', 'ymax']):
                ax.set_xlim(extent['xmin'], extent['xmax'])
                ax.set_ylim(extent['ymin'], extent['ymax'])
        else:
            # 如果没有，则使用您指定的默认固定范围
            ax.set_xlim(111.4, 113.3)
            ax.set_ylim(37.2, 38.5)

        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_facecolor('white')
        fig.set_facecolor('white')

        # --- 7. 输出图片 ---
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.05, facecolor=fig.get_facecolor(),
                    transparent=True)
        buf.seek(0)
        image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close(fig)

        return image_base64

    except Exception as e:
        print(f"ERROR in heatmap_service: {e}")
        return None