import time
import subprocess
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL = 'https://127.0.0.1:8000'


@pytest.fixture(scope="session", autouse=True)
def start_server():
    """Запуск FastAPI перед тестами"""
    process = subprocess.Popen(
        ["uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(3)
    yield
    process.terminate()


@pytest.fixture()
def browser():
    """Инициализация браузера"""
    chrome_options = Options()
    #chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--ignore-certificate-errors")

    driver = webdriver.Chrome( options=chrome_options)
    yield driver
    driver.quit()

def test_login_page_loads(browser):
    """Проверка загрузки страницы входа"""
    browser.get(f"{URL}/login")
    assert "Login" in browser.page_source or "Вход" in browser.page_source


def test_invalid_login(browser):
    """Попытка входа под несуществующем юзером"""
    browser.get(f"{URL}/login")

    username_field = browser.find_element(By.NAME, "username")
    password_field = browser.find_element(By.NAME, "password")

    username_field.send_keys("fake_user")
    password_field.send_keys("wrong_pass")
    password_field.submit()

    time.sleep(1)
    assert "Неверный логин" in browser.page_source


def test_register_page_forbidden_for_user(browser):
    """проверка /register на доступ только к админам"""
    browser.get(f"{URL}/register")
    time.sleep(1)
    assert "403" in browser.page_source or "Доступ запрещён" in browser.page_source


