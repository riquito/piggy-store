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

Try it with docker
------------------

You can try it locally using our docker image.
You'll need [packer](https://www.packer.io/), [docker](https://www.docker.com/) and [docker-compose](https://docs.docker.com/compose/)

If it's the first time that you build the image, build the base image

```
packer build -only piggy-store-base-image build/packer-templates/docker-piggy-store.json
```

Then you can build the proper piggy-store image

```
packer build -only docker-piggy-store build/packer-templates/docker-piggy-store.json
```

Run the project

```
docker-compose run
```

