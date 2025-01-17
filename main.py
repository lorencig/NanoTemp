import firebase_admin
from firebase_admin import credentials, db
import streamlit as st
import altair as alt
from datetime import datetime, timezone, timedelta
import pandas as pd
import time

# Access Firebase credentials from secrets
FIREBASE_DATABASE_URL = st.secrets["FIREBASE"]["DATABASE_URL"]
FIREBASE_CERT = credentials.Certificate("firebase_key.json")
#FIREBASE_CERT = st.secrets["FIREBASE"]["CERT"]

# Global DataFrame to store Firebase data
df = None

def format_timestamp(unix_timestamp):
    """Convert Unix timestamp to formatted datetime string (hh:mm:ss dd/mm/yyyy)."""
    dt = datetime.fromtimestamp(int(unix_timestamp), tz=timezone.utc)
    formatted_time = dt.strftime("%H:%M:%S %d/%m/%Y")
    return formatted_time, dt

def initialize_firebase():
    """Initialize Firebase connection if not already initialized."""
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebase_key.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_DATABASE_URL
        })

def fetch_temperature_data():
    """Fetch temperature data from Firebase and process it."""
    ref = db.reference('/TemperatureData')
    temp_data = ref.get()
    
    if temp_data:
        data = []
        for unix, temp in sorted(temp_data.items(), key=lambda x: int(x[0])):
            formatted_time, dt = format_timestamp(unix)
            data.append({
                "Timestamp": dt,
                "FormattedTime": formatted_time,
                "Temperature": temp
            })
        
        return pd.DataFrame(data)
    return None

def create_temperature_chart(df):
    """Create Altair chart from temperature DataFrame."""
    return alt.Chart(df).mark_line().encode(
        x=alt.X('Timestamp:T', title='Time', axis=alt.Axis(format='%H:%M')),
        y=alt.Y('Temperature:Q', title='Temperature (°C)'),
        tooltip=['FormattedTime', 'Temperature']
    ).properties(
        title="Real-Time Temperature Data",
        width=800,
        height=400
    )

def filter_data_by_datetime_range(df, start_date, start_time, end_date, end_time):
    """Filter data by the user-defined date and time range."""
    # Create timezone-aware datetime objects
    start_datetime = datetime.combine(start_date, start_time).replace(tzinfo=timezone.utc)
    end_datetime = datetime.combine(end_date, end_time).replace(tzinfo=timezone.utc)
    
    return df[(df['Timestamp'] >= start_datetime) & (df['Timestamp'] <= end_datetime)]

def main():
    global df  # Use the global DataFrame to store data
    st.set_page_config(page_title="NanoTemp", page_icon="🧊", layout="centered")
    # Initialize Streamlit UI
    st.title('NanoTemp IIT')
    st.subheader('Nanomaterials for Biomedical App')

    
    # Initialize Firebase
    initialize_firebase()

    # Create placeholders for updating components
    chart_placeholder = st.empty()
    latest_temp_placeholder = st.empty()
    latest_time_placeholder = st.empty()

    # Download section
    st.header('Download Temperature Data')

    # Check if the date range values exist in session_state
    if 'start_date' not in st.session_state:
        st.session_state['start_date'] = datetime.now().date()
    if 'start_time' not in st.session_state:
        st.session_state['start_time'] = datetime.now().time()
    if 'end_date' not in st.session_state:
        st.session_state['end_date'] = datetime.now().date()
    if 'end_time' not in st.session_state:
        st.session_state['end_time'] = datetime.now().time()

    # Date and time selection for data download
    col1, col2 = st.columns(2)
    with col1:
        st.session_state['start_date'] = st.date_input("Start Date", value=st.session_state['start_date'])
        st.session_state['start_time'] = st.time_input('Start Time', value=st.session_state['start_time'])
    
    with col2:
        st.session_state['end_date'] = st.date_input("End Date", value=st.session_state['end_date'])
        st.session_state['end_time'] = st.time_input('End Time', value=st.session_state['end_time'])

    # Only fetch the data once when needed
    if df is None:
        df = fetch_temperature_data()

    # Main data display and download logic
    if df is not None:
        # Update latest temperature and timestamp
        latest_temp = df.iloc[-1]["Temperature"]
        latest_time = df.iloc[-1]["FormattedTime"]
        latest_temp_placeholder.markdown(f"<h3 style='font-size:30px;'>**Latest Temperature:** {latest_temp} °C</h3>", unsafe_allow_html=True)
        latest_time_placeholder.write(f"**Recorded at:** {latest_time}")

        # Update chart
        chart = create_temperature_chart(df)
        chart_placeholder.altair_chart(chart, use_container_width=True)

        # Handle data download
        if st.session_state['start_date'] and st.session_state['end_date'] and st.session_state['start_time'] and st.session_state['end_time']:
            filtered_df = filter_data_by_datetime_range(
                df, st.session_state['start_date'], st.session_state['start_time'], st.session_state['end_date'], st.session_state['end_time']
            )
            if not filtered_df.empty:
                st.download_button(
                    label="Download Raw Data as CSV",
                    data=filtered_df[['FormattedTime', 'Temperature']].to_csv(index=False),
                    file_name=f"temperature_data_{st.session_state['start_date']}_{st.session_state['end_date']}.csv",
                    mime="text/csv"
                )
            else:
                # Display "No data available" only if the time range filter doesn't match
                st.write("No data available for the selected time range.")


    footer = f"""
    <style>
        /* Footer container */
        .footer {{
            width: 100%;
            background-color: #252525;
            padding: 1rem;
            text-align: center;
            box-shadow: 0 -1px 5px rgba(0,0,0,0.1);
            font-size: clamp(12px, 1vw, 16px);  /* Responsive font size */
            color: #666;
            position: fixed;
            bottom: 0;
            left: 0;
        }}

        /* Footer text */
        .footer-text {{
            color: #FFFFFF;
            font-weight: 400;
            font-size: clamp(16px, 1vw, 14px); /* Responsive font size */
        }}
    </style>

    <div class="footer">
        <div class="footer-text">
            From Bolzaneto with Love!
        </div>
    </div>
    """
    # Insert the footer in the Streamlit app
    st.markdown(footer, unsafe_allow_html=True)

 # Main data display and download logic

    while True:
        df = fetch_temperature_data()
        if df is not None:
            # Update latest temperature and timestamp
            latest_temp = df.iloc[-1]["Temperature"]
            latest_time = df.iloc[-1]["FormattedTime"]
            latest_temp_placeholder.write(f"**Latest Temperature:** {latest_temp} °C")
            latest_time_placeholder.write(f"**Recorded at:** {latest_time}")
            # Update chart
            chart = create_temperature_chart(df)
            chart_placeholder.altair_chart(chart, use_container_width=True)
            time.sleep(1)  # Pause for 1 second before updating again




if __name__ == "__main__":
    main()
