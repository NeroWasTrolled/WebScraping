from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os


def setup_driver():
    """Configurar o Selenium WebDriver."""
    driver_path = r"C:\Users\gabriel.simoes\Downloads\chromedriver-win64\chromedriver-win64\chromedriver.exe"  
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service)
    driver.maximize_window()
    return driver


def save_course_names(course_names, output_path):
    """Salvar os nomes dos cursos em um arquivo de texto."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        for course_name in course_names:
            file.write(f"- {course_name}\n")


def scrape_course_names(driver, output_path):
    """Coletar apenas os nomes dos cursos navegando por paginação."""
    base_url = "https://unicv.edu.br/extensao-ead/"
    course_names = []
    page = 1

    driver.get(base_url)

    while True:
        try:
            print(f"Coletando nomes dos cursos na página {page}...")

            # Esperar os cursos carregarem
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "h2.title a"))
            )

            # Obter nomes dos cursos pelo texto do <a> dentro de <h2>
            course_elements = driver.find_elements(By.CSS_SELECTOR, "h2.title a")
            for element in course_elements:
                course_name = element.text.strip()  # Pegando o texto do <a> dentro do <h2>
                course_names.append(course_name)
                print(f"Curso encontrado: {course_name}")

            # Tentar clicar no botão "Próximo"
            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.next.page-numbers"))
                )

                driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                time.sleep(1)

                try:
                    next_button.click()
                except Exception as click_error:
                    print(f"O clique padrão falhou, tentando clique com JavaScript: {click_error}")
                    driver.execute_script("arguments[0].click();", next_button)

                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "h2.title a"))
                )
                time.sleep(3)
                page += 1
            except Exception as next_error:
                print(f"Última página alcançada ou botão 'Próximo' não encontrado: {next_error}")
                break

        except Exception as page_error:
            print(f"Erro na página {page}: {page_error}")
            break

    # Salvar nomes dos cursos
    save_course_names(course_names, output_path)


if __name__ == "__main__":
    OUTPUT_FILE = r"C:\\Users\\gabriel.simoes\\Documents\\Documents (2)\\Documents\\EAD\\nomes_dos_cursos.txt"

    driver = setup_driver()
    try:
        scrape_course_names(driver, OUTPUT_FILE)
        print(f"Coleta concluída. Nomes dos cursos salvos em {OUTPUT_FILE}")
    finally:
        driver.quit()
