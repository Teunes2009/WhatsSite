from fastapi import FastAPI, Form, Request, HTTPException, Cookie, UploadFile, File, Response
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlitedict import SqliteDict
from html import escape
import validators
import base64
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import secrets
import time
import re
import json



ph = PasswordHasher()

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode('utf-8')

templates.env.filters['b64encode'] = b64encode

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

@app.exception_handler(404)
async def NotFound(request: Request, fout):
    print("404 error:", fout)
    fout = str(fout)[5:]
    if fout == "Not Found":
        fout = "Pagina niet gevonden"
    return templates.TemplateResponse(
        request,
        "404.html",
        {"fout": fout},
        status_code=404,
    )

@app.post("/login")
async def login(request: Request, action: str = Form(...), naam: str = Form(max_length=25), wachtwoord: str = Form(min_length=4)):
    with SqliteDict("wachtwoorden.db") as db:
        print(naam, wachtwoord)
        if naam in db:
            if action == "creëer":
                raise HTTPException(status_code=404, detail="Gebruiker bestaat al")
            try:
                ph.verify(db[naam], wachtwoord)
            except VerifyMismatchError:
                raise HTTPException(status_code=403, detail="Gebruiker en wachtwoord komen niet overeen")
        else:
            if action == "inloggen":
                raise HTTPException(status_code=404, detail="Gebruiker bestaat niet")
            db[naam] = ph.hash(wachtwoord)
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
        for Chat in CurrentChats:
            if Chat not in db:
                if action == "inloggen":
                    raise HTTPException(status_code=404, detail=f"Chat {Chat} bestaat niet")
                db[Chat] = {}
                db.commit()
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
        {"naam": naam, "Messages": CurrentChats}
    )
    Response.set_cookie(key="UserID", value=SessionID, max_age=COOKIES_MAX_LIFETIME, httponly=True)
    Response.set_cookie(key="Name", value=naam, max_age=COOKIES_MAX_LIFETIME, httponly=True)
    return Response

@app.post("/logout")
async def logout(request: Request, UserID: str = Cookie(default=""), Name: str = Cookie(default="")):
    IsValidUser(Name, UserID)
    with SqliteDict("sessions.db") as db:
        del db[UserID]
        db.commit()
    Response = RedirectResponse(url="/")
    Response.delete_cookie(key="UserID")
    Response.delete_cookie(key="Name")
    return Response

@app.post("/Create")
async def create_chat(request: Request, ChatName: str = Form(...), Name: str = Cookie(default=""), Members: str = Form(...), UserID: str = Cookie(default="")):
    IsValidUser(Name, UserID)
    ChatName = ChatName.strip()
    print("Creating chat", ChatName, "with members", Members, "by", Name)
    # with SqliteDict("Chats.db") as db:
    #     print(db.keys(), ChatName, db.get_key(ChatName, []), "hoi")
    with SqliteDict("Messages.db") as db:
        print(list(db.keys()), db.get(ChatName, [1]), "hoi", ChatName in db)
        if ChatName.strip() in db:
            raise HTTPException(status_code=404, detail=f"{ChatName} already exists")
        if ChatName in ["Main", "Send", "GetMessages", "NewMember", "Leave", ""]:
            raise HTTPException(status_code=404, detail="Chat name is invalid")
        db[ChatName] = {}
        print(db[ChatName], "created chat", ChatName)
        db.commit()
    with SqliteDict("Chats.db") as db:
        NewMembers = [Name]
        MemberList = Members.split(",")
        MemberList = [Member.strip() for Member in MemberList if Member.strip()]
        for Member in MemberList.copy():
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
async def create_admin_chat(request: Request, ChatName: str = Form(...), Members: str = Form(...), UserID: str = Cookie(default=""),  Name: str = Cookie(default="")):
    IsValidAdmin(Name, UserID)
    ChatName = ChatName.strip()
    with SqliteDict("Messages.db") as db:
        print(list(db.keys()), db.get(ChatName, [1]), "hoi", ChatName in db)
        if ChatName.strip() in db:
            raise HTTPException(status_code=404, detail=f"{ChatName} already exists")
        if ChatName in ["Main", "Send", "GetMessages", "NewMember", "Leave", ""]:
            raise HTTPException(status_code=404, detail="Chat name is invalid")
        db[ChatName] = {}
        print(db[ChatName], "created chat", ChatName)
        db.commit()
    with SqliteDict("Chats.db") as db:
        NewMembers = []
        MemberList = Members.split(",")
        MemberList = [Member.strip() for Member in MemberList if Member.strip()]
        for Member in MemberList.copy():
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
    return templates.TemplateResponse(
        request,
        "ChatList.html",
        {"naam": Name, "Messages": {}}
    )

