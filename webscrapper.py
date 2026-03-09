from selenium import webdriver

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import os

import json

def config_file():
    with open("config.json", "r") as f:
        conf = json.load(f)

    required_keys = ["url", "starting_page", "driver_path", "out_file", "already_scanned_file", "category", "modality"]
    for key in required_keys:
        if key not in conf:
            raise ValueError(f"❌ Configuração faltando: {key}")

    return conf

# configuração do webdriver
def setup_driver(conf):
    """Configurar o Selenium WebDriver."""
    driver_path = conf["driver_path"]
    
    # Configurações adicionais do Chrome (opcional)
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")  # Inicia o Chrome maximizado
    chrome_options.add_argument("--headless")  # Desmarque para executar em modo headless (sem interface gráfica)

    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    return driver

# Fazer o log de cursos que já foram verificados
def load_registered_courses(registry_path):
    """Carregar cursos registrados de um arquivo."""
    if os.path.exists(registry_path):
        with open(registry_path, "r", encoding="utf-8") as file:
            return set(line.strip() for line in file)
    return set()

# Fazer o cadastro dos cursos em sí
def save_registered_courses(registry_path, courses):
    """Salvar cursos registrados em um arquivo."""
    with open(registry_path, "w", encoding="utf-8") as file:
        for course in courses:
            file.write(f"{course}\n")

# Padrão de salvamento do arquivo
def save_course(course, output_path):
    """Salvar detalhes de um curso diretamente em um arquivo de texto e atualizar o índice no topo."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Adiciona os dados do novo curso ao final
    with open(output_path, "a", encoding="utf-8") as file:
        file.write(f"Curso: {course['name']}\n")
        file.write(f"Modalidade: {course['modality']}\n")
        file.write(f"Categoria: {course['category']}\n")
        file.write(f"Duração: {course['duration']}\n")
        file.write(f"Descrição: {course['description']}\n")
        file.write("-----------------------------------------------\n")

    # Após adicionar, atualizar o índice no topo
    with open(output_path, 'r', encoding='utf-8') as file:
        linhas = file.readlines()

    # Pega só os títulos
    titulos = [linha.strip().split("Curso: ")[1]
               for linha in linhas if linha.startswith("Curso:")]

    # Monta o índice
    indice = ["ÍNDICE DE CURSOS:\n"]
    for i, titulo in enumerate(titulos, 1):
        indice.append(f"{i}. {titulo}\n")
    indice.append("\n")  # espaço entre índice e corpo

    # Remove índices antigos, pega só a parte dos cursos
    curso_inicio_index = next((i for i, linha in enumerate(linhas) if linha.startswith("Curso:")), 0)
    corpo = linhas[curso_inicio_index:]

    # Reescreve o arquivo com o índice no topo
    with open(output_path, 'w', encoding='utf-8') as file:
        file.writelines(indice + corpo)

# Pegar todas as informações sobre o curso
def scrape_course_details(driver, course_url, conf):
    """Coletar detalhes de um curso individual com verificações de erro."""
    try:
        driver.get(course_url)

        try:
            WebDriverWait(driver, 20, 1.0).until(
                EC.presence_of_element_located((By.XPATH, "//h3[@class='course-single-title']"))
            )
        except:
            print(f"Curso desativado ou página inválida: {course_url}")
            return None

        # Coletando o nome do curso
        try:
            name = driver.find_element(By.XPATH, "//h3[@class='course-single-title']").text.strip()
        except Exception as e:
            print(f"Erro ao coletar nome do curso {course_url}: {e}")
            name = "Nome não disponível"

        # Coletando a descrição do curso
        try:
            description_elements = driver.find_elements(By.XPATH, "//div[@class='tutor-course-summery']/p")
            description = " ".join([element.text.strip() for element in description_elements]) if description_elements else "Descrição não disponível"
        except Exception as e:
            print(f"Erro ao coletar descrição do curso {course_url}: {e}")
            description = "Descrição não disponível"

        # Coletando a duração
        try:
            duration_min_elements = driver.find_elements(By.XPATH, "//span[@class='value']/span[@class='tutor-meta-level']")
            duration = duration_min_elements[0].text.strip() if duration_min_elements else "Duração mínima não disponível"
        except Exception as e:
            print(f"Erro ao coletar duração do curso {course_url}: {e}")
            duration = "Duração mínima não disponível"

        # Coletando o valor do curso
        try:
            course_value = driver.find_element(By.XPATH, "//div[@class='price']").text.strip()
        except Exception as e:
            print(f"Erro ao coletar valor do curso {course_url}: {e}")
            course_value = "Valor não disponível"

        # Coletando o valor com desconto
        try:
            discount_value = driver.find_element(By.XPATH, "//div[@class='por']").text.strip()
        except Exception as e:
            print(f"Erro ao coletar valor com desconto do curso {course_url}: {e}")
            discount_value = "Valor com desconto não disponível"

        # Categoria e Modalidade fixas
        category = conf["category"]
        modality = conf["modality"]

        return {
            "name": name,
            "description": description,
            "duration": duration,
            "category": category,
            "modality": modality,
            "value_norm": course_value,
            "value_disc": discount_value,
            "url": course_url,
        }
    except Exception as e:
        print(f"Erro ao acessar detalhes do curso {course_url}: {e}")
        return None

def scrape_courses(driver, conf, output_path, registry_path):
    """Coletar todos os cursos navegando por paginação com verificações de erro."""
    base_url = conf["url"]
    starting_page = conf["starting_page"]
    registered_courses = load_registered_courses(registry_path)
    page = starting_page
    page_signatures = set()

    while True:
        try:
            print(f"Coletando página {page}...")

            page_url = f"{base_url}?current_page={page}"
            driver.get(page_url)

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'item-course')]"))
                )
            except Exception:
                print("Nenhum curso encontrado nesta página. Encerrando coleta.")
                break

            course_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'item-course')]//a[contains(@class, 'link-overlay')]")
            course_links = [element.get_attribute("href") for element in course_elements]

            if not course_links:
                print("Nenhum link de curso encontrado. Encerrando coleta.")
                break

            page_signature = tuple(course_links)
            if page_signature in page_signatures:
                print("Paginação repetida detectada. Encerrando para evitar loop infinito.")
                break
            page_signatures.add(page_signature)

            unregistered_courses = [link for link in course_links if link not in registered_courses]

            if not unregistered_courses:
                print(f"Todos os cursos da página {page} já estão registrados.")
            else:
                for link in unregistered_courses:
                    print(f"Processando curso: {link}")
                    course_data = scrape_course_details(driver, link, conf)
                    if course_data:
                        save_course(course_data, output_path)
                        registered_courses.add(link)
                        save_registered_courses(registry_path, registered_courses)

            page += 1
            time.sleep(1)

        except Exception as page_error:
            print(f"Erro na página {page}: {page_error}")
            break

if __name__ == "__main__":
    conf_file = config_file()

    OUTPUT_FILE = conf_file["out_file"]
    REGISTRY_FILE = conf_file["already_scanned_file"]

    driver = setup_driver(conf_file)
    try:
        scrape_courses(driver, conf_file, OUTPUT_FILE, REGISTRY_FILE)
        print(f"Coleta concluída. Resultados salvos em {OUTPUT_FILE}")
    finally:
        driver.quit()