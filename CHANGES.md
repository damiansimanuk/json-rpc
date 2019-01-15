# 0.3 - 2018-11-28

* Implementing a custom handler should now be easier.
  We now provide a BasicJSONRPCHandler that implements all the crucial parts
  except overriding the desired HTTP verb functions and implementing how an
  RPC is actually processed.
  For easier overriding the processing functions have been split apart.
  The behaviour of JSONRPCHandler remains unchanged.
  You will find a full example in `examples/custom_handler.py`.

# 0.2 - 2018-11-19

* Use tornados json encoding / decoding.
* Added support for JSON-RPC 1.0.

# 0.1 - 2018-11-13

* Initial release.
* Support for JSON-RPC 2.0.
