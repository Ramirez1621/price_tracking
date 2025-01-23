import pandas as pd
import re
import datetime as dt

from os.path import join

from ..processing.utils import create_dataset
from  settings import BASE_DIR, REPORT_DIR, REPORT_NAME
from robot import PATH

def homolagated_data() -> str:

    create_dataset()
    homolagated_report = join(BASE_DIR, REPORT_DIR, REPORT_NAME)

    # ------------------------------------------------------------------------------------------------ #
    #                                    Homologación de categorías                                    #
    # ------------------------------------------------------------------------------------------------ #
    with open(homolagated_report, mode='rb') as fp:
        df_homologated_categories = pd.read_excel(fp, engine="openpyxl", sheet_name=0)

    dataset_path = join(PATH, f"dataset_pricetracking_{dt.datetime.now().strftime('%Y-%m-%d')}.csv")
    # dataset_path = r"C:\Users\John Eduard\OneDrive - Blacksmith Research\BlackSmith Reasearch\RPA\Price_tracking_moda\dataset_price_tracking_05-01-2024 (2).csv"

    with open(dataset_path, mode='rb') as fp:
        df_dataset = pd.read_csv(fp, sep=',', encoding='utf-8', encoding_errors='ignore', dtype={})

    df_dataset['sale_price'] = pd.to_numeric(df_dataset['sale_price'], errors='coerce').astype('Int64')

    columns_names = {'Marca': 'canal', 'Category': 'category', 'Subcategory': 'subcategory', 'subcategory2': 'subcategory_2', 'subcategory3': 'subcategory_3'}
    df_homologated_categories = df_homologated_categories.rename(columns=columns_names)

    # df_dataset = df_dataset.merge(df_homologated_categories[['canal', 'category', 'subcategory', 'subcategory2', 'subcategory3', 'homogenized_clothing', 'homogenized_subcategory', 'homogenized_category']], 
    #             left_on=['canal', 'category', 'subcategory', 'subcategory_2', 'subcategory_3'],
    #             right_on=['canal', 'category', 'subcategory', 'subcategory2', 'subcategory3'],
    #             how='left')
    
    df_dataset = df_dataset.merge(df_homologated_categories[['canal', 'category', 'subcategory', 'subcategory_2', 'subcategory_3', 'item', 'homogenized_clothing', 'homogenized_subcategory', 'homogenized_category']], 
                on=['canal', 'category', 'subcategory', 'subcategory_2', 'subcategory_3', 'item'],
                how='left')
    # df_dataset.drop(['Marca', 'Category', 'Subcategory', 'Subcategory2', 'Subcategory3'], axis=1, inplace=True)

    df_dataset.loc[:,['homogenized_clothing', 'homogenized_subcategory', 'homogenized_category']] = df_dataset.loc[:,['homogenized_clothing', 'homogenized_subcategory', 'homogenized_category']].fillna("S/H")

    df_dataset['homogenized_category'] = df_dataset.apply(search_replace, axis=1)
    
    # ------------------------------------------------------------------------------------------------ #
    #                                      Homologación de colores                                     #
    # ------------------------------------------------------------------------------------------------ #
    with open(homolagated_report, mode='rb') as fp:
        df_homologated_colors = pd.read_excel(fp, engine="openpyxl", sheet_name=1)
    
    columns_names = {'MARCA': 'canal', 'Color original ': 'modelo'}
    df_homologated_colors = df_homologated_colors.rename(columns=columns_names)

    # Convert colors words in lowercase
    df_dataset['modelo'] = df_dataset['modelo'].str.lower()
    df_homologated_colors['modelo'] = df_homologated_colors['modelo'].str.lower()

    df_dataset = df_dataset.merge(df_homologated_colors[['canal', 'modelo', 'homogenized_color']], 
                on=['canal', 'modelo'],
                how='left')
    
    # df_dataset.drop(['MARCA', 'Color original '], axis=1, inplace=True)

    df_dataset.loc[:, ['homogenized_color']] = df_dataset.loc[:, ['homogenized_color']].fillna("S/H")

    df_dataset['homogenized_color'] = df_dataset.apply(lambda x: color_rules(x, df_homologated_colors), axis=1)

    # ------------------------------------------------------------------------------------------------ #
    #                             Generar el archivo con las homologaciones                            #
    # ------------------------------------------------------------------------------------------------ #
    
    HOMOLOGATED_DATASET = dataset_path.replace('.csv', '-homologado.csv')

    df_dataset.to_csv(HOMOLOGATED_DATASET, index=False, encoding='UTF-8', sep=',')
    


def search_replace(row):
    if row['homogenized_category'] == 'S/H':
        category = row['category'].lower()
        if 'hombre' in category or 'hombres' in category or 'man' in category or 'men' in category:
            return 'Hombre'
        elif 'mujer' in category or 'mujeres' in category or 'woman' in category or 'women' in category:
            return 'Mujer'
        else:
            return row['homogenized_category']
    else:
        return row['homogenized_category']
    
def color_rules(row, df_colors):
    if row['homogenized_color'] == 'S/H':
        
        color = str(row['modelo'])
        slash = re.findall(r'[/]', color)
        dash = re.findall(r'[-]', color)
        underscore = re.findall(r'[_]', color)

        if len(slash) > 0 :
            split_caracter = slash[0]
        elif len(dash) > 0 :
            split_caracter = dash[0]
        elif len(underscore) > 0 :
            split_caracter = underscore[0]
        else:
            return 'S/H'

        colors = color.split(split_caracter)

        list_colors = [c.lower() for c in df_colors["homogenized_color"].to_list()]
        if len(colors) == 2 and colors[0].lower() in list_colors:
            return colors[0]
        elif len(colors) >= 3:
            return 'Multicolor'
        else:
            return row['homogenized_color']
    else:
        return row['homogenized_color']
