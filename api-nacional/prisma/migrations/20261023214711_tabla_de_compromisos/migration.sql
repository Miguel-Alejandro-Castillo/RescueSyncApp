-- CreateEnum
CREATE TYPE "EstadoCompromiso" AS ENUM ('ACTIVO', 'LIBERADO');

-- CreateTable
CREATE TABLE "Compromiso" (
    "id" SERIAL NOT NULL,
    "detalleAdjudicacionRef" INTEGER NOT NULL,
    "cantidad" INTEGER NOT NULL,
    "estado" "EstadoCompromiso" NOT NULL DEFAULT 'ACTIVO',
    "fechaCompromiso" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "fechaLiberacion" TIMESTAMP(3),
    "ongId" INTEGER NOT NULL,
    "recursoId" INTEGER NOT NULL,

    CONSTRAINT "Compromiso_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Compromiso_detalleAdjudicacionRef_key" ON "Compromiso"("detalleAdjudicacionRef");

-- CreateIndex
CREATE INDEX "Compromiso_ongId_recursoId_idx" ON "Compromiso"("ongId", "recursoId");

-- AddForeignKey
ALTER TABLE "Compromiso" ADD CONSTRAINT "Compromiso_ongId_recursoId_fkey" FOREIGN KEY ("ongId", "recursoId") REFERENCES "OngRecurso"("ongId", "recursoId") ON DELETE RESTRICT ON UPDATE CASCADE;
