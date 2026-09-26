import streamlit as st
import pandas as pd
import numpy as np
import joblib
import plotly.express as px
import os

st.set_page_config(
    page_title="Intrushield | Security Console",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>

.main {
    background-color: #0e1117;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

.hero {
    padding: 2rem 2.2rem;
    border-radius: 18px;
    background: linear-gradient(135deg, #111827, #172033);
    border: 1px solid #263247;
    margin-bottom: 1.5rem;
}

.hero-title {
    font-size: 2.7rem;
    font-weight: 750;
    margin-bottom: 0.4rem;
}

.hero-subtitle {
    color: #a9b4c7;
    font-size: 1.05rem;
}

.badge {
    display: inline-block;
    padding: 0.35rem 0.8rem;
    border-radius: 999px;
    background: #123c2c;
    color: #43e69b;
    font-size: 0.82rem;
    font-weight: 600;
    margin-bottom: 1rem;
}

.section-title {
    font-size: 1.45rem;
    font-weight: 700;
    margin-top: 1.5rem;
    margin-bottom: 1rem;
}

.kpi-card {
    padding: 1.2rem;
    border-radius: 14px;
    background: #151b26;
    border: 1px solid #273143;
}

.kpi-label {
    color: #9aa6b8;
    font-size: 0.85rem;
}

.kpi-value {
    font-size: 1.8rem;
    font-weight: 700;
    margin-top: 0.3rem;
}

.info-card {
    padding: 1rem 1.2rem;
    border-radius: 12px;
    background: #121824;
    border: 1px solid #273143;
}

.footer {
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid #293241;
    color: #778196;
    text-align: center;
    font-size: 0.8rem;
}

</style>
""", unsafe_allow_html=True)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_DIR = os.path.join(BASE_DIR, "models")

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "xgboost_attack_model_13class_balanced.joblib"
)

FEATURE_PATH = os.path.join(
    MODEL_DIR,
    "xgboost_attack_model_13class_features.joblib"
)

MAPPING_PATH = os.path.join(
    MODEL_DIR,
    "xgboost_attack_model_13class_mapping.joblib"
)

@st.cache_resource
def load_artifacts():
    model = joblib.load(MODEL_PATH)
    features = joblib.load(FEATURE_PATH)
    mapping = joblib.load(MAPPING_PATH)

    return model, features, mapping


try:
    model, feature_columns, label_mapping = load_artifacts()
    model_loaded = True

except Exception as e:
    model_loaded = False
    model = None
    feature_columns = None
    label_mapping = None
    load_error = str(e)


def get_label(prediction):

    if isinstance(label_mapping, dict):

        if prediction in label_mapping:
            return label_mapping[prediction]

        if str(prediction) in label_mapping:
            return label_mapping[str(prediction)]

        for key, value in label_mapping.items():

            if value == prediction:
                return key

    return str(prediction)


def make_predictions(data):

    X = data[feature_columns]

    predictions = model.predict(X)

    if hasattr(model, "predict_proba"):

        probabilities = model.predict_proba(X)
        confidence = probabilities.max(axis=1)

    else:

        confidence = np.ones(len(predictions))

    labels = [get_label(pred) for pred in predictions]

    result = data.copy()

    result["Prediction"] = predictions
    result["Traffic Category"] = labels
    result["Confidence"] = confidence

    return result


with st.sidebar:

    st.markdown("## 🛡️ Intrushield")
    st.caption("Network Intrusion Detection System")

    st.divider()

    st.markdown("### Model")

    st.write("**Algorithm:** XGBoost")
    st.write("**Classes:** 13")
    st.write("**Features:** 77")
    st.write("**Training:** Balanced dataset")

    st.divider()

    st.markdown("### Supported Classes")

    if isinstance(label_mapping, dict):

        labels = []

        for key, value in label_mapping.items():

            if isinstance(key, (int, np.integer)):
                labels.append(str(value))
            else:
                labels.append(str(key))

        for label in sorted(set(labels))[:13]:
            st.caption(f"• {label}")

    st.divider()

    st.caption("Intrushield • Final Balanced 13-Class XGBoost Model")


st.markdown("""
<div class="hero">

<div class="badge">● MODEL ONLINE</div>

<div class="hero-title">
🛡️ Intrushield
</div>

<div class="hero-subtitle">
Security console for multi-class network traffic classification
using a trained 13-class XGBoost intrusion detection model.
</div>

</div>
""", unsafe_allow_html=True)


if model_loaded:

    st.success(
        "Model loaded successfully — Intrushield 13-class XGBoost intrusion detection system is ready."
    )

else:

    st.error("Unable to load the machine learning model.")
    st.code(load_error)
    st.stop()


st.markdown(
    '<div class="section-title">Model Overview</div>',
    unsafe_allow_html=True
)

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.markdown("""
    <div class="kpi-card">
    <div class="kpi-label">Algorithm</div>
    <div class="kpi-value">XGBoost</div>
    </div>
    """, unsafe_allow_html=True)

with c2:

    st.markdown("""
    <div class="kpi-card">
    <div class="kpi-label">Input Features</div>
    <div class="kpi-value">77</div>
    </div>
    """, unsafe_allow_html=True)

with c3:

    st.markdown("""
    <div class="kpi-card">
    <div class="kpi-label">Traffic Classes</div>
    <div class="kpi-value">13</div>
    </div>
    """, unsafe_allow_html=True)

with c4:

    st.markdown("""
    <div class="kpi-card">
    <div class="kpi-label">Prediction Type</div>
    <div class="kpi-value">Multi-Class</div>
    </div>
    """, unsafe_allow_html=True)


st.markdown(
    '<div class="section-title">Supported Traffic Classes</div>',
    unsafe_allow_html=True
)

if isinstance(label_mapping, dict):

    class_rows = []

    for key, value in label_mapping.items():

        if isinstance(key, (int, np.integer)):

            class_id = key
            category = value

        else:

            class_id = value
            category = key

        class_rows.append({
            "Class ID": class_id,
            "Traffic Category": category
        })

    class_df = pd.DataFrame(class_rows)

    if not class_df.empty:

        class_df = class_df.sort_values("Class ID")

        st.dataframe(
            class_df,
            use_container_width=True,
            hide_index=True
        )


st.markdown(
    '<div class="section-title">Upload Network Traffic</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="info-card">'
    'Upload a CSV containing the 77 model input features. '
    'The uploaded data should follow the preprocessing format used during model training.'
    '</div>',
    unsafe_allow_html=True
)

uploaded_file = st.file_uploader(
    "Choose a CSV file",
    type=["csv"],
    help="Maximum file size: 500 MB"
)


if uploaded_file is not None:

    if uploaded_file.size > 500 * 1024 * 1024:

        st.error("File exceeds the 500 MB upload limit.")
        st.stop()

    try:

        data = pd.read_csv(uploaded_file)

    except Exception as e:

        st.error(f"Unable to read CSV file: {e}")
        st.stop()

    st.success(
        f"File uploaded successfully — {len(data):,} traffic flows detected."
    )


    st.markdown(
        '<div class="section-title">Dataset Overview</div>',
        unsafe_allow_html=True
    )

    a, b, c = st.columns(3)

    with a:
        st.metric("Rows", f"{len(data):,}")

    with b:
        st.metric("Columns", len(data.columns))

    with c:

        missing = int(data.isna().sum().sum())

        st.metric(
            "Missing Values",
            f"{missing:,}"
        )


    st.markdown(
        '<div class="section-title">Feature Compatibility</div>',
        unsafe_allow_html=True
    )

    missing_features = [
        col for col in feature_columns
        if col not in data.columns
    ]

    extra_features = [
        col for col in data.columns
        if col not in feature_columns
    ]

    if missing_features:

        st.error(
            f"Dataset is missing {len(missing_features)} required features."
        )

        with st.expander("View missing features"):
            st.write(missing_features)

        st.stop()

    if extra_features:

        st.warning(
            f"{len(extra_features)} additional columns detected. "
            "They will be ignored during prediction."
        )

    else:

        st.success(
            f"All {len(feature_columns)} required model features are available."
        )


    with st.expander("Preview uploaded data"):

        st.dataframe(
            data.head(10),
            use_container_width=True
        )


    st.markdown(
        '<div class="section-title">Traffic Analysis</div>',
        unsafe_allow_html=True
    )

    if st.button(
        "🔎 Analyse Network Traffic",
        use_container_width=True,
        type="primary"
    ):

        with st.spinner("Running XGBoost intrusion detection..."):

            try:

                results = make_predictions(data)

                st.session_state["results"] = results

            except Exception as e:

                st.error(
                    "Prediction failed. Please verify that the uploaded "
                    "dataset uses the expected 77-feature format."
                )

                st.exception(e)
                st.stop()


if "results" in st.session_state:

    results = st.session_state["results"]

    st.success(
        "Intrushield network traffic analysis completed successfully."
    )


    st.markdown(
        '<div class="section-title">Traffic Analysis Summary</div>',
        unsafe_allow_html=True
    )

    total = len(results)

    benign = (
        results["Traffic Category"]
        .astype(str)
        .str.upper()
        .eq("BENIGN")
        .sum()
    )

    attacks = total - benign

    avg_confidence = results["Confidence"].mean()


    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.metric(
            "Total Traffic Flows",
            f"{total:,}"
        )

    with c2:

        st.metric(
            "Benign Traffic",
            f"{benign:,}"
        )

    with c3:

        st.metric(
            "Detected Attacks",
            f"{attacks:,}"
        )

    with c4:

        st.metric(
            "Average Confidence",
            f"{avg_confidence:.4f}"
        )


    st.markdown(
        '<div class="section-title">Prediction Results</div>',
        unsafe_allow_html=True
    )

    st.dataframe(
        results.head(100),
        use_container_width=True,
        height=420
    )


    st.markdown(
        '<div class="section-title">Traffic Intelligence</div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)


    with col1:

        traffic_counts = pd.DataFrame({
            "Traffic Type": ["Benign", "Attack"],
            "Count": [benign, attacks]
        })

        fig = px.bar(
            traffic_counts,
            x="Traffic Type",
            y="Count",
            title="Network Traffic Classification",
            text="Count"
        )

        fig.update_layout(
            template="plotly_dark",
            height=420,
            margin=dict(
                l=20,
                r=20,
                t=60,
                b=20
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


    with col2:

        attack_results = results[
            results["Traffic Category"]
            .astype(str)
            .str.upper() != "BENIGN"
        ]

        if not attack_results.empty:

            category_counts = (
                attack_results["Traffic Category"]
                .value_counts()
                .reset_index()
            )

            category_counts.columns = [
                "Attack Category",
                "Count"
            ]

            fig = px.bar(
                category_counts,
                x="Attack Category",
                y="Count",
                title="Detected Attack Categories",
                text="Count"
            )

            fig.update_layout(
                template="plotly_dark",
                height=420,
                margin=dict(
                    l=20,
                    r=20,
                    t=60,
                    b=20
                )
            )

            fig.update_xaxes(
                tickangle=-35
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:

            st.info("No attack traffic detected.")


    st.markdown(
        '<div class="section-title">Model Confidence</div>',
        unsafe_allow_html=True
    )

    confidence_df = pd.DataFrame({
        "Flow": np.arange(1, len(results) + 1),
        "Confidence": results["Confidence"]
    })

    fig = px.line(
        confidence_df,
        x="Flow",
        y="Confidence",
        title="Prediction Confidence by Traffic Flow"
    )

    fig.update_layout(
        template="plotly_dark",
        height=400,
        yaxis=dict(
            range=[0, 1.05]
        ),
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


    st.markdown(
        '<div class="section-title">Confidence Distribution</div>',
        unsafe_allow_html=True
    )

    fig = px.histogram(
        results,
        x="Confidence",
        nbins=20,
        title="Distribution of Model Confidence"
    )

    fig.update_layout(
        template="plotly_dark",
        height=350,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


    st.markdown(
        '<div class="section-title">Export Results</div>',
        unsafe_allow_html=True
    )

    csv_data = results.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="⬇️ Download Prediction Results",
        data=csv_data,
        file_name="intrushield_prediction_results.csv",
        mime="text/csv",
        use_container_width=True
    )


st.markdown("""
<div class="footer">
Intrushield<br>
Final Balanced 13-Class XGBoost Model
</div>
""", unsafe_allow_html=True)