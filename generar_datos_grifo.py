"""
Generador de datos SINTETICOS para el proyecto DEMO de un grifo (estacion de servicio).
Todos los datos son inventados: no corresponden a ningun negocio real.

Crea 11 archivos CSV en la carpeta donde ejecutes el script:
  dim_producto, dim_surtidor, dim_empleado, dim_cliente_credito,
  fact_ventas, fact_compras, fact_inventario_diario,
  fact_facturas_credito, fact_cobros_credito,
  fact_cierre_caja, fact_precios_competencia

Uso:       python generar_datos_grifo.py
Requiere:  pandas, numpy      (pip install pandas numpy)
"""
import numpy as np
import pandas as pd

# ----------------------------------------------------------------------
# 1. PARAMETROS GENERALES (puedes cambiarlos)
# ----------------------------------------------------------------------
rng = np.random.default_rng(2026)      # semilla fija: siempre salen los mismos datos
INICIO = pd.Timestamp("2025-07-01")
FIN = pd.Timestamp("2026-09-30")       # fecha de corte del analisis
DESPACHOS_BASE_DIA = 240               # despachos promedio por dia

dias = pd.date_range(INICIO, FIN, freq="D").as_unit("ns")
n_dias = len(dias)
n_semanas = (n_dias - 1) // 7 + 1

# ----------------------------------------------------------------------
# 2. CATALOGOS (tablas de dimensiones)
# ----------------------------------------------------------------------
productos = pd.DataFrame({
    "id_producto": [1, 2, 3, 4, 5],
    "producto": ["Gasohol 90", "Gasohol 95", "Gasohol 97", "Diesel B5", "GLP"],
    "capacidad_tanque_gal": [8000, 4000, 3000, 8000, 5000],
    # Parametros internos para simular (NO se exportan al CSV):
    "peso_ventas": [0.38, 0.12, 0.05, 0.30, 0.15],
    "margen_base": [1.60, 1.90, 2.30, 1.40, 1.20],        # soles por galon
    "precio_inicial": [16.50, 19.00, 22.00, 16.00, 8.50],  # soles por galon
    "galones_promedio": [5, 5, 5, 11, 6],
    "prob_credito": [0.02, 0.01, 0.01, 0.22, 0.05],
})

surtidores = pd.DataFrame({
    "id_surtidor": [1, 2, 3, 4, 5, 6],
    "isla": ["A", "A", "B", "B", "C", "C"],
})
# Que surtidores despachan cada producto (clave = id_producto)
surtidores_por_producto = {1: [1, 2, 3], 2: [1, 2], 3: [1], 4: [4, 5], 5: [6]}

empleados = pd.DataFrame({
    "id_empleado": range(1, 9),
    "empleado": ["Carlos Quispe", "Juan Huaman", "Luis Flores", "Pedro Vargas",
                 "Miguel Rojas", "Jose Castillo", "Raul Mendoza", "Andres Salazar"],
    "turno": ["Mañana"] * 3 + ["Tarde"] * 3 + ["Noche"] * 2,
})
# Que empleado atiende cada isla en cada turno
mapa_empleado = {
    "Mañana_A": 1, "Mañana_B": 2, "Mañana_C": 3,
    "Tarde_A": 4, "Tarde_B": 5, "Tarde_C": 6,
    "Noche_A": 7, "Noche_B": 7, "Noche_C": 8,
}

