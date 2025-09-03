#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для анализа данных о квартирах и построения гистограмм распределения по площадям
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import font_manager
import io
import base64
import logging

logger = logging.getLogger('ifc-exporter')

# Настройка для поддержки кириллицы в графиках
try:
    # Попытка использовать системные шрифты с поддержкой кириллицы
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Liberation Sans']
    plt.rcParams['axes.unicode_minus'] = False
except:
    pass


class ApartmentAnalyzer:
    """Класс для анализа данных о квартирах"""

    def __init__(self, roominess_data_path='roominess_data.csv'):
        """
        Инициализация анализатора

        :param roominess_data_path: путь к файлу с данными о комнатности
        """
        self.roominess_ranges = self._load_roominess_data(roominess_data_path)

    def _load_roominess_data(self, path=None):
        """
        Загрузка данных о диапазонах площадей для разных типов квартир
        Если файл не найден, используем встроенные данные
        """
        try:
            if path:
                df = pd.read_csv(path, encoding='utf-8')
                return df
        except Exception as e:
            logger.warning(f"Could not load roominess data from {path}: {e}")

        # Встроенные данные о комнатности (на основе предоставленного файла)
        data = {
            'Комнатность': ['СТ-XS', 'СТ-S', 'СТ-М', 'СТ-L', 'СТ-XL',
                            '1К-XS', '1К-S', '1К-М', '1К-L', '1К-XL', '1К-XXL',
                            '2К-XS', '2К-S', '2К-М', '2К-L', '2К-XL', '2К-XXL',
                            '3К-XS', '3К-S', '3К-М', '3К-L', '3К-XL', '3К-XXL',
                            '4К-XS', '4К-S', '4К-М', '4К-L', '4К-XL', '4К-XXL'],
            'min': [17.5, 20, 22.5, 25, 27.5,
                    30, 32.5, 35, 37.5, 40, 42.5,
                    45, 47.5, 50, 52.5, 55, 57.5,
                    60, 62.5, 65, 67.5, 70, 72.5,
                    75, 80, 85, 90, 95, 100],
            'max': [20, 22.5, 25, 27.5, 30,
                    32.5, 35, 37.5, 40, 42.5, 45,
                    47.5, 50, 52.5, 55, 57.5, 60,
                    62.5, 65, 67.5, 70, 72.5, 75,
                    80, 85, 90, 95, 100, 105]
        }
        return pd.DataFrame(data)

    def determine_roominess(self, area, flat_type):
        """
        Определение категории комнатности квартиры

        :param area: площадь квартиры
        :param flat_type: тип квартиры (СТ, 1С, 2С, 3С, 4С)
        :return: категория комнатности (например, '1К-М')
        """
        # Маппинг типов квартир
        type_mapping = {
            'СТ': 'СТ',
            '0С': 'СТ',  # Студии
            '1С': '1К',
            '2С': '2К',
            '3С': '3К',
            '4С': '4К'
        }

        room_type = type_mapping.get(flat_type, '1К')

        # Находим подходящий диапазон
        room_data = self.roominess_ranges[
            self.roominess_ranges['Комнатность'].str.startswith(room_type)
        ]

        for _, row in room_data.iterrows():
            if row['min'] <= area < row['max']:
                return row['Комнатность']

        # Если не нашли точное соответствие, возвращаем ближайший
        if area < room_data.iloc[0]['min']:
            return room_data.iloc[0]['Комнатность']
        else:
            return room_data.iloc[-1]['Комнатность']

    def prepare_histogram_data(self, csv_path):
        """
        Подготовка данных для гистограммы из CSV файла

        :param csv_path: путь к CSV файлу с данными о квартирах
        :return: DataFrame с подготовленными данными
        """
        # Чтение CSV файла
        df = pd.read_csv(csv_path, delimiter=';', encoding='utf-8')

        # Преобразование площади в числовой формат
        if 'Area_m2' in df.columns:
            df['Area_numeric'] = df['Area_m2'].str.replace(',', '.').astype(float)
        else:
            logger.error("Column 'Area_m2' not found in CSV")
            return None

        # Определение комнатности для каждой квартиры
        df['Roominess'] = df.apply(
            lambda row: self.determine_roominess(
                row['Area_numeric'],
                row.get('FlatType', '1С')
            ),
            axis=1
        )

        return df

    def create_histogram(self, df, title="Гистограмма общего ассортимента соответствия рынку"):
        """
        Создание гистограммы распределения квартир по площадям

        :param df: DataFrame с данными о квартирах
        :param title: заголовок графика
        :return: matplotlib figure
        """
        # Создание бинов для гистограммы (с шагом 2.5 м²)
        min_area = 15
        max_area = 150
        bins = np.arange(min_area, max_area + 2.5, 2.5)

        # Подсчет квартир в каждом бине
        hist, bin_edges = np.histogram(df['Area_numeric'], bins=bins)

        # Вычисление процентов
        total = len(df)
        percentages = (hist / total * 100) if total > 0 else hist * 0

        # Создание графика
        fig, ax = plt.subplots(figsize=(16, 8))

        # Определение цветов для разных типов квартир
        colors = []
        labels_for_bins = []

        for i, (left, right) in enumerate(zip(bin_edges[:-1], bin_edges[1:])):
            center = (left + right) / 2

            # Определяем основной тип квартир в этом диапазоне
            mask = (df['Area_numeric'] >= left) & (df['Area_numeric'] < right)
            if mask.any():
                most_common_type = df[mask]['FlatType'].mode()
                if not most_common_type.empty:
                    flat_type = most_common_type.iloc[0]
                else:
                    flat_type = '1С'
            else:
                flat_type = '1С'

            # Цветовая схема по типам квартир
            color_map = {
                'СТ': '#90EE90',  # Светло-зеленый
                '0С': '#90EE90',  # Светло-зеленый (студии)
                '1С': '#FFD700',  # Золотой
                '2С': '#87CEEB',  # Небесно-голубой
                '3С': '#FFB6C1',  # Светло-розовый
                '4С': '#DDA0DD'  # Сливовый
            }

            colors.append(color_map.get(flat_type, '#808080'))
            labels_for_bins.append(f"{left:.1f}-{right:.1f}")

        # Построение столбцов
        bars = ax.bar(bin_edges[:-1], percentages, width=2.5,
                      color=colors, edgecolor='black', linewidth=0.5, alpha=0.7)

        # Добавление значений над столбцами
        for bar, pct in zip(bars, percentages):
            if pct > 0:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2., height,
                        f'{pct:.1f}%', ha='center', va='bottom', fontsize=8)

        # Настройка осей
        ax.set_xlabel('Площадь квартир, м²', fontsize=12)
        ax.set_ylabel('Доля от общего количества, %', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')

        # Настройка оси Y
        ax.set_ylim(0, 15)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1f}%'))

        # Настройка оси X
        ax.set_xlim(min_area, max_area)
        ax.set_xticks(np.arange(min_area, max_area + 5, 5))
        ax.set_xticklabels([f'{x:.0f}' for x in np.arange(min_area, max_area + 5, 5)],
                           rotation=45, ha='right')

        # Создание легенды
        legend_elements = [
            mpatches.Patch(color='#90EE90', label='Студии', alpha=0.7),
            mpatches.Patch(color='#FFD700', label='1-комн.', alpha=0.7),
            mpatches.Patch(color='#87CEEB', label='2-комн.', alpha=0.7),
            mpatches.Patch(color='#FFB6C1', label='3-комн.', alpha=0.7),
            mpatches.Patch(color='#DDA0DD', label='4-комн.', alpha=0.7)
        ]
        ax.legend(handles=legend_elements, loc='upper right')

        # Добавление сетки
        ax.grid(True, axis='y', alpha=0.3)
        ax.set_axisbelow(True)

        # Добавление статистики
        stats_text = f"Всего квартир: {total}\n"
        stats_text += f"Средняя площадь: {df['Area_numeric'].mean():.1f} м²\n"
        stats_text += f"Медиана: {df['Area_numeric'].median():.1f} м²"

        ax.text(0.02, 0.98, stats_text,
                transform=ax.transAxes,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout()
        return fig

    def save_histogram_to_base64(self, fig):
        """
        Сохранение графика в base64 строку для отображения в веб-интерфейсе

        :param fig: matplotlib figure
        :return: base64 строка
        """
        img = io.BytesIO()
        fig.savefig(img, format='png', dpi=100, bbox_inches='tight')
        img.seek(0)
        return base64.b64encode(img.getvalue()).decode()

    def generate_analytics_report(self, df):
        """
        Генерация аналитического отчета по данным о квартирах

        :param df: DataFrame с данными о квартирах
        :return: словарь с аналитикой
        """
        report = {
            'total_apartments': len(df),
            'by_type': df['FlatType'].value_counts().to_dict(),
            'area_stats': {
                'mean': df['Area_numeric'].mean(),
                'median': df['Area_numeric'].median(),
                'min': df['Area_numeric'].min(),
                'max': df['Area_numeric'].max(),
                'std': df['Area_numeric'].std()
            },
            'by_section': df.groupby('Section').size().to_dict() if 'Section' in df.columns else {},
            'by_floor': df.groupby('FloorNum').size().to_dict() if 'FloorNum' in df.columns else {}
        }

        # Распределение по категориям комнатности
        if 'Roominess' in df.columns:
            report['by_roominess'] = df['Roominess'].value_counts().to_dict()

        return report


def process_and_visualize(csv_path, output_path=None):
    """
    Основная функция для обработки CSV и создания визуализации

    :param csv_path: путь к CSV файлу
    :param output_path: путь для сохранения графика (опционально)
    :return: base64 строка с изображением или путь к файлу
    """
    if not MATPLOTLIB_AVAILABLE:
        logger.error("Cannot create visualization - matplotlib not available")
        return None

    analyzer = ApartmentAnalyzer()

    # Подготовка данных
    df = analyzer.prepare_histogram_data(csv_path)
    if df is None:
        logger.error(f"Failed to prepare data from {csv_path}")
        return None

    # Создание гистограммы
    fig = analyzer.create_histogram(df)
    if fig is None:
        logger.error("Failed to create histogram figure")
        return None

    # Сохранение или возврат base64
    if output_path:
        fig.savefig(output_path, dpi=100, bbox_inches='tight')
        plt.close(fig)
        return output_path
    else:
        img_base64 = analyzer.save_histogram_to_base64(fig)
        plt.close(fig)
        return img_base64


if __name__ == "__main__":
    # Пример использования
    import sys

    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else "histogram.png"

        result = process_and_visualize(csv_file, output_file)
        if result:
            print(f"Гистограмма сохранена в {result}")
        else:
            print("Ошибка при создании гистограммы")
    else:
        print("Использование: python apartment_analytics.py <csv_file> [output_file]")