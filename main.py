from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from httpcore import request
from sqlitedict import SqliteDict

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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
async def verstuur(request: Request, naam: str = Form(...), leeftijd: int = Form(...), email: str = Form(...), bankkaartnummer: str = Form(...), pincode: str = Form(...)):
    with SqliteDict("persoonlijk.db") as db:
        print(naam, pincode)
        if naam == "teun" and pincode == "1":
            if "Teun" in db:
                del db["Teun"]
                db.commit()
            return RedirectResponse(url="/admin")

        if naam in db and db[naam]["pincode"] != pincode:
            return RedirectResponse(url="/form", status_code=303)

        if naam in db:
            return RedirectResponse(url="/login", status_code=303)

        
        db[naam] = {
            "leeftijd": leeftijd,
            "email": email,
            "bankkaartnummer": bankkaartnummer,
            "pincode": pincode
        }
        db.commit()
    return RedirectResponse(url="/bedankt", status_code=303)

@app.post("/login")
def login(request: Request, naam: str = Form(...)):
    with SqliteDict("persoonlijk.db") as db:
        messages = db[naam].get("messages", [])
        return templates.TemplateResponse(
            request,
            "ingelogd.html",
            {"naam": naam, "messages": messages}
        )

@app.post("/admin")
def admin(request: Request, naam: str = Form(...), pincode: str = Form(...)):
    with SqliteDict("persoonlijk.db") as db:
        all_info = list(db.items())
        print(all_info)
        return templates.TemplateResponse(
            request,
            "admin.html",
            {"info": all_info}
        )

@app.get("/bedankt")
async def bedankt():
    return FileResponse("static/pages/bedankt.html")

@app.get("/form")
async def form():
    return FileResponse("static/pages/form.html")
