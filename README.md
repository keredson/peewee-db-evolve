<img src="https://cloud.githubusercontent.com/assets/2049665/17952702/c04e0846-6a32-11e6-8797-60ba50fc0fa6.png" style='width:100%'>


Peewee DB Evolve
================

Diffs your models against your database, and outputs SQL to (non-destructively) update your schema.

Think of it as `db.create_tables()` on steriods (which doesn't drop your database).

You can also think of it as schema migrations, without having to actually write the migrations.

Quick Start
-----------

1. Run: `sudo pip install git+git://github.com/keredson/peewee-db-evolve.git`
2. Add `import peeweedbevolve` anywhere before your models are defined.
3. Run `db.evolve()` where you would have normally run `db.create_tables()`, and enjoy!

Example
-------
See our [Hello World](https://github.com/keredson/peewee-db-evolve/tree/master/examples/hello_world) example.


Tests
-----

```bash
$ python test.py PostgreSQL
..............................
----------------------------------------------------------------------
Ran 30 tests in 22.421s

OK
```
