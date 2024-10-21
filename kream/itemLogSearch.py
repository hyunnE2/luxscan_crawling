import time
import re
import pymysql
import pymysql.cursors
import traceback

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementNotInteractableException, NoSuchElementException
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
import os

# 환경 변수를 로드
load_dotenv()

# URL과 DB 설정을 환경 변수에서 불러옴
base_url = os.environ.get('KREAM_URL')
DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

# 크롤링에 필요한 경로와 로그인 정보 설정
SAVE_PATH = os.environ.get('SAVE_PATH') + 'kream/'
crawling_id = os.environ.get('CRAWLING_ID')
crawling_pw = os.environ.get('CRAWLING_PW')

# 드라이버 종료 함수
def quitDriver(driver):
    try:
        driver.close()
    except Exception:
        pass
    try:
        driver.quit()
    except Exception:
        pass

# 로그 파일을 작성
file = open(SAVE_PATH + 'itemLogSearch.log', 'a', encoding='euc-kr')
file.write(f'start bot2 at : {datetime.now()}\n')

# 크롬 드라이버 옵션 설정
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

# 크롬 드라이버 초기화
exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')
driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
driver.execute_cdp_cmd('Network.enable', {})

# 크롤링 진행을 위한 변수
last_cpl_id = 0

try:
    # Kream 사이트 로그인
    driver.get(base_url + '/login')
    time.sleep(2)
    # F12를 열어 ID INPUT 칸의 XPATH를 가져와야 함
    id = driver.find_element(By.XPATH, '//*[@id="wrap"]/div[3]/div/form/div[1]/div/input')
    id.send_keys(crawling_id)
    pw = driver.find_element(By.XPATH, '//*[@id="wrap"]/div[3]/div/form/div[2]/div/input')
    pw.send_keys(crawling_pw)
    driver.find_element(By.XPATH, '//*[@id="wrap"]/div[3]/div/form/div[3]/button').click()
    time.sleep(2)

    # 데이터베이스 연결 설정
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # SQL 모드에서 ONLY_FULL_GROUP_BY 제거
    cur.execute('SET SESSION sql_mode=(SELECT REPLACE(@@sql_mode,\'ONLY_FULL_GROUP_BY\',\'\'))')

    # 크롤링할 상품 목록 가져오기
    cur.execute('SELECT product.p_id as p_id, cpl_id, p_url FROM crawling_product_list '
                'JOIN product ON crawling_product_list.p_id = product.p_id '
                'ORDER BY cpl_id ASC LIMIT 200')
    crawling_items = cur.fetchall()

    # 각 상품에 대해 크롤링 시작
    for crawling_item in crawling_items:
        count = 0
        file.write(f'bot2 crawling url : {crawling_item["p_url"]}\n')

        # 상품 페이지 접속
        driver.get(crawling_item['p_url'])
        time.sleep(2)

        # 상세 페이지 열기 시도
        try:
            driver.find_element(By.CSS_SELECTOR, '.tab_content > .outlinegrey').click()
        except ElementNotInteractableException:
            continue
        except NoSuchElementException:
            # 존재하지 않는 상품의 경우 목록에서 삭제
            cur.execute('DELETE FROM crawling_product_list WHERE cpl_id = %s', (crawling_item['cpl_id']))
            file.write(f"NoSuch Error for cpl_id: {crawling_item['cpl_id']}\n")
            conn.commit()
            continue

        # 판매 내역 데이터 가져오기
        cur.execute(f'SELECT COUNT(*) as count, DATE(psh_sold_datetime) as psh_sold_datetime FROM product_sell_history WHERE p_id = {crawling_item["p_id"]} GROUP BY psh_sold_datetime ORDER BY psh_sold_datetime DESC')
        last_data = cur.fetchone()

        if last_data is None:
            last_data = {'psh_sold_datetime': datetime.strptime('2000-01-01', '%Y-%m-%d')}
            count = 0
        else:
            last_data['psh_sold_datetime'] = datetime.strptime(str(last_data['psh_sold_datetime']), '%Y-%m-%d')
            count = int(last_data['count'])

        scrollItem = driver.find_element(By.CSS_SELECTOR, '.market_price_table > .price_body')

        tmp = -1
        scrollY = 0

        # 스크롤을 통해 더 많은 데이터 로드
        while tmp != scrollY:
            isbreak = False
            scrollY += 8000
            tmp = driver.execute_script(f'arguments[0].scrollTo(0, {scrollY}); return arguments[0].scrollHeight', scrollItem)
            time.sleep(0.6)
            scrollY = driver.execute_script(f'arguments[0].scrollTo(0, {scrollY}); return arguments[0].scrollHeight', scrollItem)

            # BeautifulSoup로 HTML 파싱
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            browser_items = soup.select('.price_body > .body_list > .list_txt:nth-child(3) > span')

            # 날짜 확인 및 중지 여부 체크 중복 체크를 위한 기능
            for i in browser_items:
                date = datetime.strptime('20' + i.text.replace('/', '-'), '%Y-%m-%d')
                if date > last_data['psh_sold_datetime']:
                    isbreak = True
                    break

            if isbreak:
                break

        # 데이터 수집
        browser_items = soup.select('.price_body > .body_list')
        insert_items = []

        for item in browser_items:
            txt_list = item.select('.list_txt')
            option = txt_list[0].text
            price = re.sub(r'[,\s원-]', '', txt_list[1].text)
            price = int(price) if price != "" else 0
            date = ('20' + txt_list[2].select('span')[-1].text).replace('/', '-')
            quickly = 0 if item.select_one('.express_icon') != None else 1
            insert_items.append({'option': option, 'price': price, 'date': date, 'quickly': quickly})

        # 수집된 데이터를 정렬 후 DB에 삽입
        sorted_items = sorted(insert_items, key=lambda item: item['date'])

        for item in sorted_items:
            date = datetime.strptime(item['date'], '%Y-%m-%d')
            if date < last_data['psh_sold_datetime']:
                continue
            elif date == last_data['psh_sold_datetime'] and count > 0:
                count -= 1
                continue

            sql = (f'INSERT INTO product_sell_history(p_id, psh_option, psh_price, psh_is_quickly, psh_sold_datetime) VALUES ({crawling_item["p_id"]}, "{item["option"]}", {item["price"]}, {item["quickly"]}, "{item["date"]}")')
            cur.execute(sql)
            conn.commit()

        # 크롤링 완료된 상품 삭제
        last_cpl_id = crawling_item["cpl_id"]
        cur.execute('DELETE FROM crawling_product_list WHERE cpl_id = %s', (crawling_item['cpl_id']))
        conn.commit()

    # 크롤링된 상품 삭제
    if len(crawling_items) > 0:
        file.write(f'bot2 : delete smaller than {last_cpl_id}\n')
        cur.execute(f'DELETE FROM crawling_product_list WHERE cpl_id <= {last_cpl_id}')
    else:
        file.write(f'bot2 : truncated\n')
        cur.execute(f'TRUNCATE crawling_product_list')

    conn.commit()

except Exception:
    # 오류 발생 시 처리
    err = traceback.format_exc()
    file.write(f'error bot2 : {err}\n')
    cur.execute(f'DELETE FROM crawling_product_list WHERE cpl_id <= {last_cpl_id}')
    conn.commit()

finally:
    # 종료 처리
    file.write(f'end bot2 at : {datetime.now()}\n\n')
    file.close()
    quitDriver(driver)
    conn.close()
