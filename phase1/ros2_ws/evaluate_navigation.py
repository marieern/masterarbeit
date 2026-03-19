import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def load_and_trim_data(filepath):
    """
    Lädt die CSV-Datei und schneidet die Ruhephasen am Anfang und Ende ab.
    Passt sich automatisch an 'Timestamp' oder 'Timestamp_s' an.
    """
    df = pd.read_csv(filepath)
    
    # === NEU: Automatische Erkennung der Zeit-Spalte ===
    time_col = 'Timestamp_s' if 'Timestamp_s' in df.columns else 'Timestamp'
    
    # Finde den tatsächlichen Start (sobald die Distanz > 0 ist)
    start_idx = df[df['Distanz_m'] > 0].index.min()
    if pd.isna(start_idx): 
        start_idx = 0
        
    # Finde das tatsächliche Ende (sobald die maximale Distanz erreicht wurde)
    max_dist = df['Distanz_m'].max()
    end_idx = df[df['Distanz_m'] >= max_dist].index.min()
    if pd.isna(end_idx): 
        end_idx = len(df) - 1
        
    # Daten zuschneiden
    df_trimmed = df.loc[start_idx:end_idx].copy()
    
    # 1. Zeitliche Normalisierung: Timestamp beginnt bei 0
    df_trimmed['Timestamp_Norm_s'] = df_trimmed[time_col] - df_trimmed[time_col].iloc[0]
    
    # 2. Distanz Normalisierung: Distanz beginnt bei 0
    df_trimmed['Distanz_Norm_m'] = df_trimmed['Distanz_m'] - df_trimmed['Distanz_m'].iloc[0]
    
    return df_trimmed

def normalize_columns_min_max(df, columns):
    """
    Normalisiert die angegebenen Spalten auf einen Bereich von [0, 1].
    """
    df_norm = df.copy()
    for col in columns:
        min_val = df_norm[col].min()
        max_val = df_norm[col].max()
        if max_val - min_val != 0:
            df_norm[f'{col}_Scaled'] = (df_norm[col] - min_val) / (max_val - min_val)
        else:
            df_norm[f'{col}_Scaled'] = 0.0
    return df_norm

def calculate_kpis(df):
    """
    Berechnet die wichtigsten wissenschaftlichen Metriken für dein Ergebnis-Kapitel.
    """
    duration = df['Timestamp_Norm_s'].iloc[-1]
    total_dist = df['Distanz_Norm_m'].iloc[-1]
    
    # Effizienz-Metriken
    avg_speed = df['Speed_ms'].mean()
    max_speed = df['Speed_ms'].max()
    
    # Genauigkeits-Metriken (Cross-Track Error)
    rmse_ct = np.sqrt((df['CT_Error_m']**2).mean())
    max_ct = df['CT_Error_m'].abs().max()
    
    # Sicherheits-Metriken
    min_clearance = df['Min_Scan_m'].min()
    recoveries = df['Recoveries'].iloc[-1] - df['Recoveries'].iloc[0]
    
    kpis = {
        'Fahrzeit (s)': round(duration, 2),
        'Gefahrene Distanz (m)': round(total_dist, 2),
        'Durchschnittsgeschwindigkeit (m/s)': round(avg_speed, 3),
        'Max. Geschwindigkeit (m/s)': round(max_speed, 3),
        'Spurabweichung RMSE (m)': round(rmse_ct, 4),
        'Max. Spurabweichung (m)': round(max_ct, 3),
        'Min. Abstand zu Hindernissen (m)': round(min_clearance, 2),
        'Ausgelöste Recoveries': int(recoveries)
    }
    
    return kpis

def plot_results(df):
    """
    Erstellt publikationsreife Diagramme für deine Arbeit (mit .to_numpy() Fix).
    """
    plt.style.use('seaborn-whitegrid')
    fig, axs = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
    
    # Plot 1: Geschwindigkeit
    axs[0].plot(df['Timestamp_Norm_s'].to_numpy(), df['Speed_ms'].to_numpy(), color='blue', linewidth=2)
    axs[0].set_ylabel('Geschwindigkeit (m/s)', fontweight='bold')
    axs[0].set_title('Geschwindigkeitsprofil über Zeit', fontweight='bold')
    
    # Plot 2: Cross-Track Error (Spurtreue)
    axs[1].plot(df['Timestamp_Norm_s'].to_numpy(), df['CT_Error_m'].to_numpy(), color='red', linewidth=2)
    axs[1].axhline(0, color='black', linestyle='--', linewidth=1) # Ideallinie
    axs[1].set_ylabel('Abweichung (m)', fontweight='bold')
    axs[1].set_title('Cross-Track Error (Spurabweichung)', fontweight='bold')
    
    # Plot 3: Hindernisabstand
    axs[2].plot(df['Timestamp_Norm_s'].to_numpy(), df['Min_Scan_m'].to_numpy(), color='green', linewidth=2)
    axs[2].set_ylabel('Abstand (m)', fontweight='bold')
    axs[2].set_xlabel('Zeit (s)', fontweight='bold')
    axs[2].set_title('Minimaler Laser-Abstand zu Hindernissen', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('fahrt_auswertung.png', dpi=300) 
    plt.show()

if __name__ == "__main__":
    # Hier den Dateinamen anpassen (z.B. deine neu hochgeladene Datei)
    file_path = '/home/marieernst/ros2_ws/02_einfacheFahrt_Outdoor/10/nav_test_log.csv'
    
    # 1. Lade und trimme die Daten
    df_clean = load_and_trim_data(file_path)
    
    # 2. (Optional) Normalisiere Spalten
    #df_clean = normalize_columns_min_max(df_clean, ['Speed_ms', 'CT_Error_m'])
    
    # 3. Berechne KPIs
    kpis = calculate_kpis(df_clean)
    print("=== ERGEBNISSE FÜR DEIN KAPITEL ===")
    for key, value in kpis.items():
        print(f"{key}: {value}")
        
    # 4. Generiere die Plots
    plot_results(df_clean)
