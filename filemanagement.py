from sqlitedict import SqliteDict

with SqliteDict("Messages.db") as db:
    print(list(db.keys()))
    for chat in db.keys():
        del db[chat]
    db.commit()

with SqliteDict("Chats.db") as db:
    print(list(db.keys()))
    for user in db.keys():
        del db[user]
    db.commit()

with SqliteDict("wachtwoorden.db") as db:
    print(list(db.keys()))
    for chat in db.keys():
        del db[chat]
    db.commit()