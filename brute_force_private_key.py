import itertools
import multiprocessing
import time
from eth_keys import keys
from eth_utils import keccak, to_checksum_address

hex_chars = "0123456789abcdef"

log_lock = multiprocessing.Lock()

# Decrypt the private key to get the public key
def private_key_to_address(private_key_hex):
    private_key_bytes = bytes.fromhex(private_key_hex)
    public_key = keys.PrivateKey(private_key_bytes).public_key
    address = keccak(public_key.to_bytes())[12:].hex()
    return to_checksum_address(address)

# Worker function for multiprocessing
def worker(args):
    prefix, PKa, missing_x, missing_y, V, start_time, total_tasks, found_event, queue = args
    total_combinations = len(hex_chars) ** missing_y  # Total number of combinations to check of y
    checked = 0  # Number of checked combinations

    for suffix in itertools.product(hex_chars, repeat=missing_y):
        
        if found_event.is_set():
            return None
        
        test_PK = ''.join(prefix) + PKa + ''.join(suffix)
        checked += 1

        # Update progress each 1000 checks
        if checked % 1000 == 0:
            elapsed_time = time.time() - start_time
            avg_time_per_check = elapsed_time / (total_tasks - total_combinations + checked)
            remaining_time = avg_time_per_check * (total_combinations - checked)
            percent_done = ((total_tasks - total_combinations + checked) / total_tasks) * 100
            
            with log_lock:
                queue.put(f"🔹 {checked}/{total_combinations} ({percent_done:.2f}%) tổ hợp, còn ~{remaining_time:.2f}s")

        # Check if the private key is correct
        if private_key_to_address(test_PK) == V:
            print(f"✅ Tìm thấy! Private Key: {test_PK} tại checked: {checked}")
            
            found_event.set()
            return test_PK
    return None

def log_listener(queue):
    while True:
        msg = queue.get()
        if msg == "DONE":
            break
        print(msg)

# Found missing private key using multiprocessing
def find_missing_private_key(PKa, V):
    """ Tìm kiếm Private Key bị mất bằng multiprocessing """
    missing_total = 64 - len(PKa)
    total_tasks = len(hex_chars) ** missing_total  # Total number of combinations to check
    
    print(f"Missing total: {missing_total}")
    
    with multiprocessing.Manager() as manager:
        found_event = manager.Event()
        queue = manager.Queue()
        
        log_process = multiprocessing.Process(target=log_listener, args=(queue,))
        log_process.start()

        for missing_x in range(missing_total + 1):
            missing_y = missing_total - missing_x
            print(f"🚀 Thử missing_x={missing_x}, missing_y={missing_y}")

            # Split prefixes for multiprocessing
            prefixes = list(itertools.product(hex_chars, repeat=missing_x))
            num_workers = min(multiprocessing.cpu_count(), len(prefixes))

            with multiprocessing.Pool(num_workers) as pool:
                start_time = time.time()
                args_list = [(prefix, PKa, missing_x, missing_y, V, start_time, total_tasks, found_event, queue) for prefix in prefixes]
                results = pool.map(worker, args_list)

            # Check if private is correct
            for result in results:
                if result:
                    queue.put("DONE")
                    log_process.join()
                    return result
                
        queue.put("DONE")
        log_process.join()
    
    return None

if __name__ == "__main__":
    PKa = input("Enter missing private key: ").strip()
    V = input("Enter wallet address: ").strip()

    # 🔥 Run
    start = time.time()
    found_PK = find_missing_private_key(PKa, V)
    end = time.time()

    if found_PK:
        print(f"🔑 Private Key Tìm Thấy: {found_PK}")
    else:
        print("❌ Không tìm thấy Private Key phù hợp.")

    print(f"⏳ Tổng thời gian chạy: {end - start:.2f} giây")
    