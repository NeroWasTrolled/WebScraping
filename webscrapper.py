from pathlib import Path
import json
import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager


def config_file(config_path="config.json"):
    """Carrega e valida o arquivo de configuração."""
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"❌ Arquivo de configuração não encontrado: {config_path.resolve()}")

    with open(config_path, "r", encoding="utf-8") as f:
        conf = json.load(f)

    required_keys = [
        "url",
        "starting_page",
        "out_file",
        "already_scanned_file",
        "category",
        "modality",
    ]

    for key in required_keys:
        if key not in conf:
            raise ValueError(f"❌ Configuração faltando: {key}")

    try:
        conf["starting_page"] = int(conf["starting_page"])
    except ValueError:
        raise ValueError("❌ 'starting_page' deve ser um número inteiro.")

    conf["headless"] = bool(conf.get("headless", False))
    conf["max_retries"] = int(conf.get("max_retries", 3))
    conf["retry_delay"] = float(conf.get("retry_delay", 2))
    conf["pagination_wait_timeout"] = int(conf.get("pagination_wait_timeout", 25))
    conf["pagination_click_retries"] = int(conf.get("pagination_click_retries", 3))

    return conf


def _first_existing_file(paths):
    """Retorna o primeiro caminho de arquivo existente."""
    for path in paths:
        if not path:
            continue
        candidate = Path(path)
        if candidate.is_file():
            return str(candidate.resolve())
    return None


