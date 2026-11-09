create database GrifoDemo

select MIN(fecha_emision), MAX(fecha_emision)
from fact_facturas_credito

select id_factura, count(*)
from fact_cobros_credito
group by id_factura
having count(*) = 2

select *
from dim_cliente_credito
select *
from fact_ventas

--Crear vista.

CREATE OR ALTER VIEW vw_credito AS
SELECT  
	fc.id_factura,
	fc.nro_factura,
	dcc.id_cliente,
	dcc.cliente,
	fc.fecha_emision,
	fc.fecha_vencimiento,
	fc.monto,
	ISNULL(SUM(fcc.monto_cobrado),0) AS monto_cobrado,
	fc.monto - ISNULL(SUM(fcc.monto_cobrado),0) AS saldo_factura,
	MAX(fcc.fecha_cobro) AS ultima_fecha_cobro,
	CAST('2026-09-30' AS DATE) AS fecha_corte,
	CASE WHEN fecha_vencimiento < CAST('2026-09-30' AS DATE) AND (fc.monto - ISNULL(SUM(fcc.monto_cobrado),0)) > 0
	THEN DATEDIFF(DAY, fecha_vencimiento, '2026-09-30') 
	ELSE 0 
	END AS dias_atraso
FROM fact_facturas_credito fc
LEFT JOIN fact_cobros_credito fcc ON fc.id_factura=fcc.id_factura
JOIN dim_cliente_credito dcc ON fc.id_cliente=dcc.id_cliente
GROUP BY 
	fc.id_factura,
	fc.nro_factura,
	dcc.id_cliente,
	dcc.cliente,
	fc.fecha_emision,
	fc.fecha_vencimiento,
	fc.monto
	

CREATE OR ALTER VIEW vw_aging_credito AS
SELECT *,
	CASE 
	WHEN saldo_factura <= 0 THEN 'Pagada'
	WHEN dias_atraso = 0	THEN 'Vigente'
	WHEN dias_atraso <= 30	THEN '1-30 dias'
	WHEN dias_atraso <= 60	THEN '31-60 dias'
	WHEN dias_atraso <= 90	THEN '61-90 dias'
	ELSE '+90 dias'
	END AS tramo_antiguedad,
	CASE 
	WHEN saldo_factura <= 0 THEN 0
	WHEN dias_atraso = 0	THEN 1
	WHEN dias_atraso <= 30	THEN 2
	WHEN dias_atraso <= 60	THEN 3
	WHEN dias_atraso <= 90	THEN 4
	ELSE 5
	END AS orden_tramo
FROM vw_credito
			
select *
from vw_aging_credito

--Validacion
SELECT COUNT(*) AS filas, SUM(monto) AS facturado, SUM(saldo_factura) AS deuda
FROM vw_aging_credito;
-- 360 filas | facturado 3,618,448.56 | deuda cerca de 812,055

SELECT tramo_antiguedad, orden_tramo, COUNT(*) AS facturas, SUM(saldo_factura) AS deuda
FROM vw_aging_credito
WHERE saldo_factura > 0
GROUP BY tramo_antiguedad, orden_tramo
ORDER BY orden_tramo;

