# Bibliotecas
from shiny.express import ui, render, input
from shiny.ui import page_navbar
from shinyswatch import theme
import pandas as pd
import plotnine as p9
import mizani as mi
from functools import partial
from faicons import icon_svg

# Funções
def preparar_dados(parquet, y):
    df_tmp = pd.read_parquet(parquet).reset_index(names = "data")
    ult = df_tmp.query("Tipo == @y").query("data == data.max()")
    df_tmp = pd.concat([
        df_tmp, 
        pd.DataFrame(
            {
                "data": ult.data.repeat(2), 
                "Valor": ult.Valor.repeat(2), 
                "Tipo": df_tmp.query("Tipo not in [@y, 'IA']").Tipo.unique().tolist(), 
                "Intervalo Inferior": ult.Valor.repeat(2), 
                "Intervalo Superior": ult.Valor.repeat(2)
            }
        )
        ])
    return df_tmp

def gerar_grafico(df, y, n, unidade, linha_zero = True):
    dt = input.periodo()
    mod = list(input.modelo())
    mod.insert(0, y)
    df_tmp = df.assign(
        Tipo = lambda x: pd.Categorical(x.Tipo, mod)
        ).query("data >= @dt and Tipo in @mod")

    def plotar_zero():
        if linha_zero:
            return p9.geom_hline(yintercept = 0, linetype = "dashed")
        else:
            return None

    def plotar_ic():
        if input.ic():
            return  p9.geom_ribbon(
                data = df_tmp,
                mapping = p9.aes(
                    ymin = "Intervalo Inferior",
                    ymax = "Intervalo Superior",
                    fill = "Tipo"
                    ),
                alpha = 0.25,
                color = "none",
                show_legend = False
            ) 
        else:
            return None

    plt = (
        p9.ggplot(df_tmp) +
        p9.aes(x = "data", y = "Valor", color = "Tipo") +
        plotar_zero() +
        plotar_ic() +
        p9.geom_line() +
        p9.scale_x_date(date_breaks = "1 year", date_labels = "%Y") +
        p9.scale_y_continuous(breaks = mi.breaks.breaks_extended(6)) +
        p9.scale_color_manual(
            values = {
                y: "black", 
                "IA": "green",
                "Ridge": "blue",
                "Bayesian Ridge": "orange",
                "Huber": "red",
                "Ensemble": "brown"
                },
            drop = True,
            breaks = df_tmp.Tipo.unique().tolist()
            ) +
        p9.scale_fill_manual(
            values = {
                "IA": "green",
                "Ridge": "blue",
                "Bayesian Ridge": "orange",
                "Huber": "red",
                "Ensemble": "brown"
                },
            drop = True
            ) +
        p9.labs(color = "", x = "", y = unidade) +
        p9.theme(
            panel_grid_minor = p9.element_blank(),
            legend_position = "bottom"
            )
    )
    return plt

# Dados
df_ipca = preparar_dados("previsao/ipca.parquet", "IPCA")
df_cambio = preparar_dados("previsao/cambio.parquet", "Câmbio")
df_pib = preparar_dados("previsao/pib.parquet", "PIB")
df_selic = preparar_dados("previsao/selic.parquet", "Selic")

lista_modelos = list(set(
    df_ipca.query("Tipo != 'IPCA'").Tipo.unique().tolist() +
    df_cambio.query("Tipo != 'Câmbio'").Tipo.unique().tolist() +
    df_pib.query("Tipo != 'PIB'").Tipo.unique().tolist() +
    df_selic.query("Tipo != 'Selic'").Tipo.unique().tolist()
))


# Layout
ui.page_opts(
    title = ui.span(
        ui.img(
            src = "https://aluno.analisemacro.com.br/download/59787/?tmstv=1712933415",
            height = 30,
            style = "padding-right:10px;"
            )
    ),
    window_title = "Painel de Previsões",
    page_fn = partial(page_navbar, fillable = True),
    theme = theme.minty
)