@app.post("/GetChats")
async def get_chats(request: Request, Name: str = Cookie(default=""), UserID: str = Cookie(default="")):
    IsValidUser(Name, UserID)
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
async def get_all_chats(request: Request, Name: str = Cookie(default=""), UserID: str = Cookie(default="")):
    print(Name, UserID)
    IsValidAdmin(Name, UserID)
    with SqliteDict("Messages.db") as db:
        CurrentChats = list(db.keys())
    print(CurrentChats)
    return templates.TemplateResponse(
        request,
        "ChatList.html",
        {"naam": Name, "Messages": CurrentChats}
    )

@app.post("/Send")
async def send(request: Request, Message: str = Form(...), ChatName: str = Form(...), Name: str = Cookie(default=""), UserID: str = Cookie(default="")):
    IsValidUser(Name, UserID)
    with SqliteDict("Chats.db") as db:
        if ChatName not in db.get(Name, []) and Name not in Admins:
            raise HTTPException(status_code=404, detail="Je zit niet in deze chat")
    print(Name, "sent ", Message, "in", ChatName)
    print(Message, ChatName, Name)
    Message = Message.strip()
    if not Message:
        raise HTTPException(status_code=404, detail="Message is empty")
    
    Message = MakeURLWork(escape(Message))
    
    with SqliteDict("Messages.db") as db:
        print(list(db.keys()))
        if ChatName not in db:
            db[ChatName] = {}
        Messages = db[ChatName]
        MessageID = len(Messages)-1
        Messages[MessageID] = {"Name": Name, "Content": Message, "Type": "text"}
        db[ChatName] = Messages
        db.commit()
    return templates.TemplateResponse(
        request,
        "Message.html",
        {"Messages": {MessageID: {"Name": Name, "Content": Message, "Type": "text"}}, "Name": Name, "ChatName": ChatName}
    )

@app.post("/SendFile")
async def SendFile(request: Request, ChatName: str = Form(...), UploadedFile: UploadFile = File(...), UserID: str = Cookie(default=""), Name: str = Cookie(default="")):
    IsValidUser(Name, UserID)
    Content = await UploadedFile.read()
    TypeHelp = UploadedFile.content_type
    with SqliteDict("Messages.db") as db:
        print(list(db.keys()))
        if ChatName not in db:
            db[ChatName] = {}
        Messages = db[ChatName]
        MessageID = len(Messages)-1
        Messages[MessageID] = {"Name": Name, "Content": Content, "Type": TypeHelp, "Filename": UploadedFile.filename}
        db[ChatName] = Messages
        db.commit()
    return templates.TemplateResponse(
        request,
        "Message.html",
        {"Messages": {MessageID: {"Name": Name, "Content": Content, "Type": TypeHelp, "Filename": UploadedFile.filename}, "Name": Name, "ChatName": ChatName}}
    )

