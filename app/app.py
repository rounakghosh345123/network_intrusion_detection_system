"""
Network Intrusion Detection System

This Streamlit application loads the trained XGBoost intrusion detection
model, target label encoder, and feature configuration generated during
the machine learning pipeline.

Users can upload network traffic data in CSV format, run the trained
model on the traffic flows, view predicted traffic categories and model
confidence, analyse benign versus attack traffic, and download the
prediction results.
"""

import os
import joblib
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Network Intrusion Detection System",
    page_icon="🛡️",
    layout="wide"
)


# Project paths

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

MODEL_DIR = os.path.join(
    BASE_DIR,
    "models"
)


# Final model files

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
def load_model_files():

    model = joblib.load(MODEL_PATH)

    feature_columns = joblib.load(
        FEATURE_PATH
    )

    class_mapping = joblib.load(
        MAPPING_PATH
    )

    return (
        model,
        feature_columns,
        class_mapping
    )


# Load model files

try:

    (
        model,
        feature_columns,
        class_mapping
    ) = load_model_files()

    model_loaded = True

except Exception as error:

    model_loaded = False

    load_error = str(error)


# Convert mapping to labels

def get_class_name(
    class_id,
    mapping
):

    if isinstance(mapping, dict):

        return mapping.get(
            int(class_id),
            str(class_id)
        )

    if isinstance(mapping, list):

        return mapping[
            int(class_id)
        ]

    return str(class_id)


# Application header

st.title(
    "🛡️ Network Intrusion Detection System"
)

st.write(
    "Upload network traffic data and analyse it using "
    "the trained 13-class XGBoost intrusion detection model."
)

st.divider()


# Model status

if model_loaded:

    st.success(
        "Final 13-Class Machine Learning Model Loaded Successfully!"
    )

else:

    st.error(
        "Unable to load the machine learning model."
    )

    st.code(
        load_error
    )

    st.stop()


# Model information

st.subheader(
    "Model Information"
)

col1, col2, col3 = st.columns(3)


with col1:

    st.metric(
        "Model",
        "XGBoost"
    )


with col2:

    st.metric(
        "Input Features",
        len(feature_columns)
    )


with col3:

    st.metric(
        "Traffic Classes",
        len(model.classes_)
    )


st.divider()


# Supported classes

st.subheader(
    "Supported Traffic Classes"
)

supported_classes = pd.DataFrame(
    {
        "Class ID": model.classes_,
        "Traffic Category": [
            get_class_name(
                class_id,
                class_mapping
            )
            for class_id
            in model.classes_
        ]
    }
)

st.dataframe(
    supported_classes,
    use_container_width=True,
    hide_index=True
)


st.divider()


# File upload

st.subheader(
    "Upload Network Traffic Data"
)

uploaded_file = st.file_uploader(
    "Upload a CSV file containing network traffic data",
    type=["csv"]
)


