from typing import List, Dict, Tuple, Union

class Parser:
    def __init__(self):
        self.memory_size = 11000
        self.data_section: List[int] = [0] * self.memory_size
        self.instruction_addresses: Dict[int, str] = {}
        
    def parse_file(self, filename: str) -> None:
        """Parse a GTU-C312 assembly file and store data and instructions."""
        with open(filename, 'r') as f:
            lines = f.readlines()
            
        # First pass: Find section boundaries
        data_start = -1
        data_end = -1
        instruction_start = -1
        instruction_end = -1
        
        for i, line in enumerate(lines):
            if "Begin Data Section" in line:
                data_start = i + 1
            elif "End Data Section" in line:
                data_end = i
            elif "Begin Instruction Section" in line:
                instruction_start = i + 1
            elif "End Instruction Section" in line:
                instruction_end = i
                break
                
        if data_start == -1 or data_end == -1:
            raise ValueError("Data section not properly marked")
        if instruction_start == -1 or instruction_end == -1:
            raise ValueError("Instruction section not properly marked")
            
        # Process data section
        for line in lines[data_start:data_end]:
            line = line.split('#')[0].strip()
            if not line:
                continue
                
            parts = line.split()
            if len(parts) >= 2:
                try:
                    addr = int(parts[0])
                    value = int(parts[1])
                    if addr < self.memory_size:
                        self.data_section[addr] = value
                except ValueError:
                    continue
                    
        # Process instruction section
        for line in lines[instruction_start:instruction_end]:
            line = line.split('#')[0].strip()
            if not line:
                continue
                
            parts = line.split()
            if len(parts) >= 2:
                try:
                    addr = int(parts[0])
                    instruction = ' '.join(parts[1:])
                    if addr < self.memory_size:
                        self.instruction_addresses[addr] = instruction
                except ValueError:
                    continue
                    
    def load_into_memory(self, cpu) -> None:
        """Load the parsed program into CPU memory."""
        # First, load all data
        for addr, value in enumerate(self.data_section):
            if addr not in self.instruction_addresses:  # Don't overwrite instructions with data
                cpu.set_memory_value(addr, value)
                
        # Then load all instructions in order
        for addr in sorted(self.instruction_addresses.keys()):
            instruction = self.instruction_addresses[addr]
            cpu.set_memory_value(addr, instruction)
            
    def print_memory_layout(self):
        """Debug function to print memory layout."""
        print("\nData Section:")
        for addr, value in enumerate(self.data_section):
            if value != 0:
                print(f"Data[{addr}] = {value}")
                
        print("\nInstruction Section:")
        for addr in sorted(self.instruction_addresses.keys()):
            print(f"Instruction[{addr}] = {self.instruction_addresses[addr]}") 