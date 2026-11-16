
--consultas
CREATE VIEW dbo.vw_StockInsumos AS
SELECT i.IdInsumo, i.nombre AS producto, u.avreviatura AS Unidad, i.stockMinimo,
       ISNULL(SUM(cantidadRestante), 0) AS StockDisponible
FROM dbo.Insumos i
JOIN dbo.UnidadesMedida u ON u.IdUnidad = i.IdUnidad
LEFT JOIN dbo.EntradaInsumo e
       ON e.IdInsumo = i.IdInsumo AND e.CantidadRestante > 0
      AND e.FechaCaducidad >= CAST(GETDATE() AS DATE)
WHERE i.avtivo = 1
GROUP BY i.IdInsumo, i.Nombre, u.avreviatura, i.stockMinimo;
GO

--login
CREATE PROCEDURE dbo.sp_ValidarLogin
    @NombreUsuario VARCHAR(50), @Contrasena NVARCHAR(100), @NombreRol VARCHAR(20)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT u.IdUsuario, u.NombreUsuario, r.NombreRol
    FROM dbo.Usuarios u
    JOIN dbo.Roles r ON r.IdRol = u.IdRol
    WHERE u.NombreUsuario = @NombreUsuario
      AND u.Activo = 1
      AND r.NombreRol = @NombreRol
      AND u.contrasena = HASHBYTES('SHA2_256', CONCAT(CONVERT(NVARCHAR(36), u.Sal), @Contrasena));
END
GO

--registrar entrada
CREATE PROCEDURE dbo.sp_RegistrarEntrada
    @IdUsuario INT, @NombreProducto VARCHAR(100), @IdUnidad INT,
    @Cantidad DECIMAL(10,2), @FechaCaducidad DATE, @CostoUnitario DECIMAL(10,2) = 0
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    BEGIN TRY
        IF @Cantidad <= 0 THROW 50001, 'La cantidad debe ser mayor a 0.', 1;
        IF NOT EXISTS (SELECT 1 FROM dbo.Usuarios u JOIN dbo.Roles r ON r.IdRol = u.IdRol
                       WHERE u.IdUsuario = @IdUsuario AND u.Activo = 1 AND r.NombreRol IN ('Encargado','Dueño'))
            THROW 50002, 'El usuario no tiene permiso para registrar entradas.', 1;

        BEGIN TRAN;
        DECLARE @IdInsumo INT, @UnidadInsumo INT, @IdEntrada INT;
        SELECT @IdInsumo = IdInsumo, @UnidadInsumo = IdUnidad
        FROM dbo.Insumos WHERE Nombre = @NombreProducto;

        IF @IdInsumo IS NULL
        BEGIN
            INSERT dbo.Insumos (Nombre, IdUnidad) VALUES (@NombreProducto, @IdUnidad);
            SET @IdInsumo = SCOPE_IDENTITY();
        END
        ELSE IF @UnidadInsumo <> @IdUnidad
            THROW 50003, 'La unidad no coincide con la registrada para este producto.', 1;

        INSERT dbo.EntradaInsumo(IdInsumo, Cantidad, CantidadRestante, CostoUnitario, FechaCaducidad, IdUsuario)
        VALUES (@IdInsumo, @Cantidad, @Cantidad, @CostoUnitario, @FechaCaducidad, @IdUsuario);
        SET @IdEntrada = SCOPE_IDENTITY();
        COMMIT;

        SELECT @IdEntrada AS IdEntrada, @IdInsumo AS IdInsumo;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        THROW;
    END CATCH
END
GO

