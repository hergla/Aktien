import sys
from werkzeug.security import generate_password_hash
from app import app, db, User

def add_user(username, password):
    with app.app_context():
        existing = User.query.filter_by(username=username).first()
        if existing:
            print(f"Fehler: Benutzer '{username}' existiert bereits.")
            return
        
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        print(f"Benutzer '{username}' erfolgreich angelegt.")

def delete_user(username):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"Fehler: Benutzer '{username}' nicht gefunden.")
            return
        
        db.session.delete(user)
        db.session.commit()
        print(f"Benutzer '{username}' gelöscht.")

def list_users():
    with app.app_context():
        users = User.query.all()
        print("\nVorhandene Benutzer:")
        for u in users:
            print(f" - ID: {u.id} | Name: {u.username}")
        print()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Nutzung:")
        print("  python user_admin.py add <username> <passwort>")
        print("  python user_admin.py del <username>")
        print("  python user_admin.py list")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == 'add' and len(sys.argv) == 4:
        add_user(sys.argv[2], sys.argv[3])
    elif cmd == 'del' and len(sys.argv) == 3:
        delete_user(sys.argv[2])
    elif cmd == 'list':
        list_users()
    else:
        print("Ungültige Befehlsparameter.")