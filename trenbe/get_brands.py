from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium import webdriver
import time
from dotenv import load_dotenv
import os

# 드라이버 종료 함수
def quitDriver(driver):
    try:
        driver.close()
    except Exception as e1:
        pass
    try:
        driver.quit()
    except Exception as e:
        pass

# 환경 변수 로드
load_dotenv()

# 경로 설정
SAVE_PATH = os.environ.get('SAVE_PATH') + 'trenbe/'

# 기본 URL 정의
base_url = "https://www.trenbe.com/used/brands?consonant={}&lang=en"

# 브랜드 정보를 저장할 리스트 생성
brands = []

# 크롬 드라이버 옵션 설정
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("window-size=1920,1080")
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)

# 크롬 드라이버 초기화
exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')
driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
driver.execute_cdp_cmd('Network.setUserAgentOverride', {
    "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
driver.execute_cdp_cmd('Network.enable', {})

# 트렌비 페이지 로드
driver.get('https://www.trenbe.com/brands')
time.sleep(2)

# 중고 브랜드 필터 버튼 클릭
driver.find_element(By.CSS_SELECTOR, '#all-and-used-filter-btn > div.AllUsedFilterToggle__UsedRoundedBtn-sc-13xobwy-3').click()
time.sleep(2)

# 브랜드 정보를 가져오는 함수
def brand_get_type(consonant):
    url = base_url.format(consonant)

    # URL에 GET 요청 보내기
    driver.get(url)
    time.sleep(2)

    # BeautifulSoup로 HTML 콘텐츠 파싱
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # 브랜드 목록이 들어있는 컨테이너 찾기
    container = soup.select_one(".SearchBrandList__BrandListWrap-sc-12rxqu4-0")

    if container:
        # 각 브랜드 정보가 들어있는 div 태그 반복 처리
        for brand_div in container.select("div"):
            # 영어 및 한글 브랜드 이름 추출
            eng_name = brand_div.select_one(".SearchBrandCard__BrandCardMainName-sc-1qk47b7-2")
            kor_name = brand_div.select_one(".SearchBrandCard__BrandCardSubName-sc-1qk47b7-3")

            if eng_name and kor_name:
                brands.append((eng_name.text.strip(), kor_name.text.strip()))

# A부터 Z까지 브랜드 목록 가져오기
for char in range(65, 91):  # ASCII 값 A-Z
    consonant = chr(char)
    brand_get_type(consonant)

# 기타 브랜드 처리
brand_get_type('Etc.')

# 브랜드 정보를 파일에 저장
with open(SAVE_PATH + "brand.txt", "w", encoding="utf-8") as file:
    for eng_name, kor_name in brands:
        file.write(f"{eng_name},{kor_name}\n")

# 드라이버 종료
quitDriver(driver)
