#include <linux/module.h>
#define INCLUDE_VERMAGIC
#include <linux/build-salt.h>
#include <linux/elfnote-lto.h>
#include <linux/export-internal.h>
#include <linux/vermagic.h>
#include <linux/compiler.h>

#ifdef CONFIG_UNWINDER_ORC
#include <asm/orc_header.h>
ORC_HEADER;
#endif

BUILD_SALT;
BUILD_LTO_INFO;

MODULE_INFO(vermagic, VERMAGIC_STRING);
MODULE_INFO(name, KBUILD_MODNAME);

__visible struct module __this_module
__section(".gnu.linkonce.this_module") = {
	.name = KBUILD_MODNAME,
	.init = init_module,
#ifdef CONFIG_MODULE_UNLOAD
	.exit = cleanup_module,
#endif
	.arch = MODULE_ARCH_INIT,
};

#ifdef CONFIG_RETPOLINE
MODULE_INFO(retpoline, "Y");
#endif



static const struct modversion_info ____versions[]
__used __section("__versions") = {
	{ 0xe141779d, "tty_port_close" },
	{ 0xac4da666, "tty_port_open" },
	{ 0x6e85e9f2, "usb_deregister" },
	{ 0x8e17b3ae, "idr_destroy" },
	{ 0x51695248, "usb_ifnum_to_if" },
	{ 0x32c7db13, "usb_get_intf" },
	{ 0xb8f11603, "idr_alloc" },
	{ 0xd9a5ea54, "__init_waitqueue_head" },
	{ 0xcefb0c9f, "__mutex_init" },
	{ 0x6d71daa8, "tty_port_init" },
	{ 0xd16036ab, "usb_alloc_coherent" },
	{ 0xfdfb17fe, "usb_alloc_urb" },
	{ 0xef0b85f, "_dev_info" },
	{ 0x7c298c66, "usb_register_dev" },
	{ 0xd9d7bd54, "usb_driver_claim_interface" },
	{ 0x3a043631, "tty_port_register_device" },
	{ 0xb5bcb52f, "usb_driver_release_interface" },
	{ 0x53ff5165, "usb_free_urb" },
	{ 0x56c3abe4, "usb_free_coherent" },
	{ 0xcd9c13a3, "tty_termios_hw_change" },
	{ 0xbd394d8, "tty_termios_baud_rate" },
	{ 0xf0fdf6cb, "__stack_chk_fail" },
	{ 0xd36f4a9c, "__tty_insert_flip_string_flags" },
	{ 0x3b412863, "tty_flip_buffer_push" },
	{ 0x20978fb9, "idr_find" },
	{ 0x296695f, "refcount_warn_saturate" },
	{ 0x7602e53, "seq_puts" },
	{ 0x515554ed, "seq_printf" },
	{ 0x656e4a6e, "snprintf" },
	{ 0x8801b957, "seq_putc" },
	{ 0xfd28bb97, "tty_standard_install" },
	{ 0x2d3385d3, "system_wq" },
	{ 0xf3b0231c, "queue_work_on" },
	{ 0x6b10bee1, "_copy_to_user" },
	{ 0xb2fd5ceb, "__put_user_4" },
	{ 0x167e7f9d, "__get_user_1" },
	{ 0x8f9c199c, "__get_user_2" },
	{ 0x5df37f33, "pcpu_hot" },
	{ 0xaad8c7d6, "default_wake_function" },
	{ 0x4afb2238, "add_wait_queue" },
	{ 0x1000e51, "schedule" },
	{ 0x37110088, "remove_wait_queue" },
	{ 0xc6cbbc89, "capable" },
	{ 0x14d1ab45, "usb_deregister_dev" },
	{ 0xb696ca11, "tty_port_tty_get" },
	{ 0x43f4843d, "tty_vhangup" },
	{ 0xcbf39f11, "tty_kref_put" },
	{ 0x5dd1b43e, "tty_unregister_device" },
	{ 0xbdfb6dbb, "__fentry__" },
	{ 0x34db050b, "_raw_spin_lock_irqsave" },
	{ 0xd35cce70, "_raw_spin_unlock_irqrestore" },
	{ 0x5b8239ca, "__x86_return_thunk" },
	{ 0xf1f19505, "usb_submit_urb" },
	{ 0x50e6ad9, "_dev_err" },
	{ 0x72a4c109, "usb_autopm_put_interface_async" },
	{ 0xb9590621, "usb_autopm_get_interface_no_resume" },
	{ 0xf85bbb40, "usb_autopm_put_interface" },
	{ 0xedbb867e, "usb_get_from_anchor" },
	{ 0x7f205eb3, "usb_kill_urb" },
	{ 0x8427cc7b, "_raw_spin_lock_irq" },
	{ 0x4b750f53, "_raw_spin_unlock_irq" },
	{ 0x860e4f25, "__tty_port_tty_hangup" },
	{ 0xe2964344, "__wake_up" },
	{ 0x83163ce9, "tty_port_put" },
	{ 0xc503c7ef, "usb_find_interface" },
	{ 0x6866aef5, "__tty_alloc_driver" },
	{ 0x67b27ec1, "tty_std_termios" },
	{ 0xba894eff, "tty_register_driver" },
	{ 0x72831666, "usb_register_driver" },
	{ 0x122c3a7e, "_printk" },
	{ 0x49960388, "tty_unregister_driver" },
	{ 0x1d3abece, "tty_driver_kref_put" },
	{ 0xe2ff1d1, "usb_autopm_get_interface" },
	{ 0xf0dad008, "usb_control_msg" },
	{ 0x580a70de, "kmalloc_caches" },
	{ 0xc70f4129, "kmalloc_trace" },
	{ 0x37a0cba, "kfree" },
	{ 0xeb233a45, "__kmalloc" },
	{ 0x88db9f48, "__check_object_size" },
	{ 0x13c49cc2, "_copy_from_user" },
	{ 0x6ebe366f, "ktime_get_mono_fast_ns" },
	{ 0x507cf598, "__dynamic_dev_dbg" },
	{ 0x4dfa8d4b, "mutex_lock" },
	{ 0x7665a95b, "idr_remove" },
	{ 0x3213f038, "mutex_unlock" },
	{ 0x9a262fce, "usb_put_intf" },
	{ 0x350b8193, "tty_port_tty_wakeup" },
	{ 0x4faef571, "tty_port_hangup" },
	{ 0x69acdf38, "memcpy" },
	{ 0xe3c97cae, "usb_autopm_get_interface_async" },
	{ 0x3f1ea8da, "usb_anchor_urb" },
	{ 0x2fda49c9, "module_layout" },
};

