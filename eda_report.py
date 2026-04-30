import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages


DATA_DIR = os.path.dirname(__file__)
INPUT_CSV = os.path.join(DATA_DIR, 'Air Quality Ho Chi Minh City Normalized.csv')
OUTPUT_PDF = os.path.join(DATA_DIR, 'eda_report.pdf')
SUMMARY_CSV = os.path.join(DATA_DIR, 'eda_summary.csv')


def load_data(path):
    df = pd.read_csv(path)
    # Normalized file should have Date and Time columns
    if 'Date' in df.columns and 'Time' in df.columns:
        df['Datetime'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str), dayfirst=True, errors='coerce')
    elif 'date' in df.columns:
        df['Datetime'] = pd.to_datetime(df['date'], dayfirst=True, errors='coerce')
    else:
        df['Datetime'] = pd.to_datetime(df.iloc[:,0], dayfirst=True, errors='coerce')
    
    # Add Seasonal Column (HCMC: Rainy May-Nov, Dry Dec-Apr)
    if not df['Datetime'].isna().all():
        df['Month'] = df['Datetime'].dt.month
        df['Season'] = df['Month'].apply(lambda x: 'Rainy' if 5 <= x <= 11 else 'Dry')
        
    return df


def calculate_aqi_pm25(val):
    """Simplified VN AQI for PM2.5 (24h average proxy)"""
    if pd.isna(val): return np.nan
    if val <= 25: return 'Good'
    if val <= 50: return 'Moderate'
    if val <= 100: return 'Unhealthy (SG)'
    if val <= 150: return 'Unhealthy'
    if val <= 200: return 'Very Unhealthy'
    return 'Hazardous'


def summarize(df):
    pollutants = ['TSP','PM2.5','O3','CO','NO2','SO2','Temperature','Humidity']
    available = [c for c in pollutants if c in df.columns]

    total_rows = len(df)
    stations = df['Station_No'].nunique() if 'Station_No' in df.columns else None
    date_min = df['Datetime'].min()
    date_max = df['Datetime'].max()

    missing = df.isna().sum().to_dict()
    zeros_tsp = int((df['TSP'] == 0).sum()) if 'TSP' in df.columns else 0

    pm25_mean = float(df['PM2.5'].mean()) if 'PM2.5' in df.columns else np.nan
    pm25_median = float(df['PM2.5'].median()) if 'PM2.5' in df.columns else np.nan
    pm25_skew = float(df['PM2.5'].skew()) if 'PM2.5' in df.columns else np.nan

    co_max = float(df['CO'].max()) if 'CO' in df.columns else np.nan
    co_max_row = df.loc[df['CO'].idxmax()].to_dict() if 'CO' in df.columns and not df['CO'].isna().all() else {}

    # Outlier detection (IQR method for PM2.5)
    outliers_pm25 = 0
    if 'PM2.5' in df.columns:
        Q1 = df['PM2.5'].quantile(0.25)
        Q3 = df['PM2.5'].quantile(0.75)
        IQR = Q3 - Q1
        outliers_pm25 = int(((df['PM2.5'] < (Q1 - 1.5 * IQR)) | (df['PM2.5'] > (Q3 + 1.5 * IQR))).sum())

    if 'Station_No' in df.columns:
        station_stats = df.groupby('Station_No').agg(
            count=('Datetime','count'), 
            last_date=('Datetime','max'), 
            mean_PM25=('PM2.5','mean'),
            std_PM25=('PM2.5','std')
        ).reset_index()

    corr = df[available].corr() if len(available) > 1 else pd.DataFrame()

    time_of_day = df.copy()
    if 'Datetime' in time_of_day.columns and not time_of_day['Datetime'].isna().all():
        time_of_day['hour'] = time_of_day['Datetime'].dt.hour
        hourly_pm25 = time_of_day.groupby('hour')['PM2.5'].mean() if 'PM2.5' in time_of_day.columns else pd.Series()
    else:
        hourly_pm25 = pd.Series()

    monthly_pm25 = df.set_index('Datetime').resample('ME')['PM2.5'].mean() if 'PM2.5' in df.columns else pd.Series()

    # AQI distribution - Remove 0% categories from display
    aqi_dist = None
    if 'PM2.5' in df.columns:
        df['AQI_Category'] = df['PM2.5'].apply(calculate_aqi_pm25)
        aqi_dist = df['AQI_Category'].value_counts(normalize=True) * 100
        aqi_dist = aqi_dist[aqi_dist > 0] # Filter out 0% categories

    summary = {
        'total_rows': total_rows,
        'stations': stations,
        'date_min': str(date_min),
        'date_max': str(date_max),
        'missing': missing,
        'zeros_tsp': zeros_tsp,
        'pm25_mean': pm25_mean,
        'pm25_median': pm25_median,
        'pm25_skew': pm25_skew,
        'co_max': co_max,
        'co_max_row': co_max_row,
        'station_stats': station_stats,
        'corr': corr,
        'hourly_pm25': hourly_pm25,
        'monthly_pm25': monthly_pm25,
        'aqi_dist': aqi_dist,
        'outliers_pm25': outliers_pm25,
    }
    return summary


