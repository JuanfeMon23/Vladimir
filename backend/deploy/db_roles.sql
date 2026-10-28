-- Roles de BD de minimo privilegio para Vladimir (idempotente; ver README,
-- seccion "Produccion (backend)").
--
--   vladimir_migrator  duenio del esquema, tablas, funciones y triggers; hace el
--                      DDL. SOLO lo usa Alembic (MIGRATION_DATABASE_URL).
--   vladimir_app       lo que usa la API (DATABASE_URL): SELECT/INSERT/UPDATE
--                      sobre las tablas y USAGE/SELECT en las secuencias. Sin
--                      DELETE (todas las tablas tienen trigger anti-borrado
--                      VLD01: nada se elimina, solo se desactiva), sin DDL, sin
--                      TRUNCATE, sin acceso a alembic_version; sobre
--                      activity_events y settings_history (append-only) solo
--                      SELECT e INSERT. Sin superusuario.
--
-- Correr como superusuario (o un rol que pueda crear roles y cambiar duenios),
-- conectado a la BD de Vladimir:
--
--   psql -d vladimir -v ON_ERROR_STOP=1 -f deploy/db_roles.sql
--
-- NO define contrasenas (no hay secretos en el repo): los roles se crean LOGIN
-- sin contrasena y no pueden entrar hasta que el operador la fije, p. ej. con
-- `\password vladimir_app` en psql. Volver a correr despues de CADA migracion
-- que agregue tablas: los permisos no se heredan solos (a proposito: una tabla
-- nueva falla cerrada hasta que se re-aplica el script). Si una tabla nueva
-- debe ser append-only, agregarla a la lista de la seccion 4.

-- 1) Roles (sin superusuario, sin crear BD/roles, sin saltarse RLS).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vladimir_migrator') THEN
        CREATE ROLE vladimir_migrator LOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vladimir_app') THEN
        CREATE ROLE vladimir_app LOGIN;
    END IF;
END
$$;

ALTER ROLE vladimir_migrator NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE vladimir_app NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;

-- 2) Conexion a esta BD.
DO $$
BEGIN
    EXECUTE format(
        'GRANT CONNECT ON DATABASE %I TO vladimir_app, vladimir_migrator',
        current_database()
    );
END
$$;

-- 3) vladimir_migrator es duenio del esquema y de sus tablas y funciones
-- (los triggers pertenecen a su tabla).
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO vladimir_migrator;

DO $$
DECLARE
    obj record;
BEGIN
    FOR obj IN
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public' AND tableowner <> 'vladimir_migrator'
    LOOP
        -- Las secuencias de columnas serial/identity cambian de duenio con la tabla.
        EXECUTE format('ALTER TABLE public.%I OWNER TO vladimir_migrator', obj.tablename);
    END LOOP;
    FOR obj IN
        SELECT p.oid::regprocedure AS signature
        FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public' AND p.prokind = 'f'
          AND pg_get_userbyid(p.proowner) <> 'vladimir_migrator'
          AND NOT EXISTS (
              SELECT 1 FROM pg_depend d
              WHERE d.objid = p.oid AND d.deptype = 'e'
          )
    LOOP
        EXECUTE format('ALTER FUNCTION %s OWNER TO vladimir_migrator', obj.signature);
    END LOOP;
END
$$;

-- 4) vladimir_app: solo SELECT/INSERT/UPDATE. Se parte de cero para quitar lo
-- que sobrara.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM vladimir_app;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM vladimir_app;
GRANT USAGE ON SCHEMA public TO vladimir_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO vladimir_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO vladimir_app;

-- Excepciones: historiales append-only (solo leer y agregar; ademas tienen
-- trigger que bloquea UPDATE/DELETE) y la tabla de control de Alembic.
DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['activity_events', 'settings_history']
    LOOP
        IF to_regclass('public.' || t) IS NOT NULL THEN
            EXECUTE format('REVOKE ALL ON TABLE public.%I FROM vladimir_app', t);
            EXECUTE format('GRANT SELECT, INSERT ON TABLE public.%I TO vladimir_app', t);
        END IF;
    END LOOP;
    IF to_regclass('public.alembic_version') IS NOT NULL THEN
        REVOKE ALL ON TABLE public.alembic_version FROM vladimir_app;
    END IF;
END
$$;