@app.post("/ChangeMessage", response_class=HTMLResponse)
async def change_message(request: Request, ChatName: str = Form(...), ID: str = Form(...), UserID: str = Cookie(default=""), Name: str = Cookie(default="")):
    IsValidUser(Name, UserID)
    prompt = MakeURLWork(escape(request.headers.get("HX-Prompt").strip()))
    if not prompt:
        raise HTTPException(status_code=404, detail="Je hebt geen bericht ingetypt")
    ID = int(ID.lstrip("M"))
    with SqliteDict("Messages.db") as db:
        Messages = db.get(ChatName, {})
        if ID not in Messages:
            raise HTTPException(status_code=404, detail="Bericht bestaat niet")
        if Messages[ID]["Name"] != Name and Name not in Admins:
            raise HTTPException(status_code=403, detail="Jij mag dit bericht niet aanpassen")
        OriginalName = Messages[ID]["Name"]
        if Messages[ID]["Type"] == "text":
            Messages[ID]["Content"] = prompt
        db[ChatName] = Messages
        db.commit()
    hxvals = json.dumps({'ChatName': ChatName, 'ID': f'M{ID}'})
    return f"""<p>{OriginalName}: {prompt}</p>
    <button hx-post="/ChangeMessage" hx-vals='{hxvals}' hx-target="#M{ID}" hx-swap="innerHTML" hx-prompt="Voer het veranderde bericht in:" Edit>Verander bericht</button>
    <button hx-post="/DeleteMessage" hx-vals='{hxvals}' hx-target="#M{ID}" hx-swap="innerHTML" hx-confirm="Wil je dit bericht echt verwijderen?">Verwijder</button>"""

@app.post("/DeleteMessage", response_class=HTMLResponse)
async def delete_message(request: Request, ChatName: str = Form(...), ID: str = Form(...), UserID: str = Cookie(default=""), Name: str = Cookie(default="")):
    IsValidUser(Name, UserID)
    ID = int(ID.lstrip("M"))
    with SqliteDict("Messages.db") as db:
        Messages = db.get(ChatName, {})
        if ID not in Messages:
            raise HTTPException(status_code=404, detail="Bericht bestaat niet")
        if Messages[ID]["Name"] != Name and Name not in Admins:
            raise HTTPException(status_code=403, detail="Jij mag dit bericht niet verwijderen")
        OriginalName = Messages[ID]["Name"]
        Messages[ID]["Content"] = "Dit bericht is verwijderd"
        if "FileName" in Messages[ID]:
            Messages[ID]["Type"] = "text"
            Messages[ID].erase("FileName")
        db[ChatName] = Messages
        print(Messages[ID])
        db.commit()
    hxvals = json.dumps({'ChatName': ChatName, 'ID': f'M{ID}'})
    return f"""<p>{OriginalName}: Dit bericht is verwijderd</p>
    <button hx-post="/ChangeMessage" hx-vals='{hxvals}' hx-target="#M{ID}" hx-swap="innerHTML" hx-prompt="Voer het veranderde bericht in:" Edit>Verander bericht</button>"""

@app.post("/GetMessages")
async def get_messages(request: Request, ChatName: str = Form(...), AfterID: int = Form(default=-2), UserID: str = Cookie(default=""), Name: str = Cookie(default="")):
    IsValidUser(Name, UserID)
    with SqliteDict("Chats.db") as db:
        if ChatName not in db.get(Name, []) and Name not in Admins:
            raise HTTPException(status_code=404, detail="Je zit niet in deze chat")
    with SqliteDict("Messages.db") as db:
        Messages = db.get(ChatName, {})
        Messages = {ID: Messages[ID] for ID in sorted(Messages) if ID > AfterID}
        # print(Messages)
    if not Messages:
        return Response(status_code=204)
    return templates.TemplateResponse(
        request,
        "Message.html",
        {"Messages": Messages}
    )

@app.post("/NewMember")
async def new_member(request: Request, ChatName: str = Form(...), NewMember: str = Form(...), UserID: str = Cookie(default=""), Name: str = Cookie(default="")):
    IsValidUser(Name, UserID)
    with SqliteDict("Chats.db") as db:
        if ChatName not in db.get(Name, []) and Name not in Admins:
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

