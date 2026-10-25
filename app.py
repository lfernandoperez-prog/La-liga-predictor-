import math
from io import BytesIO
import pandas as pd
import streamlit as st

st.set_page_config(page_title="LaLiga Predictor", page_icon="⚽", layout="wide")

st.title("⚽ LaLiga Predictor")
st.caption("Prototipo personal de análisis estadístico · No garantiza resultados ni beneficios")

st.info(
    "Carga un CSV histórico que tengas derecho a utilizar. El modelo solo usa partidos anteriores "
    "al encuentro seleccionado; las probabilidades son estimaciones experimentales, no consejos de apuesta."
)

with st.expander("Cómo conseguir datos gratuitos"):
    st.markdown(
        """
        1. Abre [Football-Data.co.uk — España](https://www.football-data.co.uk/spainm.php).
        2. Descarga manualmente el CSV de LaLiga de una temporada (código `SP1`).
        3. Sube el archivo aquí. Para una evaluación más sólida, combina temporadas históricas en un CSV.

        Football-Data indica que sus datos gratuitos son para uso personal/académico y que las descargas
        deben ser manuales o ligeras. Respeta sus condiciones: [política de uso](https://www.football-data.co.uk/contact.php).

        También puedes consultar [datos históricos de LaLiga en DataHub](https://datahub.io/football/spanish-la-liga).
        """
    )

uploaded = st.file_uploader("Sube un CSV de resultados históricos de LaLiga", type=["csv"])

def read_csv(file):
    # Football-Data files commonly use Windows-1252 and comma separators.
    raw = file.getvalue()
    for enc in ("utf-8-sig", "cp1252", "latin1"):
        try:
            return pd.read_csv(BytesIO(raw), encoding=enc)
        except Exception:
            pass
    raise ValueError("No se pudo leer el CSV.")

def poisson_pmf(k, lam):
    if lam < 0:
        return 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def poisson_cdf(k, lam):
    if k < 0:
        return 0.0
    return sum(poisson_pmf(i, lam) for i in range(k + 1))

