import time
import csv
import statistics
from datetime import datetime, timedelta
from bitcoin.rpc import RawProxy, JSONRPCError
import random
import requests
from dotenv import load_dotenv
import os

load_dotenv()
RPC_USER = os.getenv("RPC_USER")
RPC_PASSWORD = os.getenv("RPC_PASSWORD")
RPC_HOST = os.getenv("RPC_HOST")
RPC_PORT = int(os.getenv("RPC_PORT"))
def connect_to_bitcoin_core(max_retries=5, initial_delay=1):
    for attempt in range(max_retries):
        try:
            rpc_connection = RawProxy(service_url=f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_HOST}:{RPC_PORT}")
            rpc_connection.getblockchaininfo()
            print("Successfully connected to Bitcoin Core")
            return rpc_connection
        except JSONRPCError as e:
            delay = min(initial_delay * (2 ** attempt) + random.uniform(0, 1), 30)
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            print(f"Retrying in {delay:.2f} seconds...")
            time.sleep(delay)
    print("Failed to connect to Bitcoin Core after multiple attempts")
    return None

def safe_rpc_call(rpc_connection, method, *args):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return getattr(rpc_connection, method)(*args)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(f"Error in {method} call: {str(e)}. Retrying...")
            time.sleep(min(2 ** attempt, 8))

def get_bitcoin_price():
    try:
        response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd')
        data = response.json()
        return data['bitcoin']['usd']
    except Exception as e:
        print(f"Error fetching Bitcoin price: {str(e)}")
        return None

def get_block_and_mempool_data(rpc_connection, last_block_time):
    data = {
        'timestamp': int(time.time()),
        'block_height': None,
        'tx_count': 0,
        'mempool_size_mb': 0,
        'min_fee_rate': 0,
        'max_fee_rate': 0,
        'avg_fee_rate': 0,
        'median_fee_rate': 0,
        'fee_rate_10th': 0,
        'fee_rate_90th': 0,
        'fee_rate_std': 0,
        'block_time': None,
        'difficulty': None,
        'hash_rate': None,
        'mempool_min_fee': 0,
        'total_fee': 0,
        'mempool_usage': 0,
        'transaction_count': None,
        'block_weight': None,
        'block_version': None,
        'block_interval': None,
        'bitcoin_price_usd': None
    }

    try:
        block_info = safe_rpc_call(rpc_connection, 'getblockchaininfo')
        data['block_height'] = block_info['blocks']
        data['difficulty'] = block_info['difficulty']

        # Get the most recent block hash
        block_hash = safe_rpc_call(rpc_connection, 'getblockhash', data['block_height'])
        # Get the block data
        block_data = safe_rpc_call(rpc_connection, 'getblock', block_hash, 2)
        data['block_time'] = block_data['time']
        data['transaction_count'] = len(block_data['tx'])
        data['block_weight'] = block_data['weight']
        data['block_version'] = block_data['version']

        # Calculate block interval
        if last_block_time is not None:
            data['block_interval'] = data['block_time'] - last_block_time

        print("Successfully retrieved blockchain and block info")
    except Exception as e:
        print(f"Error retrieving blockchain or block info: {str(e)}")

    try:
        mining_info = safe_rpc_call(rpc_connection, 'getmininginfo')
        data['hash_rate'] = mining_info['networkhashps']
        print("Successfully retrieved mining info")
    except Exception as e:
        print(f"Error retrieving mining info: {str(e)}")

    try:
        mempool_info = safe_rpc_call(rpc_connection, 'getmempoolinfo')
        data['tx_count'] = mempool_info['size']
        data['mempool_size_mb'] = mempool_info['bytes'] / 1_000_000
        data['mempool_min_fee'] = mempool_info['mempoolminfee']
        data['mempool_usage'] = mempool_info['usage']
        print("Successfully retrieved mempool info")
    except Exception as e:
        print(f"Error retrieving mempool info: {str(e)}")

    try:
        raw_mempool = safe_rpc_call(rpc_connection, 'getrawmempool', True)
        fee_rates = [tx_data['fees']['base'] / tx_data['vsize'] for tx_data in raw_mempool.values()]
        if fee_rates:
            fee_rates.sort()
            data['min_fee_rate'] = min(fee_rates)
            data['max_fee_rate'] = max(fee_rates)
            data['avg_fee_rate'] = sum(fee_rates) / len(fee_rates)
            data['median_fee_rate'] = fee_rates[len(fee_rates) // 2]
            data['fee_rate_10th'] = fee_rates[len(fee_rates) // 10] if len(fee_rates) > 10 else 0
            data['fee_rate_90th'] = fee_rates[int(len(fee_rates) * 0.9)] if len(fee_rates) > 10 else 0
            data['fee_rate_std'] = statistics.stdev(fee_rates) if len(fee_rates) > 1 else 0
            data['total_fee'] = sum(tx_data['fees']['base'] for tx_data in raw_mempool.values())
        print("Successfully retrieved raw mempool data")
    except Exception as e:
        print(f"Error retrieving raw mempool data: {str(e)}")

    # Fetch Bitcoin price
    data['bitcoin_price_usd'] = get_bitcoin_price()
    print("Successfully retrieved Bitcoin price")

    return data

def main():
    rpc_connection = None
    csv_file = 'bitcoin_data_real_time.csv'
    csv_fields = ['timestamp', 'block_height', 'tx_count', 'mempool_size_mb',
                  'min_fee_rate', 'max_fee_rate', 'avg_fee_rate', 'median_fee_rate',
                  'fee_rate_10th', 'fee_rate_90th', 'fee_rate_std', 'block_time',
                  'difficulty', 'hash_rate', 'mempool_min_fee', 'total_fee', 'mempool_usage',
                  'transaction_count', 'block_weight', 'block_version', 'block_interval',
                  'bitcoin_price_usd']

    with open(csv_file, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=csv_fields)
        writer.writeheader()

        last_block_time = None
        next_check_time = datetime.now()

        while True:
            try:
                current_time = datetime.now()
                if current_time >= next_check_time:
                    if rpc_connection is None:
                        rpc_connection = connect_to_bitcoin_core()

                    if rpc_connection:
                        data = get_block_and_mempool_data(rpc_connection, last_block_time)
                        writer.writerow(data)
                        file.flush()
                        print(f"Data collected and saved for timestamp: {datetime.fromtimestamp(data['timestamp'])}")
                        last_block_time = data['block_time']
                    else:
                        print("No connection to Bitcoin Core")

                    # Set the next check time
                    next_check_time = current_time + timedelta(minutes=10)

                # Sleep for a short time to prevent busy waiting
                time.sleep(5)

            except KeyboardInterrupt:
                print("Data collection stopped by user.")
                break
            except Exception as e:
                print(f"An error occurred in main loop: {str(e)}")
                rpc_connection = None
                time.sleep(60)  # Wait a minute before retrying

if __name__ == "__main__":
    main()