clientes = pd.DataFrame({
    "id_cliente": range(1, 13),
    "cliente": [
        "Transportes Andes del Centro S.A.C.", "Constructora Altavista S.A.C.",
        "Cooperativa de Mototaxis Sol Naciente", "Agroexport Valle Verde S.A.C.",
        "Logistica Pacifico Norte S.A.C.", "Minera Cerro Alto S.A.C.",
        "Transporte Escolar Los Pinos", "Distribuidora La Esperanza S.A.C.",
        "Servicios Generales Delta E.I.R.L.", "Buses Interprovinciales Sierra Azul",
        "Municipalidad Distrital Demo", "Ferreteria y Obras Santa Rosa S.A.C."],
    "tipo": ["Transporte", "Construccion", "Transporte", "Agro", "Transporte", "Mineria",
             "Transporte", "Distribucion", "Servicios", "Transporte", "Sector publico",
             "Construccion"],
    "dias_credito": [30, 30, 15, 30, 30, 30, 15, 30, 15, 30, 30, 15],
    "limite_credito": [30000, 25000, 8000, 20000, 35000, 40000, 6000, 15000, 10000,
                       30000, 25000, 9000],
})
# Perfil de pago de cada cliente (solo se usa para simular; NO se exporta)
perfil_pago = ["puntual", "puntual", "regular", "puntual", "moroso", "regular",
               "regular", "puntual", "moroso", "regular", "moroso", "regular"]
peso_cliente = np.array([0.16, 0.10, 0.05, 0.07, 0.15, 0.12, 0.03, 0.06, 0.04,
                         0.10, 0.07, 0.05])
peso_cliente = peso_cliente / peso_cliente.sum()

# ----------------------------------------------------------------------
# 3. COSTOS Y PRECIOS SEMANALES
#    El costo de compra sube o baja de forma aleatoria cada semana.
#    El precio de venta sigue al costo con una semana de retraso,
#    por eso el margen por galon varia en el tiempo.
# ----------------------------------------------------------------------
costo_sem = np.zeros((5, n_semanas))
for k in range(5):
    costo = productos.loc[k, "precio_inicial"] - productos.loc[k, "margen_base"]
    for w in range(n_semanas):
        costo = costo * (1 + rng.normal(0.0008, 0.008))
        costo_sem[k, w] = costo

margen_base = productos["margen_base"].to_numpy()[:, None]
costo_prev = np.concatenate([costo_sem[:, :1], costo_sem[:, :-1]], axis=1)
precio_sem = np.round(costo_prev + margen_base + rng.normal(0, 0.08, costo_sem.shape), 1)

semana_de_dia = np.arange(n_dias) // 7
precio_dia = precio_sem[:, semana_de_dia]          # matriz: producto x dia

# ----------------------------------------------------------------------
# 4. VENTAS (un registro por despacho)
# ----------------------------------------------------------------------
# 4.1 Cuantos despachos hay cada dia (fin de semana, quincena y tendencia)
factor_dia_semana = np.array([1.00, 1.00, 1.00, 1.03, 1.12, 1.15, 0.92])   # lun a dom
dow = dias.dayofweek.to_numpy()
dia_mes = dias.day.to_numpy()
factor_quincena = np.where(np.isin(dia_mes, [1, 2, 15, 16, 17, 30, 31]), 1.08, 1.0)
tendencia = 1 + 0.004 * np.arange(n_dias) / 30
lam = DESPACHOS_BASE_DIA * factor_dia_semana[dow] * factor_quincena * tendencia
n_desp = rng.poisson(lam * rng.lognormal(0, 0.05, n_dias))
N = int(n_desp.sum())

# 4.2 Fecha y hora de cada despacho (horas pico: manana, mediodia y tarde)
idx_dia = np.repeat(np.arange(n_dias), n_desp)
pesos_hora = np.array([0.6, 0.4, 0.3, 0.3, 0.5, 1.5, 3.5, 5.5, 6.0, 5.0, 4.2, 4.5,
                       5.5, 6.0, 5.0, 4.5, 4.8, 5.5, 6.5, 6.0, 4.5, 3.0, 2.0, 1.0])
pesos_hora = pesos_hora / pesos_hora.sum()
hora = rng.choice(24, N, p=pesos_hora)
segundos = hora * 3600 + rng.integers(0, 60, N) * 60 + rng.integers(0, 60, N)
fecha_hora = dias.values[idx_dia] + segundos.astype("timedelta64[s]")

