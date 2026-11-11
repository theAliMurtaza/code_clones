# Linux C Clone Demo

This folder contains realistic Linux kernel C files demonstrating code clone detection:

1. `mm_alloc.c` vs `driver_helper.c`:
   - `reset_device` <-> `reset_device`: **Type-1 clone** (exact copy, 100% token similarity)
   - `alloc_kernel_buffer` <-> `allocate_driver_mem`: **Type-2 clone** (same structure, renamed identifiers `size`/`sz`, `flags`/`fl`, `ptr`/`p`)

2. `mm_alloc.c` vs `kzalloc_variant.c`:
   - `alloc_kernel_buffer` <-> `get_zeroed_memory`: **Type-4 semantic clone** (different syntax/calls: `kmalloc + memset` vs `kzalloc`, same outcome)
