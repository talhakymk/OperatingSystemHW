from enum import Enum
import time
from typing import List, Dict, Union

class CPUMode(Enum):
    KERNEL = 0
    USER = 1

class CPU:
    def __init__(self, memory_size: int = 11000):
        self.memory: List[Union[int, str]] = [0] * memory_size
        self.halted = False
        self.mode = CPUMode.KERNEL
        self.blocked_cycles = 0
        self.instruction_addresses = set()  # Track instruction locations
        self.data_addresses = set()  # Track data locations
        
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
            
        value = self.memory[address]
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
        
        # Update thread's PC
        self.set_memory_value(thread_base + 4, self.get_pc())
        # Update thread's SP
        self.set_memory_value(thread_base + 5, self.get_sp())
        # Update thread's instruction count
        total_instructions = self.get_memory_value(3)
        self.set_memory_value(thread_base + 2, total_instructions)
        
    def switch_thread(self, new_thread_id):
        """Switch to a new thread."""
        if new_thread_id <= 0:
            return
            
        current_thread = self.get_memory_value(4)
        thread_table_base = self.get_memory_value(6)
        
        # Set current thread to ready if it exists and is running
        if current_thread > 0:
            old_thread_base = thread_table_base + (current_thread - 1) * 20
            old_state = self.get_memory_value(old_thread_base + 3)
            if old_state == 2:  # If running
                self.set_memory_value(old_thread_base + 3, 1)  # Set to ready
                self.update_thread_state()  # Save current PC and SP
                
        # Update current thread ID
        self.set_memory_value(4, new_thread_id)
        
        # Get new thread's info
        new_thread_base = thread_table_base + (new_thread_id - 1) * 20
        new_state = self.get_memory_value(new_thread_base + 3)
        
        if new_state == 1:  # If ready
            # Get saved PC and SP
            new_pc = self.get_memory_value(new_thread_base + 4)
            new_sp = self.get_memory_value(new_thread_base + 5)
            
            # Set new PC and SP
            self.set_pc(new_pc)
            self.set_sp(new_sp)
            
            # Set new thread state to running
            self.set_memory_value(new_thread_base + 3, 2)
            
    def find_next_ready_thread(self):
        """Find the next ready thread to run."""
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
        
    def execute(self):
        if self.blocked_cycles > 0:
            self.blocked_cycles -= 1
            current_count = self.get_memory_value(3)
            self.set_memory_value(3, current_count + 1)
            return
            
        pc = self.get_pc()
        if pc >= len(self.memory):
            print(f"Error: Program Counter {pc} out of memory bounds")
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
                self.set_memory_value(addr2, value1 - value2)
                    
            elif opcode == "JIF":
                addr, target = int(parts[1]), int(parts[2])
                value = self.get_memory_value(addr, allow_instruction=True)
                if value <= 0:
                    self.update_thread_state()
                    self.set_pc(target)
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
                self.update_thread_state()
                self.set_pc(target)
                return
                
            elif opcode == "RET":
                sp = self.get_sp() + 1
                self.set_sp(sp)
                return_addr = self.get_memory_value(sp, allow_instruction=True)
                self.update_thread_state()
                self.set_pc(return_addr)
                return
                
            elif opcode == "HLT":
                # Set thread state to inactive
                current_thread = self.get_memory_value(4)
                if current_thread > 0:
                    thread_table_base = self.get_memory_value(6)
                    thread_base = thread_table_base + (current_thread - 1) * 20
                    self.set_memory_value(thread_base + 3, 0)  # Set state to inactive
                    self.update_thread_state()  # Update final state
                    
                # Decrement active thread count
                active_threads = self.get_memory_value(5)
                self.set_memory_value(5, active_threads - 1)
                
                # Find next ready thread
                next_thread = self.find_next_ready_thread()
                if next_thread > 0:
                    self.mode = CPUMode.KERNEL
                    self.switch_thread(next_thread)
                else:
                    self.halted = True
                return
                
            elif opcode == "USER":
                addr = int(parts[1])
                self.mode = CPUMode.USER
                jump_addr = self.get_memory_value(addr, allow_instruction=True)
                self.update_thread_state()
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
                    # Same as HLT instruction
                    current_thread = self.get_memory_value(4)
                    if current_thread > 0:
                        thread_table_base = self.get_memory_value(6)
                        thread_base = thread_table_base + (current_thread - 1) * 20
                        self.set_memory_value(thread_base + 3, 0)  # Set state to inactive
                        self.update_thread_state()  # Update final state
                        
                    active_threads = self.get_memory_value(5)
                    self.set_memory_value(5, active_threads - 1)
                    
                    next_thread = self.find_next_ready_thread()
                    if next_thread > 0:
                        self.mode = CPUMode.KERNEL
                        self.switch_thread(next_thread)
                    else:
                        self.halted = True
                    return
                elif syscall_type == "YIELD":
                    self.mode = CPUMode.KERNEL
                    self.update_thread_state()
                    next_thread = self.find_next_ready_thread()
                    if next_thread > 0:
                        self.switch_thread(next_thread)
                    self.set_memory_value(2, 1)  # Set syscall result
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
        current_count = self.get_memory_value(3)
        self.set_memory_value(3, current_count + 1)