# 4.3 Producto, surtidor, empleado y turno
k_prod = rng.choice(5, N, p=productos["peso_ventas"].to_numpy())     # 0..4
id_surtidor = np.zeros(N, dtype=int)
for k in range(5):
    mask = k_prod == k
    id_surtidor[mask] = rng.choice(surtidores_por_producto[k + 1], int(mask.sum()))

turno = np.where((hora >= 6) & (hora < 14), "Mañana",
                 np.where((hora >= 14) & (hora < 22), "Tarde", "Noche"))
isla = surtidores.set_index("id_surtidor").loc[id_surtidor, "isla"].to_numpy()
clave = pd.Series(turno) + "_" + pd.Series(isla)
id_empleado = clave.map(mapa_empleado).to_numpy()

# 4.4 Forma de pago y credito
forma = rng.choice(["Efectivo", "Tarjeta", "Yape/Plin"], N, p=[0.60, 0.25, 0.15])
es_credito = rng.random(N) < productos["prob_credito"].to_numpy()[k_prod]
forma = np.where(es_credito, "Credito", forma)

id_cliente = np.full(N, np.nan)
id_cliente[es_credito] = rng.choice(clientes["id_cliente"].to_numpy(),
                                    int(es_credito.sum()), p=peso_cliente)

# 4.5 Galones, precio y monto
precio_gal = precio_dia[k_prod, idx_dia]
prom = productos["galones_promedio"].to_numpy()[k_prod]
sigma = 0.5
gal_litros = rng.lognormal(np.log(prom) - sigma ** 2 / 2, sigma)          # carga "libre"
monto_fijo = rng.choice([10, 15, 20, 30, 40, 50, 60, 80, 100], N)
gal_monto = monto_fijo / precio_gal                                       # "S/ 30 de gasolina"
por_monto = (rng.random(N) < 0.45) & (k_prod != 3)                        # el diesel no
galones = np.where(por_monto, gal_monto, gal_litros)
galones = np.where(es_credito & (k_prod == 3), galones * 2.5, galones)    # flotas cargan mas
galones = np.round(np.clip(galones, 0.5, 60), 3)
monto = np.round(galones * precio_gal, 2)

ventas = pd.DataFrame({
    "fecha_hora": fecha_hora,
    "id_producto": k_prod + 1,
    "id_surtidor": id_surtidor,
    "id_empleado": id_empleado,
    "turno": turno,
    "galones": galones,
    "precio_galon": precio_gal,
    "monto": monto,
    "forma_pago": forma,
    "id_cliente": pd.Series(id_cliente).astype("Int64"),
})
ventas = ventas.sort_values("fecha_hora").reset_index(drop=True)
ventas.insert(0, "id_despacho", np.arange(1, N + 1))
ventas["fecha"] = ventas["fecha_hora"].dt.normalize()
ventas["hora"] = ventas["fecha_hora"].dt.hour

# ----------------------------------------------------------------------
# 5. INVENTARIO DIARIO Y COMPRAS (cisternas)
#    Cada dia: stock inicial + compras - ventas = stock teorico.
#    El stock MEDIDO (varillaje) difiere un poco del teorico: esa es la merma.
#    Historia plantada: el Diesel pierde combustible entre mar y abr de 2026.
# ----------------------------------------------------------------------
ventas_dia = (ventas.groupby(["fecha", "id_producto"])["galones"].sum()
              .unstack(fill_value=0).reindex(dias, fill_value=0))

