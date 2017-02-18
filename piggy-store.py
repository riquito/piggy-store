#!/usr/bin/env python

from piggy_store.app import create_app

application = create_app()

if __name__ == "__main__":
    application.run(
    )
