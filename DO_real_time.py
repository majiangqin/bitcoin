import time
import csv
import statistics
from datetime import datetime
from bitcoin.rpc import RawProxy, JSONRPCError
import random
import requests
import os
from dotenv import load_dotenv
import logging
import backoff

# Set up error logging
logging.basicConfig(filename='error_log.txt', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()
RPC_USER = os.getenv('RPC_USER')
RPC_PASSWORD = os.getenv('RPC_PASSWORD')
RPC_HOST = os.getenv('RPC_HOST')
RPC_PORT = os.getenv('RPC_PORT')

SATS_PER_BTC = 100_000_000  # 100 million satoshis per BTC


def connect_to_bitcoin_core(max_retries=5, initial_delay=1, timeout=60):
    for attempt in range(max_retries):
        try:
            rpc_connection = RawProxy(service_url=f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_HOST}:{RPC_PORT}",
                                      timeout=timeout)
            rpc_connection.getblockchaininfo()
            print("Successfully connected to Bitcoin Core")
            logging.info("Successfully connected to Bitcoin Core")
            return rpc_connection
        except JSONRPCError as e:
            delay = min(initial_delay * (2 ** attempt) + random.uniform(0, 1), 30)
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            logging.error(f"Connection attempt {attempt + 1} failed: {str(e)}")
            print(f"Retrying in {delay:.2f} seconds...")
            time.sleep(delay)
    print("Failed to connect to Bitcoin Core after multiple attempts")
    logging.error("Failed to connect to Bitcoin Core after multiple attempts")
    return None


@backoff.on_exception(backoff.expo, Exception, max_tries=5)
def safe_rpc_call(rpc_connection, method, *args):
    try:
        logging.debug(f"Attempting RPC call: {method}")
        result = getattr(rpc_connection, method)(*args)
        logging.debug(f"RPC call successful: {method}")
        return result
    except Exception as e:
        logging.error(f"RPC call failed: {method} - {str(e)}")
        raise


@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def get_bitcoin_price():
    try:
        response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd',
                                timeout=10)
        data = response.json()
        price = data['bitcoin']['usd']
        logging.debug(f"Bitcoin price fetched: ${price}")
        return price
    except Exception as e:
        logging.error(f"Failed to fetch Bitcoin price: {str(e)}")
        return None


