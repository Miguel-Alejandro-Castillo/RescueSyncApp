# Bonita

Este directorio contiene los artefactos y scripts necesarios para desplegar la organización, el proceso BPM y la configuración de membresias en perfiles User y Administrator.

## Estructura

```text
bonita/
├── deploy.sh
└── artifacts/
    ├── RESCUE.xml
    └── Plataforma RescueSync--1.0.bar
```

### Archivos principales

- **`deploy.sh`**: script de despliegue e inicialización. Importa la organización, sustituye el proceso existente, activa la nueva versión y configura las membresías de los perfiles User y Administrator.
- **`artifacts/RESCUE.xml`**: definición de la organización de Bonita, incluyendo grupos, roles y estructura organizacional.
- **`artifacts/Plataforma RescueSync--1.0.bar`**: paquete exportado desde Bonita Studio con el proceso BPM y su configuración asociada.

## Requisitos previos

- Docker y Docker Compose instalados.
- Los servicios definidos en el `docker-compose.yml` del proyecto.
- La variable `BONITA_PROCESS` configurada en el servicio `bonita-engine` con el nombre exacto del proceso exportado desde Bonita Studio.

Ejemplo:

```yaml
environment:
  BONITA_PROCESS: Plataforma RescueSync
```

## Despliegue inicial

Desde la raíz del proyecto, levanta los servicios:

```bash
docker compose up -d
```

Comprueba el estado de los contenedores:

```bash
docker compose ps
```

Cuando `bonita-engine` esté disponible, ejecuta el despliegue:

```bash
docker compose exec bonita-engine sh /opt/bonita/deploy.sh
```

Este último comando normalmente sólo es necesario:

- durante la primera instalación del proyecto;
- cuando se actualiza el archivo `.bar`;
- cuando cambia la organización definida en `RESCUE.xml`;
- cuando se modifican las membresías configuradas en `deploy.sh`;
- o cuando se desea reconstruir la configuración administrada por el script.

## Qué hace el script

El script ejecuta las siguientes acciones, en este orden:

1. Valida que existan `RESCUE.xml`, el archivo `.bar` y la variable `BONITA_PROCESS`.
2. Espera a que Bonita esté disponible.
3. Inicia sesión con el usuario técnico configurado en el contenedor.
4. Sube e importa `RESCUE.xml` como organización.
5. Busca el proceso indicado por `BONITA_PROCESS`.
6. Si el proceso ya existe, lo deshabilita y elimina.
7. Sube e instala el archivo `.bar`.
8. Activa el proceso instalado.
9. Recupera los identificadores de los grupos y roles definidos en la organización.
10. Elimina las membresías `roleAndGroup` existentes de los perfiles administrados por el script.
11. Crea nuevamente las membresías configuradas para los perfiles `User` y `Administrator`.

## Resultado esperado

Al finalizar correctamente, el script muestra un resumen similar al siguiente:

```text
===================================
DEPLOY FINALIZADO
===================================
Proceso: Plataforma RescueSync
ProcessId: <identificador>
User profile configurado
Administrator profile configurado
```

Bonita quedará con:

- la organización de RescueSync importada;
- el proceso BPM desplegado y habilitado;
- los grupos y roles disponibles;
- los perfiles `User` y `Administrator` configurados con las membresías definidas en `deploy.sh`.

## Reejecución

El despliegue puede volver a ejecutarse bajo demanda:

```bash
docker compose exec bonita-engine sh /opt/bonita/deploy.sh
```

El script reconstruye el proceso y las membresías que administra. Por tanto, el estado funcional final será el definido en los artefactos y en el propio script, aunque los identificadores internos generados por Bonita puedan cambiar entre ejecuciones.

> **Importante:** cualquier membresía `roleAndGroup` añadida manualmente a los perfiles `User` o `Administrator` será eliminada durante la siguiente ejecución y sólo se crearán las membresías declaradas en `deploy.sh`.

## Notas sobre los artefactos

- `RESCUE.xml` prepara la estructura organizacional, pero no despliega el proceso BPM.
- El archivo `.bar` contiene el proceso que se instala y activa en Bonita.
- Las membresías vinculan un perfil con una combinación de grupo y rol.
- Los perfiles y sus membresías se almacenan en la base de datos de Bonita.
- El script no depende de la importación XML de perfiles.
- No es necesario modificar ni reconstruir la imagen oficial de Bonita.
