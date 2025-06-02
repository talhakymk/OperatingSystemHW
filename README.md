# GTU-C312 CPU Simulator

This is a simulator for the GTU-C312 CPU architecture, implementing a simple operating system with cooperative multitasking and thread management.

## Features

- Custom CPU architecture with a simple instruction set
- Memory-mapped registers and stack
- Operating system with cooperative multitasking
- Thread management with round-robin scheduling
- Three example threads:
  1. Bubble Sort implementation
  2. Linear Search implementation
  3. Custom countdown thread with yielding

## Requirements

- Python 3.6 or higher
- Windows OS (for debug mode 2 which uses msvcrt)

## File Structure

- `cpu_simulator.py`: The CPU implementation with instruction set
- `parser.py`: Parser for GTU-C312 assembly format
- `simulator.py`: Main simulation program with debugging capabilities
- `os_and_threads.txt`: Example OS and thread implementations

## Usage

Run the simulator with:

```bash
python simulator.py os_and_threads.txt [-D debug_level]
```

Debug levels:
- 0: No debug output (default)
- 1: Print memory state after each instruction
- 2: Print memory state and wait for keypress after each instruction
- 3: Print thread state changes during context switches

## GTU-C312 Instruction Set

The CPU supports the following instructions:

- `SET B A`: Set memory location A with value B
- `CPY A1 A2`: Copy from memory A1 to A2
- `CPYI A1 A2`: Indirect copy from memory pointed by A1 to A2
- `ADD A B`: Add value B to memory location A
- `ADDI A1 A2`: Add contents of A2 to A1
- `SUBI A1 A2`: Subtract contents of A2 from A1
- `JIF A C`: Jump to C if memory A ≤ 0
- `PUSH A`: Push memory A to stack
- `POP A`: Pop from stack to memory A
- `CALL C`: Call subroutine at C
- `RET`: Return from subroutine
- `HLT`: Halt CPU
- `USER A`: Switch to user mode and jump to address in A
- `SYSCALL PRN A`: Print memory A
- `SYSCALL HLT`: Halt thread
- `SYSCALL YIELD`: Yield to scheduler

## Memory Map

- 0: Program Counter
- 1: Stack Pointer
- 2: System Call Result
- 3: Instructions Executed
- 4: Current Thread ID
- 5: Number of Active Threads
- 6: Thread Table Base
- 21-999: OS Data and Code
- 1000+: User Thread Space

## Example Program

The included `os_and_threads.txt` demonstrates:
1. OS initialization and thread setup
2. Thread scheduling implementation
3. Three example threads:
   - Bubble sort of 10 numbers
   - Linear search in an array
   - Custom countdown with cooperative yielding

