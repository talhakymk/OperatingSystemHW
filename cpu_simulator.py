from enum import Enum
import time
from typing import List, Dict, Union

class CPUMode(Enum):
    KERNEL = 0
    USER = 1

class CPU:
    def __init__(self, memory_size: int = 11000, debug_level: int = 0):
        self.memory: List[Union[int, str]] = [0] * memory_size
        self.halted = False
        self.mode = CPUMode.KERNEL
        self.blocked_cycles = 0
        self.instruction_addresses = set()  # Track instruction locations
        self.data_addresses = set()  # Track data locations
        self.debug_level = debug_level
        self.instruction_counter = 0
        self.last_pc = -1  # Track last PC for loop detection
        self.same_pc_count = 0  # Count how many times we've seen the same PC
        
    def is_halted(self) -> bool:
        return self.halted
        
    def get_pc(self) -> int:
        return self.memory[0]
        
    def set_pc(self, value: int):
        if value >= len(self.memory):
            print(f"Error: Program Counter {value} out of memory bounds")
            self.halted = True
            return
        self.memory[0] = value
        
    def increment_pc(self):
        self.set_pc(self.get_pc() + 1)
        
    def get_sp(self) -> int:
        return self.memory[1]
        
    def set_sp(self, value: int):
        if value >= len(self.memory):
            print(f"Error: Stack Pointer {value} out of memory bounds")
            self.halted = True
            return
        self.memory[1] = value
        
    def check_user_mode_access(self, address: int):
        if address >= len(self.memory):
            print(f"Error: Memory access {address} out of bounds")
            self.halted = True
            return False
        if self.mode == CPUMode.USER and address < 1000:
            print(f"Memory protection violation: User mode tried to access address {address}")
            self.halted = True
            return False
        return True
        
    def get_memory_value(self, address: int, allow_instruction: bool = False) -> int:
        """Safely get an integer value from memory."""
        if not self.check_user_mode_access(address):
            return 0
            
        # Doğrudan memory dizisine bak
        raw_value = self.memory[address]
        
        # Debug
        if hasattr(self, 'debug_level') and self.debug_level >= 3:
            print(f"get_memory_value({address}): raw_value={raw_value}")
        
        value = raw_value
        if isinstance(value, str):
            if not allow_instruction and address in self.instruction_addresses:
                print(f"Error: Trying to read instruction as data at address {address}")
                self.halted = True
                return 0
            try:
                return int(value)
            except ValueError:
                if not allow_instruction:
                    print(f"Error: Expected number at address {address}, got '{value}'")
                    self.halted = True
                return 0
        return value
        
    def set_memory_value(self, address: int, value: Union[int, str]):
        """Safely set a value in memory."""
        if address >= len(self.memory):
            print(f"Error: Memory address {address} out of bounds")
            self.halted = True
            return
            
        # Don't check user mode for kernel operations during initialization
        if self.mode == CPUMode.USER and address < 1000:
            print(f"Memory protection violation: User mode tried to access address {address}")
            self.halted = True
            return
            
        # Clear previous memory type tracking
        self.instruction_addresses.discard(address)
        self.data_addresses.discard(address)
        
        # Update memory and track type
        self.memory[address] = value
        if isinstance(value, str):
            self.instruction_addresses.add(address)
        else:
            self.data_addresses.add(address)
            
    def update_thread_state(self):
        """Update the current thread's state in the thread table."""
        current_thread = self.get_memory_value(4)  # Get current thread ID
        if current_thread <= 0:
            return
            
        thread_table_base = self.get_memory_value(6)  # Get thread table base
        thread_offset = (current_thread - 1) * 20  # Each thread entry is 20 bytes
        thread_base = thread_table_base + thread_offset
        
        # Update thread's PC - make sure this is the current PC
        self.set_memory_value(thread_base + 4, self.get_pc())
        # Update thread's SP - make sure this is the current SP
        self.set_memory_value(thread_base + 5, self.get_sp())
        # Update thread's instruction count
        total_instructions = self.get_memory_value(3)
        self.set_memory_value(thread_base + 2, total_instructions)
        
    def switch_thread(self, thread_id):
        """Switch execution to the specified thread."""
        if hasattr(self, 'debug_level') and self.debug_level >= 2:
            print(f"Switching to thread {thread_id}")
        
        # Save current thread state if a thread is running
        current_thread = self.get_memory_value(4)
        thread_table_base = self.get_memory_value(6)
        
        if current_thread > 0:
            current_thread_base = thread_table_base + (current_thread - 1) * 20
            # Save PC
            self.set_memory_value(current_thread_base + 4, self.get_pc())  # PC değerini +4 indeksine kaydet
            # Save SP 
            self.set_memory_value(current_thread_base + 5, self.get_sp())  # SP değerini +5 indeksine kaydet
            # Save registers if they exist
            if hasattr(self, 'registers'):
                for i in range(8):
                    self.set_memory_value(current_thread_base + 10 + i, self.registers[i])
        
        # Set the new thread as current
        self.set_memory_value(4, thread_id)
        
        if thread_id > 0:
            # Load the new thread state
            new_thread_base = thread_table_base + (thread_id - 1) * 20
            # Load PC - önemli: +4 indeksindeki PC değerini al (yanlışlıkla +1 kullanıldı gibi görünüyor)
            new_pc = self.get_memory_value(new_thread_base + 4)  # +4 indeksindeki PC değerini al
            self.set_pc(new_pc)
            
            # Load SP - önemli: +5 indeksindeki SP değerini al
            new_sp = self.get_memory_value(new_thread_base + 5)  # +5 indeksindeki SP değerini al
            self.set_sp(new_sp)
            
            # Load registers if they exist
            if hasattr(self, 'registers'):
                for i in range(8):
                    self.registers[i] = self.get_memory_value(new_thread_base + 10 + i)
            
            # Set thread state to RUNNING (2)
            self.set_memory_value(new_thread_base + 3, 2)
            
            if hasattr(self, 'debug_level') and self.debug_level >= 2:
                print(f"Thread {thread_id} now running at PC={self.get_pc()}")
        else:
            # No thread to run
            self.halted = True

    def find_next_ready_thread(self):
        """Find the next thread in READY state (state=1) and return its ID."""
        current_thread = self.get_memory_value(4)
        max_threads = 3  # We have 3 threads
        thread_table_base = self.get_memory_value(6)
        
        # Try threads after current thread
        for i in range(current_thread + 1, max_threads + 1):
            thread_base = thread_table_base + (i - 1) * 20
            state = self.get_memory_value(thread_base + 3)
            if state == 1:  # Ready
                return i
                
        # Try threads before current thread
        for i in range(1, current_thread):
            thread_base = thread_table_base + (i - 1) * 20
            state = self.get_memory_value(thread_base + 3)
            if state == 1:  # Ready
                return i
                
        return 0  # No ready thread found
    
    def find_next_ready_thread(self):
        """Find the next ready thread (state = 1)."""
        thread_table_base = self.get_memory_value(6)
        thread_count = 3  # Toplam thread sayısı (örneğin)
        
        for i in range(1, thread_count + 1):
            thread_base = thread_table_base + (i - 1) * 20
            thread_id = self.get_memory_value(thread_base + 0)
            thread_state = self.get_memory_value(thread_base + 3)
            
            if thread_id > 0 and thread_state == 1:  # Thread exists and is ready
                return thread_id
        
        return 0  # No ready thread found
            
    def execute(self):
        # Infinite loop detection - more sophisticated version
        if not hasattr(self, 'instruction_counter'):
            self.instruction_counter = 0
        self.instruction_counter += 1
        
        current_pc = self.get_pc()
        if current_pc == self.last_pc:
            self.same_pc_count += 1
            if self.same_pc_count > 100:  # If we're stuck at the same PC for too long
                print(f"Warning: Stuck at PC={current_pc} for {self.same_pc_count} cycles.")
                print("Memory state around PC:")
                for i in range(max(0, current_pc-5), min(len(self.memory), current_pc+6)):
                    print(f"Memory[{i}] = {self.memory[i]}")
                    
                # Try to recover by switching to next thread
                current_thread = self.get_memory_value(4)
                if current_thread > 0:
                    thread_table_base = self.get_memory_value(6)
                    thread_base = thread_table_base + (current_thread - 1) * 20
                    # Mark current thread as inactive
                    self.set_memory_value(thread_base + 3, 0)
                    # Update active thread count
                    active_threads = self.get_memory_value(5)
                    self.set_memory_value(5, active_threads - 1)
                    
                # Try to switch to next thread
                next_thread = self.find_next_ready_thread()
                if next_thread > 0:
                    print(f"Switching from stuck thread {current_thread} to thread {next_thread}")
                    self.mode = CPUMode.KERNEL
                    self.switch_thread(next_thread)
                    self.same_pc_count = 0
                    self.last_pc = -1
                    return
                else:
                    print("No other threads available, halting.")
                    self.halted = True
                    return
        else:
            self.same_pc_count = 0
            self.last_pc = current_pc
            
        if self.instruction_counter > 100000:  # Overall instruction limit
            print("Warning: Maximum instruction count reached. Halting.")
            print(f"Current thread: {self.get_memory_value(4)}, PC: {self.get_pc()}")
            self.halted = True
            return
            
        if self.blocked_cycles > 0:
            self.blocked_cycles -= 1
            current_count = self.get_memory_value(3, allow_instruction=True)
            self.set_memory_value(3, current_count + 1)  # Increment instruction count
            return
            
        pc = self.get_pc()
        if pc >= len(self.memory) or pc < 0 or not isinstance(self.memory[pc], str) or not self.memory[pc].strip():
            if self.debug_level >= 1:
                print(f"Warning: No valid instruction at address {pc}, switching threads")
            
            # PC geçersiz, thread'i durdurup diğerine geç
            current_thread = self.get_memory_value(4)
            if current_thread > 0:
                thread_table_base = self.get_memory_value(6)
                thread_base = thread_table_base + (current_thread - 1) * 20
                # Thread durumunu inactive (0) olarak işaretle
                self.set_memory_value(thread_base + 3, 0)
            
            # Yeni thread'e geçiş yap
            next_thread = self.find_next_ready_thread()
            if next_thread > 0:
                self.switch_thread(next_thread)
            else:
                self.halted = True
            
            return
                
        instruction = self.memory[pc]
        if not isinstance(instruction, str):
            if instruction == 0:  # Uninitialized memory
                print(f"Error: No instruction at address {pc}")
            else:
                print(f"Error: Invalid instruction at {pc}: {instruction}")
            self.halted = True
            return
            
        # Parse instruction
        parts = instruction.strip().split()
        if not parts:
            print(f"Error: Empty instruction at {pc}")
            self.halted = True
            return
            
        opcode = parts[0]
        
        try:
            if opcode == "SET":
                value, addr = int(parts[1]), int(parts[2])
                self.set_memory_value(addr, value)
                    
            elif opcode == "CPY":
                addr1, addr2 = int(parts[1]), int(parts[2])
                value = self.get_memory_value(addr1, allow_instruction=True)
                
                # Debug çıktısı ekleyin
                if hasattr(self, 'debug_level') and self.debug_level >= 3:
                    print(f"CPY at PC={self.get_pc()}: Memory[{addr1}]={value} to Memory[{addr2}]")
                    
                self.set_memory_value(addr2, value)
                    
            elif opcode == "CPYI":
                addr1, addr2 = int(parts[1]), int(parts[2])
                indirect_addr = self.get_memory_value(addr1, allow_instruction=True)
                value = self.get_memory_value(indirect_addr, allow_instruction=True)
                self.set_memory_value(addr2, value)
                    
            elif opcode == "ADD":
                addr, value = int(parts[1]), int(parts[2])
                current = self.get_memory_value(addr, allow_instruction=True)
                self.set_memory_value(addr, current + value)
                    
            elif opcode == "ADDI":
                addr1, addr2 = int(parts[1]), int(parts[2])
                value1 = self.get_memory_value(addr1, allow_instruction=True)
                value2 = self.get_memory_value(addr2, allow_instruction=True)
                self.set_memory_value(addr1, value1 + value2)
                    
            elif opcode == "SUBI":
                addr1, addr2 = int(parts[1]), int(parts[2])
                value1 = self.get_memory_value(addr1, allow_instruction=True)
                value2 = self.get_memory_value(addr2, allow_instruction=True)
                result = value1 - value2
                
                if hasattr(self, 'debug_level') and self.debug_level >= 3:
                    print(f"SUBI at PC={self.get_pc()}: Memory[{addr1}]={value1} - Memory[{addr2}]={value2} = {result}")
                    print(f"  Setting Memory[{addr1}] = {result}")  # addr1'e yazıldığını belirt
                
                # Değeri addr1'e yaz (addr2'ye değil)
                self.set_memory_value(addr1, result)
                
                if hasattr(self, 'debug_level') and self.debug_level >= 3:
                    check = self.get_memory_value(addr1, allow_instruction=True)
                    print(f"  Verification: Memory[{addr1}] = {check}")
                                
            elif opcode == "JIF":
                addr, target = int(parts[1]), int(parts[2])
                value = self.get_memory_value(addr, allow_instruction=True)
                
                if hasattr(self, 'debug_level') and self.debug_level >= 3:
                    print(f"JIF at PC={self.get_pc()}: Memory[{addr}]={value}, Target={target}")
                    print(f"  Direct memory access: Memory[{addr}]={self.memory[addr]}")
                
                if value <= 0:
                    if hasattr(self, 'debug_level') and self.debug_level >= 3:
                        print(f"  Jumping to {target} because {value} <= 0")
                    
                    # PC'yi güncelle
                    self.set_pc(target)
                    
                    # Thread durumunu güncelle (önemli!)
                    self.update_thread_state()
                    
                    return
                        
            elif opcode == "PUSH":
                addr = int(parts[1])
                value = self.get_memory_value(addr, allow_instruction=True)
                sp = self.get_sp()
                self.set_memory_value(sp, value)
                self.set_sp(sp - 1)
                    
            elif opcode == "POP":
                addr = int(parts[1])
                sp = self.get_sp() + 1
                self.set_sp(sp)
                value = self.get_memory_value(sp, allow_instruction=True)
                self.set_memory_value(addr, value)
                    
            elif opcode == "CALL":
                target = int(parts[1])
                sp = self.get_sp()
                self.set_memory_value(sp, pc + 1)
                self.set_sp(sp - 1)
                self.update_thread_state()  # Update state before call
                self.set_pc(target)
                return
                
            elif opcode == "RET":
                sp = self.get_sp() + 1
                self.set_sp(sp)
                return_addr = self.get_memory_value(sp, allow_instruction=True)
                self.update_thread_state()  # Update state before return
                self.set_pc(return_addr)
                return
                
            elif opcode == "HLT":
                # Set thread state to inactive (0)
                current_thread = self.get_memory_value(4)
                if current_thread > 0:
                    thread_table_base = self.get_memory_value(6)
                    thread_offset = (current_thread - 1) * 20
                    thread_base = thread_table_base + thread_offset
                    self.set_memory_value(thread_base + 3, 0)  # Set state to inactive
                    
                # Decrement active thread count
                active_threads = self.get_memory_value(5)
                self.set_memory_value(5, active_threads - 1)
                
                if active_threads <= 1:
                    self.halted = True
                else:
                    # Switch to scheduler
                    self.mode = CPUMode.KERNEL
                    self.set_pc(50)  # Jump to scheduler
                return
                
            elif opcode == "USER":
                addr = int(parts[1])
                self.mode = CPUMode.USER
                jump_addr = self.get_memory_value(addr, allow_instruction=True)
                self.update_thread_state()  # Update state before mode switch
                self.set_pc(jump_addr)
                return
                
            elif opcode == "SYSCALL":
                syscall_type = parts[1]
                if syscall_type == "PRN":
                    addr = int(parts[2])
                    value = self.get_memory_value(addr, allow_instruction=True)
                    print(f"Output: {value}")
                    self.blocked_cycles = 100
                elif syscall_type == "HLT":
                    # Current thread is done, set it to inactive
                    current_thread = self.get_memory_value(4)
                    if current_thread > 0:
                        thread_table_base = self.get_memory_value(6)
                        thread_base = thread_table_base + (current_thread - 1) * 20
                        self.set_memory_value(thread_base + 3, 0)  # Set state to inactive
                        self.update_thread_state()  # Update final state
                        
                        if hasattr(self, 'debug_level') and self.debug_level > 1:
                            print(f"Thread {current_thread} halted")
                        
                    # Decrease active thread count
                    active_threads = self.get_memory_value(5)
                    self.set_memory_value(5, active_threads - 1)
                    
                    # Find next ready thread
                    next_thread = self.find_next_ready_thread()
                    
                    if next_thread > 0:
                        # Switch to next thread
                        self.mode = CPUMode.KERNEL
                        self.switch_thread(next_thread)
                        
                        if hasattr(self, 'debug_level') and self.debug_level > 0:
                            print(f"Switched to thread {next_thread} at PC={self.get_pc()}")
                    else:
                        # No more threads to run
                        self.halted = True
                    return
                elif syscall_type == "YIELD":
                    self.mode = CPUMode.KERNEL
                    self.update_thread_state()  # Update state before yield
                    self.set_memory_value(2, 1)  # Set syscall result
                    self.set_pc(50)  # Jump to scheduler
                    return
                    
            else:
                print(f"Error: Unknown instruction {opcode} at {pc}")
                self.halted = True
                return
                
        except (IndexError, ValueError) as e:
            print(f"Error executing instruction at {pc}: {e}")
            self.halted = True
            return
            
        self.increment_pc()
        current_count = self.get_memory_value(3, allow_instruction=True)
        self.set_memory_value(3, current_count + 1)  # Increment instruction count