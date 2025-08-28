import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
import tensorflow as tf
from tensorflow.keras import layers, models


# Streamlit UI
st.title("Medical Reviews Classification")
st.write("Feedforward Neural Network with 1 Hidden Layer")

uploaded_file = st.file_uploader("Upload_Independent_Medical_Reviews.csv", type=["csv"])

if uploaded_file is not None:
    # 1. Load Dataset
    df = pd.read_csv(uploaded_file)
    print(df.head())
    print(df.tail())
    st.write("### Dataset Preview", df.head())

    # 2. Preprocessing
    if "Reference ID" in df.columns:
        df = df.drop(["Reference ID"], axis=1)
    if "Findings" in df.columns:
        df = df.drop(["Findings"], axis=1)

    df = df.fillna("Unknown")

    print("After-pre-processing", df.head())

    label_encoders = {}
    for col in df.columns:
        if df[col].dtype == 'object':
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col])
            label_encoders[col] = le

    X = df.drop("Determination", axis=1).values
    print("print_X::::", X)
    y = df["Determination"].values
    print("y::::", y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    # 3. Build Neural Network
    model = models.Sequential([
        layers.Input(shape=(X_train.shape[1],)),   # ✅ fix warning: use Input layer
        layers.Dense(32, activation='relu'),
        layers.Dense(1, activation='sigmoid')
    ])

    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

    # 4. Train Model
    epochs = st.slider("Select number of epochs", 5, 20, 10)

    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=epochs,
        batch_size=32,
        verbose=1
    )

    # 5. Plot Accuracy & Loss
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))

    # Accuracy Plot
    ax[0].plot(history.history['accuracy'], label='Train Accuracy')
    ax[0].plot(history.history['val_accuracy'], label='Val Accuracy')
    ax[0].set_title('Model Accuracy')
    ax[0].set_xlabel('Epoch')
    ax[0].set_ylabel('Accuracy')
    ax[0].legend()

    # Loss Plot
    ax[1].plot(history.history['loss'], label='Train Loss')
    ax[1].plot(history.history['val_loss'], label='Val Loss')
    ax[1].set_title('Model Loss')
    ax[1].set_xlabel('Epoch')
    ax[1].set_ylabel('Loss')
    ax[1].legend()

    st.pyplot(fig)

    # 6. Evaluation Metrics
    loss, accuracy = model.evaluate(X_test, y_test, verbose=0)
    st.write(f"### Final Model Accuracy: {accuracy:.4f}")
    st.write(f"### Final Model Loss: {loss:.4f}")

    # 7. Confusion Matrix
    y_pred_prob = model.predict(X_test)
    y_pred = (y_pred_prob > 0.5).astype("int32")   # threshold at 0.5

    cm = confusion_matrix(y_test, y_pred)
    fig_cm, ax_cm = plt.subplots()
    disp = ConfusionMatrixDisplay(confusion_matrix=cm)
    disp.plot(ax=ax_cm, cmap="Blues", values_format="d")
    st.pyplot(fig_cm)

    # 8. Save Model
    if st.button("Save Model"):
        model.save("medical_reviews_model.h5")
        st.success("Model saved as medical_reviews_model.h5")
