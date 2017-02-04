Piggy-Store
===========

Store files easily

Install
-------

```
pip install -r requirements.lock
```

Run
---

You can either use flask directly

```
python -m piggy_store.app
```

or run the application with uwsgi

```
uwsgi --socket 0.0.0.0:9000 --protocol=http -w wsgi
```

