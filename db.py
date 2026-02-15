import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="flaskapp-db.c5ko68gmyjyf.ap-south-1.rds.amazonaws.com",
        user="admin",
        password="sarvs7899",
        database="event_management",
        port=3306
    )
