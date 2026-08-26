import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.database import engine, Base
from app.api.routers import quadrinhos
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env
load_dotenv()

# Inicializa o banco de dados
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Controle de Quadrinhos", 
    description="Sistema com Clean Architecture e Leitor de Código de Barras"
)

from fastapi.staticfiles import StaticFiles

# Configuração de Rotas
app.include_router(quadrinhos.router)

# Configurar diretórios
base_dir = os.path.dirname(os.path.dirname(__file__))
static_dir = os.path.join(base_dir, "static")
templates_dir = os.path.join(base_dir, "templates")

# Montar arquivos estáticos
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Configuração de Templates HTML
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)
templates = Jinja2Templates(directory=templates_dir)

@app.get("/", response_class=HTMLResponse, tags=["Web"])
async def pagina_inicial(request: Request):
    """Renderiza a interface principal com o scanner."""
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/ping", tags=["Health Check"])
async def ping():
    """Rota para o UptimeRobot manter a aplicação ativa no Render."""
    return {"status": "alive"}
