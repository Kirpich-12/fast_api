import csv
from datetime import timedelta, datetime
import uuid
import pandas as pd
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


USERS = "users.csv"
SESSION_TTL = timedelta(10)
sessions = {}
white_urls = ["/", "/login", "/logout"]


@app.middleware("http")
async def check_session(request: Request, call_next):
    if request.url.path.startswith("/static") or request.url.path in white_urls:
        return await call_next(request)

    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return RedirectResponse(url="/")

    created_session = sessions[session_id]
    if datetime.now() - created_session > SESSION_TTL:
        del sessions[session_id]
        return RedirectResponse(url="/")

    return await call_next(request)

@app.get("/", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
def get_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(request: Request,
          username: str = Form(...),
          password: str = Form(...)):
    users = pd.read_csv(USERS)
    if username in users['users'].values:
        user_data = users[users['users'] == username].iloc[0]
        if str(user_data['password']) == password:
            session_id = str(uuid.uuid4())
            sessions[session_id] = datetime.now()
            response = RedirectResponse(url=f"/home/{username}", status_code=302)
            response.set_cookie(key="session_id", value=session_id)
            return response
        else:
            return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный пароль"})
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный логин"})

@app.get("/logout", response_class=HTMLResponse)
def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id in sessions:
        del sessions[session_id]    
    return templates.TemplateResponse("login.html", {"request": request, "message": "Сессия завершена"})

@app.get("/home/{username}", response_class=HTMLResponse)
def home(request: Request, username: str):
    users = pd.read_csv(USERS)
    user = users['users']
    if user.empty:
        return RedirectResponse("/")
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/home/admin", response_class=HTMLResponse)
def get_start_page(request: Request):
    return templates.TemplateResponse("register.html",
                                       {"request": request})

@app.post("/login", response_class=HTMLResponse)
def login(request: Request,
          username:str = Form(...),
          password:str = Form(...)):
    print('asdadas')
    users = pd.read_csv(USERS)
    users.loc[len(users)] = [username, password]


@app.exception_handler(StarletteHTTPException)
async def not_found_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "path": request.url.path},
            status_code=404
        )
    raise exc
