# Improved snippet (Streamlit-friendly, drop into your app)
import pandas as pd
import numpy as np
import streamlit as st
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.utils import class_weight
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib
import tensorflow as tf
from tensorflow.keras import layers, models, callbacks

st.title("Medical Reviews Classification (Improved)")

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
if uploaded_file is None:
    st.info("Upload a CSV to continue")
else:
    df = pd.read_csv(uploaded_file)

    # 1) Drop identifier and long free-text columns for now
    for c in ["Reference ID", "Findings"]:
        if c in df.columns:
            df = df.drop(columns=[c])

    df = df.fillna("Unknown")
    print("After-pre-processing", df.head())

    # 2) Target encoding (encode only target with LabelEncoder)
    if df['Determination'].dtype == 'object':
        le_target = LabelEncoder()
        df['Determination'] = le_target.fit_transform(df['Determination'])
        print("Target classes mapping:", dict(enumerate(le_target.classes_)))
    else:
        le_target = None # if already 0/1
        print("After target encoding:\n", df['Determination'].value_counts())

    # Save target mapping for later
    if le_target:
        st.write("Target classes:", dict(enumerate(le_target.classes_)))

    # 3) Categorical encoding for features using get_dummies (one-hot)
    y = df['Determination'].values
    X = df.drop(columns=['Determination'])
    print("Feature columns before encoding:", X.columns.tolist())
    cat_cols = X.select_dtypes(include=['object']).columns.tolist()
    print("Categorical columns:", cat_cols)



    # One-hot encode categorical columns (drop_first to reduce collinearity)
    X = pd.get_dummies(X, columns=cat_cols, drop_first=True)
    print("After one-hot encoding, X shape:", X.shape)
    print("Columns after encoding:", X.columns.tolist()[:10], "...")

    # 4) Train/val/test split
    X_train_full, X_test, y_train_full, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_full, y_train_full, test_size=0.25, random_state=42, stratify=y_train_full
    )
    print(f"Shapes -> Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")

    # 5) Scale numeric features (scale all columns after get_dummies)
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)
    X_test = scaler.transform(X_test)
    print("After scaling, sample X_train row:", X_train[0][:10])

    # 6) Handle class imbalance (optional)
    classes = np.unique(y_train)
    if len(classes) == 2:
        cw = class_weight.compute_class_weight("balanced", classes=classes, y=y_train)
        class_weight_dict = dict(zip(classes, cw))
    else:
        class_weight_dict = None
        print("Class weights:", class_weight_dict)

    # 7) Build a larger model (more capacity)
    model = models.Sequential([
        layers.Input(shape=(X_train.shape[1],)),
        layers.Dense(128, activation='relu'),
        layers.Dropout(0.3),
        layers.Dense(64, activation='relu'),
        layers.Dropout(0.3),
        layers.Dense(32, activation='relu'),
        layers.Dense(16, activation='relu'),
        layers.Dense(5, activation='sigmoid'),
    ])
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
                  loss='binary_crossentropy',
                  metrics=['accuracy'])
    print("Model summary:")
    model.summary()

    # Callbacks
    es = callbacks.EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
    mc = callbacks.ModelCheckpoint("best_medical_model.h5", save_best_only=True, monitor='val_loss')

    epochs = st.slider("Epochs", 5, 100, 30)
    print("Starting training for", epochs, "epochs...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=64,
        class_weight=class_weight_dict,
        callbacks=[es, mc],
        verbose=1
    )

    # 8) Evaluate
    print("Evaluating model...")
    y_pred_prob = model.predict(X_test).ravel()
    y_pred = (y_pred_prob > 0.5).astype(int)
    print("\nClassification Report:\n", classification_report(y_test, y_pred, digits=4))
    print("\nROC AUC:", float(roc_auc_score(y_test, y_pred_prob)))

    st.write("Classification report:")
    st.text(classification_report(y_test, y_pred, digits=4))

    st.write("ROC AUC (probabilities):", float(roc_auc_score(y_test, y_pred_prob)))

    cm = confusion_matrix(y_test, y_pred)
    print("\nConfusion Matrix:\n", cm)
    st.write("Confusion matrix:\n", cm)

    # 9) Save preprocessing objects
    joblib.dump(scaler, "scaler.joblib")
    if le_target:
        joblib.dump(le_target, "label_encoder_target.joblib")

    st.success("Training complete. Model saved as best_medical_model.h5 and scaler/label encoder saved.")
    print("Preprocessing objects and model saved successfully.")


