import sqlite3
from sqlite3 import Error


def create_connection(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(sqlite3.version)
        return conn
    except Error as e:
        print(e)
    return conn

def create_user(conn, project):
    """
    Create a new project into the projects table
    :param conn:
    :param project:
    :return: project id
    """
    sql = ''' INSERT INTO Users(UUID,name,vaccination_status,last_screening_date)
              VALUES(?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, project)
    conn.commit()
    

def search_all_users(conn,uuid):
    """
    Query all rows in the tasks table
    :param conn: the Connection object
    :return:
    """
    cur = conn.cursor()
    cur.execute('''SELECT * FROM Users WHERE UUID=?''', (uuid,))
    row = cur.fetchone()
    return row
         
        

def delete_user(conn, uuid):
    """
    Delete a task by task id
    :param conn:  Connection to the SQLite database
    :param UUID: UUID of the User
    :return:
    """
    sql = 'DELETE FROM Users WHERE UUID=?'
    cur = conn.cursor()
    cur.execute(sql, (uuid,))
    conn.commit()

    #from datetime import datetime
    #date_time_str = '2021-03-15 11:50:23.040258'
    #date_time_obj = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S.%f')
    #x = datetime.now()
    #Y = x - date_time_obj
    #Y.total_seconds()/3600



