#!/usr/bin/env python3
"""Simulacion Monte Carlo para comparar tres estrategias de trading.

El modelo genera el mismo flujo ordenado de oportunidades de arbitraje para
las tres estrategias. Cada oportunidad representa un ciclo de intercambios
que ya fue descubierto a partir de ordenes de compra e intercambio.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
from dataclasses import dataclass
from pathlib import Path

# Mantiene las caches de Matplotlib y de fuentes dentro del proyecto. Esto
# evita escrituras en el directorio personal y hace al proyecto autocontenido.
DIRECTORIO_CACHE = Path(__file__).resolve().parent / ".cache"
os.environ.setdefault("MPLCONFIGDIR", str(DIRECTORIO_CACHE / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(DIRECTORIO_CACHE))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


NOMBRES_ESTRATEGIAS = (
    "Estrategia 1: retorno a A",
    "Estrategia 2: primer ciclo",
    "Estrategia 3: mejor ciclo",
)


@dataclass(frozen=True)
class Configuracion:
    simulaciones: int = 1_000_000
    capital_inicial: float = 10_000.0
    fraccion_invertida: float = 1.0
    cantidad_divisas: int = 6
    oportunidades_promedio: float = 8.0
    max_oportunidades: int = 16
    longitud_maxima_ciclo: int = 8
    k: int = 6
    limite_temporal: int = 12
    rendimiento_minimo_intercambio: float = 0.003
    rendimiento_maximo_intercambio: float = 0.012
    comision_intercambio: float = 0.0005
    volatilidad_intercambio: float = 0.004
    tamano_lote: int = 50_000
    tamano_muestra_grafico: int = 100_000
    semilla: int = 2026
    directorio_salida: Path = Path("resultados")

    def validar(self) -> None:
        if self.simulaciones <= 0:
            raise ValueError("La cantidad de simulaciones debe ser positiva.")
        if self.capital_inicial <= 0:
            raise ValueError("El capital inicial debe ser positivo.")
        if not 0 < self.fraccion_invertida <= 1:
            raise ValueError("La fraccion invertida debe pertenecer a (0, 1].")
        if self.cantidad_divisas < 2:
            raise ValueError("Deben existir al menos dos divisas.")
        if self.oportunidades_promedio <= 0 or self.max_oportunidades <= 0:
            raise ValueError("La cantidad de oportunidades debe ser positiva.")
        if self.longitud_maxima_ciclo < 2:
            raise ValueError("La longitud maxima de ciclo debe ser al menos 2.")
        if not 2 <= self.k <= self.longitud_maxima_ciclo:
            raise ValueError("k debe estar entre 2 y la longitud maxima del ciclo.")
        if not 1 <= self.limite_temporal <= self.max_oportunidades:
            raise ValueError(
                "El limite temporal debe estar entre 1 y max_oportunidades."
            )
        if not (
            self.comision_intercambio
            < self.rendimiento_minimo_intercambio
            <= self.rendimiento_maximo_intercambio
        ):
            raise ValueError(
                "Los rendimientos deben ser crecientes y superar la comision."
            )
        if self.volatilidad_intercambio < 0:
            raise ValueError("La volatilidad no puede ser negativa.")
        if self.tamano_lote <= 0 or self.tamano_muestra_grafico <= 0:
            raise ValueError("Los tamanos de lote y muestra deben ser positivos.")


@dataclass
class Acumulador:
    cantidad: int = 0
    suma: float = 0.0
    suma_cuadrados: float = 0.0
    minimo: float = math.inf
    maximo: float = -math.inf
    ganancias: int = 0
    perdidas: int = 0
    operaciones: int = 0

    def agregar(self, capitales: np.ndarray, opero: np.ndarray, inicial: float) -> None:
        self.cantidad += capitales.size
        self.suma += float(np.sum(capitales, dtype=np.float64))
        self.suma_cuadrados += float(
            np.sum(np.square(capitales, dtype=np.float64), dtype=np.float64)
        )
        self.minimo = min(self.minimo, float(np.min(capitales)))
        self.maximo = max(self.maximo, float(np.max(capitales)))
        self.ganancias += int(np.count_nonzero(capitales > inicial))
        self.perdidas += int(np.count_nonzero(capitales < inicial))
        self.operaciones += int(np.count_nonzero(opero))

    def resumen(self, inicial: float) -> dict[str, float]:
        media = self.suma / self.cantidad
        varianza = max(
            0.0, self.suma_cuadrados / self.cantidad - media * media
        )
        desviacion = math.sqrt(varianza)
        error_95 = 1.96 * desviacion / math.sqrt(self.cantidad)
        return {
            "capital_final_promedio": media,
            "ganancia_promedio": media - inicial,
            "desviacion_estandar": desviacion,
            "ic95_inferior_ganancia": media - inicial - error_95,
            "ic95_superior_ganancia": media - inicial + error_95,
            "capital_minimo": self.minimo,
            "capital_maximo": self.maximo,
            "probabilidad_ganancia": self.ganancias / self.cantidad,
            "probabilidad_perdida": self.perdidas / self.cantidad,
            "probabilidad_operar": self.operaciones / self.cantidad,
        }


def _primer_indice(mascara: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Devuelve si existe una oportunidad y su primer indice por escenario."""
    existe = np.any(mascara, axis=1)
    indice = np.argmax(mascara, axis=1)
    return existe, indice