if uploaded_file is not None:

    try:

        traffic_data = pd.read_csv(
            uploaded_file
        )


        st.success(
            f"File uploaded successfully! "
            f"{len(traffic_data)} traffic flows detected."
        )


        st.subheader(
            "Uploaded Data Preview"
        )

        st.dataframe(
            traffic_data.head(20),
            use_container_width=True
        )


        # Remove non-feature columns

        columns_to_remove = [

            "Label",

            "Traffic_Status",

            "Predicted_Label",

            "Actual_Label",

            "Confidence",

            "Prediction_Correct",

            "Timestamp",

            "Flow_Number"

        ]


        input_data = traffic_data.drop(
            columns=[
                column
                for column
                in columns_to_remove
                if column
                in traffic_data.columns
            ],
            errors="ignore"
        )


        # Check required features

        missing_features = [

            feature

            for feature
            in feature_columns

            if feature
            not in input_data.columns

        ]


        if missing_features:

            st.error(
                "Feature compatibility failed. "
                "The uploaded dataset does not contain "
                "all 77 features required by the model."
            )

            st.write(
                f"Missing features: "
                f"{len(missing_features)}"
            )

            with st.expander(
                "View Missing Features"
            ):

                st.write(
                    missing_features
                )


            st.info(
                "The model can only analyse datasets "
                "containing the same 77-feature schema "
                "used during training."
            )

            st.stop()


        # Arrange features correctly

        input_data = input_data[
            feature_columns
        ]


        # Clean invalid values

        input_data = input_data.replace(
            [
                float("inf"),
                float("-inf")
            ],
            0
        )

        input_data = input_data.fillna(
            0
        )


        st.success(
            "Feature compatibility verified. "
            "All required 77 features are available."
        )


        # Prediction section

        st.subheader(
            "Traffic Analysis"
        )


        if st.button(
            "🔍 Analyse Network Traffic",
            use_container_width=True
        ):


            with st.spinner(
                "Analysing network traffic..."
            ):


                predicted_values = (
                    model.predict(
                        input_data
                    )
                )


                predicted_probabilities = (
                    model.predict_proba(
                        input_data
                    )
                )


                confidence_scores = (
                    predicted_probabilities.max(
                        axis=1
                    )
                )


                predicted_labels = [

                    get_class_name(
                        prediction,
                        class_mapping
                    )

                    for prediction
                    in predicted_values

                ]


            # Create results

            results = traffic_data.copy()


            results[
                "Predicted_Label"
            ] = predicted_labels


            results[
                "Confidence"
            ] = confidence_scores


            results[
                "Traffic_Status"
            ] = results[
                "Predicted_Label"
            ].apply(

                lambda value:

                "Benign"

                if value == "BENIGN"

                else "Attack"

            )


            # Summary statistics

            total_flows = len(
                results
            )


            benign_count = (
                results[
                    "Traffic_Status"
                ]
                .value_counts()
                .get(
                    "Benign",
                    0
                )
            )


            attack_count = (
                results[
                    "Traffic_Status"
                ]
                .value_counts()
                .get(
                    "Attack",
                    0
                )
            )


            average_confidence = (
                results[
                    "Confidence"
                ].mean()
            )


            st.success(
                "Network traffic analysis "
                "completed successfully!"
            )


            # Summary metrics

            st.subheader(
                "Traffic Analysis Summary"
            )


            (
                metric1,
                metric2,
                metric3,
                metric4
            ) = st.columns(4)


            with metric1:

                st.metric(
                    "Total Traffic Flows",
                    total_flows
                )


            with metric2:

                st.metric(
                    "Benign Traffic",
                    benign_count
                )


            with metric3:

                st.metric(
                    "Detected Attacks",
                    attack_count
                )


            with metric4:

                st.metric(
                    "Average Confidence",
                    f"{average_confidence:.4f}"
                )


            st.divider()


            # Prediction results

            st.subheader(
                "Prediction Results"
            )


            st.dataframe(
                results.head(100),
                use_container_width=True
            )


            st.divider()


            # Traffic distribution

            st.subheader(
                "Network Traffic Classification"
            )


            traffic_counts = (
                results[
                    "Traffic_Status"
                ]
                .value_counts()
            )


            st.bar_chart(
                traffic_counts
            )


            # Attack categories

            attack_results = results[

                results[
                    "Traffic_Status"
                ] == "Attack"

            ]


            if len(
                attack_results
            ) > 0:


                st.subheader(
                    "Detected Attack Categories"
                )


                attack_distribution = (

                    attack_results[
                        "Predicted_Label"
                    ]
                    .value_counts()

                )


                st.bar_chart(
                    attack_distribution
                )


            else:


                st.info(
                    "No attack traffic was detected "
                    "in the uploaded dataset."
                )


            # Confidence chart

            st.subheader(
                "Model Prediction Confidence"
            )


            confidence_data = results[

                [
                    "Confidence"
                ]

            ]


            st.line_chart(
                confidence_data
            )


            st.divider()


            # Download results

            st.subheader(
                "Download Analysis Results"
            )


            csv_data = results.to_csv(
                index=False
            ).encode(
                "utf-8"
            )


            st.download_button(
                label=(
                    "⬇️ Download Prediction Results"
                ),
                data=csv_data,
                file_name=(
                    "network_intrusion_predictions.csv"
                ),
                mime="text/csv",
                use_container_width=True
            )


    except Exception as error:


        st.error(
            "An error occurred while processing "
            "the uploaded file."
        )


        st.code(
            str(error)
        )


else:


    st.info(
        "Upload a network traffic CSV file "
        "to begin intrusion detection analysis."
    )


st.divider()


st.caption(
    "Network Intrusion Detection System | "
    "Final Balanced 13-Class XGBoost Model"
)