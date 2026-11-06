"""Compara modelos de regressão para prever o consumo do laboratório."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error


BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_DADOS = BASE_DIR / "consumo_laboratorio.csv"
PASTA_RESULTADOS = BASE_DIR / "resultados"


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sem-janelas",
        action="store_true",
        help="salva os gráficos sem abrir janelas",
    )
    parser.add_argument("--computadores", type=int, default=30)
    parser.add_argument("--horas-ar", type=float, default=6.0)
    return parser.parse_args()


def executar(args: argparse.Namespace) -> None:
    if args.sem_janelas:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    dados = pd.read_csv(ARQUIVO_DADOS)
    colunas = {"dia", "computadores_ativos", "horas_ar_condicionado", "consumo_kwh"}
    if not colunas.issubset(dados.columns):
        raise ValueError(f"O CSV precisa conter as colunas: {sorted(colunas)}")
    if len(dados) < 60:
        raise ValueError("São necessárias pelo menos 60 observações.")

    treino = dados.iloc[:40].copy()
    validacao = dados.iloc[40:50].copy()
    teste = dados.iloc[50:60].copy()

    modelo_a = LinearRegression().fit(treino[["computadores_ativos"]], treino["consumo_kwh"])
    modelo_b = LinearRegression().fit(
        treino[["computadores_ativos", "horas_ar_condicionado"]],
        treino["consumo_kwh"],
    )

    pred_a = modelo_a.predict(validacao[["computadores_ativos"]])
    pred_b = modelo_b.predict(validacao[["computadores_ativos", "horas_ar_condicionado"]])
    erro_a = abs(validacao["consumo_kwh"].to_numpy() - pred_a)
    erro_b = abs(validacao["consumo_kwh"].to_numpy() - pred_b)
    mae_a = mean_absolute_error(validacao["consumo_kwh"], pred_a)
    mae_b = mean_absolute_error(validacao["consumo_kwh"], pred_b)

    comparacao = pd.DataFrame(
        {
            "dia": validacao["dia"].to_numpy(),
            "consumo_real_kwh": validacao["consumo_kwh"].to_numpy(),
            "previsao_modelo_a": pred_a,
            "erro_modelo_a": erro_a,
            "previsao_modelo_b": pred_b,
            "erro_modelo_b": erro_b,
            "menor_erro": ["A" if a < b else "B" if b < a else "Empate" for a, b in zip(erro_a, erro_b)],
        }
    )

    modelos = {"A": modelo_a, "B": modelo_b}
    escolhido = "A" if mae_a < mae_b else "B"
    modelo_final = modelos[escolhido]
    entradas_teste = (
        teste[["computadores_ativos"]]
        if escolhido == "A"
        else teste[["computadores_ativos", "horas_ar_condicionado"]]
    )
    pred_teste = modelo_final.predict(entradas_teste)
    erro_teste = abs(teste["consumo_kwh"].to_numpy() - pred_teste)
    mae_teste = mean_absolute_error(teste["consumo_kwh"], pred_teste)
    resultado_teste = pd.DataFrame(
        {
            "dia": teste["dia"].to_numpy(),
            "consumo_real_kwh": teste["consumo_kwh"].to_numpy(),
            f"previsao_modelo_{escolhido.lower()}": pred_teste,
            "erro_absoluto": erro_teste,
        }
    )

    PASTA_RESULTADOS.mkdir(exist_ok=True)
    comparacao.to_csv(PASTA_RESULTADOS / "comparacao_validacao.csv", index=False, float_format="%.4f")
    resultado_teste.to_csv(PASTA_RESULTADOS / "resultado_teste.csv", index=False, float_format="%.4f")

    fig, eixos = plt.subplots(1, 2, figsize=(12, 4.5))
    eixos[0].scatter(treino["computadores_ativos"], treino["consumo_kwh"], color="#277da1")
    eixos[0].set(xlabel="Computadores ativos", ylabel="Consumo (kWh)", title="Consumo × computadores")
    eixos[1].scatter(treino["horas_ar_condicionado"], treino["consumo_kwh"], color="#f8961e")
    eixos[1].set(xlabel="Horas de ar-condicionado", ylabel="Consumo (kWh)", title="Consumo × ar-condicionado")
    fig.suptitle("Dados de treinamento — dias 1 a 40")
    fig.tight_layout()
    fig.savefig(PASTA_RESULTADOS / "01_dados_treino.png", dpi=150)

    fig, eixo = plt.subplots(figsize=(10, 5))
    eixo.plot(validacao["dia"], validacao["consumo_kwh"], "o-", label="Consumo real", linewidth=2)
    eixo.plot(validacao["dia"], pred_a, "s--", label=f"Modelo A (MAE {mae_a:.2f})")
    eixo.plot(validacao["dia"], pred_b, "^--", label=f"Modelo B (MAE {mae_b:.2f})")
    eixo.set(xlabel="Dia", ylabel="Consumo (kWh)", title="Comparação dos modelos na validação")
    eixo.set_xticks(validacao["dia"])
    eixo.grid(alpha=0.25)
    eixo.legend()
    fig.tight_layout()
    fig.savefig(PASTA_RESULTADOS / "02_comparacao_validacao.png", dpi=150)

    entradas_novas = (
        pd.DataFrame({"computadores_ativos": [args.computadores]})
        if escolhido == "A"
        else pd.DataFrame(
            {"computadores_ativos": [args.computadores], "horas_ar_condicionado": [args.horas_ar]}
        )
    )
    nova_previsao = modelo_final.predict(entradas_novas)[0]

    print(f"MAE na validação — modelo A: {mae_a:.2f} kWh")
    print(f"MAE na validação — modelo B: {mae_b:.2f} kWh")
    print(f"Modelo escolhido: {escolhido}")
    print(f"MAE no teste: {mae_teste:.2f} kWh")
    print(
        f"Previsão para {args.computadores} computadores e {args.horas_ar:g} h de ar-condicionado: "
        f"{nova_previsao:.2f} kWh"
    )
    print(f"Resultados salvos em: {PASTA_RESULTADOS}")

    if not args.sem_janelas:
        plt.show()
    plt.close("all")


if __name__ == "__main__":
    executar(argumentos())
