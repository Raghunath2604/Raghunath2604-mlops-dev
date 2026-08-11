import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_rbac():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--disable-web-security")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        print("Navigating to dashboard...")
        driver.get("http://localhost:8080/dashboard.html")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "auth-screen")))
        
        # Register a new user
        print("Switching to Request Access tab...")
        # Since I didn't change the switchTab logic, I can just click the tab
        tabs = driver.find_elements(By.CLASS_NAME, "atab")
        tabs[1].click() # Click 'Request Access'
        
        time.sleep(1)
        driver.find_element(By.ID, "ri-name").send_keys("Test User")
        driver.find_element(By.ID, "ri-email").send_keys("test@example.com")
        driver.find_element(By.ID, "ri-pw").send_keys("password123")
        driver.find_element(By.ID, "ri-btn").click()
        
        print("Waiting for registration success...")
        WebDriverWait(driver, 5).until(
            EC.text_to_be_present_in_element((By.ID, "reg-err"), "Success!")
        )
        print("Registration successful (pending admin approval).")
        
        # Now try to login as test user, it should fail
        tabs[0].click() # Back to Login
        time.sleep(1)
        driver.find_element(By.ID, "li-email").clear() # If any
        driver.find_element(By.ID, "li-pw").clear()
        driver.find_element(By.ID, "li-pw").send_keys("password123")
        driver.find_element(By.ID, "li-btn").click()
        
        time.sleep(2)
        err = driver.find_element(By.ID, "login-err").text
        print("Login attempt for unapproved user:", err)
        
        # Now login as Demo Admin
        driver.find_element(By.ID, "li-pw").clear()
        driver.find_element(By.ID, "li-pw").send_keys("demo")
        driver.find_element(By.ID, "li-btn").click()
        
        print("Logged in as Admin. Checking for Admin Panel...")
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "nav-admin")))
        print("Admin Panel tab is visible!")
        
        driver.find_element(By.ID, "nav-admin").click()
        time.sleep(2)
        driver.save_screenshot("C:/Users/raghu/.gemini/antigravity-ide/brain/48025fbf-3a82-47c3-94c0-c9da7da2d000/browser/admin_panel_1786433509121.webp")
        print("Admin Panel loaded and screenshot saved.")
        
    except Exception as e:
        print("Test failed:", e)
        driver.save_screenshot("C:/Users/raghu/.gemini/antigravity-ide/brain/48025fbf-3a82-47c3-94c0-c9da7da2d000/browser/error.webp")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_rbac()
