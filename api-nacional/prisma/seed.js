import prisma from '../src/config/prisma.js';

const usuariosBase = [
  { username: 'admin', password: 'admin123' },
  { username: 'user', password: 'user123' },
];

const categoriasBase = [
  {
    codigo: 'INS',
    nombre: 'Insumos',
    descripcion: 'Comida, Agua y Medicamentos',
  },
  {
    codigo: 'PER',
    nombre: 'Personal',
    descripcion: 'Policias, Medicos y Bomberos',
  },
  {
    codigo: 'MAT',
    nombre: 'Materiales',
    descripcion: 'Arena, Ladrillos, Tierra y Cemento',
  },
  {
    codigo: 'TRA',
    nombre: 'Transporte',
    descripcion: 'Vehículos y combustibles',
  },
];

const ongsBase = [
  {
    razonSocial: 'Cruz Roja Argentina',
    sigla: 'CRA',
    cuit: '30-54603392-5',
    estado: 'HABILITADA',
    descripcion: 'Organización humanitaria internacional dedicada a la asistencia en emergencias, primeros auxilios, resiliencia comunitaria y respuesta ante catástrofes naturales o sanitarias.',
  },
  {
    razonSocial: 'Cáritas Argentina',
    sigla: 'Cáritas',
    cuit: '30-51731290-4',
    estado: 'HABILITADA',
    descripcion: 'Organización de la Iglesia Católica dedicada a brindar asistencia inmediata, desarrollo comunitario, comedores, refugios y proyectos de integración social para poblaciones vulnerables.',
  },
  {
    razonSocial: 'Fundación Sí',
    sigla: 'Fundación Sí',
    cuit: '30-71250682-9',
    estado: 'HABILITADA',
    descripcion: 'ONG centrada en promover la inclusión social, contención nocturna de personas en situación de calle (recorridas), comedores y residencias universitarias para jóvenes de zonas rurales.',
  },
  {
    razonSocial: 'Fundación Huésped',
    sigla: 'FH',
    cuit: '30-63749647-2',
    estado: 'HABILITADA',
    descripcion: 'Organización de salud pública enfáticamente abocada a la lucha contra el VIH/SIDA, la prevención de enfermedades transmisibles y la defensa de los derechos sexuales y reproductivos.',
  },
  {
    razonSocial: 'Fundación Cruzada Patagónica',
    sigla: 'FCP',
    cuit: '30-58650783-0',
    estado: 'HABILITADA',
    descripcion: 'ONG orientada a acompañar y potenciar el desarrollo integral de las comunidades rurales del oeste de la Patagonia mediante educación rural y desarrollo sostenible.',
  },
  {
    razonSocial: 'Fundación Potenciar Solidario',
    sigla: 'Potenciar Solidario',
    cuit: '30-71203700-4',
    estado: 'HABILITADA',
    descripcion: 'Organización dedicada al fortalecimiento institucional, capacitación y articulación de redes para impulsar el impacto de más de 500 ONGs en Argentina.',
  },
  {
    razonSocial: 'Fundación Cultura de Trabajo',
    sigla: 'FCT',
    cuit: '30-71600757-6',
    estado: 'HABILITADA',
    descripcion: 'Organización orientada a facilitar la inserción laboral y reincorporación en el mercado de trabajo formal para personas en situación de vulnerabilidad o exclusión socioeconómica.',
  },
{
    razonSocial: 'Fundación Banco de Alimentos',
    sigla: 'BDA',
    cuit: '30-70759612-7',
    estado: 'HABILITADA',
    descripcion: 'Organización sin fines de lucro que rescata alimentos aptos para el consumo que salieron del circuito comercial y los distribuye entre comedores y organizaciones sociales que asisten a personas con inseguridad alimentaria.',
  }
];

const recursosPorCategoria = {
  Insumos: ["Raciones de comida", "Agua", "Medicamentos"],
  Personal: ["Policias", "Medicos", "Bomberos"],
  Materiales: ["Arena", "Ladrillos", "Tierra", "Cemento"],
  Transporte: ["Vehículos", "Combustible"],
};

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

async function ensureRecurso({ codigo, nombre, descripcion, categoriaId }) {
  return prisma.recurso.upsert({
    where: { codigo },
    update: {
      nombre,
      descripcion,
      categoriaId,
    },
    create: {
      codigo,
      nombre,
      descripcion,
      categoriaId,
    },
  });
}

async function ensureOngRecurso({ ongId, recursoId, cantidadTotal, cantidadReservada }) {
  return prisma.ongRecurso.upsert({
    where: {
      ongId_recursoId: {
        ongId,
        recursoId,
      },
    },
    update: {
      cantidadTotal,
      cantidadReservada,
    },
    create: {
      ongId,
      recursoId,
      cantidadTotal,
      cantidadReservada,
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

    for (let i = 0; i < categoriasCreadas.length; i++) {
      const categoria = categoriasCreadas[i % categoriasCreadas.length];
      const claveCategoria = Object.keys(recursosPorCategoria).find((key) => key.toLowerCase() === (categoria.nombre || "").toLowerCase());
      const opciones = recursosPorCategoria[claveCategoria] || ["RecursosGeneral"];
      const nombreTipoRecurso = opciones[(ongIndex + i) % opciones.length];
      const recurso = await ensureRecurso({
        codigo: buildRecursoCodigo(ongIndex * 4 + i),
        nombre: nombreTipoRecurso,
        descripcion: "",
        categoriaId: categoria.id,
      });

      await ensureOngRecurso({
        ongId: ong.id,
        recursoId: recurso.id,
        cantidadTotal: 100 + i * 50,
        cantidadReservada: i * 10,
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
