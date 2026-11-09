CREATE TABLE "ReservaConvocatoria" (
    "id" TEXT NOT NULL,
    "solicitud" JSONB,
    "resultado" JSONB NOT NULL,
    "liberadaEn" TIMESTAMP(3),
    CONSTRAINT "ReservaConvocatoria_pkey" PRIMARY KEY ("id")
);
