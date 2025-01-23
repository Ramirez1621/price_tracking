import pandas as pd
from os.path import join
import os
import datetime as dt


from robot import PATH
from settings import BASE_DIR

def fix_koaj(row):
    return row.split("\n")[0]

def fix_tennis(row):
    return row.replace("\n", "")

def create_dataframe(dataset_path):
    path = join(BASE_DIR, "Backup")
    df_path = join(path, dataset_path)
    with open(df_path, mode='rb') as fp:
        df = pd.read_csv(fp, sep=',', encoding='utf-8', encoding_errors='ignore')
    return df

def create_dataset():

    # df_ae = create_dataframe("dataset_AE.csv")
    # df_koaj = create_dataframe("dataset_KOAJ.csv")
    # df_aerie = create_dataframe("dataset_AERIE.csv")
    # df_nafnaf = create_dataframe("dataset_NAFNAF.csv")
    # df_bershka = create_dataframe("dataset_BERSHKA.csv")
    # df_massimo = create_dataframe("dataset_MASSIMO.csv")
    # df_nauty = create_dataframe("dataset_NAUTY.csv")
    # df_tennis = create_dataframe("dataset_TENNIS.csv")
    df_hm = create_dataframe("dataset_HM.csv")
    # df_pullbear = create_dataframe("dataset_PULLBEAR.csv")
    df_zara = create_dataframe("dataset_ZARA.csv")
    # df_mango = create_dataframe("dataset_MANGO.csv")
    # df_offcorss = create_dataframe("dataset_OFFCORSS.csv")
    # df_arturo = create_dataframe("dataset_ARTURO.csv")
    # df_bronzini = create_dataframe("dataset_BRONZINI.csv")
    # df_polito = create_dataframe("dataset_POLITO.csv")


    # df_ae = df_ae[df_ae["category"] != "Aerie"]

    # df_bershka["fecha"] = dt.datetime.now().strftime("%Y/%m/%d")

    # df_koaj = df_koaj[df_koaj["canal"] == "Koaj Colombia"]
    # df_koaj["fecha"] = dt.datetime.now().strftime("%Y/%m/%d")

    # df_nafnaf["fecha"] = dt.datetime.now().strftime("%Y/%m/%d")
    # df_zara['price'] = df_zara['price'].astype('Str')

    # df_hm["price"] = df_hm.price.apply(lambda x: str(x))
    # df_hm["final_price"] = df_hm.final_price.apply(lambda x: str(x))
    # df_nafnaf["upc"] = df_nafnaf.upc.apply(lambda x: fix_koaj(x))

    # df_tennis["stock"] = df_tennis.stock.apply(lambda x: fix_tennis(x))
    # df_tennis["upc"] = df_tennis.upc.apply(lambda x: fix_tennis(x))
    list_df = [
        # df_ae,
        # df_aerie,
        # df_koaj,
        # df_nafnaf,
        # df_bershka,
        # df_massimo,
        # df_nauty,
        df_hm,
        # df_pullbear,
        # df_tennis,
        # df_polito,
        df_zara,
        # df_mango,
        # df_offcorss,
        # df_arturo,
        # df_bronzini,
    ]
    df = pd.concat(list_df)
    df.drop_duplicates(inplace=True)

    # df["fecha"] = dt.datetime.now().strftime("%Y/%m/%d")

    PATH_DATASET = join(PATH, f"dataset_pricetracking_{dt.datetime.now().strftime('%Y-%m-%d')}.csv")

    df.to_csv(PATH_DATASET, index=False, encoding='UTF-8', sep=',')

    # df.to_csv("dataset_price_tracking_05-01-2024.csv", index=False, encoding='UTF-8', sep=',')


