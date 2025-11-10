import hashlib


ll = ['1', '2']
print('1' in ll)

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    hash_object = hashlib.sha256(password.encode('utf-8'))
    return hash_object.hexdigest()

print(hash_password('asd'))