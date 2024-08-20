import pandas as pd
import pymysql
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()

# Load the Excel file into a pandas DataFrame
file_path = './bunjangData.xlsx'  # Change this to your actual file path
sheet_name = '통합본'
df = pd.read_excel(file_path, sheet_name=sheet_name)

# Set up database connection using SQLAlchemy
db_config = {
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'host': os.environ.get('HOST'),
    'database': os.environ.get('DB_TABLE')
}

engine = create_engine(f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}/{db_config['database']}")

# Process and clean data as required
try:
    df['price'] = df['price'].replace({'₩': '', ',': '', '-':''}, regex=True).astype(int)
except Exception:
    df['price'] = 0
df['transaction_count'] = df['transaction_count'].astype(int)
df['m_id'] = 6  # Assuming m_id is fixed as 6
df['p_count'] = df['transaction_count']

# Rename DataFrame columns to match database table
df = df.rename(columns={
    'brand': 'p_option',
    'name': 'p_name_kr',
    'price': 'p_price',
    'img_url': 'p_img_url',
    'url' : 'p_url'
})

# Reorder columns to match the database table
df = df[['m_id', 'p_name_kr', 'p_price', 'p_count', 'p_url', 'p_img_url']]

# Insert data into the table using SQLAlchemy
df.to_sql('bunjang_product', con=engine, if_exists='replace', index=True)

print("Data inserted successfully")