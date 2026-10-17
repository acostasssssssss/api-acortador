ERROR:    Traceback (most recent call last):
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\starlette\routing.py", line 732, in lifespan
    async with self.lifespan_context(app) as maybe_state:
  File "C:\Users\carlos\AppData\Local\Programs\Python\Python312\Lib\contextlib.py", line 210, in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\app\main.py", line 22, in lifespan
    await init_db()
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\app\db\session.py", line 45, in init_db
    async with engine.begin() as conn:
  File "C:\Users\carlos\AppData\Local\Programs\Python\Python312\Lib\contextlib.py", line 210, in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\ext\asyncio\engine.py", line 1063, in begin
    async with conn:
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\ext\asyncio\base.py", line 121, in __aenter__
    return await self.start(is_ctxmanager=True)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\ext\asyncio\engine.py", line 273, in start
    await greenlet_spawn(self.sync_engine.connect)
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 190, in greenlet_spawn
    result = context.switch(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 3276, in connect
    return self._connection_cls(self)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 146, in __init__
    self._dbapi_connection = engine.raw_connection()
                             ^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\engine\base.py", line 3300, in raw_connection
    return self.pool.connect()
           ^^^^^^^^^^^^^^^^^^^
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\pool\base.py", line 449, in connect
    return _ConnectionFairy._checkout(self)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\pool\base.py", line 1263, in _checkout
    fairy = _ConnectionRecord.checkout(pool)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\pool\base.py", line 712, in checkout
    rec = pool._do_get()
          ^^^^^^^^^^^^^^
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\pool\impl.py", line 179, in _do_get
    with util.safe_reraise():
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\util\langhelpers.py", line 146, in __exit__
    raise exc_value.with_traceback(exc_tb)
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\pool\impl.py", line 177, in _do_get
    return self._create_connection()
           ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\pool\base.py", line 390, in _create_connection
    return _ConnectionRecord(self)
           ^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\pool\base.py", line 674, in __init__
    self.__connect()
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\pool\base.py", line 900, in __connect
    with util.safe_reraise():
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\util\langhelpers.py", line 146, in __exit__
    raise exc_value.with_traceback(exc_tb)
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\pool\base.py", line 896, in __connect
    self.dbapi_connection = connection = pool._invoke_creator(self)
                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\engine\create.py", line 643, in connect
    return dialect.connect(*cargs, **cparams)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\engine\default.py", line 620, in connect
    return self.loaded_dbapi.connect(*cargs, **cparams)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\carlos\Desktop\404-API-PY\API-ACORTADOR\BACKEND\venv\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 932, in connect
    await_only(creator_fn(*arg, **kw)),
               ^^^^^^^^^^^^^^^^^^^^^^
TypeError: connect() got an unexpected keyword argument 'sslmode'