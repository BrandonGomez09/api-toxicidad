from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware 
from pydantic import BaseModel
from pysentimiento import create_analyzer
import re

from database import init_db, guardar_prediccion

app = FastAPI(
    title="API de Comentarios Malos",
    description="Detección de lenguaje ofensivo",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"], 
)
# ---------------------------------------------------------------

@app.on_event("startup")
def startup_event():
    init_db()

analyzer = create_analyzer(
    task="hate_speech",
    lang="es"
)

PALABRAS_PROHIBIDAS = {
    "idiota","imbécil","estúpido","pendejo","puta","puto",
    "verga","mierda","chingada","hijo de puta","hdp",
    "basura humana","ojalá te mueras","maricón"
}

def contiene_insulto(texto: str) -> bool:
    texto = texto.lower()
    texto = re.sub(r"[^\w\s]", "", texto)
    return any(p in texto for p in PALABRAS_PROHIBIDAS)

class TextoEntrada(BaseModel):
    texto: str

class Respuesta(BaseModel):
    permitido: bool
    prob_ofensivo: float
    mensaje: str

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/predict", response_model=Respuesta)
def predecir(data: TextoEntrada):
    texto = data.texto.strip()

    if not texto:
        raise HTTPException(status_code=400, detail="Texto vacío")

    if contiene_insulto(texto):
        guardar_prediccion(texto, 1, 0.99)
        raise HTTPException(
            status_code=403,
            detail="Lo sentimos, su comentario no puede ser publicado porque infringe nuestras normas."
        )

    result = analyzer.predict(texto)
    prob_hate = result.probas["hateful"]

    guardar_prediccion(texto, int(prob_hate >= 0.70), prob_hate)

    if prob_hate >= 0.70:
        raise HTTPException(
            status_code=403,
            detail="Lo sentimos, no se puede publicar su descripción porque infringe nuestras normas."
        )

    return {
        "permitido": True,
        "prob_ofensivo": round(prob_hate, 4),
        "mensaje": "Texto permitido"
    }