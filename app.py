import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pysentimiento import create_analyzer
import re

from database import init_db, guardar_prediccion

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="API de Comentarios Malos",
    description="Detección de lenguaje ofensivo",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    logger.info("Iniciando API de Toxicidad...")
    try:
        init_db()
        logger.info("Base de datos inicializada correctamente.")
    except Exception as e:
        logger.error(f"Error al iniciar base de datos: {e}")

logger.info("Cargando modelo de Inteligencia Artificial (pysentimiento)...")
analyzer = create_analyzer(
    task="hate_speech",
    lang="es"
)
logger.info("Modelo cargado y listo para analizar.")

PALABRAS_PROHIBIDAS = {
    "idiota","imbécil","estúpido","pendejo","puta","puto",
    "verga","mierda","chingada","hijo de puta","hdp",
    "basura humana","ojalá te mueras","maricón"
}

def contiene_insulto(texto: str) -> bool:
    texto_lower = texto.lower()
    texto_limpio = re.sub(r"[^\w\s]", "", texto_lower)
    
    for p in PALABRAS_PROHIBIDAS:
        if p in texto_limpio:
            logger.warning(f"Palabra prohibida detectada: '{p}'")
            return True
    return False

class TextoEntrada(BaseModel):
    texto: str

class Respuesta(BaseModel):
    permitido: bool
    prob_ofensivo: float
    mensaje: str

@app.get("/health")
def health():
    logger.info("Health Check solicitado.")
    return {"ok": True}

@app.post("/predict", response_model=Respuesta)
def predecir(data: TextoEntrada):
    texto = data.texto.strip()
    logger.info(f"Nuevo texto recibido para análisis: '{texto}'")

    if not texto:
        logger.warning("Se recibió un texto vacío.")
        raise HTTPException(status_code=400, detail="Texto vacío")

    if contiene_insulto(texto):
        logger.info("Bloqueado por filtro de palabras prohibidas.")
        guardar_prediccion(texto, 1, 0.99)
        raise HTTPException(
            status_code=403,
            detail="Lo sentimos, su comentario no puede ser publicado porque infringe nuestras normas."
        )


    logger.info("🔍 Analizando con IA...")
    result = analyzer.predict(texto)
    prob_hate = result.probas["hateful"]
    
    logger.info(f"Resultado IA: Probabilidad de odio = {prob_hate:.4f}")
    guardar_prediccion(texto, int(prob_hate >= 0.70), prob_hate)

    if prob_hate >= 0.70:
        logger.warning(f"Bloqueado por IA (Superó el 70%): {prob_hate:.4f}")
        raise HTTPException(
            status_code=403,
            detail="Lo sentimos, no se puede publicar su descripción porque infringe nuestras normas."
        )

    logger.info("Texto permitido y limpio.")
    return {
        "permitido": True,
        "prob_ofensivo": round(prob_hate, 4),
        "mensaje": "Texto permitido"
    }