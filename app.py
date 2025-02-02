from fastapi import FastAPI, HTTPException, Query, Request, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
import json
from docxtpl import DocxTemplate, RichText
import os
from datetime import datetime
import tempfile
import subprocess
import logging.handlers
import sys
import gc
import shutil
import uvicorn
from starlette.background import BackgroundTask
from contextlib import asynccontextmanager
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from prometheus_fastapi_instrumentator import Instrumentator
import time
import platform
from PyPDF2 import PdfReader
from fastapi.responses import JSONResponse

def setup_logging():
    """Настройка логирования с учетом окружения"""
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    is_production = os.environ.get('ENVIRONMENT', 'production').lower() == 'production'
    
    # Базовый формат логов
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    if is_production:
        # В production используем JSON формат для лучшей интеграции с системами логирования
        log_format = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
    
    # Настраиваем корневой logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Очищаем существующие handlers
    root_logger.handlers = []
    
    # Handler для stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)
    
    # Создаем logger для приложения
    logger = logging.getLogger('app')
    logger.setLevel(log_level)
    
    # В development включаем более подробное логирование
    if not is_production:
        logger.setLevel(logging.DEBUG)
    
    return logger

# Инициализируем logger
logger = setup_logging()

# Создаем отдельный registry для наших метрик
metrics_registry = CollectorRegistry()

# Метрики Prometheus
pdf_conversion_errors = Counter(
    'pdf_conversion_errors',
    'Total number of PDF conversion errors',
    registry=metrics_registry
)

request_processing_duration = Histogram(
    'request_processing_duration_seconds',
    'Time spent processing request',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registry=metrics_registry
)

temp_files_gauge = Gauge(
    'temp_files_count',
    'Number of temporary files',
    registry=metrics_registry
)

memory_usage_gauge = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes',
    registry=metrics_registry
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Проверка наличия и версии LibreOffice при запуске"""
    try:
        if platform.system() == 'Windows':
            soffice = r"C:\Program Files\LibreOffice\program\soffice.exe"
        else:
            soffice = "/usr/bin/soffice"
            
        if not os.path.exists(soffice):
            logger.error(f"LibreOffice not found at {soffice}")
            yield
            return
            
        process = subprocess.run([soffice, '--version'], capture_output=True, text=True)
        if process.returncode == 0:
            logger.info(f"LibreOffice version: {process.stdout.strip()}")
        else:
            logger.error(f"Error getting LibreOffice version: {process.stderr}")
    except Exception as e:
        logger.error(f"Error checking LibreOffice: {str(e)}")
    
    yield

# Создаем приложение с настройками для больших файлов
app = FastAPI(lifespan=lifespan)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Добавляем поддержку сжатия для больших JSON
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Настройка Prometheus метрик
instrumentator = Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=["/metrics", "/health"],
    registry=metrics_registry
)

# Настраиваем метрики
instrumentator.instrument(app).expose(app, include_in_schema=True, should_gzip=True)

# Добавляем обработчик для метрик времени обработки
@app.middleware("http")
async def add_process_time_metric(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    request_processing_duration.observe(process_time)
    return response

@app.middleware("http")
async def log_request_info(request: Request, call_next):
    """Логирование информации о запросе и ошибках"""
    request_id = f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
    
    # Логируем начало запроса
    logger.info(f"[{request_id}] Started {request.method} {request.url.path}")
    logger.info(f"[{request_id}] Client IP: {request.client.host}")
    logger.info(f"[{request_id}] Headers: {dict(request.headers)}")
    
    try:
        response = await call_next(request)
        logger.info(f"[{request_id}] Completed {response.status_code}")
        return response
    except Exception as e:
        # Детальное логирование ошибки
        logger.error(f"[{request_id}] Unhandled error processing request: {str(e)}")
        logger.error(f"[{request_id}] Error type: {type(e).__name__}")
        logger.error(f"[{request_id}] Error details:", exc_info=True)
        raise

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Глобальный обработчик исключений"""
    request_id = f"err_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
    
    # Логируем детали запроса
    logger.error(f"[{request_id}] Exception occurred while processing {request.method} {request.url.path}")
    logger.error(f"[{request_id}] Client IP: {request.client.host}")
    logger.error(f"[{request_id}] Headers: {dict(request.headers)}")
    
    # Пытаемся получить тело запроса
    try:
        body = await request.body()
        # Ограничиваем размер логируемых данных
        if len(body) > 1000:
            logger.error(f"[{request_id}] Request body (truncated): {body[:1000]}...")
        else:
            logger.error(f"[{request_id}] Request body: {body}")
    except Exception as e:
        logger.error(f"[{request_id}] Could not read request body: {str(e)}")
    
    # Логируем детали исключения
    logger.error(f"[{request_id}] Exception type: {type(exc).__name__}")
    logger.error(f"[{request_id}] Exception details:", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "request_id": request_id,
            "type": type(exc).__name__
        }
    )

