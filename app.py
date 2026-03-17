import streamlit as st
import pandas as pd

st.title("Automatizador de Bases - Call Center")

INICIALES_ASESOR = {
    "comfandi93": "JSA",
    "comfandi94": "DC"
}

st.write("Sube la base de Aigree y una o varias bases de teléfonos.")

archivo_aigree = st.file_uploader("Subir base Aigree", type=["csv","xlsx"])

estados_seleccionados = []

# --------------------------------
# DETECTAR ESTADOS + CONTADOR
# --------------------------------

if archivo_aigree:

    if archivo_aigree.name.endswith(".csv"):
        df_preview = pd.read_csv(archivo_aigree, sep=";", encoding="latin1")
    else:
        df_preview = pd.read_excel(archivo_aigree)

    df_preview.columns = df_preview.columns.str.strip()

    df_preview = df_preview.rename(columns={
        "NÃºmero IdentificaciÃ³n": "CEDULA"
    })

    df_preview["Estado Deudor"] = (
        df_preview["Estado Deudor"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # eliminar duplicados
    df_preview = df_preview.drop_duplicates(subset=["CEDULA"])

    # CONTADOR DE ESTADOS
    conteo_estados = df_preview["Estado Deudor"].value_counts().sort_values(ascending=False)

    st.subheader("Cantidad de registros por estado")

    st.dataframe(conteo_estados)

    estados_disponibles = conteo_estados.index.tolist()

    st.subheader("Seleccionar estados a traer")

    estados_seleccionados = st.multiselect(
        "Estados disponibles",
        estados_disponibles,
        default=["SIN GESTION"] if "SIN GESTION" in estados_disponibles else None
    )

# --------------------------------
# BASES DE TELEFONO
# --------------------------------

archivos_tel = st.file_uploader(
    "Subir bases de teléfonos",
    type=["csv","xlsx"],
    accept_multiple_files=True
)

horas_bases = {}
estado_bases = {}
plantilla_bases = {}

# -------------------------
# CONFIGURACION POR BASE
# -------------------------

if archivos_tel:

    st.subheader("Configuración por base")

    for archivo in archivos_tel:

        st.markdown(f"### {archivo.name}")

        col1, col2 = st.columns(2)

        with col1:
            horas_bases[archivo.name] = st.time_input(
                "Hora de envío",
                key=f"hora_{archivo.name}"
            )

        with col2:
            estado_bases[archivo.name] = st.selectbox(
                "Estado cliente",
                ["WHATSAP","EMAIL","MENSAJE DE TEXTO"],
                key=f"estado_{archivo.name}"
            )

        plantilla_bases[archivo.name] = st.text_area(
            "Mensaje plantilla para esta base",
            key=f"mensaje_{archivo.name}"
        )

# -------------------------
# PROCESAMIENTO
# -------------------------

if archivo_aigree and archivos_tel and estados_seleccionados:

    if st.button("Procesar bases"):

        archivo_aigree.seek(0)

        if archivo_aigree.name.endswith(".csv"):
            df = pd.read_csv(archivo_aigree, sep=";", encoding="latin1")
        else:
            df = pd.read_excel(archivo_aigree)

        df.columns = df.columns.str.strip()

        df["Estado Deudor"] = df["Estado Deudor"].astype(str).str.strip().str.upper()

        df_filtrado = df[df["Estado Deudor"].isin(estados_seleccionados)]

        df_filtrado = df_filtrado.drop_duplicates(subset=["NÃºmero IdentificaciÃ³n"])

        df_filtrado = df_filtrado.rename(columns={
            "NÃºmero IdentificaciÃ³n":"CEDULA"
        })

        lista_bases = []

        for archivo in archivos_tel:

            if archivo.name.endswith(".csv"):
                df_tel = pd.read_csv(archivo)
            else:
                df_tel = pd.read_excel(archivo)

            df_tel.columns = df_tel.columns.str.strip()

            df_tel = df_tel.rename(columns={
                "cedula":"CEDULA",
                "telefono":"NUMERO TELEFONO",
                "fecha_envio":"FECHA GESTION",
                "campana":"CAMPANA"
            })

            df_tel["NUMERO TELEFONO"] = (
                df_tel["NUMERO TELEFONO"]
                .astype(str)
                .str.replace("^57","",regex=True)
            )

            df_tel["FECHA GESTION"] = df_tel["FECHA GESTION"].astype(str)

            df_tel["CAMPANA"] = (
                df_tel["CAMPANA"]
                .astype(str)
                .str.lower()
                .str.replace("-","",regex=False)
                .str.replace(" ","",regex=False)
            )

            hora = horas_bases[archivo.name]
            df_tel["HORA_ENVIO"] = str(hora)

            estado_cliente = estado_bases[archivo.name]
            df_tel["ESTADO CLIENTE"] = estado_cliente

            plantilla = plantilla_bases[archivo.name]
            df_tel["PLANTILLA"] = plantilla

            lista_bases.append(
                df_tel[[
                    "CEDULA",
                    "NUMERO TELEFONO",
                    "FECHA GESTION",
                    "CAMPANA",
                    "HORA_ENVIO",
                    "ESTADO CLIENTE",
                    "PLANTILLA"
                ]]
            )

        df_tel_total = pd.concat(lista_bases, ignore_index=True)

        df_tel_total = df_tel_total.sort_values("FECHA GESTION", ascending=False)

        df_tel_total = df_tel_total.drop_duplicates(subset=["CEDULA"])

        df_final = df_filtrado.merge(
            df_tel_total,
            on="CEDULA",
            how="left"
        )

        # LIMPIEZA
        df_final = df_final.dropna(subset=["NUMERO TELEFONO"])
        df_final = df_final[df_final["NUMERO TELEFONO"] != ""]

        df_final["FECHA GESTION"] = df_final["FECHA GESTION"].astype(str).str.strip()

        df_final = df_final[
            (df_final["FECHA GESTION"] != "") &
            (df_final["FECHA GESTION"].str.lower() != "nan")
        ]

        # INICIALES
        df_final["INICIALES"] = df_final["CAMPANA"].map(INICIALES_ASESOR)

        # MENSAJE
        df_final["MENSAJE"] = (
        df_final["INICIALES"].fillna("").astype(str) + " " +
        df_final["FECHA GESTION"].astype(str) + " " +
        df_final["HORA_ENVIO"].astype(str) + " " +
        df_final["NUMERO TELEFONO"].astype(str) + " " +
        df_final["PLANTILLA"].fillna("").astype(str)
        )

        # BASE FINAL
        nueva_base = pd.DataFrame()

        nueva_base["CEDULA"] = df_final["CEDULA"]
        nueva_base["NUMERO TELEFONO"] = df_final["NUMERO TELEFONO"]
        nueva_base["MENSAJE"] = df_final["MENSAJE"]
        nueva_base["ASESOR"] = df_final["CAMPANA"]
        nueva_base["FECHA GESTION"] = df_final["FECHA GESTION"]
        nueva_base["CANAL"] = "SMS"
        nueva_base["ESTADO CLIENTE"] = df_final["ESTADO CLIENTE"]
        nueva_base["ESTADO CONTACTO"] = "NO CONTACTO"

        st.success("Bases procesadas correctamente")

        st.write("Registros base original:", len(df_filtrado))
        st.write("Registros finales:", len(nueva_base))

        st.dataframe(nueva_base.head())

        archivo_salida = "base_final.xlsx"

        nueva_base.to_excel(archivo_salida,index=False)

        with open(archivo_salida,"rb") as f:

            st.download_button(
                "Descargar base final",
                f,
                file_name="base_final.xlsx"
            )