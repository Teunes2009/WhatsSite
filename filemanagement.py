from sqlitedict import SqliteDict

#deze hoort eigenlijk niet bij mijn project, maar is veel te handig om weg te gooien voor als ik ooit nog iets zou willen veranderen

with SqliteDict("data/Messages.db") as db:
    for chat in db.keys():
        del db[chat]
    db.commit()

with SqliteDict("data/Chats.db") as db:
    for user in db.keys():
        del db[user]
    db.commit()

with SqliteDict("data/wachtwoorden.db") as db:
    for chat in db.keys():
        del db[chat]
    db.commit()