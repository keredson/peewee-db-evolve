<img src="https://cloud.githubusercontent.com/assets/2049665/17952702/c04e0846-6a32-11e6-8797-60ba50fc0fa6.png" style='width:100%'>

[![Build Status](https://travis-ci.org/keredson/peewee-db-evolve.svg?branch=master)](https://travis-ci.org/keredson/peewee-db-evolve)

Peewee DB Evolve
================

Diffs your models against your database, and outputs SQL to (non-destructively) update your schema.

Think of it as `db.create_tables()` on steriods (which doesn't drop your database).

You can also think of it as schema migrations, without having to actually write the migrations.

Quick Start
-----------

1. Run: `sudo pip install peewee-db-evolve`
2. Add `import peeweedbevolve` anywhere before your models are defined.
3. Run `db.evolve()` where you would have normally run `db.create_tables()`, and enjoy!

Arguments
---------

 evolve(db, interactive=True, ignore_tables=None)

Example
-------
See our [Hello World](https://github.com/keredson/peewee-db-evolve/tree/master/examples/hello_world) example.

![image](https://cloud.githubusercontent.com/assets/2049665/17993037/1d1c8cf2-6b12-11e6-8591-cd11eb263938.png)


Supported Databases
-------------------

- PostgreSQL
- MySQL

Frequently Asked Questions
--------------------------

*Does this work with existing projects, or only with new projects?*

This works very well with existing projects.  If your API only works with new projects, you're probably doing it wrong.

*Don't you give up control by not writing your own migrations?*

Managing your schema by writing your own migrations is kind of like managing your source code by writing your own `patch` files in addition to writing your actual code.  A well vetted `diff` tool is going to be better and faster at it than you.

*How old / well vetted is this tool?*

This project has been in production use since August 2016.  (We switched to Peewee as an ORM.)  But it's a style of schema management I've been using for ~10 years now.

*How can I prevent `peewee-db-evolve` from evolving a specific table or class?*

In the class' `Meta` class, add `evolve = False` and `peewee-db-evolve` will ignore it.  If you don't have a class for a specific table, just make a do-nothing dummy class for it.  Or you can pass in any iterable into the `ignore_tables` kwarg of `evolve()`.

Tests
-----

How to run:

```bash
$ python3 test.py
..................................................................................................
----------------------------------------------------------------------
Ran 98 tests in 39.860s

OK
```

<img src="https://travis-ci.org/keredson/peewee-db-evolve.svg">
