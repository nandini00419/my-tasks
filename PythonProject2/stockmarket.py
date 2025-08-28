import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense

st.title("📈 Stock Price Prediction App")

# Upload CSV
uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.write(df.head())

    df.columns = [c.strip().lower() for c in df.columns]

    # Feature Engineering
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    df['vwap'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
    df['sma_14'] = df['close'].rolling(14).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    df['turnover'] = df['close'] * df['volume']

    def compute_rsi(data, window=14):
        delta = data.diff()
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        avg_gain = pd.Series(gain).rolling(window=window).mean()
        avg_loss = pd.Series(loss).rolling(window=window).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    df['rsi_14'] = compute_rsi(df['close'])

    # Drop NaNs and prepare features
    features = ['open', 'high', 'low', 'volume', 'vwap', 'sma_14', 'sma_50', 'rsi_14', 'turnover']
    df_ml = df.dropna(subset=features + ['close'])
    X = df_ml[features]
    y = df_ml['close']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, shuffle=False)

    # Random Forest Regressor
    rf_model = RandomForestRegressor(n_estimators=100, max_depth=None, random_state=42)
    rf_model.fit(X_train, y_train)
    st.write("RF Train R²:", r2_score(y_train, rf_model.predict(X_train)))
    st.write("RF Test R²:", r2_score(y_test, rf_model.predict(X_test)))

    # Neural Network
    scaler = MinMaxScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    nn_model = Sequential([
        Dense(128, activation='relu', input_shape=(X_train_scaled.shape[1],)),
        Dense(128, activation='relu'),
        Dense(128, activation='relu'),
        Dense(128, activation='relu'),
        Dense(1)
    ])
    nn_model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    history = nn_model.fit(X_train_scaled, y_train,
                           validation_data=(X_test_scaled, y_test),
                           epochs=100, batch_size=64, verbose=1)

    # Training Curves
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    ax[0].plot(history.history['loss'], label='train_loss')
    ax[0].plot(history.history['val_loss'], label='val_loss')
    ax[0].set_title('Loss Curve')
    ax[0].legend()

    ax[1].plot(history.history['mae'], label='train_mae')
    ax[1].plot(history.history['val_mae'], label='val_mae')
    ax[1].set_title('MAE Curve')
    ax[1].legend()
    st.pyplot(fig)

    # Neural Network Predictions
    nn_pred_train = nn_model.predict(X_train_scaled)
    nn_pred_test = nn_model.predict(X_test_scaled)

    # Metrics: MSE and MAE
    train_mse = mean_squared_error(y_train, nn_pred_train)
    train_mae = mean_absolute_error(y_train, nn_pred_train)
    test_mse = mean_squared_error(y_test, nn_pred_test)
    test_mae = mean_absolute_error(y_test, nn_pred_test)

    st.write(f"Neural Network Train MSE: {train_mse:.2f}")
    st.write(f"Neural Network Train MAE: {train_mae:.2f}")
    st.write(f"Neural Network Test MSE: {test_mse:.2f}")
    st.write(f"Neural Network Test MAE: {test_mae:.2f}")

    # Show first 10 predictions vs actual
    nn_comparison = pd.DataFrame({
        "Actual": y_test[:10].values,
        "Predicted": nn_pred_test[:10].flatten()
    })
    st.write(nn_comparison)

    # Recommendation based on latest prediction
    latest_actual_price = y_test.values[-1]
    latest_predicted_price = nn_pred_test[-1][0]

    if latest_predicted_price > latest_actual_price:
        recommendation = "📈 Recommendation: BUY this stock"
    else:
        recommendation = "📉 Recommendation: NOT BUY / HOLD this stock"

    st.markdown(f"### {recommendation}")
