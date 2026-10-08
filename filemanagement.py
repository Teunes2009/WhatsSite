from sqlitedict import SqliteDict

with SqliteDict("Messages.db") as db:
    print(list(db.keys()))
    for chat in db.keys():
        print(chat)
        db[chat] = []
        print(db[chat])
        if chat == "Test":
            del db[chat]
    db.commit()

with SqliteDict("Chats.db") as db:
    print(list(db.keys()))
    for user in db.keys():
        print(user, db[user])
        if "Test" in db[user]:
            Chats = db[user]
            Chats.remove("Test")
            db[user] = Chats
            print(user, db[user])
    db.commit()