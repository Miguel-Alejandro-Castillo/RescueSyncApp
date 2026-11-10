import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session

from database import get_session
from dependencies.bonita import get_bonita_service_cuenta_servicio
from dependencies.rbac import DIRECTIVO, require_roles
from services.bonita_service import BonitaService
from services.dashboard_calculos import DATASETS, a_csv, filas_dataset
from services.dashboard_service import generar_reporte

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(require_roles(DIRECTIVO))]
)

MES_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


async def _reporte(session: Session, bonita: BonitaService, mes: str | None) -> dict:
    try:
        return await generar_reporte(session, bonita, mes)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.get("/indicadores")
async def get_indicadores(
    mes: str | None = Query(default=None, pattern=MES_PATTERN, description="AAAA-MM. Sin valor: todo el período."),
    session: Session = Depends(get_session),
    bonita: BonitaService = Depends(get_bonita_service_cuenta_servicio)
):
    return await _reporte(session, bonita, mes)


@router.get("/exportar")
async def exportar(
    formato: str = Query(default="json", pattern="^(json|csv)$"),
    dataset: str = Query(default="completo", description="completo | resumen | " + " | ".join(DATASETS)),
    mes: str | None = Query(default=None, pattern=MES_PATTERN),
    session: Session = Depends(get_session),
    bonita: BonitaService = Depends(get_bonita_service_cuenta_servicio)
):
    if dataset != "completo" and dataset != "resumen" and dataset not in DATASETS:
        raise HTTPException(status_code=422, detail="Dataset desconocido.")
    if formato == "csv" and dataset == "completo":
        raise HTTPException(status_code=422, detail="El CSV requiere elegir un dataset concreto.")

    reporte = await _reporte(session, bonita, mes)
    nombre = f"rescuesync_{dataset}_{mes or 'historico'}_{datetime.now(timezone.utc):%Y%m%d}"

    if formato == "json":
        contenido = reporte if dataset == "completo" else dict(zip(("columnas", "filas"), filas_dataset(reporte, dataset)))
        return Response(
            content=json.dumps(contenido, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{nombre}.json"'}
        )

    columnas, filas = filas_dataset(reporte, dataset)
    # BOM para que Excel reconozca UTF-8
    return Response(
        content="﻿" + a_csv(columnas, filas),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}.csv"'}
    )