-- registrar consumo y descontar
CREATE PROCEDURE dbo.sp_RegistrarConsumo
    @IdUsuario INT, @IdInsumo INT, @Cantidad DECIMAL(10,2), @IdUnidad INT
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    BEGIN TRY
        IF @Cantidad <= 0 THROW 50010, 'La cantidad debe ser mayor a 0.', 1;
        IF NOT EXISTS (SELECT 1 FROM dbo.Insumos WHERE IdInsumo = @IdInsumo AND IdUnidad = @IdUnidad)
            THROW 50011, 'La unidad no coincide con la del insumo.', 1;

        BEGIN TRAN;
        DECLARE @Disponible DECIMAL(10,2) =
            (SELECT ISNULL(SUM(CantidadRestante), 0)
             FROM dbo.EntradaInsumo WITH (UPDLOCK, HOLDLOCK)
             WHERE IdInsumo = @IdInsumo AND CantidadRestante > 0
               AND FechaCaducidad >= CAST(GETDATE() AS DATE));
        IF @Disponible < @Cantidad THROW 50012, 'Stock insuficiente (sin contar lotes vencidos).', 1;

        DECLARE @Pendiente DECIMAL(10,2) = @Cantidad, @IdEntrada INT, @Lote DECIMAL(10,2), @Tomar DECIMAL(10,2);
        WHILE @Pendiente > 0
        BEGIN
            SELECT TOP 1 @IdEntrada = idEntrada, @Lote = CantidadRestante
            FROM dbo.EntradaInsumo
            WHERE IdInsumo = @IdInsumo AND CantidadRestante > 0
              AND FechaCaducidad >= CAST(GETDATE() AS DATE)
            ORDER BY FechaCaducidad, IdEntrada;

            SET @Tomar = CASE WHEN @Lote < @Pendiente THEN @Lote ELSE @Pendiente END;
            UPDATE dbo.EntradaInsumo SET CantidadRestante = CantidadRestante - @Tomar WHERE IdEntrada = @IdEntrada;
            SET @Pendiente = @Pendiente - @Tomar;
        END

        INSERT dbo.ConsumoInsumo (IdInsumo, Cantidad, IdUsuario) VALUES (@IdInsumo, @Cantidad, @IdUsuario);
        COMMIT;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        THROW;
    END CATCH
END
GO

-- inventario actual con aviso
CREATE PROCEDURE dbo.sp_VerInventario @DiasAviso INT = 7
AS
BEGIN
    SET NOCOUNT ON;
    SELECT i.Nombre AS Producto,
           e.CantidadRestante AS Cantidad,
           u.avreviatura AS Unidad,
           e.FechaCaducidad,
           CASE WHEN e.FechaCaducidad < CAST(GETDATE() AS DATE) THEN 'Vencido'
                WHEN e.FechaCaducidad <= DATEADD(DAY, @DiasAviso, CAST(GETDATE() AS DATE)) THEN 'Por vencer'
                ELSE 'Vigente' END AS Aviso
    FROM dbo.EntradaInsumo e
    JOIN dbo.Insumos i ON i.IdInsumo = e.IdInsumo
    JOIN dbo.UnidadesMedida u ON u.IdUnidad = i.IdUnidad
    WHERE e.CantidadRestante > 0
    ORDER BY e.FechaCaducidad, i.Nombre;
END
GO

--insumos por agotarse-- insumos por agotarse
CREATE PROCEDURE dbo.sp_InsumosPorAgotarse
AS
BEGIN
    SET NOCOUNT ON;
    SELECT Producto, StockDisponible, Unidad,
           CASE WHEN StockDisponible = 1 THEN 'Queda ' ELSE 'Quedan ' END
           + FORMAT(StockDisponible, '0.##') + ' ' + Unidad AS Mensaje
    FROM dbo.vw_StockInsumos
    WHERE StockMinimo > 0 AND StockDisponible <= StockMinimo
    ORDER BY StockDisponible;
END
GO

-- insumosproximos a vencer
CREATE PROCEDURE dbo.sp_InsumosProximosAVencer @Dias INT = 3
AS
BEGIN
    SET NOCOUNT ON;
    SELECT i.Nombre AS Producto, e.CantidadRestante AS Cantidad, u.avreviatura AS Unidad,
           e.FechaCaducidad, DATEDIFF(DAY, CAST(GETDATE() AS DATE), e.FechaCaducidad) AS DiasRestantes
    FROM dbo.EntradaInsumo e
    JOIN dbo.Insumos i ON i.IdInsumo = e.IdInsumo
    JOIN dbo.UnidadesMedida u ON u.IdUnidad = i.IdUnidad
    WHERE e.CantidadRestante > 0
      AND e.FechaCaducidad BETWEEN CAST(GETDATE() AS DATE) AND DATEADD(DAY, @Dias, CAST(GETDATE() AS DATE))
    ORDER BY e.FechaCaducidad;
END
GO

-- registrar merma

