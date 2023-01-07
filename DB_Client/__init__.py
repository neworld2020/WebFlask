import pyodbc


class DB_Client:
    def __init__(self):
        self.connect_str = \
            """Driver={ODBC Driver 18 for SQL Server};
               Server=tcp:interest-based-memo-app-db.database.windows.net,1433;
               Database=CorpusDB;
               Uid=app_root;Pwd=db_774225688;
               Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"""
        client = pyodbc.connect(self.connect_str)
        self.cursor = client.cursor()

    def select(self, cmd: str):
        # with result
        self.cursor.execute(cmd)
        return self.cursor.fetchall()

    def run(self, cmd: str):
        # without result
        self.cursor.execute(cmd)
        self.cursor.commit()
