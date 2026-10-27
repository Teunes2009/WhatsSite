from fastapi import FastAPI, Form, Request, HTTPException, Query, Cookie
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from httpcore import request
from sqlitedict import SqliteDict
import secrets


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

COOKIES_MAX_LIFETIME = 60 * 60 * 24 * 30
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

# @app.post("/verstuur")
# @limiter.limit("3/minute")
# async def verstuur(request: Request, naam: str = Form(..., max_length=25), wachtwoord: str = Form(min_length=5)):
#     with SqliteDict("wachtwoorden.db") as db:
#         print(naam, wachtwoord)
#         if naam == "Teun" and wachtwoord == "1":
#             return RedirectResponse(url="/admin")

#         if naam in db:
#             if db[naam]["wachtwoord"] == wachtwoord:
#                 return RedirectResponse(url="/login")
#             return RedirectResponse(url="/form", status_code=303)

#         db[naam] = {"wachtwoord": wachtwoord}
#         db.commit()
#     return RedirectResponse(url="/login")


@app.post("/login")
@limiter.limit("3/minute")
async def login(request: Request, action: str = Form(...), naam: str = Form(...), wachtwoord: str = Form(min_length=5)):
    with SqliteDict("wachtwoorden.db") as db:
            print(naam, wachtwoord)
            if naam == "Teun" and wachtwoord == "1":
                return RedirectResponse(url="/admin")
    
            if naam in db:
                if action == "inloggen":
                    if db[naam]["wachtwoord"] == wachtwoord:
                        return RedirectResponse(url="/login")
                    raise HTTPException(status_code=403, detail="Ongeldig wachtwoord")
                raise HTTPException(status_code=403, detail="Ongeldige actie")
            else:
                if action == "inloggen":
                    raise HTTPException(status_code=404, detail=f"gebruiker {naam} bestaat niet")
                db[naam] = {"wachtwoord": wachtwoord}
                db.commit()
    with SqliteDict("Chats.db") as db:
        if naam not in db:
            if action == "inloggen":
                raise HTTPException(status_code=404, detail=f"gebruiker {naam} bestaat niet")
            db[naam] = ["Main"]
            db.commit()
        CurrentChats = db[naam]
    print(CurrentChats)
    with SqliteDict("Messages.db") as db:
        Messages = {}
        for Chat in CurrentChats:
            if Chat not in db:
                if action == "inloggen":
                    raise HTTPException(status_code=404, detail=f"Chat {Chat} bestaat niet")
                db[Chat] = []
                db.commit()
            Messages[Chat] = db[Chat]
        print(Messages)
        # messages = db[naam].get("", [])
    SessionID = secrets.token_hex(16)
    with SqliteDict("sessions.db") as db:
        db[SessionID] = naam
        db.commit()
    Response = templates.TemplateResponse(
        request,
        "ingelogd.html",
        {"naam": naam, "wachtwoord": wachtwoord, "Messages": Messages}
    )
    Response.set_cookie(key="UserID", value=SessionID, max_age=COOKIES_MAX_LIFETIME, httponly=True)
    return Response

@app.post("/Create")
@limiter.limit("5/minute")
async def create_chat(request: Request, ChatName: str = Form(...), Name: str = Form(...), Password: str = Form(...), Members: str = Form(...), Cookie: str = Cookie(default="")):
    with SqliteDict("sessions.db") as db:
        if db.get(Cookie) != Name:
            raise HTTPException(status_code=404, detail="Invalide sessie")
    with SqliteDict("wachtwoorden.db") as db:
        if db.get(Name, {}).get("wachtwoord") != Password:
            raise HTTPException(status_code=403, detail="Ongeldig wachtwoord")
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
@limiter.limit("35/minute")
async def get_chats(request: Request, Name: str = Form(...), Cookie: str = Cookie(default="")):
    with SqliteDict("sessions.db") as db:
        if db.get(Cookie) != Name:
            raise HTTPException(status_code=404, detail="Invalide sessie")
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
async def send(request: Request, Message: str = Form(...), ChatName: str = Form(...), Name: str = Form(...), Cookie: str = Cookie(default="")):
    with SqliteDict("Chats.db") as db:
        with SqliteDict("sessions.db") as dbS:
            if dbS.get(Cookie) not in db.get(ChatName):
                raise HTTPException(status_code=404, detail="Je zit niet in deze chat")
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
@limiter.limit("35/minute")
async def get_messages(request: Request, ChatName: str = Form(...), Cookie: str = Cookie(default="")):
    print(ChatName)
    with SqliteDict("Chats.db") as db:
        with SqliteDict("sessions.db") as dbS:
            if dbS.get(Cookie) not in db.get(ChatName):
                raise HTTPException(status_code=404, detail="Je zit niet in deze chat")
    with SqliteDict("Messages.db") as db:
        Messages = db.get(ChatName, [])
        # print(Messages)
    return templates.TemplateResponse(
        request,
        "Message.html",
        {"Messages": Messages}
    )

@app.post("/Chats/NewMember")
async def new_member(request: Request, ChatName: str = Form(...), NewMember: str = Form(...), Name: str = Form(...), Cookie: str = Cookie(default="")):
    with SqliteDict("Chats.db") as db:
        with SqliteDict("sessions.db") as dbS:
            if dbS.get(Cookie) not in db.get(ChatName):
                raise HTTPException(status_code=404, detail="Je zit niet in deze chat")
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

@limiter.limit("35/minute")
@app.post("/Chats/GetMembers")
async def get_members(request: Request, ChatName: str = Form(...), Cookie: str = Cookie(default="")):
    with SqliteDict("Chats.db") as db:
        with SqliteDict("sessions.db") as dbS:
            if dbS.get(Cookie) not in db.get(ChatName):
                raise HTTPException(status_code=404, detail="Je zit niet in deze chat")
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
@limiter.limit("10/minute")
async def leave_chat(request: Request, ChatName: str = Form(...), Name: str = Form(...), Cookie: str = Cookie(default="")):
    print(Name, "left", ChatName)
    with SqliteDict("Chats.db") as db:
        with SqliteDict("sessions.db") as dbS:
            if dbS.get(Cookie) not in db.get(ChatName):
                raise HTTPException(status_code=404, detail="Je zit niet in deze chat")
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
async def chat(request: Request, ChatName: str, Name: str = Form(...), Cookie: str = Cookie(default="")):
    with SqliteDict("Chats.db") as db:
        with SqliteDict("sessions.db") as dbS:
            if dbS.get(Cookie) not in db.get(ChatName):
                raise HTTPException(status_code=404, detail="Je zit niet in deze chat")
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

@limiter.limit("1/minute")
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
