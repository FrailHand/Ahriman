import base64
import hashlib
import getpass
import pymongo
import random
import string


DATABASE_HOST = 'localhost'
DATABASE_PORT = 27017

def create_user(user, password):
    collec = pymongo.MongoClient(DATABASE_HOST, DATABASE_PORT).ahriman.credentials
    result = collec.find_one({"_id": user})
    if result is not None:
        print('Username already in use')
        return

    hasher = hashlib.sha512()

    salt = ''.join(random.choice(string.printable) for i in range(10))
    hasher.update(password.encode())
    hasher.update(salt.encode())
    hash = base64.b64encode(hasher.digest()).decode()

    result = collec.insert_one({"_id": user, "pwd":hash, "salt": salt})
    if result.acknowledged:
        print('User created')
    else:
        print('Failed to create user')


if __name__ == "__main__":
    user = input("Username: ")
    password = getpass.getpass()
    create_user(user, password)
