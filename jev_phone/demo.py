"""Compatibility entry point; install jev-phone[demo] to use it."""
if __name__ == '__main__':
    from jev_phone_demo.app import main
    main()
else:
    import sys
    from jev_phone_demo import app as implementation
    sys.modules[__name__] = implementation
