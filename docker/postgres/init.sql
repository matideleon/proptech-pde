-- ============================================================
-- PropTech PDE — Inicialización de PostgreSQL
-- ============================================================

-- Habilitar extensiones necesarias
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- Búsqueda de texto fuzzy
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";    -- UUID generation
CREATE EXTENSION IF NOT EXISTS btree_gin;      -- GIN indexes para btree ops
CREATE EXTENSION IF NOT EXISTS unaccent;       -- Búsqueda sin acentos

-- Base de datos para Metabase
CREATE DATABASE metabase;

-- Configuración de locale para español
-- (ya configurado en el Dockerfile con POSTGRES_INITDB_ARGS)

-- ─── INDICES ADICIONALES (post-migration) ─────────────────────
-- Estos se crean después de que Alembic crea las tablas

-- Índice de texto completo en español
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_properties_fts
-- ON properties
-- USING GIN (to_tsvector('spanish', coalesce(title,'') || ' ' || coalesce(description,'')));

-- ─── FUNCIONES ÚTILES ─────────────────────────────────────────

-- Función para calcular distancia en km entre dos puntos
CREATE OR REPLACE FUNCTION distance_km(
    lat1 FLOAT, lon1 FLOAT,
    lat2 FLOAT, lon2 FLOAT
) RETURNS FLOAT AS $$
    SELECT ST_Distance(
        ST_MakePoint(lon1, lat1)::geography,
        ST_MakePoint(lon2, lat2)::geography
    ) / 1000.0;
$$ LANGUAGE SQL IMMUTABLE;

-- Función para obtener propiedades en radio
CREATE OR REPLACE FUNCTION properties_in_radius(
    center_lat FLOAT,
    center_lon FLOAT,
    radius_km FLOAT
) RETURNS TABLE(property_id UUID, distance_km FLOAT) AS $$
    SELECT
        p.id,
        distance_km(center_lat, center_lon, p.latitude, p.longitude) as dist
    FROM properties p
    WHERE p.latitude IS NOT NULL
      AND p.longitude IS NOT NULL
      AND ST_DWithin(
          ST_MakePoint(p.longitude, p.latitude)::geography,
          ST_MakePoint(center_lon, center_lat)::geography,
          radius_km * 1000
      )
    ORDER BY dist;
$$ LANGUAGE SQL;

-- ─── ROL DE SOLO LECTURA (para Metabase) ─────────────────────
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'metabase_reader') THEN
        CREATE ROLE metabase_reader WITH LOGIN PASSWORD 'metabase_readonly_123';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE proptech_pde TO metabase_reader;
GRANT USAGE ON SCHEMA public TO metabase_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO metabase_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO metabase_reader;

-- ─── LOG ─────────────────────────────────────────────────────
DO $$
BEGIN
    RAISE NOTICE 'PropTech PDE: Base de datos inicializada correctamente';
    RAISE NOTICE 'PostGIS version: %', (SELECT PostGIS_Version());
END
$$;
