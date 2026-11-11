// Network driver initialization and memory
#include <linux/slab.h>
#include <linux/types.h>

// Type-2 clone of alloc_kernel_buffer (renamed identifiers)
void *allocate_driver_mem(size_t sz, gfp_t fl)
{
    void *p;
    if (!sz)
        return NULL;
    p = kmalloc(sz, fl);
    if (!p)
        return NULL;
    memset(p, 0, sz);
    return p;
}

// Type-1 exact clone of reset_device
int reset_device(struct net_device *dev)
{
    unsigned long flags;
    spin_lock_irqsave(&dev->lock, flags);
    writel(0, dev->base + 0x10);
    spin_unlock_irqrestore(&dev->lock, flags);
    return 0;
}
