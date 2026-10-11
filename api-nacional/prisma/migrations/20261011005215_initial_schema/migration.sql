-- CreateTable
CREATE TABLE "Ong" (
    "id" SERIAL NOT NULL,
    "razonSocial" TEXT NOT NULL,
    "descripcion" TEXT,
    "sigla" TEXT NOT NULL,
    "cuit" TEXT NOT NULL,
    "estado" TEXT NOT NULL DEFAULT 'habilitada',

    CONSTRAINT "Ong_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Recurso" (
    "id" SERIAL NOT NULL,
    "nombre" TEXT NOT NULL,
    "descripcion" TEXT,
    "categoriaId" INTEGER NOT NULL,
    "cantidadTotal" INTEGER NOT NULL,
    "cantidadComprometida" INTEGER NOT NULL DEFAULT 0,
    "ongId" INTEGER NOT NULL,

    CONSTRAINT "Recurso_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Categoria" (
    "id" SERIAL NOT NULL,
    "nombre" TEXT NOT NULL,
    "descripcion" TEXT,

    CONSTRAINT "Categoria_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "User" (
    "id" SERIAL NOT NULL,
    "username" TEXT NOT NULL,
    "password" TEXT NOT NULL,

    CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Ong_sigla_key" ON "Ong"("sigla");

-- CreateIndex
CREATE UNIQUE INDEX "Ong_cuit_key" ON "Ong"("cuit");

-- CreateIndex
CREATE UNIQUE INDEX "Categoria_nombre_key" ON "Categoria"("nombre");

-- CreateIndex
CREATE UNIQUE INDEX "User_username_key" ON "User"("username");

-- AddForeignKey
ALTER TABLE "Recurso" ADD CONSTRAINT "Recurso_categoriaId_fkey" FOREIGN KEY ("categoriaId") REFERENCES "Categoria"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Recurso" ADD CONSTRAINT "Recurso_ongId_fkey" FOREIGN KEY ("ongId") REFERENCES "Ong"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