MODULE_INFO(depends, "");

MODULE_ALIAS("usb:v1A86p55D2d*dc*dsc*dp*ic*isc*ip*in*");
MODULE_ALIAS("usb:v1A86p55D3d*dc*dsc*dp*ic*isc*ip*in*");
MODULE_ALIAS("usb:v1A86p55D5d*dc*dsc*dp*ic*isc*ip*in*");
MODULE_ALIAS("usb:v1A86p55D6d*dc*dsc*dp*ic*isc*ip*in*");
MODULE_ALIAS("usb:v1A86p55DAd*dc*dsc*dp*ic*isc*ip*in*");
MODULE_ALIAS("usb:v1A86p55DBd*dc*dsc*dp*ic*isc*ip*in00*");
MODULE_ALIAS("usb:v1A86p55DDd*dc*dsc*dp*ic*isc*ip*in00*");
MODULE_ALIAS("usb:v1A86p55DEd*dc*dsc*dp*ic*isc*ip*in00*");
MODULE_ALIAS("usb:v1A86p55DEd*dc*dsc*dp*ic*isc*ip*in02*");
MODULE_ALIAS("usb:v1A86p55E7d*dc*dsc*dp*ic*isc*ip*in00*");
MODULE_ALIAS("usb:v1A86p55D8d*dc*dsc*dp*ic*isc*ip*in*");
MODULE_ALIAS("usb:v1A86p55D4d*dc*dsc*dp*ic*isc*ip*in*");
MODULE_ALIAS("usb:v1A86p55D7d*dc*dsc*dp*ic*isc*ip*in*");
MODULE_ALIAS("usb:v1A86p55DFd*dc*dsc*dp*ic*isc*ip*in*");

MODULE_INFO(srcversion, "B0F39AC8D1C2A1CA5A6AAB1");
