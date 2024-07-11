import paramiko

from datetime import datetime

import os
from dotenv import load_dotenv

upload_path = '/home/luxscan/luxscan/public/xlsx/'
csv_file_name = 'kream_test_data.csv'

load_dotenv()

save_path = os.environ.get('SAVE_PATH')
key_file_path = save_path + 'luxscan_crawling.pem'

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
        sftp.put(str(save_path+csv_file_name), str(upload_path+csv_file_name))

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