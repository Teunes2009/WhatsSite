from fastapi import FastAPI, Form, Request, HTTPException, Query, Cookie
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from httpcore import request
from sqlitedict import SqliteDict
from html import escape
import validators
# from argon2 import PasswordHasher
# from argon2.exceptions import VerifyMismatchError
import hashlib
import secrets
import time


limiter = Limiter(key_func=get_remote_address)
#ph = PasswordHasher()

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

COOKIES_MAX_LIFETIME = 60 * 60 * 24 * 30
Admins = ["Teun", "Admin"]

@app.get("/")
async def home():
    return FileResponse("static/pages/home.html")

@app.get("/project")
async def project():
    return FileResponse("static/pages/form.html")

@app.get("/about")
async def about():
    return FileResponse("static/pages/about.html")


@app.post("/login")
@limiter.limit("3/minute")
async def login(request: Request, action: str = Form(...), naam: str = Form(...), wachtwoord: str = Form(min_length=4)):
    with SqliteDict("wachtwoorden.db") as db:
        print(naam, wachtwoord)
        if naam in db:
            if action == "creëer":
                raise HTTPException(status_code=403, detail="Ongeldige actie")
            if db[naam]["wachtwoord"] != hashlib.sha256(wachtwoord.encode()).hexdigest():
                raise HTTPException(status_code=404, detail="Gebruiker en wachtwoord komen niet overeen")
        else:
            if action == "inloggen":
                raise HTTPException(status_code=404, detail="Gebruiker en wachtwoord komen niet overeen")
            db[naam] = {"wachtwoord": hashlib.sha256(wachtwoord.encode()).hexdigest()}
            db.commit()
    if naam in Admins:
        return RedirectResponse(url="/admin")
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
        Sessions = db
        Sessions[SessionID] = {"naam": naam, "tot": time.time() + COOKIES_MAX_LIFETIME}
        db = Sessions
        db.commit()
    Response = templates.TemplateResponse(
        request,
        "ingelogd.html",
        {"naam": naam, "wachtwoord": wachtwoord, "Messages": Messages}
    )
    Response.set_cookie(key="UserID", value=SessionID, max_age=COOKIES_MAX_LIFETIME, httponly=True)
    return Response

@app.post("/logout")
@limiter.limit("3/minute")
async def logout(request: Request, Name: str = Form(...), Password: str = Form(...), UserID: str = Cookie(default="")):
    IsValidUser(Name, Password, UserID)
    with SqliteDict("sessions.db") as db:
        del db[UserID]
        db.commit()
    Response = RedirectResponse(url="/")
    Response.delete_cookie(key="UserID")
    return Response

@app.post("/Create")
@limiter.limit("5/minute")
async def create_chat(request: Request, ChatName: str = Form(...), Name: str = Form(...), Password: str = Form(...), Members: str = Form(...), UserID: str = Cookie(default="")):
    IsValidUser(Name, Password, UserID)
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

@app.post("/CreateAdmin")
async def create_admin_chat(request: Request, ChatName: str = Form(...), Name: str = Form(...), Password: str = Form(...), Members: str = Form(...), UserID: str = Cookie(default="")):
    IsValidAdmin(Name, Password, UserID)
    ChatName = ChatName.strip()
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
        NewMembers = []
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
        db.commit()
    with SqliteDict("Messages.db") as db:
        Messages = db[ChatName]
    return templates.TemplateResponse(
        request,
        "ChatList.html",
        {"naam": Name, "Messages": Messages}
    )

@app.post("/GetChats")
@limiter.limit("35/minute")
async def get_chats(request: Request, Name: str = Form(...), Password: str = Form(...), UserID: str = Cookie(default="")):
    IsValidUser(Name, Password, UserID)
    with SqliteDict("Chats.db") as db:
        print(list(db.keys()), Name, db[Name], db.get(Name, []))
        CurrentChats = db.get(Name, [])
    print(CurrentChats)
    return templates.TemplateResponse(
        request,
        "ChatList.html",
        {"naam": Name, "Messages": CurrentChats}
    )

@app.post("/GetAllChats")
@limiter.limit("35/minute")
async def get_all_chats(request: Request, Name: str = Form(...), Password: str = Form(...), UserID: str = Cookie(default="")):
    print(Name, Password, UserID)
    IsValidAdmin(Name, Password, UserID)
    with SqliteDict("Messages.db") as db:
        CurrentChats = list(db.keys())
    print(CurrentChats)
    return templates.TemplateResponse(
        request,
        "ChatList.html",
        {"naam": Name, "Messages": CurrentChats}
    )

