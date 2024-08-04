from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# WebDriver 경로 설정
driver_path = 'C:/Users/leedo/Downloads/chromedriver-win64/chromedriver-win64/chromedriver.exe'  # ChromeDriver 경로
driver = webdriver.Chrome(driver_path)

try:
    # 대상 웹페이지 열기
    driver.get('https://www.trenbe.com/resale/product-registration/brand')
    # 클릭할 요소 찾기
    wait = WebDriverWait(driver, 10)
    clickable_element = wait.until(EC.element_to_be_clickable((By.XPATH, '//div[@data-log-param="eyJicmFuZCI6eyJpZCI6MTY5NjMsIm5hbWUiOiLqtazssIwifX0="]')))

    driver.execute_script("var elem = arguments[0]; var evt = document.createEvent('MouseEvents'); evt.initMouseEvent('click', true, true, window, 1, 0, 0, 0, 0, false, false, false, false, 1, null); elem.dispatchEvent(evt);", clickable_element)

    # 새 탭이 열릴 때까지 기다리기
    wait.until(EC.number_of_windows_to_be(2))

    # 모든 창의 핸들 가져오기
    windows = driver.window_handles

    # 새 탭으로 전환
    driver.switch_to.window(windows[1])


    # 새 탭에서 원하는 작업 수행
    print(driver.current_url)
    # 여기서 추가적인 작업 수행 가능

finally:
    # WebDriver 종료
    driver.quit()
