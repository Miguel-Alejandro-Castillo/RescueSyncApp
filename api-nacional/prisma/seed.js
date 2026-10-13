import prisma from '../src/config/prisma.js';

const usuariosBase = [
  { username: 'admin', password: 'admin123' },
  { username: 'user', password: 'user123' },
];

const categoriasBase = [
  {
    codigo: 'ALI',
    nombre: 'Alimentos',
    descripcion: 'Recursos alimenticios y bebidas',
  },
  {
    codigo: 'MED',
    nombre: 'Medicinas',
    descripcion: 'Medicamentos y suministros médicos',
  },
  {
    codigo: 'ROP',
    nombre: 'Ropa',
    descripcion: 'Prendas de vestir y accesorios',
  },
  {
    codigo: 'EQU',
    nombre: 'Equipamiento',
    descripcion: 'Herramientas y equipos especializados',
  },
  {
    codigo: 'TRA',
    nombre: 'Transporte',
    descripcion: 'Vehículos y combustibles',
  },
  {
    codigo: 'INF',
    nombre: 'Infraestructura',
    descripcion: 'Materiales de construcción y mantenimiento',
  },
];

const ongsBase = [
  {
    razonSocial: 'Cruz Roja Argentina',
    sigla: 'CRA',
    cuit: '30-54603392-5',
    estado: 'habilitada',
    descripcion: 'Organización humanitaria internacional dedicada a la asistencia en emergencias, primeros auxilios, resiliencia comunitaria y respuesta ante catástrofes naturales o sanitarias.',
  },
  {
    razonSocial: 'Cáritas Argentina',
    sigla: 'Cáritas',
    cuit: '30-51731290-4',
    estado: 'habilitada',
    descripcion: 'Organización de la Iglesia Católica dedicada a brindar asistencia inmediata, desarrollo comunitario, comedores, refugios y proyectos de integración social para poblaciones vulnerables.',
  },
  {
    razonSocial: 'Fundación Sí',
    sigla: 'Fundación Sí',
    cuit: '30-71250682-9',
    estado: 'habilitada',
    descripcion: 'ONG centrada en promover la inclusión social, contención nocturna de personas en situación de calle (recorridas), comedores y residencias universitarias para jóvenes de zonas rurales.',
  },
  {
    razonSocial: 'Fundación Huésped',
    sigla: 'FH',
    cuit: '30-63749647-2',
    estado: 'habilitada',
    descripcion: 'Organización de salud pública enfáticamente abocada a la lucha contra el VIH/SIDA, la prevención de enfermedades transmisibles y la defensa de los derechos sexuales y reproductivos.',
  },
  {
    razonSocial: 'Fundación Cruzada Patagónica',
    sigla: 'FCP',
    cuit: '30-58650783-0',
    estado: 'habilitada',
    descripcion: 'ONG orientada a acompañar y potenciar el desarrollo integral de las comunidades rurales del oeste de la Patagonia mediante educación rural y desarrollo sostenible.',
  },
  {
    razonSocial: 'Fundación Potenciar Solidario',
    sigla: 'Potenciar Solidario',
    cuit: '30-71203700-4',
    estado: 'habilitada',
    descripcion: 'Organización dedicada al fortalecimiento institucional, capacitación y articulación de redes para impulsar el impacto de más de 500 ONGs en Argentina.',
  },
  {
    razonSocial: 'Fundación Cultura de Trabajo',
    sigla: 'FCT',
    cuit: '30-71600757-6',
    estado: 'habilitada',
    descripcion: 'Organización orientada a facilitar la inserción laboral y reincorporación en el mercado de trabajo formal para personas en situación de vulnerabilidad o exclusión socioeconómica.',
  },
{
    razonSocial: 'Fundación Banco de Alimentos',
    sigla: 'BDA',
    cuit: '30-70759612-7',
    estado: 'habilitada',
    descripcion: 'Organización sin fines de lucro que rescata alimentos aptos para el consumo que salieron del circuito comercial y los distribuye entre comedores y organizaciones sociales que asisten a personas con inseguridad alimentaria.',
  }
];

async function ensureUser({ username, password }) {
  return prisma.user.upsert({
    where: { username },
    update: { password },
    create: { username, password },
  });
}

function buildRecursoCodigo(index) {
  return `R${(index + 1).toString(36).toUpperCase().padStart(2, '0')}`;
}

async function ensureCategoria({ codigo, nombre, descripcion }) {
  return prisma.categoria.upsert({
    where: { codigo },
    update: { nombre, descripcion },
    create: { codigo, nombre, descripcion },
  });
}

async function ensureOng(ongData) {
  return prisma.ong.upsert({
    where: { cuit: ongData.cuit },
    update: {
      razonSocial: ongData.razonSocial,
      sigla: ongData.sigla,
      estado: ongData.estado,
      descripcion: ongData.descripcion,
    },
    create: {
      razonSocial: ongData.razonSocial,
      sigla: ongData.sigla,
      cuit: ongData.cuit,
      estado: ongData.estado,
      descripcion: ongData.descripcion,
    },
  });
}

async function ensureRecurso({ codigo, nombre, descripcion, categoriaId, cantidadTotal, cantidadComprometida, ongId }) {
  return prisma.recurso.upsert({
    where: { codigo },
    update: {
      nombre,
      descripcion,
      categoriaId,
      cantidadTotal,
      cantidadComprometida,
      ongId,
    },
    create: {
      codigo,
      nombre,
      descripcion,
      categoriaId,
      cantidadTotal,
      cantidadComprometida,
      ongId,
    },
  });
}

async function main() {
  for (const usuario of usuariosBase) {
    await ensureUser(usuario);
  }

  const categoriasCreadas = [];
  for (const categoria of categoriasBase) {
    categoriasCreadas.push(await ensureCategoria(categoria));
  }

  for (const [ongIndex, ongData] of ongsBase.entries()) {
    const ong = await ensureOng(ongData);

    for (let i = 0; i < 2; i++) {
      const categoria = categoriasCreadas[i % categoriasCreadas.length];
      await ensureRecurso({
        codigo: buildRecursoCodigo(ongIndex * 2 + i),
        nombre: `${ong.sigla} - Recurso ${i + 1}`,
        descripcion: `Recurso ${i + 1} de ${ong.razonSocial}`,
        categoriaId: categoria.id,
        cantidadTotal: 100 + i * 50,
        cantidadComprometida: i * 10,
        ongId: ong.id,
      });
    }
  }

  console.log('Seed completado exitosamente');
}

main()
  .catch((error) => {
    console.error(error);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
