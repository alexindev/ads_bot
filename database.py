import sqlite3

class Database:
    def __init__(self):
        self.connect = sqlite3.connect('db.qslite3')
        self.cursor = self.connect.cursor()


