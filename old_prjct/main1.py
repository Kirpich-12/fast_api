import csv
import uuid
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
import pandas as pd

app = FastAPI()
app.mount("/static", StaticFiles(directory='static'), name='static')
#app.mount("/sourses", StaticFiles(directory='sourses'), name='sourses')
templates = Jinja2Templates(directory="templates")
USERS = "users.csv"
SESSION_TTL = timedelta(10)
sessions = {}
white_urls = ['/', '/login']


#Контроль автризации и сессии
@app.middleware("http")
async def check_session(request: Request, call_next):
    print('path')
    print(request.url.path.startswith("/static") or request.url.path in white_urls)
    if request.url.path.startswith("/static") or request.url.path in white_urls:
        return await call_next(request)
    
    
    session_id =  request.cookies.get("session_id")
    print('id')
    print(session_id not in sessions)
    if session_id not in sessions:
        return RedirectResponse(url="/")
    
    create_session = sessions[session_id]
    print('time')
    print(datetime.now - create_session > SESSION_TTL)
    if datetime.now - create_session > SESSION_TTL:
        del sessions[session_id]
        return RedirectResponse(url="/")



#Маршутизация
@app.get('/', response_class=HTMLResponse)
@app.get('/login', response_class=HTMLResponse)
def get_login_page(request: Request):
    return templates.TemplateResponse("index.html", {"request":request})

@app.post("/login")
def login(request: Request,
          username:str = Form(...),
          password:str = Form(...)):
    users = pd.read_csv(USERS)
    print(username in users['user'])
    if username in users['user']:
        if str(users[users["user"] == username].values[0][1]) == password:
            session_id = str(uuid.uuid4())
            sessions[session_id] = datetime.now()
            response = RedirectResponse(url=f'/home/{username}',status_code=302)
            response.set_cookie(key="session_id", value=session_id)
            return response
    return templates.TemplateResponse("login.html",
                                       {"request":request,
                                        "error":"Неверный логин"})


@app.get('/home/admin', response_class=HTMLResponse)
def get_home_page(request: Request):
    return templates.TemplateResponse("home.html", {"request":request})