def _capital_segun_seleccion(
    factores_reales: np.ndarray,
    existe: np.ndarray,
    indice: np.ndarray,
    config: Configuracion,
) -> np.ndarray:
    filas = np.arange(factores_reales.shape[0])
    factor = np.where(existe, factores_reales[filas, indice], 1.0)
    return config.capital_inicial * (
        1.0 + config.fraccion_invertida * (factor - 1.0)
    )


def simular_lote(
    cantidad: int, rng: np.random.Generator, config: Configuracion
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Genera escenarios compartidos y aplica las tres estrategias."""
    posiciones = np.arange(config.max_oportunidades)[None, :]
    cantidad_oportunidades = np.minimum(
        rng.poisson(config.oportunidades_promedio, size=cantidad),
        config.max_oportunidades,
    )
    oportunidad_valida = posiciones < cantidad_oportunidades[:, None]

    objetivos = rng.integers(
        0,
        config.cantidad_divisas,
        size=(cantidad, config.max_oportunidades),
        dtype=np.int16,
    )
    longitudes = rng.integers(
        2,
        config.longitud_maxima_ciclo + 1,
        size=(cantidad, config.max_oportunidades),
        dtype=np.int16,
    )

    # Una condicion de mercado compartida por todos los ciclos del escenario.
    # Por construccion, el rendimiento esperado crece estrictamente con la
    # longitud porque el rendimiento por intercambio supera a la comision.
    rendimiento_intercambio = rng.uniform(
        config.rendimiento_minimo_intercambio,
        config.rendimiento_maximo_intercambio,
        size=(cantidad, 1),
    )
    factor_por_intercambio = (1.0 + rendimiento_intercambio) * (
        1.0 - config.comision_intercambio
    )
    factores_esperados = np.power(factor_por_intercambio, longitudes)

    # El impacto de ejecucion puede transformar una oportunidad esperada en
    # ganancia o perdida. La correccion -sigma^2/2 mantiene E[impacto] = 1.
    sigma = config.volatilidad_intercambio * np.sqrt(longitudes)
    impacto = np.exp(
        rng.normal(0.0, 1.0, size=longitudes.shape) * sigma
        - 0.5 * np.square(sigma)
    )
    factores_reales = factores_esperados * impacto
    es_rentable = factores_esperados > 1.0

    # Estrategia 1: solo considera el primer ciclo cuyo objetivo es A (indice 0).
    mascara_1 = oportunidad_valida & es_rentable & (objetivos == 0)
    opera_1, indice_1 = _primer_indice(mascara_1)

    # Estrategia 2: considera todos los targets y cierra el primer ciclo rentable.
    mascara_2 = oportunidad_valida & es_rentable
    opera_2, indice_2 = _primer_indice(mascara_2)

    # Estrategia 3: observa hasta el limite temporal y elige el ciclo esperado
    # mas rentable entre aquellos que no superan k intercambios.
    mascara_3 = (
        oportunidad_valida
        & es_rentable
        & (posiciones < config.limite_temporal)
        & (longitudes <= config.k)
    )
    opera_3 = np.any(mascara_3, axis=1)
    puntuaciones = np.where(mascara_3, factores_esperados, -np.inf)
    indice_3 = np.argmax(puntuaciones, axis=1)

    operaciones = [opera_1, opera_2, opera_3]
    indices = [indice_1, indice_2, indice_3]
    capitales = [
        _capital_segun_seleccion(factores_reales, opera, indice, config)
        for opera, indice in zip(operaciones, indices)
    ]
    return capitales, operaciones


def ejecutar_simulacion(
    config: Configuracion,
) -> tuple[list[dict[str, float]], list[np.ndarray]]:
    config.validar()
    rng = np.random.default_rng(config.semilla)
    acumuladores = [Acumulador() for _ in NOMBRES_ESTRATEGIAS]
    muestras: list[list[np.ndarray]] = [[], [], []]
    faltan_muestras = config.tamano_muestra_grafico

    procesadas = 0
    while procesadas < config.simulaciones:
        cantidad = min(config.tamano_lote, config.simulaciones - procesadas)
        capitales, operaciones = simular_lote(cantidad, rng, config)

        for acumulador, valores, opero in zip(
            acumuladores, capitales, operaciones
        ):
            acumulador.agregar(valores, opero, config.capital_inicial)

        if faltan_muestras > 0:
            tomar = min(faltan_muestras, cantidad)
            for indice, valores in enumerate(capitales):
                muestras[indice].append(valores[:tomar].copy())
            faltan_muestras -= tomar

        procesadas += cantidad

    resumenes = [
        acumulador.resumen(config.capital_inicial)
        for acumulador in acumuladores
    ]
    muestras_unidas = [np.concatenate(partes) for partes in muestras]
    return resumenes, muestras_unidas


def guardar_csv(
    resumenes: list[dict[str, float]], config: Configuracion
) -> Path:
    ruta = config.directorio_salida / "resumen_estrategias.csv"
    campos = ["estrategia", *resumenes[0].keys()]
    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        for nombre, resumen in zip(NOMBRES_ESTRATEGIAS, resumenes):
            escritor.writerow({"estrategia": nombre, **resumen})
    return ruta


def crear_grafico(
    resumenes: list[dict[str, float]],
    muestras: list[np.ndarray],
    config: Configuracion,
) -> Path:
    etiquetas = ["Estrategia 1", "Estrategia 2", "Estrategia 3"]
    colores = ["#4C78A8", "#F58518", "#54A24B"]
    ganancias = np.array([r["ganancia_promedio"] for r in resumenes])
    errores = np.array(
        [
            r["ic95_superior_ganancia"] - r["ganancia_promedio"]
            for r in resumenes
        ]
    )

    figura, ejes = plt.subplots(1, 2, figsize=(14, 6))
    barras = ejes[0].bar(
        etiquetas,
        ganancias,
        yerr=errores,
        capsize=6,
        color=colores,
        edgecolor="black",
        linewidth=0.6,
    )
    ejes[0].axhline(0, color="black", linewidth=0.8)
    ejes[0].set_title("Ganancia promedio e intervalo de confianza del 95 %")
    ejes[0].set_ylabel("Ganancia sobre el capital inicial (USD)")
    ejes[0].grid(axis="y", alpha=0.25)
    ejes[0].bar_label(barras, labels=[f"USD {x:,.2f}" for x in ganancias])

    ganancias_muestra = [valores - config.capital_inicial for valores in muestras]
    caja = ejes[1].boxplot(
        ganancias_muestra,
        tick_labels=etiquetas,
        showfliers=False,
        patch_artist=True,
        widths=0.6,
    )
    for parche, color in zip(caja["boxes"], colores):
        parche.set_facecolor(color)
        parche.set_alpha(0.75)
    ejes[1].axhline(0, color="black", linewidth=0.8)
    ejes[1].set_title(
        f"Distribucion de una muestra de {len(muestras[0]):,} escenarios"
    )
    ejes[1].set_ylabel("Ganancia sobre el capital inicial (USD)")
    ejes[1].grid(axis="y", alpha=0.25)

    figura.suptitle(
        f"Monte Carlo: {config.simulaciones:,} escenarios compartidos\n"
        f"Capital inicial: USD {config.capital_inicial:,.2f}",
        fontsize=14,
    )
    figura.tight_layout()
    ruta = config.directorio_salida / "comparacion_estrategias.png"
    figura.savefig(ruta, dpi=180, bbox_inches="tight")
    plt.close(figura)
    return ruta


def mostrar_resumen(resumenes: list[dict[str, float]], config: Configuracion) -> None:
    print(f"\nResultados de {config.simulaciones:,} simulaciones")
    print(f"Capital inicial: USD {config.capital_inicial:,.2f}\n")
    encabezado = (
        f"{'Estrategia':<34} {'Capital promedio':>18} "
        f"{'Ganancia promedio':>19} {'P(opera)':>10} {'P(gana)':>10}"
    )
    print(encabezado)
    print("-" * len(encabezado))
    for nombre, resultado in zip(NOMBRES_ESTRATEGIAS, resumenes):
        print(
            f"{nombre:<34} "
            f"USD {resultado['capital_final_promedio']:>13,.2f} "
            f"USD {resultado['ganancia_promedio']:>14,.2f} "
            f"{resultado['probabilidad_operar']:>9.2%} "
            f"{resultado['probabilidad_ganancia']:>9.2%}"
        )


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compara tres estrategias de trading mediante Monte Carlo."
    )
    parser.add_argument("--simulaciones", type=int, default=1_000_000)
    parser.add_argument("--capital-inicial", type=float, default=10_000.0)
    parser.add_argument("--fraccion-invertida", type=float, default=1.0)
    parser.add_argument("--divisas", type=int, default=6)
    parser.add_argument("--oportunidades-promedio", type=float, default=8.0)
    parser.add_argument("--max-oportunidades", type=int, default=16)
    parser.add_argument("--longitud-maxima", type=int, default=8)
    parser.add_argument("--k", type=int, default=6)
    parser.add_argument("--limite-temporal", type=int, default=12)
    parser.add_argument("--rendimiento-minimo", type=float, default=0.003)
    parser.add_argument("--rendimiento-maximo", type=float, default=0.012)
    parser.add_argument("--comision", type=float, default=0.0005)
    parser.add_argument("--volatilidad", type=float, default=0.004)
    parser.add_argument("--tamano-lote", type=int, default=50_000)
    parser.add_argument("--muestra-grafico", type=int, default=100_000)
    parser.add_argument("--semilla", type=int, default=2026)
    parser.add_argument("--salida", type=Path, default=Path("resultados"))
    return parser


def main() -> None:
    argumentos = construir_parser().parse_args()
    config = Configuracion(
        simulaciones=argumentos.simulaciones,
        capital_inicial=argumentos.capital_inicial,
        fraccion_invertida=argumentos.fraccion_invertida,
        cantidad_divisas=argumentos.divisas,
        oportunidades_promedio=argumentos.oportunidades_promedio,
        max_oportunidades=argumentos.max_oportunidades,
        longitud_maxima_ciclo=argumentos.longitud_maxima,
        k=argumentos.k,
        limite_temporal=argumentos.limite_temporal,
        rendimiento_minimo_intercambio=argumentos.rendimiento_minimo,
        rendimiento_maximo_intercambio=argumentos.rendimiento_maximo,
        comision_intercambio=argumentos.comision,
        volatilidad_intercambio=argumentos.volatilidad,
        tamano_lote=argumentos.tamano_lote,
        tamano_muestra_grafico=argumentos.muestra_grafico,
        semilla=argumentos.semilla,
        directorio_salida=argumentos.salida,
    )
    config.directorio_salida.mkdir(parents=True, exist_ok=True)
    resumenes, muestras = ejecutar_simulacion(config)
    ruta_csv = guardar_csv(resumenes, config)
    ruta_grafico = crear_grafico(resumenes, muestras, config)
    mostrar_resumen(resumenes, config)
    print(f"\nResumen CSV: {ruta_csv}")
    print(f"Grafico: {ruta_grafico}")


if __name__ == "__main__":
    main()
