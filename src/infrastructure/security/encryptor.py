from cryptography.fernet import Fernet, InvalidToken


class Encryptor:
    def __init__(self, key):
        self.key = key
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