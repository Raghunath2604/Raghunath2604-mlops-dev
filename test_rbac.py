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
        driver.get("http://localhost:8000/dashboard.html")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "auth-screen")))
        
        test_email = f"test_{int(time.time())}@example.com"
        # Register a new user
        print("Switching to Request Access tab...")
        tabs = driver.find_elements(By.CLASS_NAME, "atab")
        tabs[1].click() # Click 'Request Access'
        
        time.sleep(1)
        driver.find_element(By.ID, "ri-name").send_keys("Test User")
        driver.find_element(By.ID, "ri-email").send_keys(test_email)
        driver.find_element(By.ID, "ri-pw").send_keys("password123")
        driver.find_element(By.ID, "ri-btn").click()
        
        print("Waiting for registration success...")
        WebDriverWait(driver, 5).until(
            EC.text_to_be_present_in_element((By.ID, "reg-err"), "Success!")
        )
        print("Registration successful (pending admin approval).")
        
        # Now try to login as test user, it should fail with pending approval
        tabs[0].click() # Back to Login
        time.sleep(1)
        email_field = driver.find_element(By.ID, "li-email")
        email_field.clear()
        email_field.send_keys(test_email)
        
        pw_field = driver.find_element(By.ID, "li-pw")
        pw_field.clear()
        pw_field.send_keys("password123")
        driver.find_element(By.ID, "li-btn").click()
        
        time.sleep(1)
        WebDriverWait(driver, 5).until(
            EC.text_to_be_present_in_element((By.ID, "login-err"), "pending")
        )
        print("Verified: Unapproved user was rejected properly.")
        
        # Now login as Demo Admin
        email_field = driver.find_element(By.ID, "li-email")
        email_field.clear()
        email_field.send_keys("demo@nodepilot.dev")
        
        pw_field = driver.find_element(By.ID, "li-pw")
        pw_field.clear()
        pw_field.send_keys("demo")
        driver.find_element(By.ID, "li-btn").click()
        
        print("Logged in as Admin. Checking for Admin Panel...")
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "nav-admin")))
        print("Admin Panel tab is visible!")
        
        driver.find_element(By.ID, "nav-admin").click()
        time.sleep(1)
        print("Admin Panel loaded successfully!")
        
    except Exception as e:
        print("Test failed:", e)
        for entry in driver.get_log('browser'):
            print(entry)
        raise e
    finally:
        driver.quit()

if __name__ == "__main__":
    test_rbac()