def normalize_data(df):
    df = df.copy()
    # tolerate whitespace / common alternate column names
    df.columns = [str(c).strip() for c in df.columns]
    aliases = {
        "HomeTeam": ["HomeTeam", "Home Team", "home_team"],
        "AwayTeam": ["AwayTeam", "Away Team", "away_team"],
        "FTHG": ["FTHG", "HG", "HomeGoals", "home_goals"],
        "FTAG": ["FTAG", "AG", "AwayGoals", "away_goals"],
        "Date": ["Date", "date", "MatchDate"],
        "HC": ["HC", "HomeCorners", "home_corners"],
        "AC": ["AC", "AwayCorners", "away_corners"],
        "HY": ["HY", "HomeYellowCards", "home_yellow_cards"],
        "AY": ["AY", "AwayYellowCards", "away_yellow_cards"],
        "HR": ["HR", "HomeRedCards", "home_red_cards"],
        "AR": ["AR", "AwayRedCards", "away_red_cards"],
    }
    rename = {}
    for target, candidates in aliases.items():
        for candidate in candidates:
            if candidate in df.columns:
                rename[candidate] = target
                break
    df = df.rename(columns=rename)
    required = ["HomeTeam", "AwayTeam", "FTHG", "FTAG"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Faltan columnas necesarias: " + ", ".join(missing) +
                         ". Se necesitan HomeTeam, AwayTeam, FTHG y FTAG.")
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
        df = df.sort_values("Date")
    for c in ["FTHG", "FTAG", "HC", "AC", "HY", "AY", "HR", "AR"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG"])
    df = df[(df["FTHG"] >= 0) & (df["FTAG"] >= 0)]
    return df.reset_index(drop=True)

def weighted_mean(series, decay=0.92):
    vals = pd.to_numeric(series, errors="coerce").dropna().tolist()
    if not vals:
        return None
    vals = vals[-10:]
    weights = [decay ** (len(vals) - 1 - i) for i in range(len(vals))]
    return sum(v*w for v, w in zip(vals, weights)) / sum(weights)

def team_rates(history, team, home=True):
    if home:
        played = history[history["HomeTeam"] == team]
        scored_col, conceded_col = "FTHG", "FTAG"
    else:
        played = history[history["AwayTeam"] == team]
        scored_col, conceded_col = "FTAG", "FTHG"
    return weighted_mean(played[scored_col]), weighted_mean(played[conceded_col]), len(played)

def estimate_rates(history, home_team, away_team):
    # Blend team home/away scoring and conceding rates with league-wide means.
    lg_home = max(history["FTHG"].mean(), 0.05)
    lg_away = max(history["FTAG"].mean(), 0.05)
    hs, hc, hn = team_rates(history, home_team, True)
    as_, ac, an = team_rates(history, away_team, False)
    # Fallback to overall league rates when a team has insufficient matching venue history.
    hs = hs if hs is not None else lg_home
    hc = hc if hc is not None else lg_away
    as_ = as_ if as_ is not None else lg_away
    ac = ac if ac is not None else lg_home
    # Blend venue-specific team rates with league means to reduce small-sample extremes.
    home_attack = (hs * min(hn, 8) + lg_home * 4) / (min(hn, 8) + 4)
    away_defence = (ac * min(an, 8) + lg_home * 4) / (min(an, 8) + 4)
    away_attack = (as_ * min(an, 8) + lg_away * 4) / (min(an, 8) + 4)
    home_defence = (hc * min(hn, 8) + lg_away * 4) / (min(hn, 8) + 4)
    lam_home = max(0.05, home_attack * away_defence / lg_home)
    lam_away = max(0.05, away_attack * home_defence / lg_away)
    return min(lam_home, 4.5), min(lam_away, 4.5), (hn, an)

def build_score_matrix(lh, la, max_goals=10):
    home = [poisson_pmf(i, lh) for i in range(max_goals + 1)]
    away = [poisson_pmf(i, la) for i in range(max_goals + 1)]
    return [[home[i] * away[j] for j in range(max_goals + 1)] for i in range(max_goals + 1)]

if not uploaded:
    st.markdown("### Vista previa")
    st.write("Cuando cargues los datos, aquí aparecerán las probabilidades 1X2, goles, ambos marcan y estadísticas adicionales disponibles.")
    st.stop()

try:
    raw_df = read_csv(uploaded)
    df = normalize_data(raw_df)
except Exception as e:
    st.error(f"No pude procesar el archivo: {e}")
    st.stop()

st.success(f"Archivo leído: {len(df)} partidos válidos · {df['HomeTeam'].nunique()} equipos")
st.caption("Las columnas disponibles dependen de la temporada. Córners y tarjetas solo se calculan si el CSV contiene esos campos.")

teams = sorted(set(df["HomeTeam"].dropna().astype(str)) | set(df["AwayTeam"].dropna().astype(str)))
if len(teams) < 2:
    st.error("El archivo no contiene suficientes equipos.")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    home_team = st.selectbox("Equipo local", teams, index=teams.index("Barcelona") if "Barcelona" in teams else 0)
with col2:
    away_default = 1 if len(teams) > 1 else 0
    away_team = st.selectbox("Equipo visitante", teams, index=teams.index("Real Madrid") if "Real Madrid" in teams and teams.index("Real Madrid") != teams.index(home_team) else away_default)

if home_team == away_team:
    st.warning("Selecciona dos equipos diferentes.")
    st.stop()

# Optional date cutoff to ensure only prior matches are used.
if "Date" in df.columns and df["Date"].notna().any():
    dates = sorted(df["Date"].dropna().dt.date.unique())
    st.caption("Para evitar filtraciones de información, selecciona una fecha de análisis y solo se utilizarán partidos anteriores.")
    cutoff = st.date_input("Fecha del partido que quieres analizar", value=max(dates) + pd.Timedelta(days=1), min_value=min(dates), max_value=max(dates) + pd.Timedelta(days=365))
    history = df[df["Date"].dt.date < cutoff].copy()
else:
    st.warning("No se detectó una columna de fecha fiable. El modelo usará todo el archivo histórico; no uses esta opción para validar temporadas pasadas.")
    history = df.copy()

if len(history) < 20:
    st.warning("Hay pocos partidos en el histórico. Las estimaciones pueden ser muy inestables; carga más temporadas si puedes.")

if len(history) == 0:
    st.error("No hay partidos anteriores a la fecha seleccionada.")
    st.stop()

lh, la, sample_n = estimate_rates(history, home_team, away_team)
matrix = build_score_matrix(lh, la)
p_home = sum(matrix[i][j] for i in range(11) for j in range(11) if i > j)
p_draw = sum(matrix[i][j] for i in range(11) for j in range(11) if i == j)
p_away = sum(matrix[i][j] for i in range(11) for j in range(11) if i < j)
p_over15 = 1 - sum(matrix[i][j] for i in range(11) for j in range(11) if i + j <= 1)
p_over25 = 1 - sum(matrix[i][j] for i in range(11) for j in range(11) if i + j <= 2)
p_over35 = 1 - sum(matrix[i][j] for i in range(11) for j in range(11) if i + j <= 3)
p_btts = 1 - math.exp(-lh) - math.exp(-la) + math.exp(-(lh + la))
top_scores = sorted([(matrix[i][j], i, j) for i in range(8) for j in range(8)], reverse=True)[:5]

st.divider()
st.subheader(f"{home_team} vs {away_team}")
m1, m2 = st.columns(2)
m1.metric("Goles esperados · local", f"{lh:.2f}")
m2.metric("Goles esperados · visitante", f"{la:.2f}")

st.markdown("### Resultado final (1X2)")
a, b, c = st.columns(3)
a.metric("Victoria local", f"{p_home:.1%}")
b.metric("Empate", f"{p_draw:.1%}")
c.metric("Victoria visitante", f"{p_away:.1%}")

st.markdown("### Mercados de goles")
g1, g2, g3, g4 = st.columns(4)
g1.metric("Más de 1,5", f"{p_over15:.1%}")
g2.metric("Más de 2,5", f"{p_over25:.1%}")
g3.metric("Más de 3,5", f"{p_over35:.1%}")
g4.metric("Ambos marcan: Sí", f"{p_btts:.1%}")

st.markdown("### Marcadores exactos más probables")
scores_df = pd.DataFrame([
    {"Marcador": f"{i}-{j}", "Probabilidad estimada": f"{p:.1%}"}
    for p, i, j in top_scores
])
st.dataframe(scores_df, hide_index=True, use_container_width=True)

# Additional markets only when the dataset includes those fields.
st.markdown("### Estadísticas adicionales")
extra = []
for label, home_col, away_col in [
    ("Córners", "HC", "AC"),
    ("Tarjetas amarillas", "HY", "AY"),
    ("Tarjetas rojas", "HR", "AR"),
]:
    if home_col in history.columns and away_col in history.columns:
        hval = weighted_mean(history.loc[history["HomeTeam"] == home_team, home_col])
        aval = weighted_mean(history.loc[history["AwayTeam"] == away_team, away_col])
        if hval is not None and aval is not None:
            extra.append({"Mercado": label, f"{home_team} (media local)": round(hval, 2),
                          f"{away_team} (media visitante)": round(aval, 2),
                          "Media combinada estimada": round(hval + aval, 2)})
if extra:
    st.dataframe(pd.DataFrame(extra), hide_index=True, use_container_width=True)
else:
    st.caption("Este archivo no contiene suficientes datos de córners/tarjetas para mostrarlos.")

st.markdown("### Datos utilizados")
st.write(f"Partidos históricos anteriores a la fecha elegida: **{len(history)}**.")
st.write(f"Partidos de local disponibles para {home_team}: **{sample_n[0]}** · partidos de visitante disponibles para {away_team}: **{sample_n[1]}**.")
st.caption(
    "Metodología inicial: medias ponderadas de los últimos 10 partidos por condición local/visitante, "
    "ajustadas hacia promedios de liga y distribuciones de Poisson independientes. No incorpora alineaciones, "
    "lesiones ni xG. No es un modelo validado ni una recomendación de apuesta."
)

st.download_button(
    "Descargar resumen de esta predicción",
    data=pd.DataFrame([{
        "Local": home_team, "Visitante": away_team, "Goles esperados local": lh,
        "Goles esperados visitante": la, "P_local": p_home, "P_empate": p_draw,
        "P_visitante": p_away, "P_over_2_5": p_over25, "P_ambos_marcan": p_btts,
        "Partidos_historicos": len(history)
    }]).to_csv(index=False).encode("utf-8"),
    file_name="prediccion_laliga.csv",
    mime="text/csv"
)
