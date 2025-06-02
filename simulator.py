import sys
import tty
import termios

def wait_key():
    """Wait for a key press on Linux."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

from cpu_simulator import CPU
from parser import Parser

def print_memory_state(cpu: CPU, file=sys.stderr):
    """Print the current state of memory to stderr."""
    print("\nMemory State:", file=file)
    print("Registers:", file=file)
    print(f"PC: {cpu.memory[0]}", file=file)
    print(f"SP: {cpu.memory[1]}", file=file)
    print(f"Syscall Result: {cpu.memory[2]}", file=file)
    print(f"Instructions Executed: {cpu.memory[3]}", file=file)
    print(f"Current Thread: {cpu.memory[4]}", file=file)
    print(f"Active Threads: {cpu.memory[5]}", file=file)
    
    # Print thread table
    thread_table_base = cpu.memory[6]
    print("\nThread Table:", file=file)
    for i in range(3):  # We have 3 threads
        base = thread_table_base + i * 20
        print(f"\nThread {i+1}:", file=file)
        print(f"  ID: {cpu.memory[base]}", file=file)
        print(f"  Start Time: {cpu.memory[base+1]}", file=file)
        print(f"  Instructions: {cpu.memory[base+2]}", file=file)
        print(f"  State: {cpu.memory[base+3]}", file=file)
        print(f"  PC: {cpu.memory[base+4]}", file=file)
        print(f"  SP: {cpu.memory[base+5]}", file=file)

def print_thread_state(cpu: CPU, file=sys.stderr):
    """Print the current state of threads to stderr."""
    thread_table_base = cpu.memory[6]
    print("\nThread States:", file=file)
    for i in range(3):  # We have 3 threads
        base = thread_table_base + i * 20
        state_map = {0: "inactive", 1: "ready", 2: "running", 3: "blocked"}
        state = state_map.get(cpu.memory[base+3], "unknown")
        print(f"Thread {i+1}: {state} (PC: {cpu.memory[base+4]})", file=file)

def main():
    if len(sys.argv) < 2:
        print("Usage: python simulator.py <filename> [-D debug_level]")
        sys.exit(1)
        
    filename = sys.argv[1]
    debug_level = 0
    
    if len(sys.argv) > 2 and sys.argv[2] == "-D":
        debug_level = int(sys.argv[3])
        
    # Initialize CPU and parser
    cpu = CPU(debug_level=debug_level)
    parser = Parser()
    
    try:
        # Load program
        parser.parse_file(filename)
        parser.load_into_memory(cpu)
        
        # Main execution loop
        while not cpu.is_halted():
            if debug_level == 1:
                print_memory_state(cpu)
            elif debug_level == 2:
                print_memory_state(cpu)
                print("\nPress any key to continue...")
                wait_key()
            elif debug_level == 3:
                old_thread = cpu.memory[4]
                cpu.execute()
                new_thread = cpu.memory[4]
                if old_thread != new_thread:
                    print_thread_state(cpu)
                continue
                
            cpu.execute()
            
        # Print final memory state
        print_memory_state(cpu)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 