def get_pdf_pages(pdf_path):
    """Получение количества страниц в PDF файле с помощью PyPDF2"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf = PdfReader(file)
            pages = len(pdf.pages)
            logger.debug(f"PDF has {pages} pages")
            return pages
    except Exception as e:
        logger.error(f"Error counting PDF pages: {str(e)}")
        return 3  # Возвращаем 3 как значение по умолчанию, если что-то пошло не так

def convert_to_pdf(input_docx, output_pdf):
    """Конвертация DOCX в PDF с помощью LibreOffice"""
    try:
        # Определяем путь к soffice в зависимости от ОС
        if platform.system() == 'Windows':
            possible_paths = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
            ]
            soffice = next((path for path in possible_paths if os.path.exists(path)), None)
            if not soffice:
                raise Exception("LibreOffice not found in standard locations")
        else:
            soffice = os.environ.get('LIBREOFFICE_PATH', '/usr/bin/soffice')
        
        if not os.path.exists(soffice):
            raise Exception(f"LibreOffice not found at {soffice}")
            
        logger.debug(f"Using LibreOffice path: {soffice}")
        logger.debug(f"Input DOCX: {input_docx}")
        logger.debug(f"Output PDF: {output_pdf}")
        
        # Проверяем существование входного файла
        if not os.path.exists(input_docx):
            raise Exception(f"Input DOCX file not found: {input_docx}")
            
        # Проверяем права на запись в выходную директорию
        output_dir = os.path.dirname(output_pdf)
        if not os.access(output_dir, os.W_OK):
            raise Exception(f"No write permission in output directory: {output_dir}")
        
        # Используем абсолютные пути
        abs_input_docx = os.path.abspath(input_docx)
        abs_output_dir = os.path.abspath(output_dir)
        
        # Команда для конвертации
        cmd = [
            soffice,
            '--headless',
            '--invisible',
            '--nodefault',
            '--nofirststartwizard',
            '--nolockcheck',
            '--nologo',
            '--norestore',
            '--convert-to',
            'pdf',
            '--outdir',
            abs_output_dir,
            abs_input_docx
        ]
        
        # Устанавливаем переменные окружения для процесса
        env = os.environ.copy()
        env['HOME'] = os.environ.get('HOME', '/home/appuser')
        env['SAL_USE_VCLPLUGIN'] = 'svp'
        
        # Запускаем процесс конвертации
        logger.debug(f"Running command: {' '.join(cmd)}")
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=abs_output_dir,
            env=env,
            timeout=60  # Таймаут 60 секунд
        )
        
        # Проверяем вывод процесса
        if process.stdout:
            logger.debug(f"LibreOffice stdout: {process.stdout}")
        if process.stderr:
            logger.debug(f"LibreOffice stderr: {process.stderr}")
            
        if process.returncode != 0:
            raise Exception(f"LibreOffice conversion failed with return code {process.returncode}: {process.stderr}")
            
        # Ищем созданный PDF файл
        expected_pdf = os.path.join(abs_output_dir, os.path.splitext(os.path.basename(input_docx))[0] + '.pdf')
        logger.debug(f"Looking for PDF at: {expected_pdf}")
        
        # Проверяем содержимое директории
        logger.debug(f"Directory contents of {abs_output_dir}:")
        for file in os.listdir(abs_output_dir):
            logger.debug(f"- {file}")
        
        if not os.path.exists(expected_pdf):
            raise Exception(f"PDF file was not created at expected location: {expected_pdf}")
            
        # Если output_pdf отличается от expected_pdf, копируем файл
        if expected_pdf != output_pdf:
            shutil.copy2(expected_pdf, output_pdf)
            # Удаляем промежуточный файл
            os.remove(expected_pdf)
        
        # Проверяем, что финальный файл существует и имеет размер больше 0
        if not os.path.exists(output_pdf):
            raise Exception(f"Final PDF file does not exist: {output_pdf}")
        
        if os.path.getsize(output_pdf) == 0:
            raise Exception(f"Generated PDF file is empty: {output_pdf}")
            
    except subprocess.TimeoutExpired:
        raise Exception("LibreOffice conversion timed out after 60 seconds")
    except Exception as e:
        logger.error(f"PDF conversion failed: {str(e)}")
        # Проверяем права доступа и состояние системы
        logger.error(f"Current user: {os.getuid()}")
        logger.error(f"Current working directory: {os.getcwd()}")
        logger.error(f"Directory permissions for {output_dir}: {oct(os.stat(output_dir).st_mode)[-3:]}")
        logger.error(f"Environment variables:")
        for key, value in env.items():
            logger.error(f"  {key}={value}")
        raise Exception(f"PDF conversion failed: {str(e)}")

def prepare_data_for_logging(data):
    """Подготовка данных для логирования"""
    if isinstance(data, dict):
        return {k: prepare_data_for_logging(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [prepare_data_for_logging(item) for item in data]
    elif isinstance(data, RichText):
        return str(data)
    else:
        return data

def cleanup_temp_files(temp_dir):
    """Синхронная очистка временных файлов"""
    try:
        if os.path.exists(temp_dir):
            # Принудительно удаляем все файлы
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    try:
                        os.chmod(file_path, 0o777)
                        os.remove(file_path)
                    except Exception as e:
                        logger.error(f"Error removing file {file_path}: {str(e)}")
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    try:
                        os.chmod(dir_path, 0o777)
                        os.rmdir(dir_path)
                    except Exception as e:
                        logger.error(f"Error removing directory {dir_path}: {str(e)}")
            try:
                os.chmod(temp_dir, 0o777)
                os.rmdir(temp_dir)
            except Exception as e:
                logger.error(f"Error removing temp directory {temp_dir}: {str(e)}")
            logger.debug(f"Cleaned up temporary directory: {temp_dir}")
    except Exception as e:
        logger.error(f"Error in cleanup_temp_files: {str(e)}")

def chunk_registry_items(items, chunk_size=100):
    """Разбивает большой список элементов на части для оптимизации памяти"""
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]

def process_registry_items(items):
    """Обработка элементов реестра с оптимизацией памяти"""
    table_rows = []
    for chunk in chunk_registry_items(items):
        for idx, item in enumerate(chunk, len(table_rows) + 1):
            row = {
                'index': str(idx),
                'invNumber': RichText(item.get('invNumber', '')),
                'name': RichText(item.get('name', '')),
                'informationDate': RichText(str(item.get('informationDate', ''))),
                'id': RichText(str(item.get('id', ''))),
                'note': RichText(item.get('note', '') if item.get('note') else '')
            }
            table_rows.append(row)
            # Очищаем память после каждых 100 строк
            if idx % 100 == 0:
                gc.collect()
    return table_rows

@app.post("/generate-pdf")
async def generate_pdf(
    request: Request, 
    data: str = Query(None),
    file: UploadFile = File(None)
):
    request_id = f"pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
    temp_dir = None
    with request_processing_duration.time():
        try:
            request_body = None
            
            # Логируем начало обработки
            logger.info(f"[{request_id}] Starting PDF generation")
            
            # Сначала пробуем получить данные из файла
            if file:
                request_body = await file.read()
                request_body = request_body.decode('utf-8')
                logger.info(f"[{request_id}] Received data from file upload, size: {len(request_body)} bytes")
            # Затем из query параметра
            elif data:
                request_body = data
                logger.info(f"[{request_id}] Received data from query parameter, size: {len(data)} bytes")
            else:
                # Если данных нет ни в файле, ни в query, читаем тело запроса
                try:
                    body = await request.body()
                    request_body = body.decode('utf-8')
                    logger.info(f"[{request_id}] Received data from request body, size: {len(request_body)} bytes")
                except Exception as e:
                    logger.error(f"[{request_id}] Error reading request body: {str(e)}")
                    raise HTTPException(status_code=400, detail="No data provided or invalid request format")

            if not request_body:
                logger.error(f"[{request_id}] No data provided in request")
                raise HTTPException(status_code=400, detail="No data provided")

            # Проверяем размер данных
            data_size = len(request_body)
            if data_size > 50 * 1024 * 1024:  # 50MB limit
                raise HTTPException(status_code=413, detail="Request too large")
            
            # Создаем временную директорию с уникальным именем
            base_temp = os.environ.get('TMPDIR', '/tmp')
            temp_dir = os.path.join(base_temp, f'pdf_gen_{datetime.now().strftime("%Y%m%d_%H%M%S")}_{os.getpid()}')
            os.makedirs(temp_dir, mode=0o755, exist_ok=True)
            logger.debug(f"Created temporary directory: {temp_dir}")
            
            # Парсим JSON данные
            try:
                json_data = json.loads(request_body)
            except json.JSONDecodeError as e:
                logger.error(f"[{request_id}] JSON parsing error: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Invalid JSON data: {str(e)}")
            except Exception as e:
                logger.error(f"[{request_id}] Unexpected error during JSON parsing: {str(e)}")
                raise HTTPException(status_code=500, detail="Error processing JSON data")
            
            docx_path = os.path.join(temp_dir, "output.docx")
            pdf_path = os.path.join(temp_dir, "output.pdf")
            
            # Загружаем шаблон
            template_path = "templates/template.docx"
            logger.debug(f"[{request_id}] Loading template from: {template_path}")
            doc = DocxTemplate(template_path)
            
            # Подготавливаем данные для таблицы
            table_data = json_data.copy()  # Создаем копию для модификации
            
            # Обрабатываем данные заявителя в зависимости от типа
            logger.debug(f"[{request_id}] Applicant type: {json_data.get('applicantType')}")
            
            if json_data.get('applicantType') == 'ORGANIZATION':
                if json_data.get('organizationInfo'):
                    # Для организации используем полные данные
                    table_data['applicant_info'] = (
                        f"{json_data['organizationInfo'].get('name', '')}, "
                        f"{json_data['organizationInfo'].get('address', '')}, "
                        f"{json_data['organizationInfo'].get('agent', '')}"
                    )
                    table_data['applicant_name'] = json_data['organizationInfo'].get('name', '')
                    table_data['applicant_agent'] = json_data['organizationInfo'].get('agent', '')
                    table_data['is_organization'] = True
                else:
                    table_data['applicant_info'] = ''
                    table_data['applicant_name'] = ''
                    table_data['applicant_agent'] = ''
                    table_data['is_organization'] = True
            else:  # INDIVIDUAL
                if json_data.get('individualInfo'):
                    # Для физ. лица добавляем ЕСИА номер
                    esia_number = json_data['individualInfo'].get('esia', '')
                    esia_suffix = f" (ЕСИА {esia_number})" if esia_number else ''
                    name = json_data['individualInfo'].get('name', '')
                    
                    table_data['applicant_info'] = f"{name}{esia_suffix}"
                    table_data['applicant_name'] = f"физическое лицо {name}"
                    table_data['applicant_agent'] = ''  # Для физ. лица поле представителя оставляем пустым
                    table_data['is_organization'] = False
                else:
                    table_data['applicant_info'] = ''
                    table_data['applicant_name'] = ''
                    table_data['applicant_agent'] = ''
                    table_data['is_organization'] = False
            
            logger.debug(f"[{request_id}] Prepared applicant data: {table_data['applicant_info']}")
            
            # Подготавливаем данные для таблицы с оптимизацией памяти
            if 'registryItems' in json_data:
                table_data['table_rows'] = process_registry_items(json_data['registryItems'])
            
            # Форматируем дату
            if 'creationDate' in json_data:
                try:
                    # Предполагаем, что дата приходит в формате ISO
                    date_obj = datetime.fromisoformat(json_data['creationDate'].replace('Z', '+00:00'))
                    table_data['creationDate'] = date_obj.strftime("%d.%m.%Y")
                    logger.debug(f"[{request_id}] Formatted date: {table_data['creationDate']}")
                except Exception as e:
                    logger.error(f"[{request_id}] Error formatting date: {e}")
            
            # Выводим все данные перед рендерингом
            logger.debug(f"[{request_id}] Final template data:")
            logger.debug(json.dumps(prepare_data_for_logging(table_data), indent=2, ensure_ascii=False))
            
            # Оптимизируем рендеринг шаблона
            try:
                doc.render(table_data)
                logger.debug(f"[{request_id}] Template rendered successfully")
                # Очищаем память после рендеринга
                gc.collect()
            except Exception as e:
                logger.error(f"[{request_id}] Template rendering failed: {str(e)}")
                logger.error(f"[{request_id}] Template context too large to log")
                raise
            
            # Сохраняем docx
            logger.debug(f"[{request_id}] Saving DOCX to: {docx_path}")
            doc.save(docx_path)
            
            # Конвертируем в PDF для подсчета страниц
            convert_to_pdf(docx_path, pdf_path)
            
            # Получаем реальное количество страниц в PDF
            pages = get_pdf_pages(pdf_path)
            logger.debug(f"[{request_id}] Document has {pages} pages")
            
            # Обновляем количество страниц в шаблоне
            table_data['registry_pages'] = pages - 1  # Вычитаем первую страницу
            logger.debug(f"[{request_id}] Setting registry_pages to {pages - 1}")
            
            # Загружаем шаблон заново
            doc = DocxTemplate(template_path)
            
            # Рендерим документ заново с обновленным количеством страниц
            doc.render(table_data)
            doc.save(docx_path)
            
            # Конвертируем в PDF финальную версию
            convert_to_pdf(docx_path, pdf_path)
            
            # Проверяем, что количество страниц корректно обновилось
            final_pages = get_pdf_pages(pdf_path)
            logger.debug(f"[{request_id}] Final document has {final_pages} pages, registry_pages set to {table_data['registry_pages']}")
            
            # Обновляем метрики
            temp_files = sum([len(files) for r, d, files in os.walk(temp_dir)])
            temp_files_gauge.set(temp_files)
            memory_usage_gauge.set(gc.get_count()[0] * 1024 * 1024)
            
            # Возвращаем PDF файл
            response = FileResponse(
                pdf_path,
                media_type="application/pdf",
                filename="application.pdf"
            )
            
            # Создаем асинхронную функцию для очистки
            async def background_cleanup():
                await cleanup_temp_files(temp_dir)
            
            # Добавляем обработчик для очистки после отправки файла
            response.background = background_cleanup
            
            return response
        
        except Exception as e:
            pdf_conversion_errors.inc()
            if temp_dir and os.path.exists(temp_dir):
                await cleanup_temp_files(temp_dir)
            logger.error(f"[{request_id}] Error in generate_pdf: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    # Настройки uvicorn для стабильной работы с большими файлами
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "use_colors": None,
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '%(asctime)s - %(name)s - %(levelname)s - %(client_addr)s - "%(request_line)s" %(status_code)s',
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO"},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
        },
    }
    
    # Определяем, нужна ли автоперезагрузка
    should_reload = os.environ.get('RELOAD_APP', 'false').lower() == 'true'
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8005,
        workers=1,
        timeout_keep_alive=300,
        backlog=2048,
        timeout_graceful_shutdown=300,
        access_log=True,
        log_level="info",
        log_config=log_config,
        proxy_headers=True,
        forwarded_allow_ips="*",
        reload=should_reload,
        http='h11',
        loop='asyncio'
    )