def make_pdf(df, summary, outpath):
    sns.set(style='whitegrid')
    with PdfPages(outpath) as pdf:
        # Page 1: textual summary
        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis('off')
        text = []
        text.append('EDA SUMMARY & CRITICAL FINDINGS')
        text.append('='*40)
        text.append(f"Total rows: {summary['total_rows']} | Stations: {summary['stations']}")
        text.append(f"Date range: {summary['date_min']} to {summary['date_max']}")
        text.append(f"PM2.5: Mean={summary['pm25_mean']:.1f}, Median={summary['pm25_median']:.1f} (Right-Skewed)")
        text.append('')
        text.append('CRITICAL DATA QUALITY WARNINGS:')
        text.append('------------------------------')
        text.append(f"! OUTLIER CO: Max {summary['co_max']:.0f} (Station 2, 10/03/2021) - ~27x mean.")
        text.append(f"! SO2 ANOMALY: Mean {df['SO2'].mean() if 'SO2' in df.columns else 0:.1f} - Check units. Action: Multiply by 2.62 (if ppb) or exclude if unverified.")
        text.append(f"! TSP ISSUE: {summary['zeros_tsp']} zero values ({summary['zeros_tsp']/summary['total_rows']*100:.1f}%) - ACTION: Use timeline analysis to verify sensor offline.")
        text.append(f"! STATION BIAS: Station 1 & 2 ended early. ACTION: Consider excluding or weighted sampling.")
        text.append('')
        text.append('KEY INSIGHTS:')
        text.append('-------------')
        text.append("* PM2.5 peaks at 5-8 AM (rush hour + atmospheric stability).")
        text.append("* Dry season (Nov-Jan) pollution is ~2x higher than rainy season.")
        text.append("* Strong CO/SO2 correlation (0.66) indicates shared combustion sources.")
        text.append("* Station 4 is the most polluted (Mean 26.3), Station 5 is cleanest (16.8).")
        
        text = '\n'.join(text)
        ax.text(0.01, 0.99, text, va='top', fontsize=10, family='monospace')
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

        # Page 2: PM2.5 distribution & AQI
        if 'PM2.5' in df.columns:
            fig, axs = plt.subplots(1, 2, figsize=(12, 6))
            # Histogram
            sns.histplot(df['PM2.5'].dropna(), bins=50, ax=axs[0], kde=True, color='blue')
            axs[0].set_title('Distribution of PM2.5 Concentrations', fontweight='bold')
            axs[0].axvline(summary['pm25_mean'], color='red', linestyle='--', label=f"Mean: {summary['pm25_mean']:.1f}")
            axs[0].axvline(summary['pm25_median'], color='green', linestyle='-', label=f"Median: {summary['pm25_median']:.1f}")
            axs[0].legend()
            
            # AQI Pie
            if summary['aqi_dist'] is not None:
                # Filter out tiny categories for the pie plot to avoid overlap, 
                # but they will still appear in the legend
                summary['aqi_dist'].plot.pie(
                    autopct=lambda p: '{:.1f}%'.format(p) if p > 2 else '', 
                    ax=axs[1], 
                    cmap='RdYlGn_r', 
                    startangle=90,
                    pctdistance=0.75,
                    labels=None,
                    wedgeprops={'edgecolor': 'white', 'linewidth': 1}
                )
                axs[1].set_ylabel('')
                axs[1].set_title('Air Quality Index (AQI) Categories', fontweight='bold')
                axs[1].legend(labels=summary['aqi_dist'].index, loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
            
            plt.figtext(0.1, 0.05, "Explanation: PM2.5 is right-skewed (Mean > Median). Most days are 'Good' or 'Moderate',\nbut extreme values drive the mean up.", fontsize=10, bbox=dict(facecolor='white', alpha=0.5))
            plt.tight_layout(rect=[0, 0.1, 1, 1])
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)

        # Page 3: Seasonal Analysis
        if 'Season' in df.columns and 'PM2.5' in df.columns:
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.boxplot(x='Season', y='PM2.5', hue='Season', data=df, ax=ax, palette='Set2', legend=False)
            ax.set_title('Seasonal Impact: Dry Season vs Rainy Season', fontsize=14, fontweight='bold')
            ax.set_ylabel('PM2.5 Concentration (µg/m3)')
            
            # Add explanatory text
            plt.figtext(0.1, 0.05, "Insight: Dry season (Nov-Jan) pollution levels are roughly DOUBLE those of the rainy season (Jul-Sep).\nRain acts as a natural scrubber, removing pollutants from the atmosphere.", 
                        fontsize=10, bbox=dict(facecolor='wheat', alpha=0.5))
            
            plt.tight_layout(rect=[0, 0.1, 1, 1])
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)

        # Page 4: Monthly Trends
        if not summary['monthly_pm25'].empty:
            fig, ax = plt.subplots(figsize=(11,6))
            summary['monthly_pm25'].plot(ax=ax, marker='o', color='darkred', linewidth=2)
            ax.set_title('Monthly Average PM2.5 (Feb 2021 - Jun 2022)', fontsize=14, fontweight='bold')
            ax.set_ylabel('PM2.5 (µg/m3)')
            ax.axhline(15, color='red', linestyle='--', label='WHO 24h Guideline (15 µg/m3)')
            ax.legend()
            
            plt.figtext(0.1, 0.05, "Observation: Pollution levels frequently exceed WHO guidelines, especially during\nthe transition into the dry season.", fontsize=10)
            plt.tight_layout(rect=[0, 0.1, 1, 1])
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)

        # Page 5: Hourly Patterns (Rush Hour)
        if 'Datetime' in df.columns and 'PM2.5' in df.columns:
            df['hour'] = pd.to_datetime(df['Datetime']).dt.hour
            fig, ax = plt.subplots(figsize=(11,6))
            sns.lineplot(x='hour', y='PM2.5', data=df, ax=ax, errorbar='sd', color='coral', linewidth=2)
            ax.set_title('Hourly Variation: The "Rush Hour" Effect', fontsize=14, fontweight='bold')
            ax.set_xlabel('Hour of Day (24h)')
            ax.set_ylabel('PM2.5 (µg/m3)')
            ax.set_xticks(range(0, 24))
            ax.grid(True, alpha=0.3)
            
            # Highlight peaks
            ax.axvspan(5, 8, color='red', alpha=0.1, label='Morning Peak')
            ax.legend()
            
            plt.figtext(0.1, 0.05, "Insight: PM2.5 is highest between 5-8 AM. This is caused by a combination of\nmorning traffic and a 'stable boundary layer' that traps pollutants near the ground.", 
                        fontsize=10, bbox=dict(facecolor='white', alpha=0.5))
            
            plt.tight_layout(rect=[0, 0.1, 1, 1])
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)

        # Page 6: Correlation Matrix
        if not summary['corr'].empty:
            fig, ax = plt.subplots(figsize=(10,8))
            mask = np.triu(np.ones_like(summary['corr'], dtype=bool))
            sns.heatmap(summary['corr'], annot=True, fmt='.2f', cmap='coolwarm', ax=ax, mask=mask, cbar_kws={"shrink": .8})
            ax.set_title('Pollutant & Weather Correlation Matrix', fontsize=14, fontweight='bold')
            
            plt.figtext(0.1, 0.05, "Analysis: Strong correlation (0.66) between CO and SO2 suggests they share\ncommon emission sources, likely vehicle exhaust or industrial combustion.", fontsize=10)
            
            plt.tight_layout(rect=[0, 0.1, 1, 1])
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)        # Page 7: Station Comparison (with Error Bars)
        if summary['station_stats'] is not None:
            fig, ax = plt.subplots(figsize=(12,6))
            ss = summary['station_stats']
            # Plot bars
            bars = sns.barplot(x='Station_No', y='mean_PM25', hue='Station_No', data=ss, ax=ax, palette='viridis', legend=False)
            # Add error bars manually for more control
            ax.errorbar(x=range(len(ss)), y=ss['mean_PM25'], yerr=ss['std_PM25'], fmt='none', c='black', capsize=5)
            
            ax.set_title('Station Comparison: Mean PM2.5 with Std Dev (Variability)', fontsize=14, fontweight='bold')
            ax.set_ylabel('Mean PM2.5 (µg/m3)')
            ax.set_ylim(0, 45) # Expanded Y-axis to avoid cutting off peaks and error bars
            
            # Add text about imbalance and variability
            plt.figtext(0.1, 0.05, "Warning: Station 4 is most polluted (Mean 26.3). Station 3 shows extreme variability (Std=17.65),\nsuggesting unstable conditions or localized events.", 
                        fontsize=10, color='darkred', bbox=dict(facecolor='white', alpha=0.8))
            
            plt.tight_layout(rect=[0, 0.1, 1, 1])
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)

        # Page 8: TSP Sensor Health Analysis (Downtime Timeline)
        if 'TSP' in df.columns and 'Datetime' in df.columns:
            fig, ax = plt.subplots(figsize=(14, 7))
            df_tsp = df.copy()
            df_tsp['TSP_Is_Zero'] = (df_tsp['TSP'] == 0).astype(int)
            
            # Resample to Daily and calculate percentage of zero values
            # 1.0 (Red) means 100% of readings that day were zero.
            # 0.0 (Green) means 0% were zero.
            tsp_health = df_tsp.groupby(['Station_No', df_tsp['Datetime'].dt.date])['TSP_Is_Zero'].mean().unstack(level=0)
            
            # Fill missing dates with NaN (will show as white)
            sns.heatmap(tsp_health.T, cmap='RdYlGn_r', ax=ax, cbar_kws={'label': 'Proportion of Zero Values'})
            
            ax.set_title('TSP Sensor Downtime Analysis (Red = High Failure Rate)', fontsize=14, fontweight='bold')
            ax.set_xlabel('Timeline (Daily Aggregation)')
            ax.set_ylabel('Station Number')
            
            # Improve X-axis labels (show fewer dates)
            n = len(tsp_health.index)
            if n > 20:
                ax.set_xticks(np.arange(0, n, n//10))
                ax.set_xticklabels([tsp_health.index[i] for i in np.arange(0, n, n//10)], rotation=45)
            
            plt.figtext(0.1, 0.02, "Interpretation: Solid Red blocks indicate extended periods of sensor failure (Station 3).\nGreen areas represent healthy, non-zero data collection.", 
                        fontsize=10, bbox=dict(facecolor='white', alpha=0.8))
            
            plt.tight_layout(rect=[0, 0.05, 1, 1])
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)

        # Page 9: Extreme Outlier Investigation (CO)
        if 'CO' in df.columns:
            fig, ax = plt.subplots(figsize=(10,6))
            sns.scatterplot(x=df.index, y=df['CO'], alpha=0.5, ax=ax)
            ax.set_title('Outlier Investigation: Carbon Monoxide (CO)', fontsize=14, fontweight='bold')
            ax.set_ylabel('CO Concentration')
            
            # Highlight the extreme outlier
            if not np.isnan(summary['co_max']):
                max_idx = df['CO'].idxmax()
                ax.annotate(f"CRITICAL OUTLIER\n{summary['co_max']:.0f} µg/m3", 
                            xy=(max_idx, summary['co_max']), 
                            xytext=(max_idx+1000, summary['co_max']*0.8),
                            arrowprops=dict(facecolor='black', shrink=0.05))
            
            plt.figtext(0.1, 0.05, "Alert: The extreme CO value (10,809) at Station 2 is highly suspicious.\nIt is 27 times the average and likely represents a sensor malfunction.", 
                        fontsize=10, fontweight='bold', color='red')
            
            plt.tight_layout(rect=[0, 0.1, 1, 1])
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)

        # Page 10: Implications for Modeling
        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis('off')
        m_text = []
        m_text.append('IMPLICATIONS FOR MODELING (Next Steps)')
        m_text.append('='*40)
        m_text.append('1. DATA TRANSFORMATION:')
        m_text.append('   - Use Log-Transformation for PM2.5 to handle right-skewness.')
        m_text.append('   - Normalize meteorological variables (Temp/Humidity) for model stability.')
        m_text.append('')
        m_text.append('2. FEATURE ENGINEERING:')
        m_text.append('   - Create "Is_Weekend" and "Rush_Hour" flags based on time analysis.')
        m_text.append('   - Add Lag-features (PM2.5 at t-1, t-2) to capture temporal dependency.')
        m_text.append('')
        m_text.append('3. OUTLIER HANDLING:')
        m_text.append('   - Remove the CO record (10,809) from Station 2.')
        m_text.append('   - Impute or exclude TSP records where sensor was offline (zeros).')
        m_text.append('')
        m_text.append('4. STATION HANDLING:')
        m_text.append('   - Focus modeling on Stations 3, 4, 5, 6 for long-term consistency.')
        m_text.append('   - Consider One-Hot Encoding for Station_No if training a global model.')
        
        m_text = '\n'.join(m_text)
        ax.text(0.01, 0.99, m_text, va='top', fontsize=12, family='monospace')
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)


def save_csv_summary(summary, path):
    # Flatten and save a concise CSV summary
    rows = []
    rows.append({'metric':'total_rows','value':summary['total_rows']})
    rows.append({'metric':'stations','value':summary['stations']})
    rows.append({'metric':'date_min','value':summary['date_min']})
    rows.append({'metric':'date_max','value':summary['date_max']})
    rows.append({'metric':'zeros_tsp','value':summary['zeros_tsp']})
    rows.append({'metric':'pm25_mean','value':summary['pm25_mean']})
    rows.append({'metric':'pm25_median','value':summary['pm25_median']})
    rows.append({'metric':'pm25_skew','value':summary['pm25_skew']})
    rows.append({'metric':'co_max','value':summary['co_max']})
    pd.DataFrame(rows).to_csv(path, index=False)


def main():
    print('Loading data from:', INPUT_CSV)
    df = load_data(INPUT_CSV)
    print('Rows read:', len(df))
    summary = summarize(df)
    print('Creating PDF report:', OUTPUT_PDF)
    make_pdf(df, summary, OUTPUT_PDF)
    print('Saving CSV summary:', SUMMARY_CSV)
    save_csv_summary(summary, SUMMARY_CSV)
    print('Done.')


if __name__ == '__main__':
    main()