inventario, compras = [], []
id_compra = 1
for k in range(5):
    pid = k + 1
    cap = float(productos.loc[k, "capacidad_tanque_gal"])
    stock = cap * 0.70
    for i, d in enumerate(dias):
        stock_ini = stock
        comp = 0.0
        if stock_ini < cap * 0.30:                      # tanque bajo: llega una cisterna
            pedido = rng.choice([0.55, 0.65, 0.75]) * cap
            comp = float(np.round(min(pedido, cap * 0.95 - stock_ini), -2))
            if comp > 0:
                costo = round(float(costo_sem[k, i // 7] * (1 + rng.normal(0, 0.004))), 3)
                compras.append({
                    "id_compra": id_compra, "fecha": d, "id_producto": pid,
                    "galones": comp, "costo_galon": costo,
                    "monto": round(comp * costo, 2),
                    "proveedor": str(rng.choice(["PetroAndes S.A.", "Energia Sur S.A.C."])),
                })
                id_compra += 1
        vend = float(ventas_dia.at[d, pid])
        teorico = stock_ini + comp - vend
        variacion = rng.normal(-0.001 * vend, 0.003 * vend)        # merma normal (pequena)
        if pid == 4 and pd.Timestamp("2026-03-01") <= d <= pd.Timestamp("2026-04-15"):
            variacion -= rng.uniform(0.008, 0.016) * vend           # fuga plantada
        stock = teorico + variacion
        inventario.append({
            "fecha": d, "id_producto": pid,
            "stock_inicial": round(stock_ini, 2), "compras_gal": comp,
            "ventas_gal": round(vend, 2), "stock_final_medido": round(stock, 2),
        })

compras = pd.DataFrame(compras)
inventario = pd.DataFrame(inventario)

# ----------------------------------------------------------------------
# 6. CREDITOS: facturas quincenales y cobros
# ----------------------------------------------------------------------
cred = ventas[ventas["forma_pago"] == "Credito"].copy()
fin_mes = cred["fecha"] + pd.offsets.MonthEnd(0)
dia_15 = cred["fecha"].dt.to_period("M").dt.to_timestamp() + pd.Timedelta(days=14)
cred["emision"] = dia_15.where(cred["fecha"].dt.day <= 15, fin_mes)

facturas = cred.groupby(["id_cliente", "emision"], as_index=False)["monto"].sum()
facturas["id_cliente"] = facturas["id_cliente"].astype(int)
facturas["monto"] = facturas["monto"].round(2)
facturas = facturas.merge(clientes[["id_cliente", "dias_credito"]], on="id_cliente")
facturas["fecha_vencimiento"] = facturas["emision"] + pd.to_timedelta(facturas["dias_credito"], unit="D")
facturas = facturas.sort_values(["emision", "id_cliente"]).reset_index(drop=True)
facturas.insert(0, "id_factura", np.arange(1, len(facturas) + 1))
facturas["nro_factura"] = "F002-" + facturas["id_factura"].astype(str).str.zfill(6)
facturas = facturas.rename(columns={"emision": "fecha_emision"})

retraso = {"puntual": (0, 4), "regular": (10, 10), "moroso": (40, 30)}   # dias tras vencer
p_impaga = {"puntual": 0.02, "regular": 0.08, "moroso": 0.25}
perfil_de = dict(zip(clientes["id_cliente"], perfil_pago))

cobros, id_cobro = [], 1
for _, f in facturas.iterrows():
    pf = perfil_de[int(f["id_cliente"])]
    mu, sd = retraso[pf]
    fecha_cobro = f["fecha_vencimiento"] + pd.Timedelta(days=int(rng.normal(mu, sd)))
    fecha_cobro = max(fecha_cobro, f["fecha_emision"] + pd.Timedelta(days=1))
    if rng.random() < p_impaga[pf] or fecha_cobro > FIN:
        continue                                        # factura aun sin cobrar
    pago = f["monto"] if rng.random() < 0.9 else round(f["monto"] * rng.uniform(0.4, 0.8), 2)
    cobros.append({"id_cobro": id_cobro, "id_factura": int(f["id_factura"]),
                   "fecha_cobro": fecha_cobro, "monto_cobrado": pago})
    id_cobro += 1
cobros = pd.DataFrame(cobros)

# ----------------------------------------------------------------------
# 7. CIERRE DE CAJA (efectivo esperado vs entregado por empleado y dia)
#    Historia plantada: el empleado 5 entrega faltantes de forma constante.
# ----------------------------------------------------------------------
caja = (ventas[ventas["forma_pago"] == "Efectivo"]
        .groupby(["fecha", "id_empleado"], as_index=False)["monto"].sum()
        .rename(columns={"monto": "efectivo_esperado"}))
caja["efectivo_esperado"] = caja["efectivo_esperado"].round(2)
dif = rng.normal(0, 3, len(caja))
dif = np.where(caja["id_empleado"] == 5, rng.normal(-18, 10, len(caja)), dif)
caja["efectivo_entregado"] = (caja["efectivo_esperado"] + dif).round(2)
caja["diferencia"] = (caja["efectivo_entregado"] - caja["efectivo_esperado"]).round(2)
caja = caja.merge(empleados[["id_empleado", "turno"]], on="id_empleado")
caja = caja.sort_values(["fecha", "id_empleado"]).reset_index(drop=True)
caja.insert(0, "id_cierre", np.arange(1, len(caja) + 1))

# ----------------------------------------------------------------------
# 8. PRECIOS DE LA COMPETENCIA (semanales, dos grifos vecinos)
# ----------------------------------------------------------------------
filas = []
semanas = INICIO + pd.to_timedelta(np.arange(n_semanas) * 7, unit="D")
for k in range(5):
    for nombre, desfase in [("Grifo Vecino A", -0.2), ("Grifo Vecino B", 0.1)]:
        precios = np.round(precio_sem[k] + desfase + rng.normal(0, 0.08, n_semanas), 1)
        for fecha_sem, p in zip(semanas, precios):
            filas.append({"fecha_semana": fecha_sem, "id_producto": k + 1,
                          "competidor": nombre, "precio_galon": float(p)})
precios_comp = pd.DataFrame(filas)

# ----------------------------------------------------------------------
# 9. EXPORTAR A CSV
# ----------------------------------------------------------------------
def guardar(df, nombre):
    """Guarda un DataFrame como CSV (con fechas en formato AAAA-MM-DD)."""
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            formato = "%Y-%m-%d %H:%M:%S" if c == "fecha_hora" else "%Y-%m-%d"
            df[c] = df[c].dt.strftime(formato)
    df.to_csv(f"{nombre}.csv", index=False, encoding="utf-8-sig")
    print(f"{nombre}.csv  ->  {len(df):,} filas")


guardar(productos[["id_producto", "producto", "capacidad_tanque_gal"]], "dim_producto")
guardar(surtidores, "dim_surtidor")
guardar(empleados, "dim_empleado")
guardar(clientes, "dim_cliente_credito")
guardar(ventas[["id_despacho", "fecha", "hora", "fecha_hora", "id_producto", "id_surtidor",
                "id_empleado", "turno", "galones", "precio_galon", "monto",
                "forma_pago", "id_cliente"]], "fact_ventas")
guardar(compras, "fact_compras")
guardar(inventario, "fact_inventario_diario")
guardar(facturas[["id_factura", "nro_factura", "id_cliente", "fecha_emision",
                  "fecha_vencimiento", "monto"]], "fact_facturas_credito")
guardar(cobros, "fact_cobros_credito")
guardar(caja[["id_cierre", "fecha", "id_empleado", "turno", "efectivo_esperado",
              "efectivo_entregado", "diferencia"]], "fact_cierre_caja")
guardar(precios_comp, "fact_precios_competencia")

print(f"\nPeriodo: {INICIO.date()} a {FIN.date()}  |  Fecha de corte: {FIN.date()}")
print(f"Ventas totales: S/ {ventas['monto'].sum():,.0f}  |  Galones: {ventas['galones'].sum():,.0f}")
