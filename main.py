import os
import logging

from fastapi import FastAPI, Depends, Request, status
from starlette.responses import RedirectResponse, HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi_login.exceptions import InvalidCredentialsException
from fastapi_login import LoginManager
from fastapi import Form
from fastapi.responses import ORJSONResponse


class NotAuthenticatedException(Exception):
    pass


app = FastAPI()
SECRET = "super-secret-key"
manager = LoginManager(SECRET, '/login', use_cookie=True, custom_exception=NotAuthenticatedException)
templates = Jinja2Templates(directory="templates")
logging.basicConfig(filename="log.txt",
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)

logging.info("Running Urban Planning")

logger = logging.getLogger('urbanGUI')

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
    logger.info("Starting login")
    email = data.username
    password = data.password
    user = query_user(email)
    if not user:
        raise InvalidCredentialsException
    elif password != user['password']:
        raise InvalidCredentialsException

    logger.info("Login successful")
    token = manager.create_access_token(data={'sub': email})
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    manager.set_cookie(response, token)
    logger.info("Ending login")
    return response


@app.get('/')
async def index(request: Request, user=Depends(manager), param: str = ""):
    logger.info("Starting index page generating")
    user_names = os.listdir("./static")
    user_name = user.get("name")
    thedir = ""
    logger.info("Getting user folder")
    if user_name not in user_names:
        os.mkdir(f"./static/{user_name}")
    if not param:
        logger.info("Getting content of bfolder")
        thedir = f"./static/{user_name}"
        directory_folders = [name for name in os.listdir(thedir) if os.path.isdir(os.path.join(thedir, name))]
        directory_files = [name for name in os.listdir(thedir) if not os.path.isdir(os.path.join(thedir, name))]
    elif os.path.isdir(f"./static/{user_name}/{param}"):
        logger.info("Getting content of bfolder")
        thedir = f"./static/{user_name}/{param}"
        directory_folders = [os.path.join(param, name) for name in os.listdir(thedir) if os.path.isdir(os.path.join(thedir, name))]
        directory_files = [os.path.join(param, name) for name in os.listdir(thedir) if not os.path.isdir(os.path.join(thedir, name))]
    else:
        logger.info("Showing empty folder")
        directory_files = []
        directory_folders = []

    context = {'request': request,
               "file": param,
               "directory_folders": directory_folders,
               "directory_files": directory_files}
    logger.info("Ending index page generating")
    return templates.TemplateResponse("directory.html", context)


@app.get("/new_file")
async def add_file_render(request: Request, user=Depends(manager), param: str = ""):
    logger.info("Starting generating templat efile creation ")
    context = {"request": request, "param": param}
    logger.info("Ending generation template file creation")
    return templates.TemplateResponse("new_file.html", context)


@app.post("/new_file", status_code=201, response_class=ORJSONResponse)
async def add_file(request: Request, user=Depends(manager), title: str = Form(...), content: str = Form(...)):
    logger.info("Starting file creation")
    with open(os.path.join("static", user.get("name"), title), "w") as fout:
        fout.write(content)
    response = RedirectResponse(url="/index", status_code=status.HTTP_302_FOUND)
    logger.info("Ending file creation")
    return response


@app.get('/edit_file')
async def edit_file(request: Request, user=Depends(manager), param: str = ""):
    logger.info("Starting file edit template generation")
    content = ""
    user_folder = user.get("name")
    filename = os.path.join(os.getcwd(), "static", user_folder, param)
    logger.info("dit template generation. Reading file")
    with open(filename) as fin:
        content = fin.read()
    context = {'request': request,
               "title": param,
               "content": content}
    logger.info("Ending file edit template generation")
    return templates.TemplateResponse("edit_file.html", context)


@app.get("/delete_file")
async def delete_file(request: Request, user=Depends(manager), param: str = ""):
    logger.info("Starting deleting file")
    filename = os.path.join("static", user.get("name"), param)
    if os.path.exists(filename):
        os.remove(filename)
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    logger.info("Ending deleting file")
    return response


@app.get("/move_to")
async def move_to_render(request: Request, user=Depends(manager), param: str = ""):
    logger.info("Starting move to render template")
    filename = os.path.join("static", user.get("name"), param)
    dirname = os.path.dirname(filename)
    files = os.listdir(dirname)
    logger.info("Creating possible filenames for move")
    src_files = [os.path.join(os.path.dirname(param), name)
                 for name in files
                 if not os.path.isdir(os.path.join(dirname, name))]
    logger.info("Creating filename list of folders for possible move")
    dst_folders = [name
                   for name in files
                   if os.path.isdir(os.path.join(dirname, name))]

    context = {'request': request,
               "src_files": src_files,
               "dst_folders": dst_folders}
    logger.info("Ending move to render template")
    return templates.TemplateResponse("moveto.html", context)


@app.post("/move_to", status_code=201, response_class=ORJSONResponse)
async def move_to(request: Request, user=Depends(manager), src: str = Form(...), dst: str = Form(...)):
    logger.info("Starting to move file")
    logger.info("Calculating file names path")
    src_file = os.path.join("static", user.get("name"), src)
    dst_file = os.path.join("static", user.get("name"), dst, src)
    if dst == "..":
        logger.info("Starting move to paremt folder")
        dst_file = os.path.join(
                os.path.dirname(os.path.dirname(src_file)),
                os.path.basename(src_file))
    os.rename(src_file, dst_file)
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    logger.info("Ending to move file")
    return response
