/*
  Warnings:

  - The `estado` column on the `Ong` table would be dropped and recreated. This will lead to data loss if there is data in the column.
  - You are about to drop the column `cantidadComprometida` on the `Recurso` table. All the data in the column will be lost.
  - You are about to drop the column `cantidadTotal` on the `Recurso` table. All the data in the column will be lost.
  - You are about to drop the column `ongId` on the `Recurso` table. All the data in the column will be lost.

*/
-- CreateEnum
CREATE TYPE "EstadoOng" AS ENUM ('HABILITADA', 'SUSPENDIDA', 'BAJA');

-- DropForeignKey
ALTER TABLE "Recurso" DROP CONSTRAINT "Recurso_ongId_fkey";

-- AlterTable
ALTER TABLE "Ong" DROP COLUMN "estado",
ADD COLUMN     "estado" "EstadoOng" NOT NULL DEFAULT 'HABILITADA';

-- AlterTable
ALTER TABLE "Recurso" DROP COLUMN "cantidadComprometida",
DROP COLUMN "cantidadTotal",
DROP COLUMN "ongId";

-- CreateTable
CREATE TABLE "OngRecurso" (
    "ongId" INTEGER NOT NULL,
    "recursoId" INTEGER NOT NULL,
    "cantidadTotal" INTEGER NOT NULL,
    "cantidadComprometida" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "OngRecurso_pkey" PRIMARY KEY ("ongId","recursoId")
);

-- AddForeignKey
ALTER TABLE "OngRecurso" ADD CONSTRAINT "OngRecurso_ongId_fkey" FOREIGN KEY ("ongId") REFERENCES "Ong"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "OngRecurso" ADD CONSTRAINT "OngRecurso_recursoId_fkey" FOREIGN KEY ("recursoId") REFERENCES "Recurso"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
