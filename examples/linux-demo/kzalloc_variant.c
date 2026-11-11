// Alternative memory allocation helper (Type-4 semantic clone)
#include <linux/slab.h>
#include <linux/types.h>

void *get_zeroed_memory(size_t size, gfp_t flags)
{
    void *buf;
    if (size == 0)
        return NULL;
    buf = kzalloc(size, flags);
    return buf;
}
