CREATE INDEX IX_Entradas_Lotes ON dbo.EntradaInsumo (IdInsumo, FechaCaducidad)
    INCLUDE (CantidadRestante) WHERE CantidadRestante > 0;
CREATE INDEX IX_Consumos_Insumo_Fecha ON dbo.ConsumoInsumo (IdInsumo, FechaConsumo);
CREATE INDEX IX_Mermas_Fecha ON dbo.Mermas (FechaMerma);
CREATE INDEX IX_Ventas_Fecha ON dbo.Ventas (FechaVenta, IdPlatillo);