def find_chrome_binary(conf=None):
    """Localiza o executável do Google Chrome no Windows."""
    conf = conf or {}
    return _first_existing_file(
        [
            conf.get("chrome_binary"),
            os.environ.get("CHROME_BINARY"),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            str(Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe"),
        ]
    )


def find_edge_binary(conf=None):
    """Localiza o executável do Microsoft Edge no Windows."""
    conf = conf or {}
    return _first_existing_file(
        [
            conf.get("edge_binary"),
            os.environ.get("EDGE_BINARY"),
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        ]
    )


def _apply_browser_options(options, conf):
    """Aplica argumentos comuns de Chrome/Edge Chromium."""
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--log-level=3")

    if conf.get("headless", False):
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")

    return options


def _start_chrome(conf, chrome_binary):
    """Inicia o Chrome e atualiza o ChromeDriver automaticamente se necessário."""
    chrome_options = _apply_browser_options(Options(), conf)
    chrome_options.binary_location = chrome_binary

    print(f"🔍 Chrome encontrado em: {chrome_binary}")
    print("⬇️ Verificando ChromeDriver compatível (atualiza automaticamente se necessário)...")

    try:
        driver = webdriver.Chrome(options=chrome_options)
    except WebDriverException:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

    print("✅ ChromeDriver pronto e sessão iniciada.")
    return driver


def _start_edge(conf, edge_binary):
    """Inicia o Edge e atualiza o EdgeDriver automaticamente se necessário."""
    edge_options = _apply_browser_options(EdgeOptions(), conf)
    edge_options.binary_location = edge_binary

    print("Google Chrome não foi encontrado. Usando Microsoft Edge.")
    print(f"🔍 Edge encontrado em: {edge_binary}")
    print("⬇️ Verificando EdgeDriver compatível (atualiza automaticamente se necessário)...")

    try:
        driver = webdriver.Edge(options=edge_options)
    except WebDriverException:
        service = EdgeService(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=edge_options)

    print("✅ EdgeDriver pronto e sessão iniciada.")
    return driver


def setup_driver(conf):
    """Configura o Selenium com download automático do driver compatível com o navegador instalado."""
    chrome_binary = find_chrome_binary(conf)
    if chrome_binary:
        return _start_chrome(conf, chrome_binary)

    edge_binary = find_edge_binary(conf)
    if edge_binary:
        return _start_edge(conf, edge_binary)

    raise FileNotFoundError(
        "Nenhum navegador compatível foi encontrado. Instale o Google Chrome "
        "(https://www.google.com/chrome/) ou informe o caminho em config.json "
        "com a chave 'chrome_binary'."
    )


def ensure_parent_dir(file_path):
    """Garante que a pasta pai do arquivo exista."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)


def load_registered_courses(registry_path):
    """Carrega cursos já registrados de um arquivo."""
    registry_path = Path(registry_path)

    if registry_path.exists():
        with open(registry_path, "r", encoding="utf-8") as file:
            return set(line.strip() for line in file if line.strip())

    return set()


def save_registered_courses(registry_path, courses):
    """Salva cursos já registrados em um arquivo."""
    registry_path = Path(registry_path)
    ensure_parent_dir(registry_path)

    with open(registry_path, "w", encoding="utf-8") as file:
        for course in sorted(courses):
            file.write(f"{course}\n")


def save_course(course, output_path):
    """Salva detalhes de um curso em arquivo texto e atualiza índice no topo."""
    output_path = Path(output_path)
    ensure_parent_dir(output_path)

    with open(output_path, "a", encoding="utf-8") as file:
        file.write(f"Curso: {course['name']}\n")
        file.write(f"Modalidade: {course['modality']}\n")
        file.write(f"Categoria: {course['category']}\n")
        file.write(f"Duração: {course['duration']}\n")
        # file.write(f"Valor Normal: {course['value_norm']}\n")
        # file.write(f"Valor com Desconto: {course['value_disc']}\n")
        # file.write(f"URL: {course['url']}\n")
        file.write(f"Descrição: {course['description']}\n")
        file.write("--------------------------------------------------\n")

    with open(output_path, "r", encoding="utf-8") as file:
        linhas = file.readlines()

    titulos = []
    for linha in linhas:
        if linha.startswith("Curso:"):
            partes = linha.strip().split("Curso: ", 1)
            if len(partes) > 1:
                titulos.append(partes[1])

    indice = ["ÍNDICE DE CURSOS:\n"]
    for i, titulo in enumerate(titulos, 1):
        indice.append(f"{i}. {titulo}\n")
    indice.append("\n")

    curso_inicio_index = next((i for i, linha in enumerate(linhas) if linha.startswith("Curso:")), len(linhas))
    corpo = linhas[curso_inicio_index:]

    with open(output_path, "w", encoding="utf-8") as file:
        file.writelines(indice + corpo)


def safe_text(element):
    """Retorna texto limpo de um elemento."""
    try:
        return element.text.strip()
    except Exception:
        return ""


def is_bad_description_text(text):
    """
    Filtra textos que não devem entrar na descrição,
    como títulos de seção e cabeçalhos genéricos.
    """
    if not text:
        return True

    normalized = " ".join(text.split()).strip()

    if not normalized:
        return True

    blocked_exact = {
        "INFORMAÇÕES SOBRE O CURSO",
        "INFORMACOES SOBRE O CURSO",
        "SOBRE O CURSO",
        "CONHEÇA O CURSO",
        "CONHECA O CURSO",
        "MAIS INFORMAÇÕES",
        "MAIS INFORMACOES",
        "APRESENTAÇÃO DO CURSO",
        "APRESENTACAO DO CURSO",
    }

    if normalized.upper() in blocked_exact:
        return True

    # ignora títulos muito curtos em caixa alta
    if normalized.isupper() and len(normalized) <= 40:
        return True

    # ignora textos extremamente curtos
    if len(normalized) < 10:
        return True

    return False


def retry_operation(operation, description, max_retries=3, retry_delay=2):
    """Executa uma operação com retry automático."""
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            return operation()
        except Exception as e:
            last_error = e
            print(f"⚠️ Falha em '{description}' | tentativa {attempt}/{max_retries}: {e}")

            if attempt < max_retries:
                sleep_time = retry_delay * attempt
                print(f"🔁 Tentando novamente em {sleep_time:.1f}s...")
                time.sleep(sleep_time)

    print(f"❌ Falha definitiva em '{description}' após {max_retries} tentativas.")
    raise last_error


def open_page_with_retry(driver, url, wait_xpath=None, timeout=20, max_retries=3, retry_delay=2):
    """Abre uma página com retry e espera opcional por um elemento."""
    def operation():
        driver.get(url)

        if wait_xpath:
            WebDriverWait(driver, timeout, 1.0).until(
                EC.presence_of_element_located((By.XPATH, wait_xpath))
            )

        return True

    return retry_operation(
        operation=operation,
        description=f"Abrir página: {url}",
        max_retries=max_retries,
        retry_delay=retry_delay,
    )


def extract_description(driver):
    """
    Tenta extrair a descrição do curso de forma universal,
    cobrindo múltiplas estruturas possíveis do site.
    """
    description_strategies = [
        (
            "bloco tutor-course-content-content",
            "//div[contains(@class, 'tutor-course-content-content')]//*[self::p or self::li]"
        ),
        (
            "layout tutor-course-summery",
            "//div[contains(@class, 'tutor-course-summery')]//p"
        ),
        (
            "section com h2 'Sobre o curso'",
            "//section[.//h2[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÀÃÂÉÈÊÍÌÎÓÒÕÔÚÙÛÇ', 'abcdefghijklmnopqrstuvwxyzáàãâéèêíìîóòõôúùûç'), 'sobre o curso')]]//p"
        ),
        (
            "section com header e h2 'Sobre o curso'",
            "//section[.//header//h2[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÀÃÂÉÈÊÍÌÎÓÒÕÔÚÙÛÇ', 'abcdefghijklmnopqrstuvwxyzáàãâéèêíìîóòõôúùûç'), 'sobre o curso')]]//p"
        ),
        (
            "qualquer heading com 'Sobre o curso'",
            "//*[self::section or self::div][.//*[self::h1 or self::h2 or self::h3 or self::h4][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÀÃÂÉÈÊÍÌÎÓÒÕÔÚÙÛÇ', 'abcdefghijklmnopqrstuvwxyzáàãâéèêíìîóòõôúùûç'), 'sobre o curso')]]//p"
        ),
        (
            "section com id contendo unicv",
            "//section[contains(translate(@id, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'unicv')]//p"
        ),
    ]

    for label, xpath in description_strategies:
        try:
            elements = driver.find_elements(By.XPATH, xpath)

            texts = []
            for element in elements:
                text = safe_text(element)

                if is_bad_description_text(text):
                    continue

                texts.append(text)

            if texts:
                print(f"📝 Descrição encontrada usando: {label}")
                return " ".join(texts)

        except Exception as e:
            print(f"⚠️ Falha ao tentar coletar descrição usando '{label}': {e}")

    return "Descrição não disponível"


def get_course_links_from_listing(driver):
    """Retorna os links dos cursos visíveis na listagem atual."""
    course_elements = driver.find_elements(
        By.XPATH,
        "//div[contains(@class, 'item-course')]//a[contains(@class, 'link-overlay')]"
    )

    return [
        element.get_attribute("href")
        for element in course_elements
        if element.get_attribute("href")
    ]


def go_to_next_page_by_click(driver, previous_signature, timeout=25, max_attempts=3, retry_delay=2):
    """Clica em próxima página e aguarda mudança real dos cursos na listagem."""
    for attempt in range(1, max_attempts + 1):
        try:
            next_button = WebDriverWait(driver, 5, 0.5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.next.page-numbers"))
            )
        except TimeoutException:
            print("✅ Botão de próxima página não encontrado. Fim da paginação.")
            return False

        classes = (next_button.get_attribute("class") or "").lower()
        aria_disabled = (next_button.get_attribute("aria-disabled") or "").lower()
        if "disabled" in classes or aria_disabled == "true":
            print("✅ Botão de próxima página desabilitado. Fim da paginação.")
            return False

        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
            try:
                next_button.click()
            except Exception:
                # fallback para casos de sobreposição de elementos
                driver.execute_script("arguments[0].click();", next_button)

            def listing_changed(drv):
                try:
                    current_signature = tuple(get_course_links_from_listing(drv))
                    return bool(current_signature) and current_signature != previous_signature
                except Exception:
                    return False

            WebDriverWait(driver, timeout, 0.5).until(listing_changed)
            return True

        except TimeoutException:
            print(
                f"⚠️ Tentativa {attempt}/{max_attempts}: listagem não atualizou após clique em próxima página."
            )
            if attempt < max_attempts:
                time.sleep(retry_delay)
                continue
            print("⚠️ Limite de tentativas de paginação atingido.")
            return False
        except Exception as e:
            print(f"⚠️ Falha ao avançar para a próxima página: {e}")
            if attempt < max_attempts:
                time.sleep(retry_delay)
                continue
            return False

    return False


def scrape_course_details_in_new_tab(driver, course_url, conf):
    """Abre o curso em nova aba para não perder o estado da paginação na listagem."""
    main_window = driver.current_window_handle
    existing_handles = set(driver.window_handles)

    try:
        driver.execute_script("window.open(arguments[0], '_blank');", course_url)

        new_handle = next(
            (handle for handle in driver.window_handles if handle not in existing_handles),
            None,
        )

        if not new_handle:
            print(f"⚠️ Não foi possível abrir nova aba para o curso: {course_url}")
            return None

        driver.switch_to.window(new_handle)
        return scrape_course_details(driver, course_url, conf)

    except Exception as e:
        print(f"⚠️ Falha ao processar curso em nova aba ({course_url}): {e}")
        return None
    finally:
        current_handle = driver.current_window_handle

        if current_handle != main_window:
            try:
                driver.close()
            except Exception:
                pass

        try:
            driver.switch_to.window(main_window)
            WebDriverWait(driver, 10, 0.5).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'item-course')]"))
            )
        except Exception as e:
            print(f"⚠️ Não foi possível restaurar totalmente a aba da listagem: {e}")


def scrape_course_details(driver, course_url, conf):
    """Coleta detalhes de um curso individual com tratamento de erro e retry."""
    try:
        open_page_with_retry(
            driver=driver,
            url=course_url,
            wait_xpath="//h3[@class='course-single-title']",
            timeout=20,
            max_retries=conf["max_retries"],
            retry_delay=conf["retry_delay"],
        )

        try:
            name = safe_text(driver.find_element(By.XPATH, "//h3[@class='course-single-title']")) or "Nome não disponível"
        except Exception as e:
            print(f"❌ Erro ao coletar nome do curso {course_url}: {e}")
            name = "Nome não disponível"

        try:
            description = extract_description(driver)
        except Exception as e:
            print(f"❌ Erro ao coletar descrição do curso {course_url}: {e}")
            description = "Descrição não disponível"

        try:
            duration_min_elements = driver.find_elements(
                By.XPATH,
                "//span[@class='value']/span[@class='tutor-meta-level']"
            )
            duration = safe_text(duration_min_elements[0]) if duration_min_elements else "Duração não disponível"
        except Exception as e:
            print(f"❌ Erro ao coletar duração do curso {course_url}: {e}")
            duration = "Duração não disponível"

        try:
            course_value = safe_text(driver.find_element(By.XPATH, "//div[@class='price']")) or "Valor não disponível"
        except Exception as e:
            print(f"❌ Erro ao coletar valor do curso {course_url}: {e}")
            course_value = "Valor não disponível"

        try:
            discount_value = safe_text(driver.find_element(By.XPATH, "//div[@class='por']")) or "Valor com desconto não disponível"
        except Exception as e:
            print(f"❌ Erro ao coletar valor com desconto do curso {course_url}: {e}")
            discount_value = "Valor com desconto não disponível"

        return {
            "name": name,
            "description": description,
            "duration": duration,
            "category": conf["category"],
            "modality": conf["modality"],
            # "value_norm": course_value,
            # "value_disc": discount_value,
            "url": course_url,
        }

    except Exception as e:
        print(f"❌ Erro ao acessar detalhes do curso {course_url}: {e}")
        return None


def scrape_courses(driver, conf, output_path, registry_path):
    """Coleta todos os cursos navegando por paginação com retry automático."""
    base_url = conf["url"]
    starting_page = conf["starting_page"]
    registered_courses = load_registered_courses(registry_path)
    page = starting_page
    page_signatures = set()

    initial_url = base_url if starting_page <= 1 else f"{base_url}?current_page={starting_page}"

    try:
        open_page_with_retry(
            driver=driver,
            url=initial_url,
            wait_xpath="//div[contains(@class, 'item-course')]",
            timeout=10,
            max_retries=conf["max_retries"],
            retry_delay=conf["retry_delay"],
        )
    except Exception:
        print("❌ Falha ao abrir a página inicial da listagem de cursos.")
        return

    while True:
        try:
            print(f"\n📄 Coletando página {page}...")

            course_links = get_course_links_from_listing(driver)

            if not course_links:
                print("✅ Nenhum link de curso encontrado. Encerrando coleta.")
                break

            page_signature = tuple(course_links)
            if page_signature in page_signatures:
                print("⚠️ Paginação repetida detectada. Encerrando para evitar loop infinito.")
                break

            page_signatures.add(page_signature)

            unregistered_courses = [link for link in course_links if link not in registered_courses]

            if not unregistered_courses:
                print(f"ℹ️ Todos os cursos da página {page} já estão registrados.")
            else:
                for link in unregistered_courses:
                    print(f"🔎 Processando curso: {link}")
                    course_data = scrape_course_details_in_new_tab(driver, link, conf)

                    if course_data:
                        save_course(course_data, output_path)
                        registered_courses.add(link)
                        save_registered_courses(registry_path, registered_courses)
                        print(f"💾 Curso salvo: {course_data['name']}")
                    else:
                        print(f"⚠️ Não foi possível salvar o curso: {link}")

            if not go_to_next_page_by_click(
                driver,
                page_signature,
                timeout=conf["pagination_wait_timeout"],
                max_attempts=conf["pagination_click_retries"],
                retry_delay=conf["retry_delay"],
            ):
                break

            page += 1
            time.sleep(1)

        except Exception as page_error:
            print(f"❌ Erro na página {page}: {page_error}")
            break


def main():
    conf = config_file()

    output_file = conf["out_file"]
    registry_file = conf["already_scanned_file"]

    driver = setup_driver(conf)

    try:
        scrape_courses(driver, conf, output_file, registry_file)
        print(f"\n✅ Coleta concluída. Resultados salvos em: {Path(output_file).resolve()}")
    finally:
        driver.quit()
        print("🛑 Navegador encerrado.")


if __name__ == "__main__":
    main()