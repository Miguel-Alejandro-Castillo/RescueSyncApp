import prisma from '../src/config/prisma.js';

async function main() {
  // Crear usuarios
  await prisma.user.createMany({
    data: [
      {
        username: 'admin',
        password: 'admin123',
      },
      {
        username: 'user',
        password: 'user123',
      },
    ],
  });

  // Crear categorías
  const categorias = await prisma.categoria.createMany({
    data: [
      {
        nombre: 'Alimentos',
        descripcion: 'Recursos alimenticios y bebidas',
      },
      {
        nombre: 'Medicinas',
        descripcion: 'Medicamentos y suministros médicos',
      },
      {
        nombre: 'Ropa',
        descripcion: 'Prendas de vestir y accesorios',
      },
      {
        nombre: 'Equipamiento',
        descripcion: 'Herramientas y equipos especializados',
      },
      {
        nombre: 'Transporte',
        descripcion: 'Vehículos y combustibles',
      },
      {
        nombre: 'Infraestructura',
        descripcion: 'Materiales de construcción y mantenimiento',
      },
    ],
  });

  // Obtener categorías creadas
  const categoriasCreadas = await prisma.categoria.findMany();

  // Crear ONGs con recursos
  const ongs = [
    {
      razonSocial: 'Asociación Ayuda Humanitaria',
      sigla: 'AAH',
      cuit: '30-12345678-0',
      estado: 'habilitada',
      descripcion: 'Organización dedicada a la asistencia humanitaria',
    },
    {
      razonSocial: 'Fundación Solidaridad Social',
      sigla: 'FSS',
      cuit: '30-23456789-1',
      estado: 'habilitada',
      descripcion: 'Fundación enfocada en inclusión social',
    },
    {
      razonSocial: 'Red de Rescate y Emergencias',
      sigla: 'RRE',
      cuit: '30-34567890-2',
      estado: 'habilitada',
      descripcion: 'Coordinadora de operaciones de rescate',
    },
    {
      razonSocial: 'Protección Civil Comunitaria',
      sigla: 'PCC',
      cuit: '30-45678901-3',
      estado: 'habilitada',
      descripcion: 'Organización de protección civil',
    },
    {
      razonSocial: 'Voluntarios por la Vida',
      sigla: 'VPV',
      cuit: '30-56789012-4',
      estado: 'habilitada',
      descripcion: 'Red de voluntarios comunitarios',
    },
    {
      razonSocial: 'Centro de Asistencia Integral',
      sigla: 'CAI',
      cuit: '30-67890123-5',
      estado: 'habilitada',
      descripcion: 'Centro multidisciplinario de asistencia',
    },
  ];

  for (const ongData of ongs) {
    const ong = await prisma.ong.create({
      data: {
        razonSocial: ongData.razonSocial,
        sigla: ongData.sigla,
        cuit: ongData.cuit,
        estado: ongData.estado,
        descripcion: ongData.descripcion,
      },
    });

    // Crear 2 recursos para cada ONG
    for (let i = 0; i < 2; i++) {
      const categoria = categoriasCreadas[i % categoriasCreadas.length];
      await prisma.recurso.create({
        data: {
          nombre: `${ongData.sigla} - Recurso ${i + 1}`,
          descripcion: `Recurso ${i + 1} de ${ongData.razonSocial}`,
          categoriaId: categoria.id,
          cantidadTotal: 100 + i * 50,
          cantidadComprometida: i * 10,
          ongId: ong.id,
        },
      });
    }
  }

  console.log('Seed completado exitosamente');
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
