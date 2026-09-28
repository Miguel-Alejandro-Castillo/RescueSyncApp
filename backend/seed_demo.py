"""Usuarios Bonita y datos locales reproducibles: python -m seed_demo --demo [--dry-run]."""
import argparse
import os
from urllib.parse import urlparse

import httpx
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlmodel import Session, create_engine, select

from models import Emergencia, Lote, Oferta


PASSWORD = '1234'
USERS = (
    ('municipal', 'operador_municipal', 'Operador Municipal'),
    ('coordinador', 'centro_coordinador_regional', 'Centro Coordinador Regional'),
    ('ong', 'representante_ong', 'Representante de ONG'),
    ('auditor', 'auditor', 'Auditor / Directivo'),
)


def all_items(client, path, filters=None):
    items, page = [], 0
    while True:
        response = client.get(path, params={'p': page, 'c': 100, **(filters or {})})
        response.raise_for_status()
        batch = response.json()
        items.extend(batch)
        if len(batch) < 100:
            return items
        page += 1


def ensure(client, path, matches, payload, filters=None):
    existing = next((item for item in all_items(client, path, filters) if matches(item)), None)
    if existing:
        return existing, False
    response = client.post(path, json=payload)
    response.raise_for_status()
    return response.json(), True


def seed_users(client, password):
    group, _ = ensure(client, '/API/identity/group',
        lambda item: item['name'] == 'rescuesync-demo' and not item.get('parent_path'),
        {'name': 'rescuesync-demo', 'displayName': 'RescueSync DEMO',
         'description': 'Organización provisional de desarrollo', 'parent_path': ''})
    profiles = all_items(client, '/API/portal/profile')
    profile = next((item for item in profiles if item['name'] == 'User'), None)
    if not profile:
        raise RuntimeError('No existe el perfil estándar User de Bonita.')
    for username, role_name, label in USERS:
        role, _ = ensure(client, '/API/identity/role', lambda item: item['name'] == role_name,
            {'name': role_name, 'displayName': label, 'description': 'Rol provisional RescueSync'})
        user, created = ensure(client, '/API/identity/user', lambda item: item['userName'] == username,
            {'userName': username, 'password': password, 'password_confirm': password,
             'firstName': label, 'lastName': 'DEMO', 'enabled': 'true'})
        ensure(client, '/API/identity/membership',
            lambda item: str(item['user_id']) == str(user['id'])
                and str(item['role_id']) == str(role['id']) and str(item['group_id']) == str(group['id']),
            {'user_id': user['id'], 'group_id': group['id'], 'role_id': role['id']},
            {'f': f"user_id={user['id']}"})
        ensure(client, '/API/portal/profileMember',
            lambda item: str(item.get('user_id')) == str(user['id'])
                and str(item['profile_id']) == str(profile['id']),
            {'profile_id': profile['id'], 'member_type': 'USER', 'user_id': user['id']},
            {'f': [f"profile_id={profile['id']}", 'member_type=user']})
        print(f'{username}: {"creado" if created else "existente (contraseña conservada)"} — {role_name}')



def create_demo_users(url):
    username = os.getenv('BONITA_SEED_ADMIN_USER', 'tech_user')
    password = os.getenv('BONITA_SEED_ADMIN_PASSWORD', 'secret')
    with httpx.Client(base_url=url, timeout=30) as client:
        response = client.post('/loginservice', data={
            'username': username, 'password': password, 'redirect': 'false'})
        response.raise_for_status()
        token = client.cookies.get('X-Bonita-API-Token')
        if not token:
            raise RuntimeError('Bonita no devolvió una sesión administrativa válida.')
        client.headers['X-Bonita-API-Token'] = token
        try:
            seed_users(client, os.getenv('BONITA_DEMO_PASSWORD', PASSWORD))
        finally:
            client.post('/logoutservice', params={'redirect': 'false'})


