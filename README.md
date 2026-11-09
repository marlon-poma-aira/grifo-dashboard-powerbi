# Dashboard de Gestión para Estación de Servicio (Grifo)

**Power BI · SQL Server · DAX** — proyecto de portafolio basado en mi trabajo como Asesor de Análisis de Datos en una estación de servicio.

Dashboard interactivo de cuatro páginas que responde las preguntas que se hace el dueño de un grifo: **¿qué vendo y cuánto gano?**, **¿cuándo se vende?**, **¿dónde se me escapa combustible y dinero en caja?** y **¿cuánto me deben los clientes a crédito?**

> **Aviso:** este repositorio es una pequeña parte de un proyecto mayor. Para proteger la información del negocio, los datos aquí publicados son **simulados** y replican la estructura de su operación. Se generaron con un script de Python creado con ayuda de IA. Las cifras de este README corresponden a esos datos simulados, no al negocio real.

## Capturas

| Ventas y márgenes | Inventario y mermas |
|---|---|
| <img width="893" height="500" alt="image" src="https://github.com/user-attachments/assets/935f0b2d-1c96-4256-83b1-970d607a5cf5" />| <img width="886" height="500" alt="image" src="https://github.com/user-attachments/assets/991511d0-bc03-494a-ad68-302221fa57c2" />
 |

| Operación y caja | Crédito y cobranza |
|---|---|
| <img width="888" height="498" alt="image" src="https://github.com/user-attachments/assets/c350496e-5d17-4bf1-8519-527fc7597b14" />| <img width="888" height="502" alt="image" src="https://github.com/user-attachments/assets/aaac4b1e-c41b-4892-b2d9-4e9739072f61" />
 |

## Hallazgos principales (datos simulados, julio 2025 – septiembre 2026)

**Ventas y márgenes**
- El **diésel representa el 61% de las ventas** (59% de los galones).
- Margen por galón: G97 S/ 2.33 · G95 S/ 1.92 · G90 S/ 1.54 · Diésel S/ 1.38 · GLP S/ 1.18. El producto que más se vende no es el que más margen deja.
- El **25.8% de los despachos** ocurre entre las 17 y las 20 h; viernes y sábado superan los 280 despachos diarios frente a 229 del domingo.
- Los días de quincena venden **7.4% más** que el resto.
- Los surtidores 4 y 5 concentran cerca del 61% de las ventas.

**Inventario**
- Al comparar el stock medido con el teórico (stock inicial + compras − ventas), el diésel muestra **faltantes entre marzo y abril de 2026**: −1.26% en marzo y −0.68% en abril.
- En 46 días se pierden unos **643 galones (≈ S/ 9,700)**, más de la mitad de la merma total del diésel en todo el periodo.
- Al cierre, el diésel tiene solo **4.6 días de cobertura**, frente a 28 días de la G97.

**Caja**
- La diferencia de caja se concentra en **un empleado del turno tarde**, con faltantes en más del 90% de sus cierres, mientras el resto del personal se mantiene cerca de cero. El problema es de un patrón, no de errores aleatorios.

**Crédito**
- **Deuda de S/ 812,055**, con el **46% a más de 90 días**.
- Un solo cliente concentra el 30% de la deuda y los 3 mayores suman el 51%. Los 10 mayores deudores superan su límite de crédito.
- **DSO ≈ 94 días**; solo se ha cobrado el 77.6% de lo facturado.
- El 96% del crédito se otorga en diésel; el crédito es el 25.9% de las ventas.

**Precios vs. competencia**
- El grifo vende en promedio S/ 0.20 por encima del Vecino A y S/ 0.10 por debajo del Vecino B.

### Recomendaciones que se desprenden del análisis
1. Revisar el control de despacho y recepción del diésel y reponer stock antes de los 4–5 días de cobertura.
2. Hacer seguimiento de los cierres de caja del turno tarde y revisar el procedimiento de cobro.
3. Suspender nuevos créditos a clientes que exceden su límite y priorizar la cobranza de las facturas de más de 90 días.
4. Reforzar la atención en las horas pico (17–20 h) y los fines de semana.

## Herramientas

