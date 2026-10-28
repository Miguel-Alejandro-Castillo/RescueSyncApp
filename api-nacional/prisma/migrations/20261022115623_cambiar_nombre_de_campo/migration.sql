/*
 Warnings:

 - You are about to drop the column `cantidadComprometida` on the `OngRecurso` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "OngRecurso" DROP COLUMN "cantidadComprometida",
ADD COLUMN     "cantidadReservada" INTEGER NOT NULL DEFAULT 0;
