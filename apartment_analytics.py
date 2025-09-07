import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Используем non-GUI бэкенд
import matplotlib.pyplot as plt
import json
import base64
from io import BytesIO


class ApartmentAnalyzer:
    def __init__(self):
        with open('roominess_data.json', 'r') as f:
            self.roominess_data = json.load(f)

    def prepare_histogram_data(self, csv_path):
        """Подготовка данных для гистограммы из CSV файла"""
        try:
            # Чтение CSV файла
            df = pd.read_csv(csv_path, sep=';', decimal=',')

            # Добавление колонки с размером квартиры
            df['Size'] = df.apply(self._get_size_category, axis=1)

            return df
        except Exception as e:
            print(f"Error preparing data: {e}")
            return None

    def _get_size_category(self, row):
        """Определение категории размера квартиры на основе площади"""
        try:
            area = float(str(row["Area_m2'"]).replace(',', '.'))
            flat_type = row['FlatType']

            # Поиск подходящей категории
            for category in self.roominess_data['roominess_categories']:
                if (category['type'] == flat_type and
                        category['min'] <= area < category['max']):
                    return category['size']

            return 'not valid'
        except:
            return 'not valid'

    def generate_analytics_report(self, df):
        """Генерация аналитического отчета"""
        try:
            # Базовая аналитика
            report = {
                'total_apartments': len(df),
                'by_type': df['FlatType'].value_counts().to_dict(),
                'by_size': df['Size'].value_counts().to_dict(),
                'area_stats': {
                    'mean': df["Area_m2'"].astype(float).mean(),
                    'median': df["Area_m2'"].astype(float).median(),
                    'min': df["Area_m2'"].astype(float).min(),
                    'max': df["Area_m2'"].astype(float).max()
                }
            }

            # Дополнительная группировка по секциям и этажам
            if 'Section' in df.columns:
                report['by_section'] = df['Section'].value_counts().to_dict()

            if 'FloorNum' in df.columns:
                report['by_floor'] = df['FloorNum'].value_counts().to_dict()

            return report
        except Exception as e:
            print(f"Error generating analytics: {e}")
            return {}


def process_and_visualize(csv_path):
    """Создание визуализации распределения квартир"""
    try:
        analyzer = ApartmentAnalyzer()
        df = analyzer.prepare_histogram_data(csv_path)

        if df is None:
            return None

        # Создание гистограммы
        fig, ax = plt.subplots(figsize=(12, 8))

        # Группировка данных по типам и размерам
        grouped = df.groupby(['FlatType', 'Size']).size().unstack(fill_value=0)

        # Цвета для разных типов квартир
        colors = analyzer.roominess_data['colors']

        # Построение stacked bar chart
        bottom = None
        for flat_type in grouped.index:
            counts = grouped.loc[flat_type]
            ax.bar(counts.index, counts.values,
                   label=flat_type,
                   color=colors.get(flat_type, '#888888'),
                   bottom=bottom)
            if bottom is None:
                bottom = counts.values
            else:
                bottom += counts.values

        ax.set_xlabel('Размер квартиры')
        ax.set_ylabel('Количество квартир')
        ax.set_title('Распределение квартир по типам и размерам')
        ax.legend(title='Тип квартиры')
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Конвертация в base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()

        return image_base64

    except Exception as e:
        print(f"Error creating visualization: {e}")
        return None