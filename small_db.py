USERS = dict()


class User:
    def __init__(self):
        self.address = ''

    def add_address(self, address):
        self.address = address

    def clean_address(self):
        self.address = ''


def add_user(id):
    USERS[id] = User()