@app.post("/GetMembers")
async def get_members(request: Request, ChatName: str = Form(...), Name: str = Cookie(default=""), UserID: str = Cookie(default="")):
    IsValidUser(Name, UserID)
    with SqliteDict("Chats.db") as db:
        if ChatName not in db.get(Name, []) and Name not in Admins:
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
async def leave_chat(request: Request, ChatName: str = Form(...), Name: str = Cookie(default=""), UserID: str = Cookie(default="")):
    IsValidUser(Name, UserID)
    if ChatName == "Main":
        raise HTTPException(status_code=404, detail="You cannot leave the Main chat")
    Chats = []
    with SqliteDict("Chats.db") as db:
        if ChatName not in db.get(Name, []):
            raise HTTPException(status_code=404, detail="Je zit niet in deze chat")
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

@app.post("/GoBack")
async def go_back(request: Request, Name: str = Cookie(default=""), UserID: str = Cookie(default="")):
    IsValidUser(Name, UserID)
    with SqliteDict("Chats.db") as db:
        CurrentChats = db.get(Name, [])
    print(CurrentChats)
    return templates.TemplateResponse(
        request,
        "ingelogd.html",
        {"naam": Name, "Messages": CurrentChats}
    )

@app.post("/Chats/{ChatName}")
async def chat(request: Request, ChatName: str, Name: str = Cookie(default=""), UserID: str = Cookie(default="")):
    IsValidUser(Name, UserID)
    with SqliteDict("Chats.db") as db:
        if ChatName not in db.get(Name, []):
            raise HTTPException(status_code=404, detail="Je zit niet in deze chat")
    with SqliteDict("Messages.db") as db:
        if ChatName not in db:
            db[ChatName] = []
            db.commit()
        Messages = db[ChatName]
        # print(Messages)
    with SqliteDict("Chats.db") as db:
        Members = []
        for Member in db.keys():
            if ChatName in db[Member]:
                Members.append(Member)
        # print(Members)
    return templates.TemplateResponse(
        request,
        "chat.html",
        {"ChatName": ChatName, "Messages": Messages, "Name": Name, "Members": Members}
    )

@app.post("/Admin/{ChatName}")
async def admin_chat(request: Request, ChatName: str, Name: str = Cookie(default=""), UserID: str = Cookie(default="")):
    IsValidAdmin(Name, UserID)
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
        {"ChatName": ChatName, "Messages": Messages, "Name": Name, "Members": Members}
    )

@app.post("/admin")
async def admin(request: Request, naam: str = Form(...)):
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
        {"naam": naam, "Messages": AllChats}
    )
    Response.set_cookie(key="UserID", value=SessionID, max_age=COOKIES_MAX_LIFETIME, httponly=True)
    return Response

def IsValidUser(Name: str, UserID: str):
    with SqliteDict("sessions.db") as sessies:
        mijn = sessies.get(UserID, {})
        print("sessie", mijn, "cookie", UserID, UserID in sessies)
        sessie = mijn
        if mijn and mijn.get("tot", 0) < time.time():
            del sessies[UserID]
            sessies.commit()
            sessie = {}
        if mijn and mijn.get("naam", "") != Name:
            sessie = {}
    if not sessie:
        raise HTTPException(status_code=404, detail="Invalide sessie")

def IsValidAdmin(Name: str, UserID: str):
    IsValidUser(Name, UserID)
    if Name not in Admins:
        raise HTTPException(status_code=403, detail="Je bent geen admin")

def MakeURLWork(Text: str):
    ReplacedURLs = []
    url_pattern = re.compile(r'\b(?:https?|ftp)://[^\s<>"]+|\b(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/[^\s<>"]*)?', re.IGNORECASE)
    candidates = url_pattern.findall(Text)
    ReplacedURLs = []
    for Word in candidates:
        Word = Word.strip('!@#$%^&*()_+-=[]{};:\'",.<>?/\\|`~')
        TestWord = Word
        if not re.match(r'^(?:https?|ftp)://', Word, re.IGNORECASE):
            TestWord = "http://" + Word
        if validators.url(TestWord) == True and Word not in ReplacedURLs:
            Text = Text.replace(Word, f'<a href="{TestWord}">{Word}</a>')
            ReplacedURLs.append(Word)
    return Text