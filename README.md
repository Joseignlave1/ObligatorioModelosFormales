# Ejemplo 1:

## Mercado Cambiario(Quant) 

Este proyecto compara tres estrategias de compra e intercambio de divisas en
los mismos escenarios de mercado. La ejecución predeterminada genera
**1.000.000 de escenarios** y presenta cuánto dinero obtiene cada estrategia.

## Modelo utilizado

El enunciado describe el comportamiento cualitativo de las estrategias, pero
no fija distribuciones ni valores numéricos. Para poder simularlo se adoptaron
supuestos explícitos y configurables:

- Cada escenario comienza con USD 10.000 y genera un flujo ordenado de
  oportunidades de arbitraje.
- Una oportunidad representa un ciclo que fue descubierto a partir de órdenes
  de compra e intercambio. Contiene una divisa objetivo y entre 2 y 8
  intercambios.
- La cantidad de oportunidades sigue una distribución de Poisson con media 8,
  limitada a 16 por escenario.
- El rendimiento esperado por intercambio es uniforme entre 0,3 % y 1,2 %.
- Cada intercambio cobra una comisión de 0,05 %.
- El producto de las tasas determina el rendimiento del ciclo. Como el
  rendimiento mínimo supera la comisión, la rentabilidad esperada crece
  estrictamente con la longitud del ciclo, tal como supone el enunciado.
- Al ejecutar existe un impacto de mercado lognormal. Esto permite obtener
  ganancias o pérdidas aun cuando la oportunidad parecía rentable.
- Cada estrategia invierte el 100 % del capital en un único ciclo. La fracción
  puede modificarse con `--fraccion-invertida`.
- Todos los valores aleatorios de un escenario son compartidos por las tres
  estrategias, de modo que la comparación sea justa.

Las estrategias se modelan de la siguiente forma:

1. **Retorno a A:** acepta el primer ciclo rentable cuya divisa objetivo sea A
   y rechaza oportunidades con otros objetivos.
2. **Múltiples objetivos:** acepta el primer ciclo rentable, cualquiera sea su
   divisa objetivo.
3. **Exploración limitada:** espera hasta el límite temporal y elige el ciclo
   con mayor rendimiento esperado entre los que tengan como máximo `k`
   intercambios.

La simulación trabaja por lotes con NumPy. Así se pueden procesar un millón de
escenarios sin conservarlos todos en memoria. No se crea un millón de objetos
`Graph`, porque eso haría la ejecución innecesariamente lenta; las matrices de
oportunidades representan los ciclos encontrados por esos grafos dinámicos.

## Instalación

Se recomienda usar un entorno virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Ejecución

```bash
python simulacion.py
```

Para hacer una prueba rápida:

```bash
python simulacion.py --simulaciones 10000 --muestra-grafico 10000
```

Ejemplo con otros parámetros:

```bash
python simulacion.py \
  --simulaciones 1000000 \
  --capital-inicial 20000 \
  --divisas 8 \
  --k 7 \
  --comision 0.001 \
  --semilla 42
```

Todos los argumentos disponibles se consultan con:

```bash
python simulacion.py --help
```

## Resultados

La carpeta `resultados/` contendrá:

- `comparacion_estrategias.png`: ganancia promedio con intervalo de confianza
  del 95 % y distribución de ganancias.
- `resumen_estrategias.csv`: capital promedio, ganancia, desviación, extremos y
  probabilidades de operar, ganar y perder.

La semilla predeterminada es fija (`2026`), por lo que el experimento es
reproducible.

# Ejemplo 2:

## Data Center (Caché de Netflix en Antel, Pando)

Este proyecto compara distintas políticas de actualización de la caché de
Netflix (Open Connect Appliance, OCA) instalada en el data center de Antel en
Pando. Se estima cuánto cuesta por día el tráfico que no se sirve desde la
caché y debe salir por el enlace de tránsito internacional. La ejecución
predeterminada realiza **500 corridas de 28 días** para cada intervalo de
actualización y presenta el costo diario esperado de cada política.

## Modelo utilizado

El enunciado describe el problema de forma cualitativa, pero no fija
distribuciones ni valores numéricos. Para poder simularlo se adoptaron
supuestos explícitos y configurables:

- El catálogo tiene 7.000 títulos. El tamaño en disco de cada título, con
  todas sus codificaciones, es uniforme entre 5 y 60 GB.
- La probabilidad de que un pedido corresponda a un título sigue una
  distribución de tipo Zipf con exponente 0,8.
- La cantidad de reproducciones diarias de cada título sigue una distribución
  de Poisson. La tasa total es de 200.000 reproducciones por día y se
  multiplica por 1,3 los fines de semana.
- Cada día el 2 % del catálogo intercambia su popularidad con otro título
  elegido al azar, lo que representa estrenos y cambios de interés.
- La capacidad del OCA es de 120 TB. En cada actualización la caché guarda los
  títulos más populares que entran en esa capacidad.
- Cada GB que no está en la caché sale por tránsito internacional en hora pico
  y cuesta 0,010 USD. Cada GB de relleno viaja en hora valle y cuesta
  0,002 USD, porque el tránsito se factura por percentil 95.
- La capacidad y los costos unitarios son parámetros deterministas.
- Todas las políticas se evalúan con la misma semilla, de modo que la
  comparación sea justa.

Las políticas se modelan de la siguiente forma:

1. **Relleno diario (T = 1):** la caché se actualiza todos los días, como hace
   Netflix en la práctica.
2. **Rellenos intermedios (T = 2 y T = 3):** la caché se actualiza cada dos o
   tres días.
3. **Relleno semanal (T = 7):** la caché se actualiza una vez por semana.
4. **Relleno quincenal (T = 14):** la caché se actualiza cada dos semanas.

Cada corrida simula 28 días y registra el costo diario medio y la tasa de
acierto de la caché.

## Instalación

Se recomienda usar un entorno virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install numpy matplotlib
```

## Ejecución

```bash
python ejemplo2_data_center.py
```

Los parámetros del modelo (`N`, `ALPHA`, `CAP_TB`, `LAM`, `PICO`, `CHURN`,
`C_MISS`, `C_FILL`, `DIAS`, `RUNS` y `Ts`) se modifican al comienzo del archivo.

## Resultados

El script imprime una línea por cada intervalo de actualización y genera un
archivo:

- Salida en consola: costo diario medio con percentiles 5 y 95, y tasa de
  acierto de la caché (hit ratio) para cada `T`.
- `ejemplo2_resultados.png`: costo diario medio por política y distribución del
  costo para `T = 1`, `T = 7` y `T = 14`.

La semilla es fija (`42`), por lo que el experimento es reproducible.
