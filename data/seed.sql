-- ERP mock: dos copias de los mismos datos.
-- contactos / comprobantes = "SQL / HeidiSQL" (más completo).
-- api_* = lo que sirve la API REST (con 3 desfasajes plantados).

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS api_comprobantes;
DROP TABLE IF EXISTS api_contactos;
DROP TABLE IF EXISTS comprobantes;
DROP TABLE IF EXISTS contactos;
DROP TABLE IF EXISTS empresas;

CREATE TABLE empresas (
    id INTEGER PRIMARY KEY,
    razon_social TEXT NOT NULL,
    cuit TEXT NOT NULL
);

CREATE TABLE contactos (
    id INTEGER PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    nombre TEXT NOT NULL,
    email TEXT NOT NULL,
    telefono TEXT
);

CREATE TABLE comprobantes (
    id INTEGER PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    tipo TEXT NOT NULL,
    punto_venta TEXT NOT NULL,
    numero TEXT NOT NULL,
    numero_completo TEXT NOT NULL UNIQUE,
    total REAL NOT NULL,
    estado TEXT NOT NULL
);

CREATE TABLE api_contactos (
    id INTEGER PRIMARY KEY,
    empresa_id INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    email TEXT NOT NULL,
    telefono TEXT
);

CREATE TABLE api_comprobantes (
    id INTEGER PRIMARY KEY,
    empresa_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    punto_venta TEXT NOT NULL,
    numero TEXT NOT NULL,
    numero_completo TEXT NOT NULL UNIQUE,
    total REAL NOT NULL,
    estado TEXT NOT NULL
);

INSERT INTO empresas (id, razon_social, cuit) VALUES
    (12, 'Papelera del Sur S.A.', '30712345681'),
    (20, 'Distribuidora Norte S.A.', '30798765432'),
    (33, 'Logistica Andina S.R.L.', '30711122233');

INSERT INTO contactos (id, empresa_id, nombre, email, telefono) VALUES
    (501, 12, 'Ana Perez', 'ana.viejo@mail.com', '1144556677'),
    (502, 12, 'Luis Gomez', 'luis.gomez@papelera.com', '1144556678'),
    (503, 12, 'Marta Ruiz', 'marta.ruiz@papelera.com', '1144556679'),
    (601, 20, 'Sofia Diaz', 'sofia.diaz@dnorte.com', '1144001122'),
    (602, 20, 'Pablo Herrera', 'pablo.herrera@dnorte.com', '1144001123'),
    (701, 33, 'Elena Castro', 'elena.castro@andina.com', '1144889900');

INSERT INTO comprobantes (
    id, empresa_id, tipo, punto_venta, numero, numero_completo, total, estado
) VALUES
    (1890, 12, 'FC A', '0003', '00001890', 'FC A 0003-00001890', 150000.00, 'emitido'),
    (1891, 12, 'FC A', '0003', '00001891', 'FC A 0003-00001891', 87500.50, 'emitido'),
    (1892, 12, 'NC A', '0003', '00000012', 'NC A 0003-00000012', 12000.00, 'emitido'),
    (2101, 20, 'FC A', '0001', '00004500', 'FC A 0001-00004500', 150000.00, 'emitido'),
    (2102, 20, 'FC B', '0001', '00004501', 'FC B 0001-00004501', 32000.00, 'emitido'),
    (3301, 33, 'FC A', '0002', '00001001', 'FC A 0002-00001001', 99000.00, 'emitido'),
    (3302, 33, 'FC A', '0002', '00001002', 'FC A 0002-00001002', 4500.00, 'emitido'),
    (3303, 33, 'ND A', '0002', '00000003', 'ND A 0002-00000003', 2100.00, 'emitido');

-- Copia casi igual hacia la API...
INSERT INTO api_contactos SELECT * FROM contactos;
INSERT INTO api_comprobantes SELECT * FROM comprobantes;

-- Mentira 1: mail del contacto 501 distinto en la API.
UPDATE api_contactos SET email = 'ana@mail.com' WHERE id = 501;

-- Mentira 2: factura que existe en SQL y no sale por la API.
DELETE FROM api_comprobantes WHERE numero_completo = 'FC A 0003-00001890';

-- Mentira 3: un cero de menos en el importe (error típico de sync).
UPDATE api_comprobantes SET total = 15000.00 WHERE numero_completo = 'FC A 0001-00004500';
