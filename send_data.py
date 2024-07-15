import paramiko

from datetime import datetime

import pymysql
import traceback

from openpyxl import Workbook
import pandas as pd

import os
from dotenv import load_dotenv

upload_path = '/home/luxscan/luxscan/public/xlsx/'

load_dotenv()

save_path = os.environ.get('SAVE_PATH')
key_file_path = save_path + 'luxscan_crawling.pem'


DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}


table_list = ['brand', 'category', 'config', 'crawling_product_list', 'market', 'price_by_option_of_product', 'product', 'product_sell_history']

def send_data():
    file = open('crawling_sftp.log', 'a', encoding='euc-kr')
    file.write(f'start sftp at : {datetime.now()}\n')

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    try:
        ssh.connect("43.200.251.231", username="luxscan", key_filename=key_file_path)
        print('ssh connected.')
        file.write("ssh connected")


        sftp = ssh.open_sftp()
        sftp.put(str(save_path), str(upload_path))

        print('sftp upload success.')
        file.write("sftp upload success.")

        command = 'cd /home/luxscan/luxscan && npm run build'

        # 명령어 실행
        stdin, stdout, stderr = ssh.exec_command(command)

        # 빌드 명령어가 완료될 때까지 기다림
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("Build completed successfully")
            file.write("Build completed successfully")
            
        else:
            print(f"Build failed with exit status {exit_status}")
            file.write(f"Build failed with exit status {exit_status}")
        

    except Exception as err:
        print(err)
        file.write(f'sftp error : {err}\n')

    file.write(f'end sftp at : {datetime.now()}\n')    
    ssh.close()
    file.close()


if __name__ =="__main__":
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)

        for table in table_list:
            # Write results to Excel and CSV
            cur.execute(
                "SELECT * FROM "+table
            )
            rows = cur.fetchall()
            result = pd.DataFrame(rows)

            excel_path = save_path + table+'.xlsx'
            csv_path = save_path + table+'.csv'

            if not os.path.exists(excel_path):
                wb = Workbook()
                ws = wb.active
                ws.title = "result_sheet"
                wb.save(excel_path)

            with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                if "result_sheet" in writer.book.sheetnames:
                    idx = writer.book.sheetnames.index("result_sheet")
                    std = writer.book.worksheets[idx]
                    writer.book.remove(std)

                result.to_excel(writer, sheet_name='result_sheet', index=False)

            result.to_csv(csv_path, index=False)

            send_data()
    except Exception:
        err = traceback.format_exc()

    finally:
        conn.close()