| Herramienta | Uso en el proyecto |
|---|---|
| **SQL Server** | Modelo relacional, vistas, `LEFT JOIN`, cálculo de saldos y días de atraso, tramos de antigüedad con `CASE` |
| **Power BI** | Modelo en estrella, tabla de calendario, relaciones inactivas con `USERELATIONSHIP`, 4 páginas interactivas |
| **DAX** | Margen por galón, merma de inventario, días de cobertura, diferencia de caja, cartera vencida y DSO |
| **Python** (pandas, numpy) | Script que genera los datos simulados de forma reproducible (semilla fija), creado con ayuda de IA |

## Datos

11 tablas en formato CSV:

| Tipo | Tablas |
|---|---|
| Dimensiones | `dim_producto`, `dim_surtidor`, `dim_empleado`, `dim_cliente_credito` |
| Hechos | `fact_ventas`, `fact_compras`, `fact_inventario_diario`, `fact_facturas_credito`, `fact_cobros_credito`, `fact_cierre_caja`, `fact_precios_competencia` |

La **fecha de corte** del análisis de crédito es el 30/09/2026.

## Modelo de datos

Modelo en estrella: las tablas de hechos se relacionan con `dim_calendario`, `dim_producto`, `dim_surtidor`, `dim_empleado` y `dim_cliente_credito`. La cartera de crédito se consolida en dos vistas:

- `vw_credito`: una fila por factura, con saldo, última fecha de cobro y días de atraso.
- `vw_aging_credito`: agrega el tramo de antigüedad y su orden.

```sql
-- Saldo por factura: se conservan las facturas sin cobros (LEFT JOIN)
saldo_factura = monto - ISNULL(SUM(monto_cobrado), 0)

-- Tramos de antigüedad
CASE
    WHEN saldo_factura <= 0 THEN 'Pagada'
    WHEN dias_atraso = 0    THEN 'Vigente'
    WHEN dias_atraso <= 30  THEN '1-30 dias'
    WHEN dias_atraso <= 60  THEN '31-60 dias'
    WHEN dias_atraso <= 90  THEN '61-90 dias'
    ELSE '+90 dias'
END AS tramo_antiguedad
```

## Medidas DAX principales

```dax
Margen por Galon = [Precio Promedio Venta] - [Costo Promedio Compra]

% Merma = DIVIDE([Variacion Gal], SUM(fact_inventario_diario[ventas_gal]))

Dias de Cobertura = DIVIDE([Stock Actual], [Venta Diaria 30d])

Diferencia Caja = SUM(fact_cierre_caja[diferencia])

% Cartera Vencida = DIVIDE([Deuda Vencida Credito], [Deuda Credito])

DSO Credito = DIVIDE([Deuda Credito], [Ventas Credito 90d]) * 90

Cobrado por Mes =
CALCULATE(
    SUM(fact_cobros_credito[monto_cobrado]),
    USERELATIONSHIP(dim_calendario[Date], fact_cobros_credito[fecha_cobro]),
    CROSSFILTER(dim_calendario[Date], vw_aging_credito[fecha_emision], NONE)
)
```

## Estructura del repositorio

```
grifo-dashboard-powerbi/
├── data/                    # CSV simulados (11 tablas)
├── python/
│   └── generar_datos_grifo.py
├── sql/
│   └── vistas_credito.sql   # vw_credito y vw_aging_credito
├── powerbi/
│   └── Grifo.pbix
├── images/                  # capturas del dashboard
└── README.md
```

## Cómo reproducirlo

1. Ejecuta `python/generar_datos_grifo.py` para crear los 11 CSV (requiere `pandas` y `numpy`).
2. En SQL Server, crea la base `DemoGrifo` e importa los CSV con *Importar archivo plano* (fechas como `date`, montos como `decimal`).
3. Ejecuta `sql/vistas_credito.sql` para crear las vistas.
4. Abre `powerbi/Grifo.pbix` y, en *Transformar datos → Configuración de origen de datos*, apunta al nombre de tu servidor.

## Qué demuestra este proyecto

- **SQL:** vistas, uniones externas, agregaciones, `CASE` y validación de cifras contra el origen.
- **Power BI y DAX:** modelo en estrella, relaciones inactivas, medidas de negocio y diseño de un informe de varias páginas con storytelling para un dueño de negocio.
- **Visión de negocio:** convertir datos operativos en hallazgos y recomendaciones accionables.

## Próximos pasos

- Actualización automática de los datos con refresco programado.
- Alertas de stock bajo y de clientes sobre su límite de crédito.
- Seguridad por fila (RLS) para que cada responsable vea solo su información.

## Autor

**Marlon Poma Aira** — [LinkedIn](https://linkedin.com/in/marlon-poma-aira)
