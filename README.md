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
# ObligatorioModelosFormales
