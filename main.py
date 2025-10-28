from datetime import timedelta, datetime
import hashlib
import logging
import uuid
import pandas as pd
from fastapi import  FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import asyncio

#TODO
#https
#выкидывание в режиме реального времени

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(check_sessions_task())
    yield



app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

USERS = "users.csv"
UPDATE_TIME = 5
SESSION_TTL = timedelta(seconds=15)
sessions = {}
white_urls = ["/", "/login", "/logout", "/register", ]


"""Логгер"""

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("app.log", mode="a", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_error_logger = logging.getLogger("uvicorn.error")


"""Вспомогательные функции"""

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    hash_object = hashlib.sha256(password.encode('utf-8'))
    return hash_object.hexdigest()

def update_session(response: Response):
    """Обновление времени сессии"""
    response.set_cookie(
        key="session_time",
        value=str(datetime.now()),
    )
    return response

async def check_sessions_task():
    """Проверка истёкших сессий"""
    while True:
        expired_ids = []
        for id, created_session in list(sessions.items()):
            if datetime.now() - created_session > SESSION_TTL:
                expired_ids.append(id)

        for id in expired_ids:
            del sessions[id]
            logger.info(f"Сессия {id} истекла и была удалена")

        await asyncio.sleep(UPDATE_TIME)

#получение роли
def get_role(request: Request) -> str:
    """запрашивает роль пользователя"""
    role = request.cookies.get("role")
    return role

#получение имени пользователя
def get_username(request: Request) -> str:
    """запрашивает имя пользователя"""
    username = request.cookies.get("username")
    return username

def username_check(request: Request, usernames:list) -> bool:
    """Проверяет есть ли юзернейм в вайтлисте"""
    username = get_username(request)
    return (username in usernames)

def role_check(request: Request, roles:list) -> bool:
    """Проверяет есть ли роль в вайтлисте"""
    role = get_role(request)
    return (role in roles)


"""Логика сайта"""

#проверка сессии
@app.middleware("http")
async def check_session(request: Request, call_next):
    path = request.url.path
    if path.startswith("/static") or path in white_urls:
        return await call_next(request)

    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        logger.warning(f"Неавторизованный доступ: {path}")
        return RedirectResponse(url="/")
    
    created_session = sessions[session_id]
    if datetime.now() - created_session > SESSION_TTL:
        del sessions[session_id]
        logger.info("Сессия истекла, перенаправление на /")
        return RedirectResponse(url="/")

    return await call_next(request)


#страница входа
@app.get("/", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
def get_login_page(request: Request, response:Response):
    update_session(response)
    return templates.TemplateResponse("login.html", {"request": request})

#логика входа
@app.post("/login")
def login(request: Request,
          response:Response,
          username: str = Form(...),
          password: str = Form(...)):
    logger.info(f"Попытка входа пользователя: {username}")
    update_session(response)

    try:
        users = pd.read_csv(USERS)
    except FileNotFoundError:
        logger.error("Файл users.csv не найден")
        raise HTTPException(status_code=500, detail="Система пользователей недоступна")

    if username in users['users'].values:
        user_data = users[users['users'] == username].iloc[0]
        stored_hash = str(user_data['password'])
        user_role = user_data["role"]
        hex_dig = hash_password(password)

        if stored_hash == hex_dig:
            session_id = str(uuid.uuid4())
            sessions[session_id] = datetime.now()
            logger.info(f"Пользователь {username} вошёл в систему")
            
            response = RedirectResponse(url=f"/home/{username}", status_code=302)
            response.set_cookie(key="session_id", value=session_id)
            response.set_cookie(key="role", value=user_role)
            response.set_cookie(key="username", value=username)
            response.set_cookie(key="session_time", value=datetime.now)

            logger.info(f'Cookie:{request.cookies}')

            return response
        else:
            logger.warning(f"Неверный пароль для пользователя {username}")
            return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный пароль"})
    else:
        logger.warning(f"Попытка входа с несуществующим логином: {username}")
        return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный логин"})


#logout
@app.get("/logout", response_class=HTMLResponse)
def logout(request: Request, response:Response):
    session_id = request.cookies.get("session_id")
    update_session(response)
    if session_id in sessions:
        del sessions[session_id]
        logger.info("Пользователь вышел из системы и сессия завершена")
    return templates.TemplateResponse("login.html", {"request": request, "message": "Сессия завершена"})


#main
@app.get("/home/{username}", response_class=HTMLResponse)
def home(request: Request, username: str, response:Response):
    if username_check(request, [username]):
        update_session(response)
        users = pd.read_csv(USERS)
        if users.empty:
            logger.warning(f"Пользователь {username} не найден, редирект на /")
            return RedirectResponse("/")
        logger.info(f"Пользователь {username} открыл домашнюю страницу")
        return templates.TemplateResponse("main.html", {"request": request, "username": username})
    else:
        logger.warning(f'Попытка доступа без прав - {get_username(request)}')
        return templates.TemplateResponse("403.html", {"request": request})


# регистрация
@app.get("/register", response_class=HTMLResponse)
def get_register_page(request: Request, response:Response):
    if role_check(request, ['admin']):
        update_session(response)
        return templates.TemplateResponse("register.html", {"request": request})
    else:
         logger.warning(f'Попытка доступа без прав - {get_username(request)}')
         return templates.TemplateResponse("403.html", {"request": request})


# логика регистрации 
@app.post("/register", response_class=HTMLResponse)
def register(request: Request,
             response:Response,
             username: str = Form(...),
             password: str = Form(...),
             role:str = Form(...)):
    update_session(response)
    logger.info(f"Регистрация нового пользователя: {username}")
    try:
        users = pd.read_csv(USERS)
    except FileNotFoundError:
        users = pd.DataFrame(columns=["users", "password", "role"])

    if username in users["users"].values:
        logger.warning(f"Попытка регистрации уже существующего пользователя: {username}")
        return templates.TemplateResponse("register.html", {"request": request, "error": "Пользователь уже существует"})

    hex_dig = hash_password(password)

    users.loc[len(users)] = [username, str(hex_dig), role]
    users.to_csv(USERS, index=False)
    logger.info(f"Пользователь {username} успешно зарегистрирован")

    return templates.TemplateResponse("login.html", {"request": request, "message": "Регистрация успешна"})


#404
@app.exception_handler(StarletteHTTPException)
async def not_found_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        logger.warning(f"404 Not Found: {request.url.path}")
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "path": request.url.path},
            status_code=404
        )
    logger.error(f"Ошибка {exc.status_code}: {request.url.path}")
    raise exc