@app.post("/Send")
async def send(request: Request, Message: str = Form(...), ChatName: str = Form(...), Name: str = Form(...), Password: str = Form(...),  UserID: str = Cookie(default="")):
    IsValidUser(Name, Password, UserID)
    with SqliteDict("Chats.db") as db:
        if Name not in db.get(ChatName, []) and Name not in Admins:
            raise HTTPException(status_code=404, detail="Je zit niet in deze chat")
    print(Name, "sent ", Message, "in", ChatName)
    print(Message, ChatName, Name)
    Message = Message.strip()
    if not Message:
        raise HTTPException(status_code=404, detail="Message is empty")
    Message = escape(Message)
    URLs = validators.url(Message)
    for URL in URLs:
        Message = Message.replace(URL, f'<a href="{URL}">{URL}</a>')
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

@app.post("/GetMessages")
@limiter.limit("35/minute")
async def get_messages(request: Request, ChatName: str = Form(...), Name: str = Form(...), Password: str = Form(...), UserID: str = Cookie(default="")):
    IsValidUser(Name, Password, UserID)
    with SqliteDict("Chats.db") as db:
        if Name not in db.get(ChatName, []) and Name not in Admins:
            raise HTTPException(status_code=404, detail="Je zit niet in deze chat")
    with SqliteDict("Messages.db") as db:
        Messages = db.get(ChatName, [])
        # print(Messages)
    return templates.TemplateResponse(
        request,
        "Message.html",
        {"Messages": Messages}
    )

@app.post("/NewMember")
async def new_member(request: Request, Name: str = Form(...), Password: str = Form(...), ChatName: str = Form(...), NewMember: str = Form(...), UserID: str = Cookie(default="")):
    IsValidUser(Name, Password, UserID)
    with SqliteDict("Chats.db") as db:
        if Name not in db.get(ChatName, []) and Name not in Admins:
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
@app.post("/GetMembers")
async def get_members(request: Request, ChatName: str = Form(...), Name: str = Form(...), Password: str = Form(...), UserID: str = Cookie(default="")):
    IsValidUser(Name, Password, UserID)
    with SqliteDict("Chats.db") as db:
        if Name not in db.get(ChatName, []) and Name not in Admins:
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

@app.post("/Leave")
@limiter.limit("10/minute")
async def leave_chat(request: Request, ChatName: str = Form(...), Name: str = Form(...), Password: str = Form(...), UserID: str = Cookie(default="")):
    IsValidUser(Name, Password, UserID)
    with SqliteDict("Chats.db") as db:
        if Name not in db.get(ChatName, []):
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
async def chat(request: Request, ChatName: str, Name: str = Form(...), Password: str = Form(...), UserID: str = Cookie(default="")):
    IsValidUser(Name, Password, UserID)
    with SqliteDict("Chats.db") as db:
        if Name not in db.get(ChatName, []):
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
        {"ChatName": ChatName, "Messages": Messages, "Name": Name, "Password": Password, "Members": Members}
    )

@app.post("/Admin/{ChatName}")
async def admin_chat(request: Request, ChatName: str, Name: str = Form(...), Password: str = Form(...), UserID: str = Cookie(default="")):
    IsValidAdmin(Name, Password, UserID)
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
        "adminchat.html",
        {"ChatName": ChatName, "Messages": Messages, "Name": Name, "Password": Password, "Members": Members}
    )

@limiter.limit("1/minute")
@app.post("/admin")
async def admin(request: Request, naam: str = Form(...), wachtwoord: str = Form(...)):
    with SqliteDict("Messages.db") as db:
        AllChats = list(db.keys())
    SessionID = secrets.token_hex(16)
    with SqliteDict("sessions.db") as db:
        Sessions = db
        Sessions[SessionID] = {"naam": naam, "tot": time.time() + COOKIES_MAX_LIFETIME}
        db = Sessions
        db.commit()
    Response = templates.TemplateResponse(
        request,
        "admin.html",
        {"naam": naam, "wachtwoord": wachtwoord, "Messages": AllChats}
    )
    Response.set_cookie(key="UserID", value=SessionID, max_age=COOKIES_MAX_LIFETIME, httponly=True)
    return Response

@app.get("/bedankt")
async def bedankt():
    return FileResponse("static/pages/bedankt.html")

@app.get("/form")
async def form():
    return FileResponse("static/pages/form.html")

def IsValidUser(Name: str, Password: str, UserID: str):
    with SqliteDict("wachtwoorden.db") as db:
        if db.get(Name, {}).get("wachtwoord") != hashlib.sha256(Password.encode()).hexdigest():
            raise HTTPException(status_code=403, detail="Ongeldig wachtwoord")
    with SqliteDict("sessions.db") as sessies:
        mijn = sessies.get(UserID, {})
        print("sessie", mijn, "cookie", UserID, UserID in sessies)
        sessie = mijn
        if mijn and mijn.get("tot", 0) < time.time():
            del sessies[UserID]
            sessies.commit()
            sessie = {}
    if not sessie:
        raise HTTPException(status_code=404, detail="Invalide sessie")

def IsValidAdmin(Name: str, Password: str, UserID: str):
    IsValidUser(Name, Password, UserID)
    if Name not in Admins:
        raise HTTPException(status_code=403, detail="Je bent geen admin")