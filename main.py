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
    ChatName = ChatName.strip()
    print("Creating chat", ChatName, "with members", Members, "by", Name)
    # with SqliteDict("Chats.db") as db:
    #     print(db.keys(), ChatName, db.get_key(ChatName, []), "hoi")
    with SqliteDict("Messages.db") as db:
        print(list(db.keys()), db.get(ChatName, [1]), "hoi", ChatName in db)
        if ChatName.strip() in db:
            raise HTTPException(status_code=404, detail=f"{ChatName} already exists, {db.get(ChatName, [])}")
        if ChatName in ["Main", "Send", "GetMessages", "NewMember", "Leave", ""]:
            raise HTTPException(status_code=404, detail="Chat name is invalid")
        db[ChatName] = []
        print(db[ChatName], "created chat", ChatName)
        db.commit()
    with SqliteDict("Chats.db") as db:
        NewMembers = [Name]
        for Member in Members.split(","):
            Member = Member.strip()
            print(Member, Member in db)
            if Member in db:
                Chats = db[Member]
                Chats.append(ChatName)
                db[Member] = Chats
                NewMembers.append(Member)
                # db[Member].append(ChatName)
        print("New members:", NewMembers)
        print(db[Name], ChatName)
        Chats = db[Name]
        Chats.append(ChatName)
        db[Name] = Chats
        # db[Name].append(ChatName)
        print(db[Name], NewMembers, ChatName, "added chat", ChatName, "to members", NewMembers)
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
        print(list(db.keys()), Name, db[Name], db.get(Name, []))
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
        print(list(db.keys()))
        if ChatName not in db:
            db[ChatName] = []
        Messages = db[ChatName]
        Messages.append({"Name": Name, "Text": Message})
        db[ChatName] = Messages
        db.commit()
    return templates.TemplateResponse(
        request,
        "Message.html",
        {"Messages": Messages}
    )

@app.post("/Chats/GetMessages")
async def get_messages(request: Request, ChatName: str = Form(...)):
    print(ChatName)
    with SqliteDict("Messages.db") as db:
        Messages = db.get(ChatName, [])
        # print(Messages)
    return templates.TemplateResponse(
        request,
        "Message.html",
        {"Messages": Messages}
    )

@app.post("/Chats/NewMember")
async def new_member(request: Request, ChatName: str = Form(...), NewMember: str = Form(...), Name: str = Form(...)):
    Members = []
    print(Name, "added", NewMember, "to", ChatName)
    with SqliteDict("Chats.db") as db:
        if ChatName not in db[NewMember]:
            Chats = db[NewMember]
            Chats.append(ChatName)
            db[NewMember] = Chats
            # db[NewMember].append(ChatName)
            db.commit()
            for Member in db.keys():
                if ChatName in db[Member]:
                    Members.append(Member)
    return templates.TemplateResponse(
        request,
        "Members.html",
        {"Members": Members}
    )

@app.post("/Chats/GetMembers")
async def get_members(request: Request, ChatName: str = Form(...)):
    Members = []
    print(ChatName)
    with SqliteDict("Chats.db") as db:
        for Member in db.keys():
            if ChatName in db[Member]:
                Members.append(Member)
    return templates.TemplateResponse(
        request,
        "Members.html",
        {"Members": Members}
    )

@app.post("/Chats/Leave")
async def leave_chat(request: Request, ChatName: str = Form(...), Name: str = Form(...)):
    print(Name, "left", ChatName)
    if ChatName == "Main":
        raise HTTPException(status_code=404, detail="You cannot leave the Main chat")
    Chats = []
    with SqliteDict("Chats.db") as db:
        if ChatName in db[Name]:
            Chats = db[Name]
            Chats.remove(ChatName)
            db[Name] = Chats
            # db[Name].remove(ChatName)
            db.commit()
        # Chats = db.get(Name, [])
    return templates.TemplateResponse(
        request,
        "ingelogd.html",
        {"naam": Name, "Messages": Chats}
    )

@app.post("/Chats/{ChatName}")
async def chat(request: Request, ChatName: str, Name: str = Form(...)):
    with SqliteDict("Messages.db") as db:
        if ChatName not in db:
            db[ChatName] = []
            db.commit()
        Messages = db[ChatName]
        print(Messages)
    with SqliteDict("Chats.db") as db:
        Members = []
        for Member in db.keys():
            if ChatName in db[Member]:
                Members.append(Member)
        print(Members)
    return templates.TemplateResponse(
        request,
        "chat.html",
        {"ChatName": ChatName, "Messages": Messages, "Name": Name, "Members": Members}
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