CREATE PROCEDURE dbo.sp_RegistrarMerma
    @IdUsuario INT, @IdEntrada INT, @Cantidad DECIMAL(10,2), @Motivo VARCHAR(20)
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRAN;
        DECLARE @Costo DECIMAL(10,2);
        SELECT @Costo = CostoUnitario
        FROM dbo.EntradaInsumo WITH (UPDLOCK)
        WHERE IdEntrada = @IdEntrada AND CantidadRestante >= @Cantidad;

        IF @Costo IS NULL THROW 50020, 'Lote inexistente o cantidad mayor a la disponible.', 1;

        UPDATE dbo.EntradaInsumo SET CantidadRestante = CantidadRestante - @Cantidad WHERE IdEntrada = @IdEntrada;
        INSERT dbo.Mermas (IdEntrada, Cantidad, CostoPerdido, Motivo, IdUsuario)
        VALUES (@IdEntrada, @Cantidad, @Cantidad * @Costo, @Motivo, @IdUsuario);
        COMMIT;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        THROW;
    END CATCH
END
GO

-- resumen del dueño
CREATE PROCEDURE dbo.sp_ResumenDueno @FechaInicio DATE, @FechaFin DATE
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @hasta DATE = DATEADD(DAY, 1, @FechaFin);
    WITH r AS (
        SELECT
          ISNULL((SELECT SUM(Cantidad * CostoUnitario) FROM dbo.EntradaInsumo
                  WHERE FechaEntrada >= @FechaInicio AND FechaEntrada < @hasta), 0) AS InversionInsumos,
          ISNULL((SELECT SUM(Cantidad * PrecioUnitario) FROM dbo.Ventas
                  WHERE FechaVenta >= @FechaInicio AND FechaVenta < @hasta), 0) AS VentasTotales,
          ISNULL((SELECT SUM(CostoPerdido) FROM dbo.Mermas
                  WHERE FechaMerma >= @FechaInicio AND FechaMerma < @hasta), 0) AS PerdidaPorMermas
    )
    SELECT InversionInsumos, VentasTotales, VentasTotales - InversionInsumos AS Ganancias, PerdidaPorMermas
    FROM r;
END
GO

--ventas ty margen de platullo por la ia y eso
CREATE VIEW dbo.vw_VentasPorPlatillo AS
SELECT p.Nombre, ISNULL(SUM(v.Cantidad), 0) AS UnidadesVendidas,
       p.Precio - p.CostoEstimado AS MargenUnitario
FROM dbo.Platillos p
LEFT JOIN dbo.Ventas v ON v.IdPlatillo = p.idPlatillos
 AND v.FechaVenta >= DATEADD(DAY, -30, SYSDATETIME())
WHERE p.Activo = 1
GROUP BY p.Nombre, p.Precio, p.CostoEstimado;
GO

--registro de venta
CREATE PROCEDURE dbo.sp_RegistrarVenta @IdUsuario INT, @IdPlatillo INT, @Cantidad INT
AS
BEGIN
    SET NOCOUNT ON;
    INSERT dbo.Ventas (IdPlatillo, Cantidad, PrecioUnitario, IdUsuario)
    SELECT @IdPlatillo, @Cantidad, Precio, @IdUsuario FROM dbo.Platillos WHERE idPlatillos = @IdPlatillo;
END
GO

-- cambio del dueño
CREATE PROCEDURE dbo.sp_CambiarAreaDueno
    @IdUsuario INT, @Contrasena NVARCHAR(100), @RolDestino VARCHAR(20)
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @IdRolDestino INT = (SELECT IdRol FROM dbo.Roles
                                 WHERE NombreRol = @RolDestino AND NombreRol IN ('Encargado','Empleado'));

    IF @IdRolDestino IS NULL
       OR NOT EXISTS (SELECT 1 FROM dbo.Usuarios u JOIN dbo.Roles r ON r.IdRol = u.IdRol
                      WHERE u.IdUsuario = @IdUsuario AND u.Activo = 1 AND r.NombreRol = 'Dueño'
                        AND u.contrasena = HASHBYTES('SHA2_256', CONCAT(CONVERT(NVARCHAR(36), u.Sal), @Contrasena)))
    BEGIN
        SELECT 0 AS Acceso; RETURN;
    END

    INSERT dbo.BitacoraCambioArea (IdUsuario, IdRolDestino) VALUES (@IdUsuario, @IdRolDestino);
    SELECT 1 AS Acceso, @RolDestino AS RolDestino;
END
GO


