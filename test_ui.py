import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_login():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--disable-web-security")
    options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        print("Navigating to dashboard...")
        driver.get("http://localhost:8080/dashboard.html")
        
        # Wait for the login screen
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "auth-screen"))
        )
        print("Login screen loaded.")
        
        # Enter password
        pw_input = driver.find_element(By.ID, "li-pw")
        pw_input.send_keys("demo")
        
        # Click login button
        login_btn = driver.find_element(By.ID, "li-btn")
        login_btn.click()
        
        print("Login button clicked. Waiting for dashboard overview...")
        
        # Wait for overview page to become visible
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "page-overview"))
        )
        print("Dashboard loaded successfully!")
        
        # Take screenshot of the successful login
        driver.save_screenshot("C:/Users/raghu/.gemini/antigravity-ide/brain/48025fbf-3a82-47c3-94c0-c9da7da2d000/browser/dashboard_login_test_1786378740157_2.webp")
        print("Screenshot saved.")
        
    except Exception as e:
        print("Test failed:", e)
        for entry in driver.get_log('browser'):
            print(entry)
        driver.save_screenshot("C:/Users/raghu/.gemini/antigravity-ide/brain/48025fbf-3a82-47c3-94c0-c9da7da2d000/browser/error.png")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_login()
