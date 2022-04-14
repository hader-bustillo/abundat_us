from cryptography.fernet import Fernet
import os


def encrypt_string(msg:str):
    key = os.getenv('FERNET_KEY')
    print("the fenrt is %s", key)
    key_byte = key.encode(encoding='UTF-8')
    f = Fernet(key_byte)
    encrypted_bytes = f.encrypt(msg.encode(encoding='UTF-8'))
    return encrypted_bytes.decode(encoding='UTF-8')


def decrypt_string(msg:str):
    key = os.getenv('FERNET_KEY')
    print("the fenrt is %s", key)
    key_byte = key.encode(encoding='UTF-8')
    f = Fernet(key_byte)
    decrypted_bytes = f.decrypt(msg.encode(encoding='UTF-8'))
    return decrypted_bytes.decode(encoding='UTF-8')
