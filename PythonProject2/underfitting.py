# Complete Streamlit App for Medical Reviews Classification with Visualizations
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.utils import class_weight
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve
import joblib
import tensorflow as tf
from tensorflow.keras import layers, models, callbacks

st.title("Medical Reviews Classification (Improved with Visualization)")

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
if uploaded_file is None:
    st.info("Upload a CSV to continue")
else:
    print("Reading uploaded CSV file...")
    df = pd.read_csv(uploaded_file)
    print("Initial data shape:", df.shape)

    # 1) Drop identifier and free-text columns
    for c in ["Reference ID", "Findings"]:
        if c in df.columns:
            df = df.drop(columns=[c])
            print(f"Dropped column: {c}")

    df = df.fillna("Unknown")
    print("After filling missing values:\n", df.head())

    # 2) Encode target column
    print("Encoding target column if needed...")
    if df['Determination'].dtype == 'object':
        le_target = LabelEncoder()
        df['Determination'] = le_target.fit_transform(df['Determination'])
        print("Target classes mapping:", dict(enumerate(le_target.classes_)))
    else:
        le_target = None
        print("Target column already numeric:\n", df['Determination'].value_counts())

    if le_target:
        st.write("Target classes:", dict(enumerate(le_target.classes_)))

    # 3) Prepare features and target
    y = df['Determination'].values
    X = df.drop(columns=['Determination'])
    print("Feature columns before encoding:", X.columns.tolist())

    cat_cols = X.select_dtypes(include=['object']).columns.tolist()
    print("Categorical columns to encode:", cat_cols)

    # One-hot encoding
    X = pd.get_dummies(X, columns=cat_cols, drop_first=True)
    print("After one-hot encoding, X shape:", X.shape)

    # 4) Train/Validation/Test Split
    print("Splitting data into train, validation, and test sets...")
    X_train_full, X_test, y_train_full, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_full, y_train_full, test_size=0.25, random_state=42, stratify=y_train_full
    )
    print(f"Shapes -> Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")

    # 5) Feature scaling
    print("Applying StandardScaler...")
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)
    X_test = scaler.transform(X_test)
    print("Sample scaled X_train row:", X_train[0][:10])

    # 6) Class weights for imbalance
    print("Computing class weights...")
    classes = np.unique(y_train)
    if len(classes) == 2:
        cw = class_weight.compute_class_weight("balanced", classes=classes, y=y_train)
        class_weight_dict = dict(zip(classes, cw))
        print("Class weights:", class_weight_dict)
    else:
        class_weight_dict = None
        print("Multi-class detected or no imbalance adjustment needed.")

    # 7) Build the model
    print("Building neural network model...")
    model = models.Sequential([
        layers.Input(shape=(X_train.shape[1],)),
        layers.Dense(64, activation='relu'),
        layers.Dropout(0.3),
        layers.Dense(32, activation='relu'),
        layers.Dense(1, activation='sigmoid'),
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

    # 8) Evaluate model
    print("Evaluating model on test data...")
    y_pred_prob = model.predict(X_test).ravel()
    y_pred = (y_pred_prob > 0.5).astype(int)

    print("\nClassification Report:\n", classification_report(y_test, y_pred, digits=4))
    print("\nROC AUC:", float(roc_auc_score(y_test, y_pred_prob)))

    st.subheader("Classification Report")
    st.text(classification_report(y_test, y_pred, digits=4))

    st.subheader("ROC AUC")
    st.write("ROC AUC (probabilities):", float(roc_auc_score(y_test, y_pred_prob)))

    # Confusion Matrix with Heatmap
    print("Plotting Confusion Matrix...")
    cm = confusion_matrix(y_test, y_pred)
    fig1, ax1 = plt.subplots()
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax1)
    ax1.set_title("Confusion Matrix")
    ax1.set_xlabel("Predicted")
    ax1.set_ylabel("Actual")
    st.pyplot(fig1)

    # ROC Curve
    print("Plotting ROC Curve...")
    fpr, tpr, _ = roc_curve(y_test, y_pred_prob)
    fig2, ax2 = plt.subplots()
    ax2.plot(fpr, tpr, label=f"ROC Curve (AUC = {roc_auc_score(y_test, y_pred_prob):.2f})")
    ax2.plot([0, 1], [0, 1], 'k--')
    ax2.set_xlabel("False Positive Rate")
    ax2.set_ylabel("True Positive Rate")
    ax2.set_title("ROC Curve")
    ax2.legend()
    st.pyplot(fig2)

    # Training vs Validation Loss & Accuracy
    print("Plotting Training vs Validation Loss and Accuracy...")
    fig3, (ax3, ax4) = plt.subplots(1, 2, figsize=(12, 5))

    ax3.plot(history.history['loss'], label='Train Loss')
    ax3.plot(history.history['val_loss'], label='Val Loss')
    ax3.set_title('Loss Over Epochs')
    ax3.set_xlabel('Epochs')
    ax3.set_ylabel('Loss')
    ax3.legend()

    ax4.plot(history.history['accuracy'], label='Train Accuracy')
    ax4.plot(history.history['val_accuracy'], label='Val Accuracy')
    ax4.set_title('Accuracy Over Epochs')
    ax4.set_xlabel('Epochs')
    ax4.set_ylabel('Accuracy')
    ax4.legend()

    st.pyplot(fig3)

    # 9) Save preprocessing objects
    print("Saving model and preprocessing objects...")
    joblib.dump(scaler, "scaler.joblib")
    if le_target:
        joblib.dump(le_target, "label_encoder_target.joblib")

    st.success("Training complete. Model and preprocessing objects saved successfully!")
    print("All steps completed successfully.")
