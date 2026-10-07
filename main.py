from fastapi import FastAPI, Form, Request, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from httpcore import request
from sqlitedict import SqliteDict

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# with SqliteDict("wachtwoorden.db") as db:
#     with SqliteDict("Messages.db") as db:

#         print(db.keys())
#         for user in db.keys():
#             print(user, db[user])
#             del db[user]
#             # print(user, db[user], db[user])
#             # password = db[user].get("pincode")
#             # if password != None:
#             #     print("pincode found for user", user, ":", password)
#             #     del db[user]
#             #     #print(db[user])
#             #     db[user] = password
#         db.commit()

# with SqliteDict("Messages.db") as db:
#     for chat in db:
#         print(chat, db[chat])
#     del db["Test"]
#     db.commit()

@app.get("/")
async def home():
    return FileResponse("static/pages/home.html")

@app.get("/project")
async def project():
    return FileResponse("static/pages/form.html")

@app.get("/about")
async def about():
    return FileResponse("static/pages/about.html")

# @app.get("/zoek")
# async def zoek(term: str):
#     return {"je zocht naar": term}

@app.post("/verstuur")
async def verstuur(request: Request, naam: str = Form(...), wachtwoord: str = Form(...)):
    with SqliteDict("wachtwoorden.db") as db:
        print(naam, wachtwoord)
        if naam == "Teun" and wachtwoord == "1":
            return RedirectResponse(url="/admin")

        if naam in db:
            if db[naam]["wachtwoord"] == wachtwoord:
                return RedirectResponse(url="/login")
            return RedirectResponse(url="/form", status_code=303)

        db[naam] = {"wachtwoord": wachtwoord}
        db.commit()
    return RedirectResponse(url="/login")

@app.post("/login")
async def login(request: Request, naam: str = Form(...)):
    with SqliteDict("Chats.db") as db:
        if naam not in db:
            db[naam] = ["Main"]
            db.commit()
        CurrentChats = db[naam]
    print(CurrentChats)
    with SqliteDict("Messages.db") as db:
        Messages = {}
        for Chat in CurrentChats:
            if Chat not in db:
                db[Chat] = []
                db.commit()
            Messages[Chat] = db[Chat]
        print(Messages)
        # messages = db[naam].get("", [])
    return templates.TemplateResponse(
        request,
        "ingelogd.html",
        {"naam": naam, "Messages": Messages}
    )

@app.post("/Create")
async def create_chat(request: Request, ChatName: str = Form(...), Name: str = Form(...), Members: str = Form(...)):
    print("Creating chat", ChatName, "with members", Members, "by", Name)
    # with SqliteDict("Chats.db") as db:
    #     print(db.keys(), ChatName, db.get_key(ChatName, []), "hoi")
    with SqliteDict("Messages.db") as db:
        print(db.keys(), db.get(ChatName, [1]), "hoi", ChatName in db)
        if ChatName.strip() in db:
            raise HTTPException(status_code=400, detail=f"{ChatName} already exists, {db.get(ChatName, [])}")
        if ChatName.strip() in ["Main", "Send", "GetMessages", ""]:
            raise HTTPException(status_code=400, detail="Chat name is invalid")
        db[ChatName] = []
        print(db[ChatName], "created chat", ChatName)
        db.commit()
    with SqliteDict("Chats.db") as db:
        NewMembers = [Name]
        for Member in Members.split(","):
            print(Member, Member in db)
            if Member in db:
                NewMembers.append(Member)
                db[Member].append(ChatName)
        print("New members:", NewMembers)
        db[Name].append(ChatName)
        print(db[Name], NewMembers)
        Chats = db[Name]
        db.commit()
    return templates.TemplateResponse(
        request,
        "ChatList.html",
        {"naam": Name, "Messages": Chats}
    )

@app.post("/GetChats")
async def get_chats(request: Request, Name: str = Form(...)):
    with SqliteDict("Chats.db") as db:
        print(db.keys(), Name, db[Name], db.get(Name, []))
        CurrentChats = db.get(Name, [])
    print(CurrentChats)
    return templates.TemplateResponse(
        request,
        "ChatList.html",
        {"naam": Name, "Messages": CurrentChats}
    )

@app.post("/Chats/Send")
async def send(request: Request, Message: str = Form(...), ChatName: str = Form(...), Name: str = Form(...)):
    print(Name, "sent ", Message, "in", ChatName)
    print(Message, ChatName, Name)
    with SqliteDict("Messages.db") as db:
        print(db.keys())
        if ChatName not in db:
            db[ChatName] = []
        Messages = db[ChatName]
        Messages.append({"Name": Name, "Text": Message})
        db[ChatName] = Messages
        db.commit()
    return templates.TemplateResponse(
        request,
        "Message.html",
        {"ChatName": ChatName, "Messages": Messages}
    )

@app.post("/Chats/GetMessages")
async def get_messages(request: Request, ChatName: str = Form(...)):
    print(ChatName)
    with SqliteDict("Messages.db") as db:
        if ChatName not in db:
            db[ChatName] = []
        Messages = db[ChatName]
        # print(Messages)
    return templates.TemplateResponse(
        request,
        "Message.html",
        {"ChatName": ChatName, "Messages": Messages}
    )

@app.post("/Chats/{ChatName}")
async def chat(request: Request, ChatName: str, Name: str = Form(...)):
    with SqliteDict("Messages.db") as db:
        if ChatName not in db:
            db[ChatName] = []
            db.commit()
        Messages = db[ChatName]
        print(Messages)
        return templates.TemplateResponse(
            request,
            "chat.html",
            {"ChatName": ChatName, "Messages": Messages, "Name": Name}
        )

@app.post("/admin")
async def admin(request: Request):
    with SqliteDict("wachtwoorden.db") as db:
        all_info = list(db.items())
        print(all_info)
    with SqliteDict("Messages.db") as db:
        all_messages = list(db.items())
        print(all_messages)
    return templates.TemplateResponse(
        request,
        "admin.html",
        {"info": all_info, "messages": all_messages}
    )

@app.get("/bedankt")
async def bedankt():
    return FileResponse("static/pages/bedankt.html")

@app.get("/form")
async def form():
    return FileResponse("static/pages/form.html")
