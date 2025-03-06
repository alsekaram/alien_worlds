from cryptography.fernet import Fernet, InvalidToken


class Encryptor:
    def __init__(self, key):
        # self.key = b'_yyyQ2NgL06AumL67HfgB7XK53sqRYCqyCaudVbdCOB='  # Функция для загрузки ключа
        self.key = key
        # self.key = load_encryption_key()  # Функция для загрузки ключа
        self.fernet = Fernet(self.key)

    def encrypt(self, data):
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, data):
        if data:
            try:
                return self.fernet.decrypt(data.encode()).decode()
            except InvalidToken as e:
                # print(e)
                return ''
        return None


if __name__ == '__main__':
    key = Fernet.generate_key()
    print(key)