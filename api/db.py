from collections import namedtuple
from dataclasses import dataclass, asdict
from typing import Optional
from tinydb import TinyDB, Query
db = TinyDB('db.json')


@dataclass
class User:
    id: int
    name: str
    email: str
    isActive: bool
    password: str


@dataclass
class Post:
    id: int
    content: str
    file: Optional[str]
    author: str



class UserDb:

    def generate_users(self):
        self.add('ShishkaCat', 'shiiish@ya.ru', 'pizza', False)
        self.add('PlushkaCat', 'pluuush@gmail.com', 'cheeze', True)
        self.add('Venya', 'veniamin@yandex.ru', 'seliger', False)

    def __init__(self):
        self.counter = 0
        self.users: dict[int, User] = {}
        self.table = db.table('users')

    def add(self, name: str, email: str, password: str, is_active: bool = True) -> User:
        user_id = self.counter + 1
        self.counter += 1
        user = User(user_id, name, email, is_active, password)
        self.users[user_id] = user
        self.table.insert(asdict(user))
        return user

    def get_by_id(self, id: int) -> Optional[User]:
        return self.users.get(id)

    def get_by_email(self, email: str) -> Optional[User]:
        for user in self.users.values():
            if user.email == email:
                return user
        return None

    def get_all(self):
        return list(sorted(list(self.users.values()), key=lambda user: user.id))

    def get_active(self):
        data = [it for it in self.users.values() if it.isActive]
        return data


class PostDb:

    def __init__(self):
        self.counter = 0
        self.posts: list[Post] = []

    def add(self, post_id, content: str, author: str) -> Post:
        if post_id is None:
            post_id = self.counter + 1
            self.counter += 1
        post = Post(post_id, content, None, author)
        self.posts.append(post)
        return post

    def add_file(self, post_id, filename: str, author: str) -> list[Post]:
        post = self.get_by_id(post_id, author)
        for p in post:
            p.file = filename
        return post

    def get_all_by_author(self, author: str):
        user_posts = [p for p in self.posts if p.author == author]
        user_posts.sort(key=lambda it: it.id)
        return user_posts

    def get_by_id(self, post_id: int, author: str):
        return [p for p in self.posts if p.id == post_id and p.author == author]

    def delete(self, post_id, author):
        if post_id is None:
            for_deleted = [p for p in self.posts if p.author == author]
        else:
            for_deleted = [p for p in self.posts if p.id == post_id]
            if len(for_deleted) == 0:
                return None
        for it in for_deleted:
            self.posts.remove(it)
        return True
