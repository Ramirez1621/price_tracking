import pandas as pd

# Cargar el archivo CSV
file_path = "/mnt/Disco local/blacksmith/price_tracking/output/diane_geordi_data.csv"  # Ruta al archivo CSV
df = pd.read_csv(file_path)

# Convertir la columna de precios a números (removiendo formato erróneo)
df["price"] = df["price"].replace({",": "", ".": ""}, regex=True).astype(float) / 1000

# Guardar nuevamente el archivo CSV con el formato adecuado
df.to_csv(file_path, index=False, encoding="utf-8-sig", float_format="%.2f")

print("Columna de precios ajustada y archivo guardado.")
