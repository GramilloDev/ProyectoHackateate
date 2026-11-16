-- Roles y unidades
INSERT dbo.Roles (nombreRol) VALUES ('Dueño'), ('Encargado'), ('Empleado');
INSERT dbo.UnidadesMedida (nombre, avreviatura)
VALUES ('Kilogramo','kg'), ('Litro','litros'), ('Pieza','piezas');

-- 3 usuarios estándar (hash SHA-256 con sal)
DECLARE @s1 UNIQUEIDENTIFIER = NEWID(), @s2 UNIQUEIDENTIFIER = NEWID(), @s3 UNIQUEIDENTIFIER = NEWID();

INSERT dbo.Usuarios (nombreUsuario, contrasena, sal, idRol)
SELECT 'dueno', HASHBYTES('SHA2_256', CONCAT(CONVERT(NVARCHAR(36), @s1), N'Dueno123' )), @s1, idRol
FROM dbo.Roles WHERE nombreRol = 'Dueño';

INSERT dbo.Usuarios (nombreUsuario, contrasena, sal, idRol)
SELECT 'encargado', HASHBYTES('SHA2_256', CONCAT(CONVERT(NVARCHAR(36), @s2), N'Encargado123')), @s2, idRol
FROM dbo.Roles WHERE nombreRol = 'Encargado';

INSERT dbo.Usuarios (nombreUsuario, contrasena, sal, idRol)
SELECT 'empleado', HASHBYTES('SHA2_256', CONCAT(CONVERT(NVARCHAR(36), @s3), N'Empleado123')), @s3, idRol
FROM dbo.Roles WHERE nombreRol = 'Empleado';

-- 20 insumos de ejemplo
INSERT dbo.Insumos (Nombre, IdUnidad, StockMinimo)
SELECT v.Nombre, u.IdUnidad, v.Minimo
FROM (VALUES
    ('Arroz','kg',5), ('Frijol','kg',5), ('Pechuga de pollo','kg',5),
    ('Carne molida de res','kg',5), ('Tomate','kg',3), ('Cebolla','kg',4),
    ('Papa','kg',5), ('Pimiento','kg',2), ('Queso Oaxaca','kg',3),
    ('Aguacate','kg',3), ('Tortillas de maíz','kg',5),
    ('Leche','litros',3), ('Aceite vegetal','litros',5), ('Crema','litros',2),
    ('Caldo de pollo','litros',3),
    ('Jitomate','piezas',10), ('Pan para hamburguesa','piezas',10),
    ('Huevo','piezas',30), ('Lechuga romana','piezas',5), ('Limón','piezas',20)
) v(Nombre, Abrev, Minimo)
JOIN dbo.UnidadesMedida u ON u.avreviatura = v.Abrev;

-- Lotes de ejemplo (la última columna son los días para caducar: negativo = ya vencido)
DECLARE @enc INT = (SELECT IdUsuario FROM dbo.Usuarios WHERE NombreUsuario = 'encargado');
INSERT dbo.EntradaInsumo (idInsumo, cantidad, cantidadRestante, costoUnitario, fechaCaducidad, IdUsuario)
SELECT i.idInsumo, v.cant, v.cant, v.costo, DATEADD(DAY, v.Dias, CAST(GETDATE() AS DATE)), @enc
FROM (VALUES
    ('Arroz',20,28.00,120), ('Frijol',15,32.00,90),
    ('Pechuga de pollo',8,95.00,1), ('Pechuga de pollo',10,95.00,6),
    ('Carne molida de res',10,140.00,4), ('Tomate',1,30.00,6),
    ('Cebolla',12,22.00,10), ('Papa',18,20.00,14), ('Pimiento',2,45.00,1),
    ('Queso Oaxaca',6,160.00,12), ('Aguacate',4,80.00,3),
    ('Tortillas de maíz',10,24.00,2), ('Leche',12,24.00,5),
    ('Aceite vegetal',15,45.00,200), ('Crema',5,55.00,8),
    ('Caldo de pollo',6,38.00,25), ('Jitomate',30,3.50,-1),
    ('Pan para hamburguesa',5,6.00,3), ('Huevo',60,3.20,15),
    ('Huevo',30,3.20,30), ('Lechuga romana',12,18.00,4), ('Limón',40,1.50,9)
) v(nombre, cant, costo, dias)
JOIN dbo.Insumos i ON i.nombre = v.nombre;

-- 25 platillos de ejemplo
INSERT dbo.Platillos (nombre, precio, costoEstimado)
VALUES
 ('Ensalada César',95,35), ('Caldo Tlalpeño',110,40), ('Fajitas de pollo',140,50),
 ('Hamburguesa clásica',120,45), ('Hamburguesa con queso',135,52),
 ('Tacos de pollo',90,30), ('Tacos de res',100,38), ('Enchiladas verdes',115,40),
 ('Chilaquiles con pollo',105,35), ('Huevos a la mexicana',80,22),
 ('Omelette de queso',85,25), ('Quesadillas de queso Oaxaca',75,25),
 ('Sopa de tortilla',70,20), ('Sopa de arroz',55,15), ('Arroz con pollo',125,42),
 ('Pechuga a la plancha',130,48), ('Milanesa de pollo',135,50),
 ('Papas fritas',60,15), ('Guacamole con totopos',85,30), ('Frijoles charros',70,20),
 ('Tostadas de pollo',80,26), ('Molletes',65,18), ('Sincronizadas',70,22),
 ('Ensalada de la casa',80,28), ('Agua de limón',35,8);

 SELECT * FROM dbo.Roles;
SELECT * FROM dbo.Usuarios;
SELECT * FROM dbo.Insumos;