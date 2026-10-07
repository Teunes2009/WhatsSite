from sqlitedict import SqliteDict

with SqliteDict("Messages.db") as db:
    print(db.keys())
    for chat in db.keys():
        print(chat)
        db[chat] = []
        print(db[chat])
        if chat == "Test":
            del db[chat]
    db.commit()