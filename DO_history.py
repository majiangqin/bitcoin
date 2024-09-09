import time
import csv
import statistics
from datetime import datetime, timedelta
from bitcoin.rpc import RawProxy, JSONRPCError
import os
from dotenv import load_dotenv
import random

# Load environment variables
load_dotenv()
RPC_USER = os.getenv('RPC_USER')
RPC_PASSWORD = os.getenv('RPC_PASSWORD')
RPC_HOST = os.getenv('RPC_HOST')
RPC_PORT = os.getenv('RPC_PORT')

# Configuration
START_BLOCK = 850097  #803299-829998  saved in bitcoin_data_history1.csv  829998-850097 saved in bitcoin_data_history2.csv
END_BLOCK = 859768    #859312
BATCH_SIZE = 100  # number of blocks to process before writing to CSV
MIN_SLEEP_DURATION = 1
MAX_SLEEP_DURATION = 60


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


def safe_rpc_call(rpc_connection, method, *args, max_retries=3):
    for attempt in range(max_retries):
        try:
            return getattr(rpc_connection, method)(*args)
        except Exception as e:
            print(f"Error in {method} call: {str(e)}. Retrying...")
            if attempt == max_retries - 1:
                print(f"Failed to execute {method} after {max_retries} attempts")
                return None
            time.sleep(min(2 ** attempt, 8))


def get_block_and_mempool_data(rpc_connection, block_height, last_block_time):
    data = {
        'timestamp': int(time.time()),
        'block_height': block_height,
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
        'block_median_fee_rate': None  # add new field for block median fee rate
    }

    block_hash = safe_rpc_call(rpc_connection, 'getblockhash', block_height)
    if block_hash:
        block_data = safe_rpc_call(rpc_connection, 'getblock', block_hash, 2)
        if block_data:
            data['block_time'] = block_data['time']
            data['transaction_count'] = len(block_data['tx'])
            data['block_weight'] = block_data['weight']
            data['block_version'] = block_data['version']
            data['difficulty'] = block_data['difficulty']
            if last_block_time is not None:
                data['block_interval'] = data['block_time'] - last_block_time

            # Calculate median fee rate for transactions in the block
            tx_fee_rates = []
            for tx in block_data['tx'][1:]:  # Skip coinbase transaction
                if 'fee' in tx and 'vsize' in tx:
                    fee_rate = tx['fee'] / tx['vsize']
                    tx_fee_rates.append(fee_rate)
            if tx_fee_rates:
                data['block_median_fee_rate'] = statistics.median(tx_fee_rates)

    mining_info = safe_rpc_call(rpc_connection, 'getmininginfo')
    if mining_info:
        data['hash_rate'] = mining_info['networkhashps']

    mempool_info = safe_rpc_call(rpc_connection, 'getmempoolinfo')
    if mempool_info:
        data['tx_count'] = mempool_info['size']
        data['mempool_size_mb'] = mempool_info['bytes'] / 1_000_000
        data['mempool_min_fee'] = mempool_info['mempoolminfee']
        data['mempool_usage'] = mempool_info['usage']

    raw_mempool = safe_rpc_call(rpc_connection, 'getrawmempool', True)
    if raw_mempool:
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

    return data


def get_adaptive_sleep_duration(current_height, target_height):
    blocks_behind = target_height - current_height
    if blocks_behind <= 0:
        return MAX_SLEEP_DURATION
    elif blocks_behind < 100:
        return min(MAX_SLEEP_DURATION, max(MIN_SLEEP_DURATION, blocks_behind / 10))
    else:
        return MIN_SLEEP_DURATION


def main():
    rpc_connection = connect_to_bitcoin_core()
    if not rpc_connection:
        print("Failed to connect to Bitcoin Core")
        return

    csv_file = 'bitcoin_data_history.csv'
    csv_fields = ['timestamp', 'block_height', 'tx_count', 'mempool_size_mb',
                  'min_fee_rate', 'max_fee_rate', 'avg_fee_rate', 'median_fee_rate',
                  'fee_rate_10th', 'fee_rate_90th', 'fee_rate_std', 'block_time',
                  'difficulty', 'hash_rate', 'mempool_min_fee', 'total_fee', 'mempool_usage',
                  'transaction_count', 'block_weight', 'block_version', 'block_interval',
                  'block_median_fee_rate']  # Added new field

    with open(csv_file, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=csv_fields)
        writer.writeheader()

        last_block_time = None
        data_batch = []

        for block_height in range(START_BLOCK, END_BLOCK + 1):
            current_height = safe_rpc_call(rpc_connection, 'getblockcount')
            sleep_duration = get_adaptive_sleep_duration(block_height, current_height)

            data = get_block_and_mempool_data(rpc_connection, block_height, last_block_time)

            data_batch.append(data)
            print(f"Data collected for block height: {block_height}")
            last_block_time = data['block_time']

            if len(data_batch) >= BATCH_SIZE:
                writer.writerows(data_batch)
                file.flush()
                print(f"Batch of {BATCH_SIZE} blocks written to file")
                data_batch = []

            time.sleep(sleep_duration)

        # Write any remaining data
        if data_batch:
            writer.writerows(data_batch)
            file.flush()
            print(f"Final batch of {len(data_batch)} blocks written to file")

    print(f"Finished collecting data from block height {START_BLOCK} to {END_BLOCK}.")


if __name__ == "__main__":
    main()