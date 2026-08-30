#Verbindung, execute, commit
import os
import psycopg2
from dotenv import load_dotenv
load_dotenv()


class BaseRepo:
    def __init__(self):
        self.connection = psycopg2.connect(
            host = os.getenv("DB_HOST"),
            port = os.getenv("DB_PORT"),
            database = os.getenv("DB_NAME"),
            user = os.getenv("DB_USER"),
            password = os.getenv("DB_PASSWORD")
        )

        self.cursor = self.connection.cursor()

    def execute(self, query, params):
        self.cursor.execute(query, params)
        self.connection.commit()
        # -> Methode, die einen 'commit' Befehl zu der Datenbank auslöst -> Daten werden von Arbeitsspeicher dauerhaft in die DB übernomen


    def fetchall(self, query, params=None):
        self.cursor.execute(query, params)
        return self.cursor.fetchall()


    def fetchone(self, query, params=None):
        self.cursor.execute(query, params)
        return self.cursor.fetchone()

    def create(self, query, createdObject: object):
        pass
        #TODO createdObject.id = self.fetchone(query)




