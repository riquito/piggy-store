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
python piggy-store.py
```

or run the application with uwsgi

```
uwsgi --need-app --socket 0.0.0.0:5000 --protocol=http -w piggy-store --python-autoreload=1 
```