def create_fee_histogram(fee_rates, num_bins=10):
    try:
        if not fee_rates:
            logging.warning("No fee rates available for histogram creation")
            return []

        min_fee = min(fee_rates)
        max_fee = max(fee_rates)
        if min_fee == max_fee:
            logging.warning("All fee rates are the same, cannot create meaningful histogram")
            return [len(fee_rates)]  # Return a single bin with all fees

        bin_edges = [min_fee + i * (max_fee - min_fee) / num_bins for i in range(num_bins + 1)]
        histogram = [0] * num_bins

        for fee in fee_rates:
            for i in range(num_bins):
                if bin_edges[i] <= fee < bin_edges[i + 1]:
                    histogram[i] += 1
                    break
            else:
                histogram[-1] += 1  # For the max value

        logging.debug(f"Created histogram: {histogram}")
        return histogram
    except Exception as e:
        logging.error(f"Error creating fee histogram: {str(e)}")
        return []


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
        'block_median_fee_rate': None,
        'time_since_last_block': None,
        'mempool_fee_histogram': None,
        'bitcoin_price_usd': None
    }

    try:
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
                    data['time_since_last_block'] = data['block_time'] - last_block_time

                tx_fee_rates = []
                for tx in block_data['tx'][1:]:  # Skip coinbase transaction
                    if 'fee' in tx and 'vsize' in tx and tx['vsize'] > 0:
                        fee_rate = (tx['fee'] / tx['vsize']) * SATS_PER_BTC  # Convert to sat/vB
                        tx_fee_rates.append(fee_rate)
                if tx_fee_rates:
                    data['block_median_fee_rate'] = round(statistics.median(tx_fee_rates), 4)

        mining_info = safe_rpc_call(rpc_connection, 'getmininginfo')
        if mining_info:
            data['hash_rate'] = mining_info['networkhashps']

        mempool_info = safe_rpc_call(rpc_connection, 'getmempoolinfo')
        if mempool_info:
            data['tx_count'] = mempool_info['size']
            data['mempool_size_mb'] = round(mempool_info['bytes'] / 1_000_000, 6)

            # Improved mempool_min_fee calculation
            mempool_min_fee_btc_kb = mempool_info['mempoolminfee']
            data['mempool_min_fee'] = round((mempool_min_fee_btc_kb * SATS_PER_BTC) / 1000, 4)
            logging.debug(f"Raw mempool min fee: {mempool_min_fee_btc_kb} BTC/kB")
            logging.debug(f"Converted mempool min fee: {data['mempool_min_fee']} sat/vB")

            data['mempool_usage'] = mempool_info['usage']

        raw_mempool = safe_rpc_call(rpc_connection, 'getrawmempool', True)
        if raw_mempool:
            fee_rates = [(tx_data['fees']['base'] / tx_data['vsize']) * SATS_PER_BTC for tx_data in raw_mempool.values()
                         if tx_data['vsize'] > 0]
            if fee_rates:
                fee_rates.sort()
                data['min_fee_rate'] = round(min(fee_rates), 4)
                data['max_fee_rate'] = round(max(fee_rates), 4)
                data['avg_fee_rate'] = round(sum(fee_rates) / len(fee_rates), 4)
                data['median_fee_rate'] = round(statistics.median(fee_rates), 4)
                data['fee_rate_10th'] = round(fee_rates[len(fee_rates) // 10] if len(fee_rates) > 10 else 0, 4)
                data['fee_rate_90th'] = round(fee_rates[int(len(fee_rates) * 0.9)] if len(fee_rates) > 10 else 0, 4)
                data['fee_rate_std'] = round(statistics.stdev(fee_rates) if len(fee_rates) > 1 else 0, 4)
                data['total_fee'] = round(
                    sum(tx_data['fees']['base'] for tx_data in raw_mempool.values()) * SATS_PER_BTC,
                    4)  # Convert to satoshis

                data['mempool_fee_histogram'] = create_fee_histogram(fee_rates)
                logging.debug(f"Fee rates (sat/vB): {fee_rates[:10]}... (showing first 10)")
                logging.debug(f"Created histogram: {data['mempool_fee_histogram']}")

                # Enhanced checks for mempool_min_fee
                if data['mempool_min_fee'] > 1000:
                    logging.error(f"Extremely high mempool_min_fee detected: {data['mempool_min_fee']} sat/vB")
                    # Calculate a fallback value based on the lowest fee rate in the mempool
                    fallback_min_fee = data['min_fee_rate'] * 1.1  # 10% higher than the lowest fee rate
                    logging.warning(f"Using fallback mempool min fee: {fallback_min_fee} sat/vB")
                    data['mempool_min_fee'] = round(fallback_min_fee, 4)
                elif data['mempool_min_fee'] > data['median_fee_rate'] * 5:
                    logging.warning(f"Unusually high mempool_min_fee detected: {data['mempool_min_fee']} sat/vB. "
                                    f"Median fee rate is {data['median_fee_rate']} sat/vB.")

                if data['mempool_min_fee'] > data['min_fee_rate'] * 10:
                    logging.warning(f"mempool_min_fee ({data['mempool_min_fee']} sat/vB) is much higher than "
                                    f"the lowest fee rate in the mempool ({data['min_fee_rate']} sat/vB)")

        data['bitcoin_price_usd'] = get_bitcoin_price()

    except Exception as e:
        logging.error(f"Error in get_block_and_mempool_data: {str(e)}")

    logging.debug(f"Collected data: {data}")
    return data


def main():
    rpc_connection = None
    csv_file = '/mnt/volume_nyc1_01/bitcoin_data/real_time.csv'
    csv_fields = ['timestamp', 'block_height', 'tx_count', 'mempool_size_mb',
                  'min_fee_rate', 'max_fee_rate', 'avg_fee_rate', 'median_fee_rate',
                  'fee_rate_10th', 'fee_rate_90th', 'fee_rate_std', 'block_time',
                  'difficulty', 'hash_rate', 'mempool_min_fee', 'total_fee', 'mempool_usage',
                  'transaction_count', 'block_weight', 'block_version', 'block_interval',
                  'block_median_fee_rate', 'time_since_last_block', 'mempool_fee_histogram',
                  'bitcoin_price_usd']

    file_exists = os.path.isfile(csv_file)
    is_empty = os.stat(csv_file).st_size == 0 if file_exists else True

    with open(csv_file, 'a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=csv_fields)

        if is_empty:
            writer.writeheader()

        last_block_height = None
        last_block_time = None

        while True:
            try:
                if rpc_connection is None:
                    rpc_connection = connect_to_bitcoin_core()

                if rpc_connection:
                    try:
                        current_height = safe_rpc_call(rpc_connection, 'getblockcount')
                        logging.info(f"Current block height: {current_height}")
                    except:
                        logging.warning("RPC connection lost. Reconnecting...")
                        rpc_connection = connect_to_bitcoin_core()
                        continue

                    if rpc_connection and (last_block_height is None or current_height > last_block_height):
                        data = get_block_and_mempool_data(rpc_connection, current_height, last_block_time)

                        # Additional check before writing data
                        if data['mempool_min_fee'] > 1000:
                            logging.error(
                                f"Skipping data write due to extremely high mempool_min_fee: {data['mempool_min_fee']} sat/vB")
                            continue  # Skip to the next iteration without writing data

                        writer.writerow(data)
                        file.flush()
                        print(f"Data collected and saved for block height: {current_height}")
                        logging.info(f"Data collected and saved for block height: {current_height}")
                        last_block_height = current_height
                        last_block_time = data['block_time']
                    else:
                        logging.debug("No new block. Waiting...")
                        time.sleep(10)  # Wait 10 seconds before checking for a new block
                else:
                    print("No connection to Bitcoin Core")
                    logging.error("No connection to Bitcoin Core")
                    time.sleep(60)  # Wait a minute before retrying

            except KeyboardInterrupt:
                print("Data collection stopped by user.")
                break
            except Exception as e:
                print(f"An error occurred in main loop: {str(e)}")
                logging.error(f"An error occurred in main loop: {str(e)}")
                rpc_connection = None
                time.sleep(60)  # Wait a minute before retrying


if __name__ == "__main__":
    main()