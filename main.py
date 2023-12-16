import os

from fastapi import FastAPI, Depends, Request, Response, status
from starlette.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi_login.exceptions import InvalidCredentialsException
from fastapi_login import LoginManager
from fastapi import Request
from fastapi import Form
from typing_extensions import Annotated
from fastapi.responses import ORJSONResponse


class NotAuthenticatedException(Exception):
    pass
    
app = FastAPI()
SECRET = "super-secret-key"
manager = LoginManager(SECRET, '/login', use_cookie=True, custom_exception=NotAuthenticatedException)
templates = Jinja2Templates(directory="templates")


DB = {
    'users': {
        'yuriyvolokh@mail.com': {
            'name': 'Yurii Volokh',
            'password': 'hunter2'
        }
    }
}

def query_user(user_id: str):
    return DB['users'].get(user_id)


@manager.user_loader()
def load_user(user_id: str):
    user = DB['users'].get(user_id)
    return user
    
 
@app.exception_handler(NotAuthenticatedException)
def auth_exception_handler(request: Request, exc: NotAuthenticatedException):
    """
    Redirect the user to the login page if not logged in
    """
    return RedirectResponse(url='/login')
    

@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

    
@app.post('/login')
def login(data: OAuth2PasswordRequestForm = Depends()):
    email = data.username
    password = data.password
    user = query_user(email)
    if not user:
        raise InvalidCredentialsException
    elif password != user['password']:
        raise InvalidCredentialsException

    token = manager.create_access_token(data={'sub': email})
    response = RedirectResponse(url="/index",status_code=status.HTTP_302_FOUND)
    manager.set_cookie(response, token)
    return response


@app.get('/index')
async def index(request: Request, user=Depends(manager), param: str = ""):
    user_names = os.listdir("./static")
    user_name = user.get("name")
    thedir = ""
    if user_name not in user_names:
        os.mkdir(f"./static/{user_name}")
    if not param:
        thedir = f"./static/{user_name}"
        directory_folders = [ name for name in os.listdir(thedir) if os.path.isdir(os.path.join(thedir, name)) ]
        directory_files = [ name for name in os.listdir(thedir) if not os.path.isdir(os.path.join(thedir, name)) ]
    elif os.path.isdir(f"./static/{user_name}/{param}"):
        thedir = f"./static/{user_name}/{param}"
        directory_folders = [ os.path.join(param, name) for name in os.listdir(thedir) if os.path.isdir(os.path.join(thedir, name)) ]
        directory_files = [ os.path.join(param, name) for name in os.listdir(thedir) if not os.path.isdir(os.path.join(thedir, name)) ]
    else:
        directory_files = []
        directory_folders = []

    context = {'request': request,
               "file": param,
               "directory_folders": directory_folders,
               "directory_files": directory_files}
    return templates.TemplateResponse("directory.html", context)


@app.get("/new_file")
async def add_file(request: Request, user=Depends(manager), param: str = ""):
    context = {"request": request, "param": param}
    return templates.TemplateResponse("new_file.html", context)

@app.post("/new_file", status_code=201, response_class=ORJSONResponse)
async def add_file(request: Request, user=Depends(manager), title: str = Form(...), content: str = Form(...)):
    context = {"request": request}
    with open(os.path.join("static", user.get("name"), title), "w") as fout:
        fout.write(content)
    response = RedirectResponse(url="/index", status_code=status.HTTP_302_FOUND)
    return response

#@app.post("/edit_file", status_code=201, response_class=ORJSONResponse)
#async def edit_file(request: Request, user=Depends(manager), title: str = Form(...), content: str = Form(...)):
#    context = {"request": request}
#    filename = os.path.join("static", user.get("name"), title)
#    os.remove(filename)
#    with open(os.path.join("static", user.get("name"), title), "w") as fout:
#        fout.write(content)
#    response = RedirectResponse(url="/index", status_code=status.HTTP_302_FOUND)
#    return response


@app.get('/edit_file')
async def edit_file(request: Request, user=Depends(manager), param: str = ""):
    content = ""
    user_folder = user.get("name")
    filename = os.path.join(os.getcwd(), "static", user_folder, param)
    with open(filename) as fin:
        content = fin.read()
    context = {'request': request,
               "title": param,
               "content": content}
    return templates.TemplateResponse("edit_file.html", context)


@app.get("/delete_file")
async def delete_file(request: Request, user=Depends(manager), param: str = ""):
    filename = os.path.join("static", user.get("name"), param)
    if os.path.exists(filename):
        os.remove(filename)
    response = RedirectResponse(url="/index", status_code=status.HTTP_302_FOUND)
    return response


@app.get("/move_to")
async def move_to(request: Request, user=Depends(manager), param: str = ""):
    filename = os.path.join("static", user.get("name"), param)
    dirname = os.path.dirname(filename)
    files = os.listdir(dirname)
    src_files = [ name for name in files if not os.path.isdir(os.path.join(dirname, name)) ]
    dst_folders = [ name for name in files if os.path.isdir(os.path.join(dirname, name)) ]

    context = {'request': request,
               "src_files": src_files,
               "dst_folders": dst_folders}
    return templates.TemplateResponse("moveto.html", context)


@app.post("/move_to", status_code=201, response_class=ORJSONResponse)
async def move_to(request: Request, user=Depends(manager), src: str = Form(...), dst: str = Form(...)):
    context = {"request": request}
    src_file = os.path.join("static", user.get("name"), src)
    dst_file = os.path.join("static", user.get("name"), dst, src)
    os.rename(src_file, dst_file)
    response = RedirectResponse(url="/index", status_code=status.HTTP_302_FOUND)
    return response