SCENARIOS = (
    ('inundacion', 'La Plata', 'alto', 'Evacuación preventiva y asistencia a familias.', []),
    ('incendio', 'Berisso', 'critico', 'Incendio con necesidad de personal y equipamiento.', []),
    ('temporal', 'Ensenada', 'medio', 'Temporal con viviendas afectadas.', []),
    ('convocatoria', 'Magdalena', 'alto', 'Convocatoria de ayuda con cobertura parcial.', [
        ('Insumos', 'Raciones de alimentos', 1000, 250),
        ('Personal', 'Personal de asistencia', 10, 0),
    ]),
    ('cubierta', 'Punta Indio', 'bajo', 'Lote con cobertura completa para consultar.', [
        ('Refugio', 'Mantas', 100, 100),
    ]),
)


def validate_target(url):
    """No permitir que el comando de demo apunte a una base remota accidentalmente."""
    target = make_url(url)
    if target.get_backend_name() == 'sqlite':
        return
    if (target.get_backend_name() != 'postgresql'
            or target.host not in {'localhost', '127.0.0.1', '::1', 'bonita-db'}
            or target.database not in {'rescuesync', 'rescuesync_test'}):
        raise ValueError('El seed solo admite PostgreSQL local rescuesync/rescuesync_test o SQLite de pruebas.')


def seed(session, now=None):
    """Insertar escenarios completos sin actualizar escenarios existentes.

    El caller controla commit/rollback. El bloqueo serializa ejecuciones Postgres.
    """
    if session.get_bind().dialect.name == 'postgresql':
        session.execute(text('SELECT pg_advisory_xact_lock(20260928, 1)'))
    now = now or datetime.now(timezone.utc)
    result = {'emergencias': 0, 'lotes': 0, 'ofertas': 0, 'omitidos': 0}
    for key, zone, severity, description, lots in SCENARIOS:
        marker = f'[DEMO v1:{key}] {zone}'
        existing = session.exec(select(Emergencia).where(Emergencia.zonaAfectada == marker)).first()
        if existing:
            result['omitidos'] += 1
            continue
        emergency = Emergencia(
            zonaAfectada=marker, nivelGravedad=severity,
            descripcionInicial=f'Datos ficticios de desarrollo. {description}',
            estado='publicada' if lots else 'creada', fechaCreacion=now,
            bonitaCaseId=None,
        )
        session.add(emergency)
        session.flush()
        result['emergencias'] += 1
        for resource, detail, quantity, covered in lots:
            lot = Lote(
                emergenciaId=emergency.id, tipoRecurso=resource,
                descripcion=f'[DEMO] {detail}', cantidad=quantity,
                cantidadCubierta=covered,
                estado='cubierto' if covered == quantity else 'creado',
                fechaCreacion=now, fechaLimiteConvocatoria=now + timedelta(days=7),
            )
            session.add(lot)
            session.flush()
            result['lotes'] += 1
            if covered:
                # Identificador ficticio: actualmente no existe tabla local de ONGs.
                session.add(Oferta(id_lote=lot.id, id_ong=900001, cant_recurso=covered))
                result['ofertas'] += 1
    session.flush()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true', required=True,
                        help='Confirmar la carga de datos ficticios de desarrollo')
    parser.add_argument('--dry-run', action='store_true', help='Simular solo datos SQL con rollback; no conectar ni modificar Bonita')
    args = parser.parse_args()
    url = os.getenv('DATABASE_URL')
    if not url:
        parser.error('Falta DATABASE_URL. Ejecutá este comando dentro del servicio backend.')
    try:
        validate_target(url)
    except ValueError as error:
        parser.error(str(error))
    bonita_url = os.getenv('BONITA_ENGINE_URL', '').rstrip('/')
    if not args.dry_run and urlparse(bonita_url).hostname not in {
            'bonita-engine', 'localhost', '127.0.0.1', 'host.docker.internal'}:
        parser.error('El seed requiere una instancia local de Bonita en BONITA_ENGINE_URL.')
    engine = create_engine(url, echo=False)
    with Session(engine) as session:
        try:
            result = seed(session)
            if args.dry_run:
                session.rollback()
            else:
                create_demo_users(bonita_url)
                session.commit()
        except Exception:
            session.rollback()
            raise
    print('Simulación revertida.' if args.dry_run else 'Seed DEMO completado.')
    print(result)
    print('Bonita no se modifica en dry-run.' if args.dry_run else 'Usuarios y datos listos. No se crean procesos de Bonita.')


if __name__ == '__main__':
    main()
