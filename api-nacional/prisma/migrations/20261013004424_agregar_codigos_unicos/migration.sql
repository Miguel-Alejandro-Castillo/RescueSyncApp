/*
  Warnings:

  - A unique constraint covering the columns `[codigo]` on the table `Categoria` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[codigo]` on the table `Recurso` will be added. If there are existing duplicate values, this will fail.
  - Added the required column `codigo` to the `Categoria` table without a default value. This is not possible if the table is not empty.
  - Added the required column `codigo` to the `Recurso` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "Categoria" ADD COLUMN     "codigo" TEXT NOT NULL;

-- AlterTable
ALTER TABLE "Recurso" ADD COLUMN     "codigo" TEXT NOT NULL;

-- CreateIndex
CREATE UNIQUE INDEX "Categoria_codigo_key" ON "Categoria"("codigo");

-- CreateIndex
CREATE UNIQUE INDEX "Recurso_codigo_key" ON "Recurso"("codigo");
