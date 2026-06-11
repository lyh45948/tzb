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
	{ 0xe625b147, "tty_port_close" },
	{ 0xe0b9267f, "tty_port_open" },
	{ 0xab72a771, "usb_deregister" },
	{ 0x8e17b3ae, "idr_destroy" },
	{ 0x2c8519e2, "usb_ifnum_to_if" },
	{ 0x8dd5f5cd, "usb_get_intf" },
	{ 0xb8f11603, "idr_alloc" },
	{ 0xd9a5ea54, "__init_waitqueue_head" },
	{ 0xcefb0c9f, "__mutex_init" },
	{ 0x91e0731c, "tty_port_init" },
	{ 0xadc91049, "usb_alloc_coherent" },
	{ 0x36b4c4a9, "usb_alloc_urb" },
	{ 0x49f1625f, "_dev_info" },
	{ 0xa19b3b24, "usb_register_dev" },
	{ 0xf10233d4, "usb_driver_claim_interface" },
	{ 0xb91b5ab7, "tty_port_register_device" },
	{ 0x60c6ce02, "usb_driver_release_interface" },
	{ 0xaa1e2649, "usb_free_urb" },
	{ 0x5fa01fe7, "usb_free_coherent" },
	{ 0xcd9c13a3, "tty_termios_hw_change" },
	{ 0xbd394d8, "tty_termios_baud_rate" },
	{ 0xf0fdf6cb, "__stack_chk_fail" },
	{ 0x7e13d21c, "__tty_insert_flip_string_flags" },
	{ 0xb0fac646, "tty_flip_buffer_push" },
	{ 0x20978fb9, "idr_find" },
	{ 0x296695f, "refcount_warn_saturate" },
	{ 0x715e3583, "seq_puts" },
	{ 0xe36ca58a, "seq_printf" },
	{ 0x656e4a6e, "snprintf" },
	{ 0x90b281a9, "seq_putc" },
	{ 0x76aafb08, "tty_standard_install" },
	{ 0x2d3385d3, "system_wq" },
	{ 0xf3b0231c, "queue_work_on" },
	{ 0x6b10bee1, "_copy_to_user" },
	{ 0xb2fd5ceb, "__put_user_4" },
	{ 0x167e7f9d, "__get_user_1" },
	{ 0x8f9c199c, "__get_user_2" },
	{ 0x89fb2eba, "pcpu_hot" },
	{ 0xaad8c7d6, "default_wake_function" },
	{ 0x4afb2238, "add_wait_queue" },
	{ 0x1000e51, "schedule" },
	{ 0x37110088, "remove_wait_queue" },
	{ 0xc6cbbc89, "capable" },
	{ 0xba3891d6, "usb_deregister_dev" },
	{ 0x220c8457, "tty_port_tty_get" },
	{ 0x9c57f4a5, "tty_vhangup" },
	{ 0x2f03dee0, "tty_kref_put" },
	{ 0x58abe7ff, "tty_unregister_device" },
	{ 0xbdfb6dbb, "__fentry__" },
	{ 0x34db050b, "_raw_spin_lock_irqsave" },
	{ 0xd35cce70, "_raw_spin_unlock_irqrestore" },
	{ 0x5b8239ca, "__x86_return_thunk" },
	{ 0x4a17477a, "usb_submit_urb" },
	{ 0xb146c5f9, "_dev_err" },
	{ 0xf8443ef1, "usb_autopm_put_interface_async" },
	{ 0xa0190cb5, "usb_autopm_get_interface_no_resume" },
	{ 0x692fd860, "usb_autopm_put_interface" },
	{ 0x7b281a3e, "usb_get_from_anchor" },
	{ 0xedc3759e, "usb_kill_urb" },
	{ 0x8427cc7b, "_raw_spin_lock_irq" },
	{ 0x4b750f53, "_raw_spin_unlock_irq" },
	{ 0x68d74e26, "__tty_port_tty_hangup" },
	{ 0xe2964344, "__wake_up" },
	{ 0x31eba472, "tty_port_put" },
	{ 0xc5244df2, "usb_find_interface" },
	{ 0x722fd5ea, "__tty_alloc_driver" },
	{ 0x67b27ec1, "tty_std_termios" },
	{ 0x69d5b7ee, "tty_register_driver" },
	{ 0x81c0f8c, "usb_register_driver" },
	{ 0x122c3a7e, "_printk" },
	{ 0x1c696ed, "tty_unregister_driver" },
	{ 0x1235e5f3, "tty_driver_kref_put" },
	{ 0x977c3dc1, "usb_autopm_get_interface" },
	{ 0x1000ede, "usb_control_msg" },
	{ 0xfb3c9cbd, "kmalloc_caches" },
	{ 0xfd475e8c, "kmalloc_trace" },
	{ 0x37a0cba, "kfree" },
	{ 0xeb233a45, "__kmalloc" },
	{ 0x88db9f48, "__check_object_size" },
	{ 0x13c49cc2, "_copy_from_user" },
	{ 0x6ebe366f, "ktime_get_mono_fast_ns" },
	{ 0x2cee49f3, "__dynamic_dev_dbg" },
	{ 0x4dfa8d4b, "mutex_lock" },
	{ 0x7665a95b, "idr_remove" },
	{ 0x3213f038, "mutex_unlock" },
	{ 0xd6801210, "usb_put_intf" },
	{ 0x51eb4c22, "tty_port_tty_wakeup" },
	{ 0x6acb12cc, "tty_port_hangup" },
	{ 0x69acdf38, "memcpy" },
	{ 0xacd24a83, "usb_autopm_get_interface_async" },
	{ 0x9cfe90b3, "usb_anchor_urb" },
	{ 0x9581586f, "module_layout" },
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
