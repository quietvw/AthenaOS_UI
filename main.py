#main.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI
from flaskwebgui import FlaskUI, close_application

app = FastAPI()

# Mounting default static files
app.mount("/public", StaticFiles(directory="dist/"))
templates = Jinja2Templates(directory="dist")



app.mount("/static", StaticFiles(directory="dist/static/"))

@app.get("/", response_class=HTMLResponse)
async def splash(request: Request):
    return templates.TemplateResponse("time_settings.html", {"request": request})

@app.get("/home", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@app.get("/call", response_class=HTMLResponse)
async def call(request: Request):
    return templates.TemplateResponse("call.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

@app.get("/settings_wifi", response_class=HTMLResponse)
async def wifi(request: Request):
    return templates.TemplateResponse("wifi_settings.html", {"request": request})

@app.get("/settings_time", response_class=HTMLResponse)
async def wifi(request: Request):
    return templates.TemplateResponse("time_settings.html", {"request": request})

@app.route("/close", methods=["GET"])
def close_window(*args, **kwargs):
    close_application()
    return "Window closing"


if __name__ == "__main__":

    FlaskUI(app=app, server="fastapi",width=960,
            height=640, port=15500).run()
