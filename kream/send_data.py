import os
import paramiko
import pymysql
import traceback
from openpyxl import Workbook
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Define constants
SAVE_PATH = os.environ.get('SAVE_PATH')
SAVE_PATH = SAVE_PATH+'kream/'
UPLOAD_PATH = '/home/luxscan/luxscan/public/xlsx/'
CSV_LIST_PATH = os.path.join(SAVE_PATH, 'csv_list.txt')

DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

TABLE_LIST = [
    'brand', 'category', 'config', 'crawling_product_list', 'market', 
    'price_by_option_of_product', 'product', 'product_sell_history', 'grade'
]

LOG_FILE = SAVE_PATH+'send_data.log'


def log_message(message, log_file=LOG_FILE, type="a", show_date=True):
    """Logs a message to the log file with a timestamp."""
    with open(log_file, type, encoding='euc-kr') as file:
        if show_date:
            file.write(f"{datetime.now()}: {message}\n")
        else:
            file.write(f"{message}\n")


def connect_db():
    """Establishes and returns a connection to the database."""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        log_message(f"Database connection error: {e}")
        raise


def fetch_table_data(cur, table, select='*', join='', where=''):
    """Fetches all rows from the specified table."""
    cur.execute(f"SELECT {select} FROM {table} {join} {where}")
    return cur.fetchall()

def fetch_brand_list(cur):
    """Fetches the list of brands."""
    cur.execute("SELECT b_id, b_name FROM brand")
    return cur.fetchall()

def clean_data(data):
    """Cleans the data by removing illegal characters."""
    if isinstance(data, str):
        # Remove illegal characters
        return re.sub(r'[\000-\010]|[\013-\014]|[\016-\037]', '', data)
    return data


def clean_dataframe(df):
    """Applies the clean_data function to all elements in the dataframe."""
    return df.applymap(clean_data)


def save_to_csv(rows, table):
    """Saves rows to multiple CSV files, chunked by 10000 rows per sheet."""
    results = [pd.DataFrame(rows[i*10000:(i+1)*10000]) for i in range((len(rows) // 10000) + 1)]

    for idx, result in enumerate(results):
        result = clean_dataframe(result)
        csv_path = os.path.join(SAVE_PATH, f"{table}_part_{idx+1}.csv")
        result.to_csv(csv_path, index=False)


def save_to_excel(rows, table):
    """Saves rows to an Excel file, chunked by 10000 rows per sheet."""
    results = [pd.DataFrame(rows[i*10000:(i+1)*10000]) for i in range((len(rows) // 10000) + 1)]
    excel_path = os.path.join(SAVE_PATH, f"{table}.xlsx")

    if os.path.exists(excel_path):
        os.remove(excel_path)

    wb = Workbook()
    ws = wb.active
    ws.title = "result_sheet_1"
    wb.save(excel_path)

    for idx, result in enumerate(results):
        sheet_name = f"result_sheet_{idx+1}"
        result = clean_dataframe(result)
        with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            result.to_excel(writer, sheet_name=sheet_name, index=False)


def send_files_via_sftp():
    """Uploads the files to the remote server via SFTP."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect("43.200.251.231", username="luxscan", password="ld3Iilrn1I!yufRw@IGbm2$")
        log_message("SSH connected")

        ssh.exec_command("rm -rf /home/luxscan/luxscan/public/xlsx/*.csv")

        sftp = ssh.open_sftp()
        csv_list = []
        for file_name in sorted(os.listdir(SAVE_PATH)):
            if file_name.endswith('.csv') or file_name.endswith('.xlsx'):
                local_path = os.path.join(SAVE_PATH, file_name)
                remote_path = os.path.join(UPLOAD_PATH, file_name)

                if os.path.exists(local_path):
                    sftp.put(local_path, remote_path)
                    log_message(f"Uploaded {file_name} successfully.")
                else:
                    log_message(f"File {file_name} not found.")
            if file_name.endswith('.csv'):
                csv_list.append(file_name)
        log_message(','.join(csv_list), type='w+', log_file=CSV_LIST_PATH, show_date=False)
        sftp.put(CSV_LIST_PATH, os.path.join(UPLOAD_PATH, 'csv_list.txt'))

        log_message("SFTP upload completed")

        command = 'cd /home/luxscan/luxscan && npm run build'
        stdin, stdout, stderr = ssh.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            log_message("Build completed successfully")
        else:
            log_message(f"Build failed with exit status {exit_status}")
        
        ssh.close()

    except Exception as e:
        log_message(f"SFTP error: {e}")


def delete_files():
    """Deletes all CSV and XLSX files in the SAVE_PATH directory."""
    os.remove(CSV_LIST_PATH)

    for file_name in os.listdir(SAVE_PATH):
        if file_name.endswith('.csv') or file_name.endswith('.xlsx'):
            os.remove(os.path.join(SAVE_PATH, file_name))
            log_message(f"Deleted {file_name}")


def main():
    """Main function to run the data fetching, saving, and sending process."""
    try:
        log_message("Start bot")

        conn = connect_db()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        brands = fetch_brand_list(cur)
    
        for table in TABLE_LIST:
            if table == 'product':
                for brand in brands:
                    rows = fetch_table_data(cur, table, 'm_name, b_name, p_name, p_name_kr, p_price, p_origin_price, p_count, p_option, p_model_number, p_color, p_url, p_img_url, p_last_crawling_datetime', 'join market on market.m_id = product.m_id join brand on brand.b_id = product.b_id', f'where product.b_id = {brand['b_id']}')

                    if len(rows) > 0:
                        save_to_csv(rows, f'{table}_{brand['b_name']}')
            else:
                rows = fetch_table_data(cur, table)

                save_to_csv(rows, table)

        send_files_via_sftp()
        delete_files()

    except Exception as e:
        log_message(f"Error: {traceback.format_exc()}")
    finally:
        log_message("End bot")
        conn.close()


if __name__ == "__main__":
    main()