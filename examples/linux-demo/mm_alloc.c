// Linux kernel memory allocation utility
#include <linux/slab.h>
#include <linux/types.h>

void *alloc_kernel_buffer(size_t size, gfp_t flags)
{
    void *ptr;
    if (!size)
        return NULL;
    ptr = kmalloc(size, flags);
    if (!ptr)
        return NULL;
    memset(ptr, 0, size);
    return ptr;
}

int reset_device(struct net_device *dev)
{
    unsigned long flags;
    spin_lock_irqsave(&dev->lock, flags);
    writel(0, dev->base + 0x10);
    spin_unlock_irqrestore(&dev->lock, flags);
    return 0;
}
