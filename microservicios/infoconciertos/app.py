import datetime
from typing import List
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from sqlalchemy import String, DateTime, Integer, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
import uvicorn
from http.client import HTTPException


class BaseEntity(DeclarativeBase):
    pass

class Concierto(BaseEntity):
    __tablename__ = "conciertos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    descripcion: Mapped[str] = mapped_column(String(350))
    fecha: Mapped[datetime.datetime] = mapped_column(DateTime)
    fecha_apertura_venta: Mapped[datetime.datetime] = mapped_column(DateTime)
    entradas_en_venta: Mapped[int] = mapped_column(Integer)

    def __repr__(self) -> str:
        return (
            f"Concierto(id={self.id}, name={self.nombre}, fecha={self.fecha}, "
            f"apertura_venta={self.fecha_apertura_venta}, "
            f"entradas_en_venta={self.entradas_en_venta})"
        )

class InfoConciertoRequest(BaseModel):
    nombre: str
    descripcion: str
    fecha: datetime.datetime
    fecha_apertura_venta: datetime.datetime
    entradas_en_venta: int

class InfoConciertoDTO(BaseModel):
    id: int
    nombre: str
    descripcion: str
    fecha: datetime.datetime
    fecha_apertura_venta: datetime.datetime
    entradas_en_venta: int

class ListaConciertosResponse(BaseModel):
    conciertos: List[InfoConciertoDTO]

def concierto_entity_to_dto(entity: Concierto) -> InfoConciertoDTO:
    return InfoConciertoDTO(
        id=entity.id,
        nombre=entity.nombre,
        descripcion=entity.descripcion,
        fecha=entity.fecha,
        fecha_apertura_venta=entity.fecha_apertura_venta,
        entradas_en_venta=entity.entradas_en_venta
    )

# Configuración de la aplicación
class APPSettings(BaseSettings):
    database_url: str = "sqlite:///mi.db"  # Por defecto en local
    root_path: str = ""

# Motor de base de datos
db_engine = create_engine(APPSettings().database_url, echo=True)

# Función para crear las tablas
def crea_db_tablas():
    BaseEntity.metadata.create_all(db_engine)  # Opcional: crea las tablas

# Función para obtener una sesión de base de datos
def get_db_session():
    with Session(db_engine) as session:
        yield session

# Ciclo de vida de la aplicación FastAPI
@asynccontextmanager
async def lifespan(_: FastAPI):
    # Inicio
    crea_db_tablas()
    yield
    # Final
    pass

# Instancia de FastAPI
app = FastAPI(
    root_path=APPSettings().root_path,
    docs_url="/",
    lifespan=lifespan
)

@app.get("/conciertos")
def lista_conciertos(session: Session = Depends(get_db_session)) -> ListaConciertosResponse:
    query = select(Concierto).order_by(Concierto.fecha.asc())
    conciertos_db = session.scalars(query).all()
    dtos = [concierto_entity_to_dto(c) for c in conciertos_db]
    return ListaConciertosResponse(conciertos=dtos)

@app.post("/conciertos")
def crea_concierto(
    info: InfoConciertoRequest,
    session: Session = Depends(get_db_session)
) -> InfoConciertoDTO:
    new_concierto = Concierto(
        nombre=info.nombre,
        descripcion=info.descripcion,
        fecha=info.fecha,
        fecha_apertura_venta=info.fecha_apertura_venta,
        entradas_en_venta=info.entradas_en_venta
    )
    session.add(new_concierto)
    session.commit()
    return concierto_entity_to_dto(new_concierto)

@app.get("/conciertos/{concierto_id}")
def info_concierto(concierto_id: str, session: Session = Depends(get_db_session)) -> InfoConciertoDTO:
    concierto_db = session.scalars(select(Concierto).where(Concierto.id == concierto_id)).one_or_none()
    if concierto_db is None:
        raise HTTPException(status_code=404, detail="Concierto no encontrado")
    return concierto_entity_to_dto(concierto_db)

@app.delete("/conciertos/{concierto_id}")
def borra_concierto(concierto_id: int, session: Session = Depends(get_db_session)):
    concierto_db = session.get(Concierto, concierto_id)
    if concierto_db is None:
        raise HTTPException(status_code=404, detail="Concierto no encontrado")
    session.delete(concierto_db)
    session.commit()


@app.put("/conciertos/{concierto_id}")
def actualiza_concierto(concierto_id: str, info: InfoConciertoRequest, session: Session = Depends(get_db_session)):
    concierto_db = session.scalars(
        select(Concierto).where(Concierto.id == concierto_id)
    ).one_or_none()
    if concierto_db is None:
        raise HTTPException(status_code=404, detail="Concierto no encontrado")
    concierto_db.nombre = info.nombre
    concierto_db.descripcion = info.descripcion
    concierto_db.fecha = info.fecha
    concierto_db.fecha_apertura_venta = info.fecha_apertura_venta
    concierto_db.entradas_en_venta = info.entradas_en_venta
    session.add(concierto_db)
    session.commit()

if __name__ == "__main__":
    # import entities to init
    uvicorn.run("app:app", port=80, reload=True)  # Use reload=True for DEV
