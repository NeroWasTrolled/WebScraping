from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

def setup_driver(driver_path=None):
    """Configura e retorna o Selenium WebDriver.

    Caso nenhum caminho seja informado, o Selenium tentará utilizar o
    executável ``chromedriver`` disponível no ``PATH`` do sistema.
    """
    service = Service(driver_path) if driver_path else Service()
    driver = webdriver.Chrome(service=service)
    driver.maximize_window()
    return driver

def load_registered_courses(registry_path):
    """Carregar cursos registrados de um arquivo."""
    if os.path.exists(registry_path):
        with open(registry_path, "r", encoding="utf-8") as file:
            return set(line.strip() for line in file)
    return set()

def save_registered_courses(registry_path, courses):
    """Salvar cursos registrados em um arquivo."""
    with open(registry_path, "w", encoding="utf-8") as file:
        for course in courses:
            file.write(f"{course}\n")

def save_courses(courses, output_path):
    """Salvar detalhes dos cursos em um arquivo de texto."""
    directory = os.path.dirname(output_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        for course in courses:
            file.write(f"Curso: {course['name']}\n")
            file.write(f"Modalidade: {course['modality']}\n")
            file.write(f"Categoria: {course['category']}\n")
            file.write(f"Duração Mínima: {course['duration_min']}\n")
            file.write(f"Duração: {course['duration']}\n")
            file.write(f"Descrição: {course['description']}\n")
            file.write("\n")

def scrape_course_details(driver, course_url):
    """Coletar detalhes de um curso individual."""
    try:
        driver.get(course_url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h3.course-single-title"))
        )

        name = driver.find_element(By.CSS_SELECTOR, "h3.course-single-title").text.strip()

        description_elements = driver.find_elements(By.CSS_SELECTOR, "div.entry-content > p")
        description = description_elements[0].text.strip() if description_elements else "Descrição não disponível"

        duration_elements = driver.find_elements(By.XPATH, "//p[contains(text(), 'O curso possui')]")
        duration = duration_elements[0].text.strip() if duration_elements else "Duração não disponível"

        duration_min_elements = driver.find_elements(
            By.XPATH, "//span[@class='value']/span[@class='tutor-meta-level']"
        )
        duration_min = (
            duration_min_elements[0].text.strip() if duration_min_elements else "Duração mínima não disponível"
        )

        category = "Cursos Livres"
        modality = "EAD"

        return {
            "name": name,
            "description": description,
            "duration": duration,
            "duration_min": duration_min,
            "category": category,
            "modality": modality,
            "url": course_url,
        }
    except Exception as e:
        print(f"Erro ao coletar detalhes de {course_url}: {e}")
        return None

def scrape_courses(driver, output_path, registry_path):
    """Coletar todos os cursos navegando por paginação."""
    base_url = ""
    registered_courses = load_registered_courses(registry_path)
    new_courses = []
    page = 1

    driver.get(base_url)

    while True:
        try:
            print(f"Coletando página {page}...")

            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".item-course"))
            )

            course_elements = driver.find_elements(By.CSS_SELECTOR, ".item-course .course-header a.link-overlay")
            course_links = [element.get_attribute("href") for element in course_elements]

            unregistered_courses = [link for link in course_links if link not in registered_courses]

            if not unregistered_courses:
                print(f"Todos os cursos da página {page} já estão registrados.")
            else:
                for link in unregistered_courses:
                    print(f"Processando curso: {link}")
                    course_data = scrape_course_details(driver, link)
                    if course_data:
                        new_courses.append(course_data)
                        registered_courses.add(link)
                        save_registered_courses(registry_path, registered_courses)

                driver.get(f"{base_url}?current_page={page}")
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".item-course"))
                )

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
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".item-course"))
                )
                time.sleep(3)
                page += 1
            except Exception as next_error:
                print(f"Última página alcançada ou botão 'Próximo' não encontrado: {next_error}")
                break

        except Exception as page_error:
            print(f"Erro na página {page}: {page_error}")
            break

    save_courses(new_courses, output_path)

if __name__ == "__main__":
    OUTPUT_FILE = r""
    REGISTRY_FILE = r""

    driver = setup_driver()
    try:
        scrape_courses(driver, OUTPUT_FILE, REGISTRY_FILE)
        print(f"Coleta concluída. Resultados salvos em {OUTPUT_FILE}")
    finally:
        driver.quit()

