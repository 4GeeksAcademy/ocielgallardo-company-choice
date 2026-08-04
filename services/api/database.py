from tinydb import TinyDB

db = TinyDB('database.json')

contact_id = db.insert({'name': '', 'email': ''})
print(contact_id)  # Muestra un ID de documento entero, por ejemplo, 1