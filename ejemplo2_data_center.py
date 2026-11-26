"""Ejemplo 2 - Montecarlo: cache OCA (Antel, Pando) vs transito internacional.
Compara intervalos de actualizacion de la cache T (dias) por costo diario para el ISP."""
import numpy as np
import matplotlib.pyplot as plt

rng = np.random.default_rng(42)
N, ALPHA = 7000, 0.8            # titulos del catalogo, exponente Zipf (Breslau et al., 1999)
CAP_TB = 120                    # capacidad del OCA en TB (Netflix, s. f.)
LAM, PICO = 200_000, 1.3        # reproducciones/dia (Poisson) y factor de fin de semana
CHURN = 0.02                    # fraccion de titulos cuya popularidad cambia por dia
C_MISS, C_FILL = 0.010, 0.002   # USD/GB transito en hora pico vs. relleno en hora valle
DIAS, RUNS, Ts = 28, 500, [1, 2, 3, 7, 14]

p0 = 1 / np.arange(1, N + 1) ** ALPHA
p0 /= p0.sum()

def top_cache(p, size):
    """Titulos mas populares que entran en la capacidad (knapsack greedy por popularidad)."""
    orden = np.argsort(-p)
    cabe = np.cumsum(size[orden]) <= CAP_TB * 1000
    return orden[cabe]

def simular(T):
    costo, hits = np.empty(RUNS), np.empty(RUNS)
    for r in range(RUNS):
        size = rng.uniform(5, 60, N)                     # GB por titulo, todas sus codificaciones (continua)
        p = p0.copy(); cache = top_cache(p, size)
        c = h = tot = 0.0
        for d in range(DIAS):
            if d and d % T == 0:                         # dia de relleno
                nueva = top_cache(p, size)
                c += size[np.setdiff1d(nueva, cache)].sum() * C_FILL
                cache = nueva
            lam = LAM * (PICO if d % 7 >= 5 else 1)
            reqs = rng.poisson(lam * p)                  # pedidos por titulo (discreta)
            en_cache = np.zeros(N, bool); en_cache[cache] = True
            c += (reqs * size)[~en_cache].sum() * C_MISS
            h += reqs[en_cache].sum(); tot += reqs.sum()
            k = int(CHURN * N); i, j = rng.choice(N, k), rng.choice(N, k)
            p[i], p[j] = p[j], p[i]                      # deriva de popularidad
        costo[r], hits[r] = c / DIAS, h / tot
    return costo, hits

res = {T: simular(T) for T in Ts}
for T, (c, h) in res.items():
    print(f"T={T:2d} dias | costo diario medio {c.mean():8.0f} USD (p5 {np.percentile(c,5):.0f}, "
          f"p95 {np.percentile(c,95):.0f}) | hit ratio {h.mean():.3f}")

fig, ax = plt.subplots(1, 2, figsize=(11, 4))
ax[0].bar([str(T) for T in Ts], [res[T][0].mean() for T in Ts],
          yerr=[res[T][0].std() for T in Ts], capsize=4, color="#4C72B0")
ax[0].set(xlabel="Intervalo de actualizacion T (dias)", ylabel="Costo diario medio (USD)",
          title="Costo esperado para el ISP segun T")
for T, col in zip([1, 7, 14], ["#4C72B0", "#DD8452", "#55A868"]):
    ax[1].hist(res[T][0], bins=40, alpha=.6, label=f"T = {T}", color=col)
ax[1].set(xlabel="Costo diario (USD)", ylabel="Frecuencia", title=f"Distribucion del costo ({RUNS} corridas)")
ax[1].legend(); plt.tight_layout(); plt.savefig("ejemplo2_resultados.png", dpi=150)
