from pycoingecko import CoinGeckoAPI
import pandas as pd
from datetime import datetime


def get_historical_usdt_data(start_date, end_date):
    """
    Get historical USDT data
    start_date, end_date: Unix timestamps in seconds
    """
    cg = CoinGeckoAPI()

    try:
        # Get historical data
        data = cg.get_coin_market_chart_range_by_id(
            id='tether',
            vs_currency='usd',
            from_timestamp=start_date,
            to_timestamp=end_date
        )

        # Create DataFrames and convert timestamp for all
        df_price = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
        df_volume = pd.DataFrame(data['total_volumes'], columns=['timestamp', 'volume'])
        df_market_cap = pd.DataFrame(data['market_caps'], columns=['timestamp', 'market_cap'])

        # Convert timestamp to datetime for all dataframes
        for df in [df_price, df_volume, df_market_cap]:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # Merge all data
        df = df_price.merge(df_volume, on='timestamp', how='outer')
        df = df.merge(df_market_cap, on='timestamp', how='outer')

        # Set timestamp as index after merging
        df.set_index('timestamp', inplace=True)

        # Sort index
        df.sort_index(inplace=True)

        return df

    except Exception as e:
        print(f"Error fetching data: {str(e)}")
        return None



if __name__ == "__main__":
    # Convert dates to Unix timestamps
    start_date = int(datetime(2024, 1, 1).timestamp())
    end_date = int(datetime(2024, 12, 31).timestamp())

    df = get_historical_usdt_data(start_date, end_date)

    if df is not None:
        print("\nFirst few rows of data:")
        print(df.head())
        print("\nData columns:", df.columns.tolist())
        print("\nData types:")
        print(df.dtypes)

        # Save to CSV
        df.to_csv('historical_usdt_data.csv')
        print("\nData saved to historical_usdt_data.csv")