with ui.nav_panel("Painel de Previsões"):  
    with ui.layout_sidebar():

        # Inputs
        with ui.sidebar(width = 225):

            # Informação
            ui.markdown(
                (
                    "Acompanhe as previsões automatizadas dos principais " +
                    "indicadores macroeconômicos do Brasil e simule cenários" +
                    " alternativos em um mesmo dashboard."
                )
            )

            ui.input_selectize(
                id = "modelo",
                label = ui.strong("Selecionar modelos:"),
                choices = lista_modelos,
                selected = lista_modelos,
                multiple = True,
                width = "100%",
                options = {"plugins": ["clear_button"]}
                )
            ui.input_date(
                id = "periodo",
                label = ui.strong("Início do gráfico:"),
                value = pd.to_datetime("today") - pd.offsets.YearBegin(7),
                min = "2004-01-01",
                max = df_selic.data.max(),
                language = "pt-BR",
                width = "100%",
                format = "mm/yyyy",
                startview = "year"
                )
            ui.input_checkbox(
                id = "ic",
                label = ui.strong("Intervalo de confiança"),
                value = True
            )

            # Informação
            ui.markdown(
                "Elaboração: Fernando da Silva/Análise Macro"
            )

        # Outputs
        with ui.layout_column_wrap():

            with ui.navset_card_underline(title = ui.strong("Inflação (IPCA)")):
                with ui.nav_panel("", icon = icon_svg("chart-line")):
                    @render.plot
                    def ipca1():
                        plt = gerar_grafico(df_ipca, "IPCA", input.modelo(), "Var. %")
                        return plt

                with ui.nav_panel(" ", icon = icon_svg("table")):
                    @render.data_frame
                    def ipca2():
                        df_tmp = (
                            df_ipca
                            .query("Tipo != 'IPCA'")
                            .rename(
                                columns = {
                                    "Valor": "Previsão", 
                                    "Tipo": "Modelo", 
                                    "data": "Data"}
                                )
                            .assign(Data = lambda x: x.Data.dt.strftime("%m/%Y"))
                            .round(2)
                            .head(-2)
                        )
                        return render.DataGrid(df_tmp, summary = False)

            with ui.navset_card_underline(title = ui.strong("Taxa de Câmbio (BRL/USD)")):
                with ui.nav_panel("", icon = icon_svg("chart-line")):
                    @render.plot
                    def cambio1():
                        plt = gerar_grafico(df_cambio, "Câmbio", input.modelo(), "R\$/US\$", False)
                        return plt

                with ui.nav_panel(" ", icon = icon_svg("table")):
                    @render.data_frame
                    def cambio2():
                        df_tmp = (
                            df_cambio
                            .query("Tipo != 'Câmbio'")
                            .rename(
                                columns = {
                                    "Valor": "Previsão", 
                                    "Tipo": "Modelo", 
                                    "data": "Data"}
                                )
                            .assign(Data = lambda x: x.Data.dt.strftime("%m/%Y"))
                            .round(2)
                            .head(-2)
                        )
                        return render.DataGrid(df_tmp, summary = False)

        with ui.layout_column_wrap():

            with ui.navset_card_underline(title = ui.strong("Atividade Econômica (PIB)")):
                with ui.nav_panel("", icon = icon_svg("chart-line")):
                    @render.plot
                    def pib1():
                        plt = gerar_grafico(df_pib, "PIB", input.modelo(), "Var. % anual")
                        return plt

                with ui.nav_panel(" ", icon = icon_svg("table")):
                    @render.data_frame
                    def pib2():
                        df_tmp = (
                            df_pib
                            .query("Tipo != 'PIB'")
                            .rename(
                                columns = {
                                    "Valor": "Previsão", 
                                    "Tipo": "Modelo", 
                                    "data": "Data"}
                                )
                            .assign(Data = lambda x: x.Data.dt.to_period(freq = "Q").dt.strftime("T%q/%Y"))
                            .round(2)
                            .head(-2)
                        )
                        return render.DataGrid(df_tmp, summary = False)

            with ui.navset_card_underline(title = ui.strong("Taxa de Juros (SELIC)")):
                with ui.nav_panel("", icon = icon_svg("chart-line")):
                    @render.plot
                    def selic1():
                        plt = gerar_grafico(df_selic, "Selic", input.modelo, "% a.a.", False)
                        return plt

                with ui.nav_panel(" ", icon = icon_svg("table")):
                    @render.data_frame
                    def selic2():
                        df_tmp = (
                            df_selic
                            .query("Tipo != 'Selic'")
                            .rename(
                                columns = {
                                    "Valor": "Previsão", 
                                    "Tipo": "Modelo", 
                                    "data": "Data"}
                                )
                            .assign(Data = lambda x: x.Data.dt.strftime("%m/%Y"))
                            .round(2)
                            .head(-2)
                        )
                        return render.DataGrid(df_tmp, summary = False)