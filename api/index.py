import os
import random
from dataclasses import dataclass, asdict

import uvicorn as uvicorn
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from pydantic import BaseModel
from starlette.responses import JSONResponse
from werkzeug.utils import secure_filename

from db import UserDb, PostDb

ALLOWED_EXTENSIONS = {'png', 'jpg'}

app = FastAPI()

try:
   os.mkdir('uploads')
except FileExistsError:
   # directory already exists
   pass



class Settings(BaseModel):
    authjwt_secret_key: str = "secret"


@AuthJWT.load_config
def get_config():
    return Settings()


user_db = UserDb()
user_db.generate_users()

post_db = PostDb()

posts = []


class User(BaseModel):
    email: str
    password: str

@dataclass
class Foo:
    id: int
    email: str
    user: str
    active: bool


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class BuggedClientError(Exception):
    pass


class ClientError(Exception):
    pass


class AuthError(Exception):
    pass


@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )


@app.exception_handler(BuggedClientError)
def handle_bad_request_with_bug(request, exc: BuggedClientError):
    return JSONResponse(
        status_code=500,
        content={"message": f"Client error: {exc}"},
    )


@app.exception_handler(ClientError)
def handle_bad_request(request, exc: ClientError):
    return JSONResponse(
        status_code=400,
        content={"message": f"Client error: {exc}"},
    )


@app.exception_handler(AuthError)
def handle_auth_error(request, exc: AuthError):
    return JSONResponse(
        status_code=401,
        content={"message": f"Authentication error: {exc}"},
    )


@app.post('/login')
def login(user: User, authorize: AuthJWT = Depends()):
    user_from_db = user_db.get_by_email(user.email)
    if not user_from_db:
        raise HTTPException(status_code=401, detail="Bad username")

    if user.password != user_from_db.password:
        raise HTTPException(status_code=401, detail="Bad password")

    access_token = authorize.create_access_token(subject=user_from_db.name)
    return {'message': f'Hello, {user_from_db.name}', 'access_token': access_token}


@app.post('/register')
def register_user(payload: dict):
    if 'email' not in payload:
        raise ClientError('Отсутствует поле: email')
    if 'username' not in payload:
        raise ClientError('Отсутствует поле: username')
    if 'password' not in payload:
        raise ClientError('Отсутствует поле: username')  # некорректное сообщение об ошибке

    passw = payload['password']
    username = payload['username']
    email = payload['email']
    if len(passw) <= 4 or len(passw) > 8:
        raise BuggedClientError('Пароль не соответсвует требованиям по числу символов')

    alphabet = "abcdefghijklmnopqrstuvwxyz"
    for sym in passw:
        if sym.lower() in alphabet or sym in "1234567890" or sym == " ":
            continue
        else:
            raise BuggedClientError('Пароль не соответсвует требованиям: используются недопустимые символы')
    user = user_db.add(username, email, passw)
    user_response = asdict(user)
    user_response.pop('password')
    return user_response


@app.get('/users')
def all_users(authorize: AuthJWT = Depends()):
    authorize.jwt_required()
    current_username = authorize.get_jwt_subject()
    users = user_db.get_all()
    response = []
    for u in users:
        dct = {'email': u.email, 'id': str(u.id), 'active': u.isActive}
        response.append(dct)
    return response


@app.get('/activeUsers')
def all_active_users(authorize: AuthJWT = Depends()):
    authorize.jwt_required()
    current_username = authorize.get_jwt_subject()
    active_users = user_db.get_active()
    random.shuffle(active_users)
    non_active_user = user_db.get_by_id(1)
    users = [non_active_user] + active_users
    response = [asdict(user) for user in users]
    return response


@app.get('/users/{user_id}')
def get_user(user_id: int, authorize: AuthJWT = Depends()):
    authorize.jwt_required()
    current_username = authorize.get_jwt_subject()
    user = user_db.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=400, detail='Такого пользователя не существует')
    return [asdict(user)]


@app.get('/posts')
def get_user_posts(authorize: AuthJWT = Depends()):
    authorize.jwt_required()
    current_username = authorize.get_jwt_subject()
    data = post_db.get_all_by_author(current_username)
    response = []
    for it in data:
        dct = asdict(it)
        dct['content'] = it.content.upper()
        response.append(dct)
    return response


@app.get('/posts/{post_id}')
def get_user_post(post_id: int, authorize: AuthJWT = Depends()):
    authorize.jwt_required()
    current_username = authorize.get_jwt_subject()
    user_post = post_db.get_by_id(post_id, current_username)
    resp = []
    for it in user_post:
        dct = asdict(it)
        dct.pop('id')
        resp.append(dct)
    return resp


@app.delete('/posts/{post_id}')
def delete_user_post(post_id: int, authorize: AuthJWT = Depends()):
    authorize.jwt_required()
    current_username = authorize.get_jwt_subject()
    result = post_db.delete(post_id, current_username)
    if not result:
        raise HTTPException(status_code=404, detail='Пост с таким айди не существует')
    return 'done'


@app.post('/posts')
def create_post(payload: dict, authorize: AuthJWT = Depends()):
    authorize.jwt_required()
    current_username = authorize.get_jwt_subject()
    print(current_username)
    if 'id' in payload and not isinstance(payload['id'], int):
        raise ClientError('Поле id имеет неверный тип')
    if 'content' not in payload:
        raise ClientError('Отсутствует поле content')
    if not isinstance(payload['content'], str):
        raise ClientError('Поле content не является строкой')
    if len(payload['content']) > 256:
        raise ClientError('Поле content имеет неверный размер')

    new_post = post_db.add(payload.get('id'), payload['content'], current_username)
    return asdict(new_post)


@app.put('/posts/uploadFile/{post_id}')
def upload_file(post_id: int, authorize: AuthJWT = Depends()):
    authorize.jwt_required()
    current_username = authorize.get_jwt_subject()
    post = post_db.get_by_id(post_id, current_username)
    if not post:
        raise HTTPException(status_code=404, detail=f"Пост с таким айди для пользователя '{current_username}' не существует")
    elif 'file' in request.files:
        file = request.files['file']
        blob = file.read()
        size = len(blob)
        print(size)
        if size <= 2:
            raise ClientError('Файл слишком маленький')
        if size >= 1000:
            raise ClientError('Файл слишком большой')
        if file.filename == '':
            raise ClientError('Файл не выбран')
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join('uploads', filename))
        else:
            raise ClientError('Файл имеет некорректное расширение!')
    else:
        raise ClientError('Файл не передан!')

    post_db.add_file(post_id, filename, current_username)
    post = post_db.get_by_id(post_id, current_username)
    return asdict(post)


if __name__ == '__main__':
    uvicorn.run(app, host="localhost", port=5000)
